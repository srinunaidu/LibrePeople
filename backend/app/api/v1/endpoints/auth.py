"""Authentication and account administration.

Security notes
--------------
* ``/login`` is rate limited per remote IP to blunt credential stuffing, and
  additionally locks the *account* after repeated failures.
* ``/register`` is public *only* when ``ALLOW_SELF_REGISTRATION`` is enabled
  (it defaults to off). It binds to ``UserSelfRegister``, which has no
  ``role``/``is_active`` field, and the row is additionally constructed with
  hard-coded least privilege. A caller cannot self-assign a privileged role.
* Privileged user creation lives on ``POST /auth/users`` (admins only).
* Passwords are checked against the policy in
  :mod:`app.core.password_policy`: length, local breach blocklist, reuse of
  the last N, and derivation from the account identity.
* A successful login transparently upgrades a legacy password hash to the
  current scheme.
* An account whose password was set by an administrator cannot use the API
  until it changes that password. The gate lives in
  :func:`app.api.deps.get_current_active_user`.
* Every refresh token is rotated on use. Presenting a rotated token revokes
  the whole token family.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.security import (
    create_access_token,
    get_password_hash,
    password_hash_needs_upgrade,
    verify_password,
)
from app.core.mfa import (
    MFAError,
    build_enrollment,
    is_mfa_enforced_role,
    totp_qr_data_uri,
    verify_recovery_code,
    verify_totp_code,
)
from app.core.rate_limit import limiter
from app.api.deps import (
    ADMIN_ROLES,
    ALL_ROLES,
    get_db,
    is_known_role,
    require_roles,
    require_roles_ignoring_password_state,
)
from app.core.audit import record_audit
from app.core.config import settings
from app.core.password_policy import check_password
from app.core.errors import ApiError, ErrorCategory, forbidden
from app.models.user import User
from app.models.refresh_token import (
    RefreshToken,
    build_token_pair,
    hash_token,
    revoke_all_for_user,
    revoke_family,
)
from app.schemas.user import (
    AdminPasswordSetRequest,
    LoginResponse,
    MFAConfirmRequest,
    MFADisableRequest,
    MFAEnrollResponse,
    MFAStatusResponse,
    PasswordChangeRequest,
    UserCreate,
    UserOut,
    UserSelfRegister,
    SELF_SERVICE_ROLE,
    VALID_ROLES,
)
from app.crud import crud_user

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateAdmin(BaseModel):
    """Privileged creation payload — never reachable from public signup."""

    user_in: UserCreate


class RefreshRequest(BaseModel):
    refresh_token: str


def _generic_login_failure() -> HTTPException:
    """Same response for unknown user and wrong password (no user enumeration)."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
    )


#: The role that administers the platform itself. Only a SuperAdmin may create
#: a SuperAdmin account, change any role to or from SuperAdmin, or set the
#: password of a SuperAdmin account. HR administers everyone else.
SUPERADMIN_ROLE = "SuperAdmin"


def _require_superadmin_to_manage(actor: User, target_role: str | None, new_role: str | None = None) -> None:
    """Refuse an HR (or other non-SuperAdmin) administrator touching SuperAdmin.

    Applies when the target account is a SuperAdmin, or when the change would
    make an account a SuperAdmin. The message does not describe the policy.
    """
    touches_superadmin = SUPERADMIN_ROLE in (target_role, new_role)
    if touches_superadmin and actor.role != SUPERADMIN_ROLE:
        raise forbidden("Your role does not permit this operation on a SuperAdmin account.")


def _lockout_seconds_remaining(user: User) -> int:
    until = user.locked_until
    if until is None:
        return 0
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    remaining = (until - datetime.now(timezone.utc)).total_seconds()
    return max(0, int(remaining))


def _register_failed_login(db: Session, user: User) -> bool:
    """Increment the per-account failure counter and lock when it is exceeded.

    Returns ``True`` when *this* attempt locked an account that was not
    already locked, so the caller can write the lockout event in the same
    transaction as the counter. The caller commits; this function stages.

    The lock is refreshed on every failed attempt past the threshold, exactly
    as before: the lockout window is the same. What changed is that the
    caller is told only about the transition, so the audit trail records one
    ``login_locked`` row per lock episode rather than one per attempt.
    """
    now = datetime.now(timezone.utc)
    locked_until = user.locked_until
    if locked_until is not None and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    was_locked = locked_until is not None and locked_until > now

    # Failures count inside one window. A failure after the window has closed
    # opens a new window, so an old failure cannot combine with a new one.
    window_start = user.failed_login_window_started_at
    if window_start is not None and window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=timezone.utc)
    window = timedelta(seconds=settings.LOGIN_FAILURE_WINDOW_SECONDS)
    if window_start is None or now - window_start > window:
        user.failed_login_count = 0
        user.failed_login_window_started_at = now

    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
        user.locked_until = now + timedelta(seconds=settings.LOGIN_LOCKOUT_SECONDS)
        return not was_locked
    return False


@router.post("/login", response_model=LoginResponse, operation_id="authLogin")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    # Brute-force throttling. Raises 429 when the budget for this IP is spent.
    limiter.check("login", request, client_ip(request))

    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        # Spend the IP budget even for an unknown username, so that probing
        # usernames is as expensive as guessing passwords. The event is
        # audited, but the attempted username is not written: the row must
        # not turn the trail into a list of the names someone tried. The
        # caller still gets the same generic response.
        limiter.record_failure("login", client_ip(request))
        record_audit(db, None, "login_failed", "User", None, details="unknown_username")
        db.commit()
        raise _generic_login_failure()

    if not verify_password(payload.password, user.hashed_password):
        locked_now = _register_failed_login(db, user)
        limiter.record_failure("login", client_ip(request))
        record_audit(
            db,
            user,
            "login_failed",
            "User",
            user.id,
            details="invalid_credentials",
        )
        if locked_now:
            # The transition into lockout is an event of its own: an operator
            # investigating a lockout needs the moment it happened, not only
            # the attempts that followed it.
            record_audit(
                db,
                user,
                "login_locked",
                "User",
                user.id,
                details=f"failed_attempts={user.failed_login_count}",
            )
        db.commit()
        raise _generic_login_failure()

    # The password is correct, so the account exists and it is safe to say so.
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    if user.is_locked():
        remaining = _lockout_seconds_remaining(user)
        record_audit(
            db,
            user,
            "login_blocked_locked",
            "User",
            user.id,
            details=f"retry_after_seconds={remaining}",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This account is temporarily locked after repeated failed "
                "sign-in attempts. Try again later."
            ),
            headers={"Retry-After": str(remaining)},
        )

    # Successful sign-in: clear the counters and transparently upgrade a
    # legacy password hash to the current scheme.
    #
    # The IP budget is reset here as well. `limiter.check` counts every
    # attempt, so without a reset a user who signs in normally more than
    # `LOGIN_RATE_LIMIT_ATTEMPTS` times in a window would be locked out by
    # the brute-force control.
    limiter.reset("login", client_ip(request))
    user.failed_login_count = 0
    user.failed_login_window_started_at = None
    user.locked_until = None
    if password_hash_needs_upgrade(user.hashed_password):
        user.hashed_password = get_password_hash(payload.password)

    pair = build_token_pair(db, user, request=request)
    record_audit(db, user, "login", "User", user.id)
    db.commit()
    return pair


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, operation_id="authCreateAuthregister")
def register(
    user_in: UserSelfRegister,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Self-service signup.

    Intentionally does *not* accept a role. Anyone hitting this endpoint gets
    the least-privileged role regardless of what they send in the request body.
    """
    if not settings.ALLOW_SELF_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Self-service registration is disabled. "
                "Ask an administrator to provision your account."
            ),
        )

    limiter.check("register", request, client_ip(request))

    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # The schema validator enforces a basic shape; the full policy (blocklist,
    # identity derivation) is applied here so every creation path gets it.
    check_password(
        user_in.password,
        username=user_in.username,
        email=user_in.email,
        min_length=settings.PASSWORD_MIN_LENGTH,
    ).raise_if_failed()

    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        # Hard-coded least privilege — never taken from the request.
        role=SELF_SERVICE_ROLE,
        is_active=True,
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    record_audit(db, db_user, "self_register", "User", db_user.id)
    db.commit()
    return UserOut.from_user(db_user)


# --------------------------------------------------------------------------
# Session lifecycle
# --------------------------------------------------------------------------


@router.post("/refresh", operation_id="authRefresh")
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Exchange a refresh token for a new access/refresh pair.

    The presented token is rotated. Presenting a token that has already been
    rotated is treated as a compromise signal: the entire token family is
    revoked, which ends every session descended from that login.
    """
    now = datetime.now(timezone.utc)
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_token(payload.refresh_token))
        .first()
    )
    if row is None:
        raise ApiError(
            "refresh_token_invalid",
            "Your session has expired. Please sign in again.",
            ErrorCategory.AUTH,
        )

    if row.rotated_at is not None:
        # Reuse of an already-rotated token.
        revoke_family(db, row.family_id, "reuse_detected")
        record_audit(
            db,
            db.query(User).filter(User.id == row.user_id).first(),
            "refresh_token_reuse",
            "RefreshToken",
            row.id,
            details="family_revoked",
        )
        db.commit()
        raise ApiError(
            "refresh_token_reused",
            "This session was ended for security reasons. Please sign in again.",
            ErrorCategory.AUTH,
        )

    if row.revoked_at is not None:
        raise ApiError(
            "refresh_token_invalid",
            "Your session has expired. Please sign in again.",
            ErrorCategory.AUTH,
        )

    expires = row.expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires is not None and expires <= now:
        row.revoke("expired")
        db.commit()
        raise ApiError(
            "refresh_token_invalid",
            "Your session has expired. Please sign in again.",
            ErrorCategory.AUTH,
        )

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None or not user.is_active:
        revoke_family(db, row.family_id, "user_inactive")
        db.commit()
        raise ApiError(
            "refresh_token_invalid",
            "Your session has expired. Please sign in again.",
            ErrorCategory.AUTH,
        )

    # Rotate: revoke the presented token, issue a new one in the same family.
    row.rotated_at = now
    row.revoke("rotated")
    pair = build_token_pair(db, user, request=request, family_id=row.family_id)
    record_audit(db, user, "refresh_token_rotated", "User", user.id)
    db.commit()
    return pair


@router.post("/logout", operation_id="authLogout")
def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_ignoring_password_state(*ALL_ROLES)),
) -> Any:
    """Revoke the presented refresh token and its family."""
    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_token(payload.refresh_token))
        .first()
    )
    if row is not None and row.user_id == current_user.id:
        revoke_family(db, row.family_id, "logout")
    record_audit(db, current_user, "logout", "User", current_user.id)
    db.commit()
    return {"status": "signed_out"}


@router.get("/me", response_model=UserOut, operation_id="authGetMe")
def me(
    current_user: User = Depends(require_roles_ignoring_password_state(*ALL_ROLES)),
) -> Any:
    """The signed-in user's own profile.

    Deliberately reachable while a password change is outstanding, so the
    client can render the "set a new password" screen.
    """
    return UserOut.from_user(current_user)


# --------------------------------------------------------------------------
# Multi-factor authentication
# --------------------------------------------------------------------------


@router.get("/mfa/status", response_model=MFAStatusResponse, operation_id="authListAuthmfastatus")
def mfa_status(
    current_user: User = Depends(require_roles_ignoring_password_state(*ALL_ROLES)),
) -> Any:
    """Whether MFA is enabled for the current account."""
    return MFAStatusResponse(
        mfa_enabled=bool(current_user.mfa_enabled),
        mfa_enrolled_at=current_user.mfa_enrolled_at,
    )


@router.post("/mfa/enroll", response_model=MFAEnrollResponse, operation_id="authEnrollMfa")
def mfa_enroll(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_ignoring_password_state(*ALL_ROLES)),
) -> Any:
    """Begin MFA enrollment.

    Generates a TOTP secret and recovery codes. The TOTP secret is encrypted
    at rest (never stored in plaintext) and the recovery codes are bcrypt
    hashed. The secret and recovery codes are returned exactly once; the
    caller must confirm enrollment with :func:`mfa_confirm` before MFA takes
    effect.
    """
    from app.core.security import encrypt_secret

    if current_user.mfa_enabled:
        raise ApiError(
            "mfa_already_enabled",
            "MFA is already enabled for this account.",
            ErrorCategory.CONFLICT,
        )

    package = build_enrollment(current_user.username)

    # Persist the encrypted TOTP secret and recovery code hashes, but do not
    # enable MFA yet — confirmation is required.
    current_user.mfa_secret_hash = encrypt_secret(package["secret"])
    current_user.recovery_codes_hash = __import__("json").dumps(
        package["recovery_code_hashes"]
    )
    db.commit()

    record_audit(
        db,
        current_user,
        "mfa_enroll_started",
        "User",
        current_user.id,
    )
    db.commit()

    return MFAEnrollResponse(
        provisioning_uri=package["provisioning_uri"],
        recovery_codes=package["recovery_codes"],
        qr_code_data_uri=totp_qr_data_uri(package["provisioning_uri"]),
    )


@router.post("/mfa/confirm", operation_id="authConfirmMfa")
def mfa_confirm(
    payload: MFAConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_ignoring_password_state(*ALL_ROLES)),
) -> Any:
    """Confirm MFA enrollment with a TOTP code.

    Decrypts the stored TOTP secret, verifies the code, and enables MFA.
    On success, MFA is required for privileged operations on the next
    request.
    """
    from app.core.security import decrypt_secret

    if not current_user.mfa_secret_hash:
        raise ApiError(
            "mfa_not_enrolled",
            "MFA enrollment has not been started. Call POST /auth/mfa/enroll first.",
            ErrorCategory.CONFLICT,
        )

    try:
        secret = decrypt_secret(current_user.mfa_secret_hash)
    except Exception:  # noqa: BLE001
        raise ApiError(
            "mfa_secret_unreadable",
            "The stored TOTP secret could not be read. Re-enroll.",
            ErrorCategory.DEPENDENCY,
        )

    if not verify_totp_code(secret, payload.totp_code):
        record_audit(
            db,
            current_user,
            "mfa_confirm_failed",
            "User",
            current_user.id,
        )
        db.commit()
        raise ApiError(
            "mfa_invalid_code",
            "Invalid TOTP code.",
            ErrorCategory.PERMISSION,
        )

    current_user.mfa_enabled = True
    current_user.mfa_enrolled_at = datetime.now(timezone.utc)

    record_audit(
        db,
        current_user,
        "mfa_enabled",
        "User",
        current_user.id,
    )
    db.commit()

    return {"status": "mfa_enabled"}


@router.post("/mfa/disable", operation_id="authDisableMfa")
def mfa_disable(
    payload: MFADisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_ignoring_password_state(*ALL_ROLES)),
) -> Any:
    """Disable MFA for the current account.

    Requires either the current password or a single-use recovery code.
    Disabling MFA revokes all existing sessions for the account.
    """
    if not current_user.mfa_enabled:
        raise ApiError(
            "mfa_not_enabled",
            "MFA is not enabled for this account.",
            ErrorCategory.CONFLICT,
        )

    authorized = False

    if payload.password and verify_password(
        payload.password, current_user.hashed_password
    ):
        authorized = True

    if not authorized and payload.recovery_code:
        code_hashes = current_user.recovery_code_hashes()
        consumed = False
        remaining: list[str] = []
        for h in code_hashes:
            if not consumed and verify_recovery_code(payload.recovery_code, [h]):
                consumed = True
                continue
            remaining.append(h)
        if consumed:
            authorized = True
            current_user.recovery_codes_hash = (
                __import__("json").dumps(remaining) if remaining else None
            )

    if not authorized:
        raise ApiError(
            "mfa_disable_unauthorized",
            "Invalid password or recovery code.",
            ErrorCategory.PERMISSION,
        )

    current_user.mfa_enabled = False
    current_user.mfa_secret_hash = None
    current_user.mfa_enrolled_at = None
    current_user.recovery_codes_hash = None

    revoke_all_for_user(db, current_user.id, "mfa_disabled")
    record_audit(
        db,
        current_user,
        "mfa_disabled",
        "User",
        current_user.id,
    )
    db.commit()

    return {"status": "mfa_disabled"}


class MFAResetRequest(BaseModel):
    """Administrator reset of another account's MFA enrollment.

    The target is identified by id or username. Step-up proof is the
    actor's current password AND a current TOTP code — both are required.
    Either field may be omitted by the caller, but a call that does not
    prove both fails closed with 403.
    """

    target_user_id: int | None = None
    target_username: str | None = None
    current_password: str | None = None
    totp_code: str | None = None


@router.post("/mfa/reset", operation_id="authResetMfa")
def admin_mfa_reset(
    payload: MFAResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    """Reset another account's MFA enrollment (SuperAdmin only, audited).

    Clears the target's MFA state (``mfa_enabled``, the encrypted TOTP
    secret, recovery-code hashes, enrollment timestamp) and revokes all of
    the target's sessions, so a lost authenticator stops working
    immediately. The target re-enrolls through the existing self-service
    flow (``POST /auth/mfa/enroll`` then ``POST /auth/mfa/confirm``);
    this endpoint never returns secrets.

    Step-up: the actor must prove BOTH the current password AND a current
    TOTP code on every call. A password alone, a TOTP code alone, or
    neither fails closed with 403 ``step_up_required`` and a
    ``mfa_reset_blocked`` audit row that carries no secrets.

    Guards (strict defaults):

    * SuperAdmin only — HR (and every other role) is refused by the role
      gate before any logic runs.
    * No self-reset — an actor cannot reset their own MFA; a second
      SuperAdmin is required. Refused with 403 ``self_reset_not_allowed``.
    * No break-glass bypass — a break-glass grant never authorizes this
      endpoint; only a direct SuperAdmin bearer does.
    * No secrets in the audit trail — neither the success row
      (``mfa_reset``) nor the blocked row (``mfa_reset_blocked``) carries
      a password or TOTP code.

    OPEN (owner decision required): when ALL SuperAdmin accounts have lost
    MFA at once, no second SuperAdmin exists to perform this reset. The
    recovery procedure for that situation is deliberately NOT defined
    here — inventing an offline bypass would defeat the step-up control.
    The platform owner must decide and document it out of band.
    """
    if not actor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    # Brute-force throttling shares the login IP budget: every attempt here
    # spends it, so password-guessing against step-up is as expensive as
    # guessing at /login. The trusted client address is the key, so rotating
    # X-Forwarded-For from an untrusted peer cannot evade it.
    limiter.check("login", request, client_ip(request))

    # Step-up: BOTH factors required. Checked after the throttle so a caller
    # without step-up cannot probe which usernames exist.
    _step_up_ok = False
    if payload.current_password and verify_password(
        payload.current_password, actor.hashed_password
    ):
        if actor.mfa_enabled and payload.totp_code:
            from app.core.security import decrypt_secret

            try:
                _secret = decrypt_secret(actor.mfa_secret_hash)
            except Exception:  # noqa: BLE001
                _secret = None
            if _secret and verify_totp_code(_secret, payload.totp_code):
                _step_up_ok = True
    if not _step_up_ok:
        # Every failed step-up counts toward the per-account lockout, exactly
        # like a failed /login password: five failures in the window lock the
        # account, and the transition is audited as its own event.
        locked_now = _register_failed_login(db, actor)
        limiter.record_failure("login", client_ip(request))
        record_audit(
            db,
            actor,
            "mfa_reset_blocked",
            "User",
            actor.id,
            details=(
                f"actor={actor.username} actor_id={actor.id} "
                "reason=step_up_required"
            ),
        )
        if locked_now:
            record_audit(
                db,
                actor,
                "login_locked",
                "User",
                actor.id,
                details=f"failed_attempts={actor.failed_login_count}",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="step_up_required"
        )

    target: User | None = None
    if payload.target_user_id is not None:
        target = db.query(User).filter(User.id == payload.target_user_id).first()
    elif payload.target_username:
        target = db.query(User).filter(User.username == payload.target_username).first()
    else:
        raise HTTPException(
            status_code=400, detail="Provide target_user_id or target_username"
        )

    if target is None:
        raise HTTPException(status_code=404, detail="Target user not found")

    if target.id == actor.id:
        record_audit(
            db,
            actor,
            "mfa_reset_blocked",
            "User",
            actor.id,
            details=(
                f"actor={actor.username} actor_id={actor.id} "
                "reason=self_reset_not_allowed"
            ),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="self_reset_not_allowed",
        )

    if not target.mfa_enabled:
        raise ApiError(
            "mfa_not_enabled",
            "MFA is not enabled for the target account.",
            ErrorCategory.CONFLICT,
        )

    target.mfa_enabled = False
    target.mfa_secret_hash = None
    target.mfa_enrolled_at = None
    target.recovery_codes_hash = None

    # Step-up succeeded: the actor proved who they are, so the per-account
    # failure counters clear. The IP budget is deliberately NOT reset here —
    # unlike /login, a success does not refund the throttle.
    actor.failed_login_count = 0
    actor.failed_login_window_started_at = None
    actor.locked_until = None

    revoke_all_for_user(db, target.id, "mfa_reset_by_admin")
    record_audit(
        db,
        actor,
        "mfa_reset",
        "User",
        target.id,
        details=(
            f"target={target.username} target_id={target.id} "
            f"by={actor.username} actor_id={actor.id}"
        ),
    )
    db.commit()

    return {"status": "mfa_reset", "target_username": target.username}


# --------------------------------------------------------------------------
# Password management
# --------------------------------------------------------------------------


@router.post("/password", operation_id="authChangePassword")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles_ignoring_password_state(*ALL_ROLES)),
) -> Any:
    """Change your own password.

    Requires the current password, applies the full policy, and ends every
    other session for the account. The caller receives a fresh token pair
    because the old ones are revoked.
    """
    if not verify_password(payload.current_password, current_user.hashed_password):
        record_audit(
            db,
            current_user,
            "password_change_failed",
            "User",
            current_user.id,
            details="current_password_incorrect",
        )
        db.commit()
        raise ApiError(
            "invalid_credentials",
            "Your current password is incorrect.",
            ErrorCategory.AUTH,
        )

    check_password(
        payload.new_password,
        username=current_user.username,
        email=current_user.email,
        history_hashes=current_user.password_history_hashes(),
        min_length=settings.PASSWORD_MIN_LENGTH,
    ).raise_if_failed()

    new_hash = get_password_hash(payload.new_password)
    current_user.record_password_change(
        new_hash, history_depth=settings.PASSWORD_HISTORY_DEPTH
    )
    # Every existing session for this account ends here.
    revoke_all_for_user(db, current_user.id, "password_changed")

    record_audit(db, current_user, "password_change", "User", current_user.id)
    db.commit()

    pair = build_token_pair(db, current_user, request=request)
    db.commit()
    return pair


@router.post("/users/{user_id}/password", operation_id="authSetUserPassword")
def admin_set_password(
    user_id: int,
    payload: AdminPasswordSetRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Set another user's password (administrators only).

    The account is left in a ``must_change_password`` state so the user
    replaces the administrator-chosen password at first sign-in. Every session
    for that account is revoked.
    """
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    _require_superadmin_to_manage(actor, target.role)

    check_password(
        payload.new_password,
        username=target.username,
        email=target.email,
        history_hashes=target.password_history_hashes(),
        min_length=settings.PASSWORD_MIN_LENGTH,
    ).raise_if_failed()

    new_hash = get_password_hash(payload.new_password)
    previous_hash = target.hashed_password
    target.hashed_password = new_hash
    target.must_change_password = True
    target.password_changed_at = datetime.now(timezone.utc)
    target.failed_login_count = 0
    target.locked_until = None
    if previous_hash:
        import json

        history = target.password_history_hashes()
        history.insert(0, previous_hash)
        target.password_history = json.dumps(
            history[: settings.PASSWORD_HISTORY_DEPTH]
        )

    revoke_all_for_user(db, target.id, "password_reset_by_admin")
    record_audit(
        db,
        actor,
        "admin_password_reset",
        "User",
        target.id,
    )
    db.commit()
    return {"status": "password_set", "must_change_password": True}


# --------------------------------------------------------------------------
# Privileged user administration (admins only)
# --------------------------------------------------------------------------


class UserUpdateAdmin(BaseModel):
    """Administrative change to an existing account.

    Every field is optional; only the ones supplied are changed.
    """

    email: str | None = None
    role: str | None = None
    is_active: bool | None = None


@router.patch("/users/{user_id}", response_model=UserOut, operation_id="authUpdateUser")
def update_user(
    user_id: int,
    payload: UserUpdateAdmin,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Change a user's role, email address or active state.

    Deactivating an account revokes every live session for it, so a
    deactivation takes effect immediately rather than when the session
    happens to expire.
    """
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Every PATCH on a SuperAdmin target requires a SuperAdmin actor — not
    # just role changes. An email-only or deactivate-only PATCH on a
    # SuperAdmin account is gated here too.
    _require_superadmin_to_manage(actor, target.role, payload.role)

    original_role = target.role
    original_is_active = bool(target.is_active)

    if payload.is_active is False and target.id == actor.id:
        # Deactivating your own account would leave nobody able to undo it.
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account.",
        )

    if payload.role is not None:
        if not is_known_role(payload.role):
            raise HTTPException(
                status_code=422,
                detail=f"role must be one of {', '.join(VALID_ROLES)}",
            )
        target.role = payload.role

    if payload.email is not None:
        target.email = payload.email

    deactivated = payload.is_active is False
    if payload.is_active is not None:
        target.is_active = payload.is_active

    # Never leave the platform without an active SuperAdmin: refuse to
    # demote or deactivate the last one. Checked before commit so the
    # refused change is never persisted.
    removes_last_superadmin = (
        original_role == SUPERADMIN_ROLE
        and original_is_active
        and (
            (payload.role is not None and payload.role != SUPERADMIN_ROLE)
            or deactivated
        )
    )
    if removes_last_superadmin:
        remaining = (
            db.query(User)
            .filter(
                User.role == SUPERADMIN_ROLE,
                User.is_active == True,  # noqa: E712
                User.id != target.id,
            )
            .count()
        )
        if remaining == 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last active SuperAdmin account.",
            )

    if deactivated:
        revoke_all_for_user(db, target.id, "account_deactivated")
        target.failed_login_count = 0
        target.locked_until = None

    record_audit(
        db,
        actor,
        "update_user",
        "User",
        target.id,
        details=(
            f"role={target.role} is_active={target.is_active}"
            + (" (deactivated)" if deactivated else "")
        ),
    )
    db.commit()
    db.refresh(target)
    return UserOut.from_user(target)


@router.get("/users", response_model=list[UserOut], operation_id="authListUsers")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    return [UserOut.from_user(u) for u in db.query(User).order_by(User.id).all()]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED, operation_id="authCreateUser")
def create_user(
    payload: UserCreateAdmin,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Create a user with an explicit role. Administrator-only.

    Only a SuperAdmin may create a SuperAdmin account.
    """
    user_in = payload.user_in
    _require_superadmin_to_manage(actor, None, user_in.role)
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    check_password(
        user_in.password,
        username=user_in.username,
        email=user_in.email,
        min_length=settings.PASSWORD_MIN_LENGTH,
    ).raise_if_failed()

    db_user = crud_user.create_user(db, user_in)
    db_user.password_changed_at = datetime.now(timezone.utc)
    db.commit()
    record_audit(
        db,
        actor,
        "create_user",
        "User",
        db_user.id,
        details=f"role={db_user.role}",
    )
    db.commit()
    return UserOut.from_user(db_user)


# --------------------------------------------------------------------------
# SuperAdmin sudo impersonation ("View as person")
# --------------------------------------------------------------------------


class ImpersonateRequest(BaseModel):
    target_user_id: int | None = None
    target_username: str | None = None
    # Step-up proof that the actor re-authenticated for this sensitive
    # action. Either the actor's current password, or — for MFA-enabled
    # actors — a current TOTP code. Both are optional fields so that a
    # caller that supplies neither fails closed with 403 below.
    current_password: str | None = None
    totp_code: str | None = None


class ImpersonateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
    impersonated_by: UserOut


@router.post("/impersonate", response_model=ImpersonateResponse, operation_id="authImpersonate")
def impersonate(
    payload: ImpersonateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("SuperAdmin")),
) -> Any:
    """Impersonate another user (SuperAdmin only, audited).

    Creates a short-lived JWT for the target user with extra claims
    ``is_impersonation`` and ``impersonated_by``. The token is otherwise a
    normal access token — the bearer is seen by the system as the target
    user. Every call is written to the audit trail so an operator can answer
    "who viewed as whom, and when".

    Step-up: the actor must re-authenticate on every call — either the
    current password, or (for MFA-enabled actors) a current TOTP code —
    before the target is looked up. Without valid proof the call fails
    with 403 ``step_up_required`` and an ``impersonate_blocked`` audit row.
    """
    if not actor.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    # Brute-force throttling shares the login IP budget: every impersonation
    # attempt spends it, so password-guessing against step-up is as expensive
    # as guessing at /login. The trusted client address is the key, so
    # rotating X-Forwarded-For from an untrusted peer cannot evade it.
    limiter.check("login", request, client_ip(request))

    # Step-up: the actor must re-prove who they are for this sensitive
    # action, before any target lookup. A correct current password passes
    # on its own; otherwise an MFA-enabled actor may present a current
    # TOTP code verified against the stored (encrypted) secret. Anything
    # else fails closed — the response and the audit row carry only the
    # fixed code ``step_up_required``, never the supplied secrets.
    _step_up_ok = False
    if payload.current_password and verify_password(
        payload.current_password, actor.hashed_password
    ):
        _step_up_ok = True
    elif actor.mfa_enabled and payload.totp_code:
        from app.core.security import decrypt_secret

        try:
            _secret = decrypt_secret(actor.mfa_secret_hash)
        except Exception:  # noqa: BLE001
            _secret = None
        if _secret and verify_totp_code(_secret, payload.totp_code):
            _step_up_ok = True
    if not _step_up_ok:
        # Every failed step-up counts toward the per-account lockout, exactly
        # like a failed /login password: five failures in the window lock the
        # account, and the transition is audited as its own event.
        locked_now = _register_failed_login(db, actor)
        limiter.record_failure("login", client_ip(request))
        record_audit(
            db,
            actor,
            "impersonate_blocked",
            "User",
            actor.id,
            details=(
                f"actor={actor.username} actor_id={actor.id} "
                "reason=step_up_required"
            ),
        )
        if locked_now:
            record_audit(
                db,
                actor,
                "login_locked",
                "User",
                actor.id,
                details=f"failed_attempts={actor.failed_login_count}",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="step_up_required"
        )

    target: User | None = None
    if payload.target_user_id is not None:
        target = db.query(User).filter(User.id == payload.target_user_id).first()
    elif payload.target_username:
        target = db.query(User).filter(User.username == payload.target_username).first()
    else:
        raise HTTPException(status_code=400, detail="Provide target_user_id or target_username")

    if target is None:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Short-lived token — same window as a normal login (30m by default).
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_in = int(expires_delta.total_seconds())

    access_token = create_access_token(
        subject=target.username,
        expires_delta=expires_delta,
        extra_claims={
            "is_impersonation": True,
            "impersonated_by": actor.id,
            "impersonated_by_username": actor.username,
            "orig_role": actor.role,
        },
    )

    # Step-up succeeded: the actor proved who they are, so the per-account
    # failure counters clear. The IP budget is deliberately NOT reset here —
    # unlike /login, a success does not refund the throttle.
    actor.failed_login_count = 0
    actor.failed_login_window_started_at = None
    actor.locked_until = None

    record_audit(
        db,
        actor,
        "impersonate",
        "User",
        target.id,
        details=f"impersonated_as={target.username} target_role={target.role} target_id={target.id} by={actor.username} actor_id={actor.id}",
    )
    # Also log as impersonate_begin for break-glass-style trail consumers.
    import logging as _logging

    _logging.getLogger("karmathy.auth").info(
        "impersonate actor=%s (%s) -> target=%s (%s)",
        actor.username,
        actor.id,
        target.username,
        target.id,
    )
    db.commit()

    return ImpersonateResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserOut.from_user(target),
        impersonated_by=UserOut.from_user(actor),
    )


def client_ip(request: Request) -> str:
    """The client address. Forwarded headers are believed only from a trusted proxy.

    See :mod:`app.core.trusted_proxy`. The per-IP login limiter is keyed on this
    value, so a client cannot defeat it by rotating ``X-Forwarded-For``.
    """
    from app.core.trusted_proxy import client_ip as _trusted_client_ip

    return _trusted_client_ip(request)
