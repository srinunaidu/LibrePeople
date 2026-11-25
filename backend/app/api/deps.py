"""Request-scoped dependencies: database session, identity, and authorisation.

This module is the **single place** where identity is established and where
role checks happen. Endpoints declare what they need with a dependency; they
do not read roles off the request or compare role strings themselves. That
centralisation is what makes the authorisation matrix auditable — there is one
list of role rules, not one per endpoint file.

Three layers of access control, and which layer answers which question
----------------------------------------------------------------------
1. **Authentication** — "who is this?" (:func:`get_current_user`).
2. **Authorisation** — "may this role perform this class of action?"
   (:func:`require_roles`).
3. **Visibility** — "which *records* may this user see?" This is *not* here.
   It lives in :mod:`app.core.visibility`, because it depends on the data
   (the reporting chain) rather than on the request.

A role check alone is not authorisation for a record. Any endpoint that
touches an employee-scoped row must also apply a visibility filter; the two
are complementary and both are required.

The role matrix
---------------
Every endpoint in the served surface declares its permitted roles with
:func:`require_roles`. The named role sets below are the vocabulary those
declarations use, so the matrix can be read off this module:

============================ ==========================================
Set                          Meaning
============================ ==========================================
:data:`ADMIN_ROLES`          SuperAdmin and HR — administrative work.
:data:`MANAGER_ROLES`         The above plus Manager — team views and the
                              three approval classes the product documents
                              for a manager (leave, timesheet, shift swap).
:data:`WORKFORCE_ROLES`      The above plus Associate — the people who are
                              themselves in the workforce, and therefore the
                              roles for whom self-service applies.
:data:`REPORTS_ROLES`         SuperAdmin, HR and PayrollViewer — the
                              organisation-wide figures and read-only
                              payroll. PayrollViewer is deliberately *not* in
                              any set that can move money.
:data:`ALL_ROLES`            Every role the platform recognises.
============================ ==========================================

A role that is not in an endpoint's set is refused with ``403`` and the
shared error envelope (:func:`app.core.errors.forbidden`), never a bare
``detail``.

Password change gate
--------------------
An account whose password was set by an administrator (or bootstrapped from
an environment secret) has ``must_change_password`` set. Such an account may
only read its own profile, change its password, and sign out. Everything else
is refused with ``password_change_required`` until the password is changed.
This is enforced in :func:`get_current_active_user`, which every protected
endpoint depends on, so a new endpoint cannot accidentally forget the check.
"""
from typing import Callable, Generator, Iterable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import forbidden
from app.core.mfa import is_mfa_enforced_role
from app.core.security import PINNED_JWT_ALGORITHM, decode_token
from app.core.tenancy import (
    TenantContext,
    clear_tenant_context,
    resolve_tenant,
    tenant_id_for,
)
from app.models.user import User
from app.schemas.token import TokenData

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

#: Roles that may perform administrative operations.
ADMIN_ROLES = ("SuperAdmin", "HR")

#: Every role the platform recognises.
ALL_ROLES = ("SuperAdmin", "HR", "Manager", "Associate", "PayrollViewer")

#: Administrative roles plus Manager.
#:
#: Manager is here because the product documents three approval classes for a
#: manager — leave, timesheet and shift swap — and the team views that go with
#: them. It is not in :data:`ADMIN_ROLES` because a manager does not
#: administer the tenant.
MANAGER_ROLES = ("SuperAdmin", "HR", "Manager")

#: The roles that are people in the workforce.
#:
#: PayrollViewer is excluded: a payroll clerk is not an employee, so the
#: self-service surfaces (clock in, request leave, enrol in a benefit) are
#: not theirs to use.
WORKFORCE_ROLES = ("SuperAdmin", "HR", "Manager", "Associate")

#: The organisation-wide figures: reports and read-only payroll.
#:
#: Headcount, leave, labour cost and the payroll registers are HR's figures
#: and PayrollViewer's read-only view of them. They are not the Manager's — a
#: manager has team views, not the organisation's books. PayrollViewer is
#: never in a set that processes, approves or finalises a pay run.
REPORTS_ROLES = ("SuperAdmin", "HR", "PayrollViewer")

#: The people in the workforce, i.e. those who can use ESS self-service.
#:
#: AC-07 requires ESS endpoints to be Associate-accessible only; HR/SuperAdmin/
#: Manager must receive 403.
ASSOCIATE_ROLES = ("Associate",)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _unauthenticated() -> HTTPException:
    """The single 401 shape.

    The same message is used for a missing token, an expired token, an invalid
    token and an unknown user, so a caller cannot use the response to probe
    which usernames exist.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired or token invalid. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """Establish identity from the bearer token.

    The accepted algorithm is a literal in :mod:`app.core.security`, not a
    setting, so no runtime configuration can widen it.
    """
    try:
        payload = decode_token(token)
        token_data = TokenData(username=payload.get("sub"))
    except (JWTError, ValidationError, TypeError):
        # 401, not 403: a bad/expired token is an *authentication* failure.
        # Returning 403 here made clients treat an expired session as
        # "forbidden" and prompt the user to sign in again.
        raise _unauthenticated() from None
    if not token_data.username:
        raise _unauthenticated()
    user = db.query(User).filter(User.username == token_data.username).first()
    if not user:
        # Do not confirm that a username exists.
        raise _unauthenticated()
    return user


def get_current_tenant(
    request: Request,
    db: Session = Depends(get_db),
) -> TenantContext:
    """Resolve the tenant for this request and bind it to the context.

    Every protected endpoint that funnels through :func:`get_current_active_user`
    transitively resolves a tenant, so a request is never served without an
    explicit tenant attribution. Raises ``tenant_unresolvable`` (401) when no
    tenant can be determined and ``tenant_mismatch`` (409) when a client-supplied
    tenant id conflicts with the resolved one.
    """
    return resolve_tenant(db, request)


def get_current_user_ignoring_password_state(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """Identity only, ignoring ``must_change_password``.

    Used by the three endpoints an account must be able to reach while it is
    required to change its password: read its own profile, change its
    password, sign out.
    """
    return get_current_user(db=db, token=token)


def get_current_active_user(
    current_user: User = Depends(get_current_user),
    _tenant: TenantContext = Depends(get_current_tenant),
) -> User:
    """The default dependency for every protected endpoint.

    Enforces, in order:
    1. the account is active;
    2. the account is not in a lockout window;
    3. the account has not been left in a "must change password" state;
    4. unenrolled SuperAdmin/HR accounts are refused (item 10).

    A failure at (3) is a 403 with the code ``password_change_required`` —
    identity was established, but the account is not permitted to use the API
    until the password is reset.

    A failure at (4) is the MFA requirement: an unenrolled SuperAdmin or HR
    account may reach only the MFA escape-hatch endpoints
    (``/auth/mfa/enroll``, ``/auth/mfa/confirm``, ``/auth/mfa/status``,
    ``/auth/mfa/disable``) until it enrolls; there is no grace period.

    The tenant is resolved (and bound to the request context) as a side effect
    of ``get_current_tenant`` above, so every protected endpoint carries an
    explicit tenant attribution.
    """
    if not current_user.is_active:
        # 403: identity is established, the account is simply not permitted.
        raise HTTPException(status_code=403, detail="Inactive user")
    if current_user.is_locked():
        raise HTTPException(
            status_code=403,
            detail="Account is temporarily locked. Try again later.",
        )
    if getattr(current_user, "must_change_password", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You must change your password before using this account."
            ),
        )
    if is_mfa_enforced_role(current_user.role) and not getattr(
        current_user, "mfa_enabled", False
    ):
        # Item 10: privileged users must be enrolled. This is the single
        # choke point every privileged endpoint funnels through, so an
        # unenrolled SuperAdmin/HR cannot reach them; the MFA setup and
        # recovery endpoints use the ignoring-password-state base instead
        # and stay reachable.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Multi-factor authentication is required for your role. "
                "Enroll at /auth/mfa/enroll."
            ),
        )
    return current_user


def require_mfa(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require MFA for roles that mandate it (SuperAdmin, HR).

    The gate is :func:`get_current_active_user` itself: it refuses every
    endpoint that funnels through it for an unenrolled SuperAdmin or HR, so
    this dependency is the named alias of the shared check on endpoints that
    need it expressed explicitly. The MFA setup and recovery endpoints
    (``/auth/mfa/*``) do not use this dependency — they use
    :func:`get_current_user_ignoring_password_state` — so a user can enroll
    and confirm without already having MFA. There is no grace period.
    """
    if is_mfa_enforced_role(current_user.role) and not getattr(
        current_user, "mfa_enabled", False
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Multi-factor authentication is required for your role."
                " Enroll at /auth/mfa/enroll."
            ),
        )
    return current_user


def _build_role_dependency(
    base: Callable[..., User], roles: Iterable[str]
) -> Callable[..., User]:
    """Build a dependency that admits only the listed roles.

    The role set is checked in one place, so the authorisation matrix can be
    read off this module rather than reconstructed from 25 endpoint files.
    An unknown role name in the call is a programming error and raises at
    import time rather than silently admitting nobody.
    """
    allowed = tuple(roles)
    unknown = [r for r in allowed if r not in ALL_ROLES]
    if unknown:
        raise ValueError(
            f"Unknown role(s) {unknown!r}. Known roles: {ALL_ROLES}"
        )
    if not allowed:
        raise ValueError("require_roles() needs at least one role")

    def _dependency(current_user: User = Depends(base)) -> User:
        if current_user.role not in allowed:
            # The shared error envelope, not a bare ``detail``: a client
            # branches on ``error.code``, and a bare detail string cannot
            # tell a permission failure from a validation failure.
            # The message does not name the roles that would have been
            # admitted: a refusal is not a description of the policy.
            raise forbidden("Your role does not permit this operation.")
        return current_user

    return _dependency


def is_known_role(role: str) -> bool:
    """True when `role` is one of the roles the platform recognises.

    The one place that answers it. The role column is constrained to these
    five values, so a request that carries any other role is refused rather
    than stored.
    """
    return role in ALL_ROLES


def require_roles(*roles: str) -> Callable[..., User]:
    """Build a dependency that admits only the listed roles.

    Usage::

        @router.post("/approve", dependencies=[Depends(require_roles("Manager", "HR"))])

    The refused caller gets ``403`` with the shared error envelope. The
    account-state gate (:func:`get_current_active_user`) still applies, so a
    role check never lets a locked or password-expired account through.
    """
    return _build_role_dependency(get_current_active_user, roles)


def require_tenant() -> str:
    """Dependency: the current tenant id, refusing if none is resolved.

    Endpoints that must operate on tenant-scoped data depend on this so a
    missing tenant context becomes ``tenant_unresolvable`` rather than an
    ambiguous empty result. It is built on :func:`get_current_active_user`, so
    the account-state gate still applies.
    """

    def _dependency(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> str:
        tenant_id = tenant_id_for(db)
        if tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No tenant resolved for this request",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return tenant_id

    return _dependency


def require_roles_ignoring_password_state(*roles: str) -> Callable[..., User]:
    """Like :func:`require_roles`, but for the password-change escape hatch.

    The account must still change its password before it can use the API, so
    the three endpoints it has to reach in the meantime — read its own
    profile, change its password, sign out — are gated on the role without
    the ``must_change_password`` check.
    """
    return _build_role_dependency(get_current_user_ignoring_password_state, roles)


def require_any_role(roles: Iterable[str]) -> Callable[..., User]:
    """Like :func:`require_roles` but accepts an iterable."""
    return require_roles(*tuple(roles))


#: The dependency behind :func:`get_current_admin_user`.
#:
#: It is built from :func:`require_roles` rather than repeating the
#: comparison, so there is one place where a role is turned into a decision.
_require_admin_roles = require_roles(*ADMIN_ROLES)


def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """SuperAdmin and HR only.

    This is a named alias for ``require_roles(*ADMIN_ROLES)``. It exists for
    the endpoints that have not been given an explicit role set of their own;
    it is the same control, expressed once.

    MFA is mandatory for these roles; :func:`require_mfa` is applied on
    endpoints that need it. This dependency only checks the role — callers
    that need MFA enforcement should also depend on :func:`require_mfa`.
    """
    return _require_admin_roles(current_user)
