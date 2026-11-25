"""The leave endpoints: types, balances, the ledger, the requests, the reports.

The balance is derived from the ledger, so the balance endpoints read the
ledger's sum and say whether the cached columns agree with it. The ledger
itself is a history of a person's leave, which is more sensitive than the
balance: it is scoped to the roles that may see leave and to the records the
caller may see, and it carries no reason and no diagnosis.
"""
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import (
    ADMIN_ROLES,
    ALL_ROLES,
    MANAGER_ROLES,
    REPORTS_ROLES,
    WORKFORCE_ROLES,
    get_db,
    require_roles,
    tenant_id_for,
)
from app.core.tenancy import tenant_matches
from app.core.audit import record_audit
from app.core.errors import conflict, validation
from app.core.visibility import (
    ensure_can_view_employee,
    ensure_can_view_employee_or_403,
    resolve_visible_employee_ids,
)
from app.crud import crud_leave as crud
from app.crud.crud_employee import get_employee
from app.models.user import User
from app.schemas.leave import (
    EntitlementCreate,
    LeaveBalanceOut,
    LeaveLedgerEntryOut,
    LeavePayrollInputOut,
    LeaveReconciliationOut,
    LeaveReconciliationSummary,
    LeaveRequestCreate,
    LeaveRequestOut,
    LeaveTypeCreate,
    LeaveTypeOut,
    LeaveTypeUpdate,
)
from app.services import leave as ledger
from app.services import notifications as notify

router = APIRouter()


def _notify_leave(db: Session, employee_id: int, notification_type: str,
                  category: str, title: str, message: str,
                  request_id: int) -> None:
    """Notify the employee behind a leave request, if they have a login.

    The emission is best-effort by design: resolving nobody (no linked
    user) or an opted-out recipient yields no row and never fails the
    leave decision it accompanies.
    """
    recipient = notify.user_id_for_employee(db, employee_id)
    if recipient is None:
        return
    notify.emit(
        db,
        recipient_user_id=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        category=category,
        entity_type="leave_request",
        entity_id=request_id,
    )


# --- Leave types ------------------------------------------------------------ #

@router.get("/types", response_model=list[LeaveTypeOut], operation_id="leaveListTypes")
def list_types(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    return crud.get_leave_types(db, active_only=active_only)


@router.post("/types", response_model=LeaveTypeOut, status_code=201, operation_id="leaveCreateLeavetypes")
def create_type(
    payload: LeaveTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if crud.get_leave_type_by_code(db, payload.code):
        raise HTTPException(status_code=400, detail="Leave type code already exists")
    leave_type = crud.create_leave_type(db, payload)
    record_audit(db, current_user, "create_leave_type", "LeaveType", leave_type.id)
    db.commit()
    return leave_type


@router.put("/types/{leave_type_id}", response_model=LeaveTypeOut, operation_id="leaveUpdateLeavetypes")
def update_type(
    leave_type_id: int,
    payload: LeaveTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    leave_type = crud.get_leave_type(db, leave_type_id)
    if not leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found")
    leave_type = crud.update_leave_type(db, leave_type, payload)
    record_audit(db, current_user, "update_leave_type", "LeaveType", leave_type.id)
    db.commit()
    return leave_type


# --- Balances --------------------------------------------------------------- #

@router.get("/balances", response_model=list[LeaveBalanceOut], operation_id="leaveGetBalances")
def list_balances(
    employee_id: int | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Leave balances, scoped to the caller's visibility.

    ``available_days`` is the derived balance: the sum of the signed ledger
    rows. ``cached_available_days`` is what the balance row's own columns
    add up to, so a client can see whether the two agree.
    """
    rows = crud.get_balances(db, employee_id=employee_id, year=year)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        rows = [
            row
            for row in rows
            if tenant_matches(getattr(row["balance"], "tenant_id", None), tenant_id)
        ]
    visible = resolve_visible_employee_ids(db, current_user)
    allowed = [
        row["balance"]
        for row in rows
        if visible is None or row["balance"].employee_id in visible
    ]
    derived = ledger.derived_sums(db, [balance.id for balance in allowed])

    out = []
    for r in rows:
        balance = r["balance"]
        if visible is not None and balance.employee_id not in visible:
            continue
        out.append(
            LeaveBalanceOut(
                id=balance.id,
                employee_id=balance.employee_id,
                leave_type_id=balance.leave_type_id,
                entitlement_year=balance.entitlement_year,
                entitled_days=balance.entitled_days,
                carried_over_days=balance.carried_over_days,
                used_days=balance.used_days,
                available_days=float(derived.get(balance.id, 0)),
                cached_available_days=float(balance.available_days),
                leave_type_name=r["leave_type_name"],
            )
        )
    return out


@router.get("/balances/{employee_id}/ledger", response_model=list[LeaveLedgerEntryOut], operation_id="leaveGetBalanceLedger")
def read_ledger(
    employee_id: int,
    leave_type_id: int | None = None,
    year: int | None = None,
    from_: date | None = Query(None, alias="from"),
    to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """The ledger of one employee's leave, oldest first.

    Every row carries the balance after the movement, so the balance can be
    recomputed from the ledger alone. The rows are never edited and never
    deleted: a correcting movement is appended.
    """
    ensure_can_view_employee(db, current_user, employee_id)
    rows = crud.get_balances(db, employee_id=employee_id, year=year)
    out: list[dict] = []
    for r in rows:
        balance = r["balance"]
        if leave_type_id is not None and balance.leave_type_id != leave_type_id:
            continue
        out.extend(ledger.ledger_view(ledger.ledger_rows(db, balance)))
    if from_ is not None:
        out = [
            row
            for row in out
            if row["created_at"] and row["created_at"].date() >= from_
        ]
    if to is not None:
        out = [
            row
            for row in out
            if row["created_at"] and row["created_at"].date() <= to
        ]
    return out


# --- Reports ---------------------------------------------------------------- #

@router.get("/reconciliation", response_model=LeaveReconciliationOut, operation_id="leaveGetReconciliation")
def reconciliation(
    year: int | None = None,
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    """The balances of this deployment against the ledgers that explain them.

    The report is about people, so it is limited to the roles that may see
    leave, to the records the caller may see, and it carries the numbers
    that disagree and nothing else: no reason, no description, no diagnosis.
    """
    visible = resolve_visible_employee_ids(db, current_user)
    employee_ids = None if visible is None else visible
    if employee_id is not None:
        ensure_can_view_employee_or_403(db, current_user, employee_id)
        employee_ids = {employee_id}

    rows = ledger.reconcile(db, employee_ids=employee_ids, year=year)
    summary = LeaveReconciliationSummary(
        balances=len(rows),
        in_sync=sum(1 for row in rows if row["state"] == ledger.IN_SYNC),
        out_of_sync=sum(1 for row in rows if row["state"] == ledger.OUT_OF_SYNC),
        no_ledger=sum(1 for row in rows if row["state"] == ledger.NO_LEDGER),
        difference_days=round(sum(row["difference_days"] for row in rows), 2),
    )
    return LeaveReconciliationOut(year=year, rows=rows, summary=summary)


@router.get("/payroll-input", response_model=LeavePayrollInputOut, operation_id="leaveGetPayrollInput")
def payroll_input(
    period_start: date,
    period_end: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    """The approved leave of a period, quantified, for the payroll lane.

    The quantity is the leave that falls inside the period, so leave that
    straddles two periods is split between them. This is the leave lane's
    half of ``LV-05``; the other half is the payroll lane's.
    """
    if period_end < period_start:
        raise validation(
            "validation_error", "period_end must not be before period_start"
        )
    entries = ledger.approved_leave_for_period(db, period_start, period_end)
    total = sum(entry["quantity_days"] for entry in entries)
    return LeavePayrollInputOut(
        period_start=period_start,
        period_end=period_end,
        entries=entries,
        total_days=round(total, 2),
    )


@router.post("/entitlements", status_code=201, operation_id="leaveCreateLeaveentitlements")
def assign_entitlements(
    payload: EntitlementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    created = crud.assign_entitlements(db, payload)
    record_audit(
        db,
        current_user,
        "assign_leave_entitlements",
        "LeaveBalance",
        None,
        details=f"{len(created)} balances for {payload.entitlement_year}",
    )
    db.commit()
    return {"created": len(created)}


# --- Requests --------------------------------------------------------------- #

@router.get("/requests", response_model=list[LeaveRequestOut], operation_id="leaveListRequests")
def list_requests(
    employee_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Leave requests, scoped to the caller's visibility.

    Previously any authenticated user could pass no filter and read every
    colleague's leave requests and reasons.
    """
    from app.core.visibility import apply_visibility
    from app.models.leave import LeaveRequest

    query = db.query(LeaveRequest)
    query = apply_visibility(query, LeaveRequest.employee_id, current_user, db)
    if employee_id is not None:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    if status:
        query = query.filter(LeaveRequest.status == status)
    return query.order_by(LeaveRequest.id.desc()).all()


@router.post("/requests", response_model=LeaveRequestOut, status_code=201, operation_id="leaveCreateRequest")
def create_request(
    payload: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    if not get_employee(db, payload.employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    try:
        request = crud.create_request(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record_audit(db, current_user, "create_leave_request", "LeaveRequest", request.id)
    # The requester gets a receipt: their request is in the queue. Looked up
    # through the linked login, so an employee without one simply gets none.
    _notify_leave(db, request.employee_id, "info", "leave",
                  f"Leave request #{request.id} received",
                  f"Your leave request for {request.start_date.isoformat()} to "
                  f"{request.end_date.isoformat()} is pending approval.",
                  request.id)
    db.commit()
    return request


@router.post("/requests/{request_id}/approve", response_model=LeaveRequestOut, operation_id="leaveApproveRequest")
def approve_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    request = crud.get_request(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # A manager approves the leave of their own reporting line and nothing
    # else. Without this the widened manager role would let a manager decide
    # leave for anybody in the tenant.
    ensure_can_view_employee_or_403(db, current_user, request.employee_id)
    if request.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")
    try:
        request = crud.decide_request(
            db, request, approved=True, decided_by=current_user.id
        )
    except ledger.NoLeaveBalance as exc:
        # The days would be taken from nobody. The refusal is in the audit
        # trail, so the gap is visible rather than silent.
        record_audit(
            db,
            current_user,
            "leave_approval_without_entitlement",
            "LeaveRequest",
            request.id,
            details=(
                f"No leave balance exists for employee {request.employee_id}, "
                f"leave type {request.leave_type_id}, year {request.start_date.year}. "
                f"The approval was refused and {request.working_days} day(s) "
                f"were not taken."
            ),
        )
        db.commit()
        raise conflict("leave_no_entitlement", str(exc))
    except ledger.InsufficientLeaveBalance as exc:
        record_audit(
            db,
            current_user,
            "leave_approval_refused_insufficient_balance",
            "LeaveRequest",
            request.id,
            details=str(exc),
        )
        db.commit()
        raise conflict("leave_insufficient_balance", str(exc))
    record_audit(db, current_user, "approve_leave_request", "LeaveRequest", request.id)
    # Decided, so the requester hears the outcome. A refusal above raises
    # before this line, which is what keeps refusals silent.
    _notify_leave(db, request.employee_id, "success", "leave",
                  f"Leave request #{request.id} approved",
                  f"Your leave request for {request.start_date.isoformat()} to "
                  f"{request.end_date.isoformat()} was approved.",
                  request.id)
    db.commit()
    return request


@router.post("/requests/{request_id}/reject", response_model=LeaveRequestOut, operation_id="leaveRejectRequest")
def reject_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    request = crud.get_request(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # The same reporting-line scope as the approval above.
    ensure_can_view_employee_or_403(db, current_user, request.employee_id)
    if request.status != "Pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be rejected")
    request = crud.decide_request(db, request, approved=False, decided_by=current_user.id)
    record_audit(db, current_user, "reject_leave_request", "LeaveRequest", request.id)
    _notify_leave(db, request.employee_id, "warning", "leave",
                  f"Leave request #{request.id} rejected",
                  f"Your leave request for {request.start_date.isoformat()} to "
                  f"{request.end_date.isoformat()} was rejected.",
                  request.id)
    db.commit()
    return request


@router.post("/requests/{request_id}/cancel", response_model=LeaveRequestOut, operation_id="leaveCancelRequest")
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    request = crud.get_request(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    ensure_can_view_employee(db, current_user, request.employee_id)
    try:
        request = crud.cancel_request(db, request, cancelled_by=current_user.id)
    except ledger.LedgerError as exc:
        db.rollback()
        raise conflict("leave_invalid_state_transition", str(exc))
    record_audit(db, current_user, "cancel_leave_request", "LeaveRequest", request.id)
    db.commit()
    return request
