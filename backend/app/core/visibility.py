"""Object-level data visibility.

Role checks answer *"may this user perform this class of action?"*. They do
not answer *"which records may this user see?"* — the audit found a
lowest-privilege `Associate` able to read the entire employee directory, every
colleague's leave and termination records, offers, and the whole audit trail.

This module supplies the missing half: given a `User`, which employee records
may they read?

Policy
------
``SuperAdmin``, ``HR``
    Every employee record.
``PayrollViewer``
    Every employee record — running payroll legitimately requires org-wide
    visibility. They are still denied *actions* outside payroll.
``Manager``
    Themselves plus their reporting line, walked transitively so multi-level
    management works. Loop-protected: a cycle in ``manager_id`` cannot hang
    the request.
``Associate``
    Themselves only.

Design notes
------------
* Resolution returns ``None`` to mean "unrestricted" rather than materialising
  a large id set, so the common HR path adds no filter at all.
* ``MAX_DEPTH`` and the visited-set both bound the work, so a corrupt
  reporting chain cannot turn into an unbounded query.
* A user with no linked employee (``User.employee_id is None``) and no
  privileged role sees nothing rather than everything. Failing closed is the
  only safe default for a missing link.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.tenancy import (
    current_tenant_id,
    tenant_column_criterion,
    tenant_id_for,
)
from app.models.employee import Employee
from app.models.user import User

#: Roles that may see every employee record.
GLOBAL_ROLES = ("SuperAdmin", "HR", "PayrollViewer")

#: Guard against a pathological (or maliciously edited) reporting chain.
MAX_DEPTH = 12


def _all_employee_ids(db: Session) -> set[int]:
    return {row[0] for row in db.query(Employee.id).all()}


def resolve_visible_employee_ids(db: Session, user: User) -> set[int] | None:
    """Return the employee ids this user may read, or ``None`` for unrestricted."""
    if user.role in GLOBAL_ROLES:
        return None

    # An unprivileged user with no employee link cannot be scoped to anything.
    # Deny by default rather than leaking the directory.
    if not user.employee_id:
        return set()

    visible: set[int] = {user.employee_id}
    frontier = {user.employee_id}
    depth = 0

    while frontier and depth < MAX_DEPTH:
        rows = (
            db.query(Employee.id)
            .filter(Employee.manager_id.in_(frontier))
            .all()
        )
        nxt = {r[0] for r in rows} - visible
        if not nxt:
            break
        visible |= nxt
        frontier = nxt
        depth += 1

    return visible


def visible_employee_id_filter(user: User) -> set[int] | None:
    """Like :func:`resolve_visible_employee_ids` for a user with no session.

    Provided for callers that already hold the resolved set. Prefer
    :func:`resolve_visible_employee_ids` when a session is available.
    """
    if user.role in GLOBAL_ROLES:
        return None
    return {user.employee_id} if user.employee_id else set()


def ensure_manages_direct_report(
    db: Session, user: User, employee_id: int | None
) -> None:
    """Raise unless `user` manages `employee_id` directly.

    Used where a manager acts *for* someone (creating a goal). The reporting
    chain is not enough here: a manager may act for direct reports only, and
    the default is to refuse a manager acting for their own record. SuperAdmin
    and HR are unrestricted. Refusing your own record is an OPEN product
    decision (see the Phase 2 report) and is the default until confirmed.
    """
    if employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="employee_id is required",
        )
    if user.role in GLOBAL_ROLES:
        return
    if user.employee_id and employee_id == user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot act on your own record in this way.",
        )
    if user.employee_id:
        direct = (
            db.query(Employee.id)
            .filter(Employee.id == employee_id, Employee.manager_id == user.employee_id)
            .first()
        )
        if direct is not None:
            return
    # 404 rather than 403 avoids confirming that the record exists.
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Employee not found",
    )


def apply_visibility(query, column, user: User, db: Session):
    """Constrain a query to the records `user` may read.

    ``column`` is the Employee relationship on the queried model, e.g.
    ``LeaveRequest.employee_id``.

    Employee-scoped visibility (the reporting chain) is composed with, never
    replaced by, tenant scoping: every tenant-owned model is additionally
    limited to the current request's tenant. Models that carry no ``tenant_id``
    (users, audit) are left alone.
    """
    allowed = resolve_visible_employee_ids(db, user)
    if allowed is None:
        pass  # unrestricted role: no employee filter at all
    elif not allowed:
        # No visible rows. `None` is not accepted by SQLAlchemy here, so return
        # a condition that is always false without needing the db.
        return query.filter(column.is_(None))
    else:
        query = query.filter(column.in_(allowed))

    # Tenant scoping: every tenant-owned model is further limited to the
    # current request's tenant. Composed with, not replacing, employee scope.
    # ``tenant_id_for`` falls back to the value persisted on the session by
    # ``resolve_tenant`` because context variables do not cross the thread
    # boundary to the AnyIO worker that runs sync endpoints.
    # Rows whose ``tenant_id`` is NULL were written before the backfill (or
    # without a resolved tenant) and belong to the legacy default tenant, so a
    # default request still sees them.
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        model = column.class_
        if hasattr(model, "tenant_id"):
            query = query.filter(tenant_column_criterion(model.tenant_id, tenant_id))
    return query


def ensure_can_view_employee(
    db: Session, user: User, employee_id: int | None
) -> None:
    """Raise 403 unless `user` may read this employee's record."""
    if employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="employee_id is required",
        )
    if user.role in GLOBAL_ROLES:
        return
    allowed = resolve_visible_employee_ids(db, user)
    if allowed is None or employee_id in allowed:
        return
    # 404 rather than 403 avoids confirming that the record exists.
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Employee not found",
    )


def ensure_can_view_employee_or_403(
    db: Session, user: User, employee_id: int | None
) -> None:
    """As :func:`ensure_can_view_employee`, but reports 403 rather than 404."""
    try:
        ensure_can_view_employee(db, user, employee_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this employee's records",
            ) from None
        raise


def is_global_reader(user: User) -> bool:
    """True when the role may see every record, not only their own.

    A record that has no employee column — a shift swap, a webhook, a
    migration job — cannot be scoped by the reporting chain, so the only
    question is whether the role is one of the ones that sees everything.
    This is that question, asked in one place, so no endpoint has to spell
    the role list out again.
    """
    return user.role in GLOBAL_ROLES


def metric_visible_for_role(role: str, key: str) -> bool:
    """True when `role` may see the metric named `key`.

    Definitions list roles as prose ("HR, SuperAdmin, Manager (own team)"),
    so this matches the role name as a whole token rather than a substring —
    an Associate must not match "PayrollViewer".

    A metric that is not in the catalogue is visible: the endpoint has
    already refused an unknown key with a 404, and a missing definition is
    not a reason to withhold a figure.
    """
    from app.services import metrics

    definition = metrics.CATALOGUE.get(key)
    if definition is None:
        return True
    allowed_roles = {
        r.strip()
        for r in definition.permissions.replace("(", " ").replace(")", " ").split(",")
    }
    return role in allowed_roles


def describe_policy(user: User) -> dict:
    """Human-readable summary, used by the API to explain behaviour."""
    if user.role in GLOBAL_ROLES:
        scope = "all employees"
    elif user.employee_id:
        scope = "self + reporting line"
    else:
        scope = "none (no linked employee record)"
    return {"role": user.role, "scope": scope}