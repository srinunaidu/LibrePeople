import json
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, ALL_ROLES, REPORTS_ROLES, get_db, require_roles
from app.core.config import settings
from app.core.errors import ApiError, ErrorCategory, conflict, forbidden, not_found, validation
from app.core.sensitive_fields import can_access_bank_tax, mask_bank_tax, refuse_bank_tax_write
from app.core.idempotency import IdempotencyGuard, idempotency_key
from app.core.audit import record_audit
from app.core.visibility import apply_visibility, ensure_can_view_employee
from app.core.tenancy import tenant_column_criterion, tenant_id_for
from app.models.employee import Employee, EmployeeHistory
from app.models.leave import LeaveRequest, LeaveType
from app.models.payroll import (
    EmployeePayProfile,
    PayComponent,
    PayRun,
    PaySlip,
    PayrollPeriod,
)
from app.models.time_attendance import TimeEntry
from app.models.user import User
from app.schemas.payroll import (
    EmployeePayProfileCreate,
    EmployeePayProfileOut,
    PayComponentCreate,
    PayComponentOut,
    PayRunCreate,
    PayRunOut,
    PaySlipCreate,
    PaySlipOut,
    PayrollPeriodCreate,
    PayrollPeriodOut,
)
from app.services.payroll_reconciliation import build_pay_run_reconciliation
from app.services import notifications as notify

router = APIRouter()


def _notify_pay_run(
    db: Session, run, operator_id: int, title: str, message: str
) -> None:
    """Notify the operator and every employee paid in the run.

    The operator decided the run, so they hear that it moved; each employee
    with a payslip hears that their pay was processed or locked. Resolution
    is best-effort: an employee with no linked login is skipped, and an
    opted-out recipient writes no row.
    """
    recipients = {operator_id}
    for slip in db.query(PaySlip).filter(PaySlip.pay_run_id == run.id).all():
        user_id = notify.user_id_for_employee(db, slip.employee_id)
        if user_id is not None:
            recipients.add(user_id)
    for recipient_id in sorted(recipients):
        notify.emit(
            db,
            recipient_user_id=recipient_id,
            title=title,
            message=message,
            notification_type="success",
            category="payroll",
            entity_type="pay_run",
            entity_id=run.id,
        )


# --- Periods ---------------------------------------------------------------- #

@router.get("/periods", response_model=list[PayrollPeriodOut], operation_id="payrollListPayrollperiods")
def list_periods(db: Session = Depends(get_db), u: User = Depends(require_roles(*REPORTS_ROLES))):
    return db.query(PayrollPeriod).order_by(PayrollPeriod.start_date.desc()).all()


@router.post("/periods", response_model=PayrollPeriodOut, status_code=201, operation_id="payrollCreatePayrollperiods")
def create_period(payload: PayrollPeriodCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    obj = PayrollPeriod(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_payroll_period", "PayrollPeriod", obj.id); db.commit()
    return obj


# --- Components ------------------------------------------------------------- #

@router.get("/components", response_model=list[PayComponentOut], operation_id="payrollListPayrollcomponents")
def list_components(db: Session = Depends(get_db), u: User = Depends(require_roles(*REPORTS_ROLES))):
    return db.query(PayComponent).order_by(PayComponent.code).all()


@router.post("/components", response_model=PayComponentOut, status_code=201, operation_id="payrollCreatePayrollcomponents")
def create_component(payload: PayComponentCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    # `code` is the natural key and the column is unique. Without this check a
    # second create was an IntegrityError rendered as 500; the taxonomy's
    # answer for a taken natural key is 409 `duplicate_natural_key`.
    if db.query(PayComponent).filter(PayComponent.code == payload.code).first():
        raise conflict(
            "duplicate_natural_key",
            f"A pay component with code {payload.code!r} already exists.",
            entity="pay_component",
            field="code",
            value=payload.code,
        )
    obj = PayComponent(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_pay_component", "PayComponent", obj.id); db.commit()
    return obj


# --- Pay profiles ----------------------------------------------------------- #

def _pay_profile_response(profile: EmployeePayProfile, actor: User) -> dict:
    """The pay profile as a dict, with the bank account decrypted and governed.

    Returned as a dict, never the ORM object, so the bank account policy in
    :mod:`app.core.sensitive_fields` applies to every response.
    """
    from app.core.encryption import decrypt_field

    data = {c.name: getattr(profile, c.name, None) for c in profile.__table__.columns}
    raw = data.get("bank_account")
    if raw and isinstance(raw, str) and raw.startswith("ENCv1:"):
        try:
            data["bank_account"] = decrypt_field(raw)
        except Exception:
            pass
    return mask_bank_tax(data, actor.role)


@router.get("/pay-profiles", response_model=list[EmployeePayProfileOut], operation_id="payrollListPayProfiles")
def list_pay_profiles(
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ALL_ROLES)),
):
    q = db.query(EmployeePayProfile)
    q = apply_visibility(q, EmployeePayProfile.employee_id, u, db)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(EmployeePayProfile.employee_id == employee_id)
    return [_pay_profile_response(r, u) for r in q.all()]


@router.get("/pay-profiles/{employee_id}", response_model=EmployeePayProfileOut, operation_id="payrollGetPayrollpayprofiles")
def get_pay_profile(
    employee_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ALL_ROLES)),
):
    ensure_can_view_employee(db, u, employee_id)
    profile = (
        db.query(EmployeePayProfile)
        .filter(EmployeePayProfile.employee_id == employee_id)
        .first()
    )
    if not profile:
        raise not_found("Pay profile")
    return _pay_profile_response(profile, u)


@router.post("/pay-profiles", response_model=EmployeePayProfileOut, status_code=201, operation_id="payrollCreatePayrollpayprofiles")
def create_pay_profile(payload: EmployeePayProfileCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    refuse_bank_tax_write(payload.model_dump(exclude_unset=True), u.role)
    # The employee must exist: the foreign key alone would surface a missing
    # row as a 500 after the insert fails.
    if db.get(Employee, payload.employee_id) is None:
        raise not_found(f"Employee {payload.employee_id}")
    # One profile per employee is the table's unique rule. The API says so
    # with the shared code instead of letting the constraint answer 500.
    if (
        db.query(EmployeePayProfile)
        .filter(EmployeePayProfile.employee_id == payload.employee_id)
        .first()
    ):
        raise conflict(
            "duplicate_natural_key",
            f"Employee {payload.employee_id} already has a pay profile.",
            entity="pay_profile",
            field="employee_id",
            value=payload.employee_id,
        )
    data = payload.model_dump()
    # Bank_account at rest: column String(60) cannot hold Fernet token (~120 chars) without widening.
    # Keep plain for v1 DB compat; helper encrypt_field is verified via aadhaar and unit tests, and payment_file decrypts if ENCv1 present.
    obj = EmployeePayProfile(**data)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "create_pay_profile", "EmployeePayProfile", obj.id); db.commit()
    return _pay_profile_response(obj, u)


# --- Pay runs --------------------------------------------------------------- #

@router.get("/runs", response_model=list[PayRunOut], operation_id="payrollListRuns")
def list_runs(db: Session = Depends(get_db), u: User = Depends(require_roles(*REPORTS_ROLES))):
    query = db.query(PayRun)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        query = query.filter(tenant_column_criterion(PayRun.tenant_id, tenant_id))
    return query.order_by(PayRun.created_at.desc()).all()


@router.get("/runs/{run_id}", response_model=PayRunOut, operation_id="payrollGetRun")
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*REPORTS_ROLES)),
):
    run = db.query(PayRun).filter(PayRun.id == run_id).first()
    if not run:
        raise not_found(f"Pay run {run_id}")
    return run


@router.post("/runs", response_model=PayRunOut, status_code=201, operation_id="payrollCreateRun")
def create_run(payload: PayRunCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    from datetime import datetime, timezone

    period = db.query(PayrollPeriod).filter(PayrollPeriod.id == payload.period_id).first()
    if not period:
        raise not_found(f"Payroll period {payload.period_id}")

    # India payroll settles in rupees only: a run that names jurisdiction
    # IN but prices in anything else would calculate statutory lines
    # against a foreign currency, so it is refused up front (422) rather
    # than corrected silently. Other jurisdictions keep their own currency.
    if payload.jurisdiction == "IN" and payload.currency.upper() != "INR":
        raise validation(
            "non_inr_currency",
            "Pay runs for jurisdiction 'IN' must use currency 'INR'.",
            jurisdiction=payload.jurisdiction,
            currency=payload.currency,
        )

    # --- Pipeline run_type + reversal link (expand-only) ------------------ #
    # regular is the default for every row that predates the column.
    run_type = (payload.run_type or "regular").strip().lower()
    if run_type not in ("regular", "off_cycle", "adjustment", "reversal"):
        raise validation(
            "invalid_run_type",
            f"run_type must be one of regular, off_cycle, adjustment, reversal.",
            run_type=payload.run_type,
        )
    reversal_id = payload.reversal_of_run_id
    if run_type in ("adjustment", "reversal"):
        # Corrections reference the locked run they correct. The source must
        # exist and be locked (Finalized/Paid); correcting a Draft/Processing
        # run is an edit, not a correction, and is refused.
        if reversal_id is None:
            raise validation(
                "reversal_required",
                f"run_type '{run_type}' must name reversal_of_run_id of the locked run it corrects.",
                run_type=run_type,
            )
        source = db.query(PayRun).filter(PayRun.id == reversal_id).first()
        if not source:
            raise not_found(f"Pay run {reversal_id}")
        # Depth-1: corrections correct a locked regular/off-cycle run only.
        # An adjustment/reversal run is itself a correction — correcting it
        # would chain corrections (depth 2+), which reconciliation and the
        # audit history do not model. Refused so every correction names a
        # lineage root. A chained source (non-null reversal_of_run_id) is
        # refused the same way even if its run_type was backfilled.
        # Checked before the lock so a correction-of-correction is always
        # depth-exceeded regardless of the intermediate run's status.
        if (getattr(source, "run_type", None) or "regular") in ("adjustment", "reversal"):
            raise validation(
                "reversal_depth_exceeded",
                f"reversal_of_run_id {reversal_id} is itself a '{getattr(source, 'run_type', None)}' correction; "
                "corrections cannot correct corrections (depth 1 only). "
                "Name the locked regular/off-cycle run instead.",
                reversal_of_run_id=reversal_id,
                source_run_type=getattr(source, "run_type", None),
            )
        if getattr(source, "reversal_of_run_id", None) is not None:
            raise validation(
                "reversal_depth_exceeded",
                f"reversal_of_run_id {reversal_id} is itself a correction of run "
                f"{getattr(source, 'reversal_of_run_id', None)}; corrections cannot "
                "correct corrections (depth 1 only).",
                reversal_of_run_id=reversal_id,
            )
        if source.status not in ("Finalized", "Paid"):
            raise validation(
                "reversal_not_locked",
                f"reversal_of_run_id {reversal_id} must be a locked run (Finalized/Paid); found '{source.status}'.",
                reversal_of_run_id=reversal_id,
                source_status=source.status,
            )
    else:
        # Regular/off-cycle runs start their own lineage — they must not
        # carry a reversal link. A link on a regular run is a caller error.
        if reversal_id is not None:
            raise validation(
                "unexpected_reversal_link",
                f"run_type '{run_type}' must not name reversal_of_run_id; only adjustment/reversal runs correct a locked run.",
                run_type=run_type,
            )
    if run_type == "off_cycle":
        # Off-cycle runs are separate pay runs with their own period: they
        # must not reuse the period of a regular run for the same
        # jurisdiction, otherwise the correction is ambiguous. The period
        # itself must exist (checked above); the clash check is the guard.
        # Symmetry note: the check is one-way by design. A regular run is the
        # canonical run for its period — creating it first is the normal flow
        # and a later off-cycle for the same period is the ambiguous case that
        # is refused. The reverse (regular created after an off-cycle on the
        # same period) is left to the operator: the off-cycle already warned
        # that the period is taken, and refusing the regular would block the
        # canonical run. Regular-on-regular duplicates are out of scope for
        # this guard (re-runs are handled by the Finalized lock, not here).
        clash = (
            db.query(PayRun)
            .filter(
                PayRun.period_id == payload.period_id,
                PayRun.jurisdiction == payload.jurisdiction,
            )
            .first()
        )
        if clash is not None:
            raise validation(
                "off_cycle_period_clash",
                "Off-cycle runs must use their own period: this period already "
                f"has pay run {clash.id} for jurisdiction '{payload.jurisdiction}'. "
                "Create a separate period for the off-cycle correction.",
                period_id=payload.period_id,
                existing_run_id=clash.id,
            )

    obj = PayRun(
        period_id=payload.period_id,
        jurisdiction=payload.jurisdiction,
        currency=payload.currency,
        run_type=run_type,
        reversal_of_run_id=reversal_id,
        run_date=datetime.now(timezone.utc),
    )
    db.add(obj); db.flush()
    # Self guard: a correction can never name itself. On create the new id is
    # unknown until flush, so check after flush and roll back on a self-loop
    # (only reachable if the caller guessed the next autoincrement id).
    if reversal_id is not None and obj.reversal_of_run_id == obj.id:
        db.rollback()
        raise validation(
            "reversal_self_reference",
            "reversal_of_run_id must not name the run being created.",
            reversal_of_run_id=reversal_id,
        )
    db.commit(); db.refresh(obj)
    record_audit(db, u, "create_pay_run", "PayRun", obj.id); db.commit()
    return obj


# --- Pay run state machine -------------------------------------------------- #
#
# Draft -> Processing -> Approved -> Finalized -> Paid
#
# Every transition is validated server-side. Clients cannot set `status`
# directly (the schema does not expose it), so state can only move by passing
# through these endpoints.

ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "Draft": ("Processing",),
    "Processing": ("Draft", "Approved"),
    "Approved": ("Processing", "Finalized"),
    "Finalized": ("Paid",),
    "Paid": (),
}


def _assert_transition(run: PayRun, target: str) -> None:
    current = run.status or "Draft"
    if target not in ALLOWED_TRANSITIONS.get(current, ()):
        raise validation(
            "invalid_state_transition",
            f"Cannot move pay run from '{current}' to '{target}'. "
            f"Allowed next states: {list(ALLOWED_TRANSITIONS.get(current, ())) or 'none (final)'}",
            from_state=current,
            to_state=target,
        )


@router.post("/runs/{run_id}/approve", response_model=PayRunOut, operation_id="payrollApproveRun")
def approve_run(run_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Approve a processed pay run for finalisation."""
    run = db.query(PayRun).filter(PayRun.id == run_id).first()
    if not run:
        raise not_found(f"Pay run {run_id}")
    _assert_transition(run, "Approved")
    slip_count = db.query(PaySlip).filter(PaySlip.pay_run_id == run.id).count()
    if not slip_count:
        raise validation(
            "invalid_state_transition",
            "Cannot approve a pay run with no payslips",
            from_state=run.status,
            to_state="Approved",
        )
    # Segregation of duties: the operator who processed the run must not be the
    # one who approves it.
    if run.processed_by and run.processed_by == u.id:
        raise ApiError(
            code="separation_of_duties",
            message="Segregation of duties: the operator who processed this run "
            "cannot also approve it",
            category=ErrorCategory.PERMISSION,
            status_code=403,
            details={"conflicting_role": u.role},
        )
    run.status = "Approved"
    run.approved_by = u.id
    run.approved_at = datetime.now(timezone.utc)
    db.add(run); db.commit(); db.refresh(run)
    record_audit(db, u, "approve_pay_run", "PayRun", run.id); db.commit()
    return run


@router.post("/runs/{run_id}/finalize", response_model=PayRunOut, operation_id="payrollCreatePayrollrunsfinalize")
def finalize_run(run_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Lock an approved pay run. Payslips become read-only afterwards."""
    run = db.query(PayRun).filter(PayRun.id == run_id).first()
    if not run:
        raise not_found(f"Pay run {run_id}")
    _assert_transition(run, "Finalized")
    run.status = "Finalized"
    run.finalized_by = u.id
    run.finalized_at = datetime.now(timezone.utc)
    # Payslips are marked final so the UI and exports can distinguish them.
    for slip in db.query(PaySlip).filter(PaySlip.pay_run_id == run.id).all():
        slip.status = "Final"
    db.add(run); db.commit(); db.refresh(run)
    record_audit(db, u, "finalize_pay_run", "PayRun", run.id)
    # Finalized is a success: the lock held and every slip is final. A run
    # that never reaches this line (wrong state, missing run) raises above
    # and notifies nobody.
    _notify_pay_run(
        db, run, u.id,
        f"Pay run #{run.id} finalized",
        f"Pay run #{run.id} was finalized. Its payslips are now read-only.",
    )
    db.commit()
    return run


@router.post("/runs/{run_id}/payment-file", operation_id="payrollGetPaymentFile")
def payment_file(
    run_id: int,
    format: str | None = Query(default=None, alias="format", description="Payment file format: nacha|neft"),
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Generate a bank-ready payment file from an approved pay run.

    Returns a NACHA-equivalent plain-text file containing, per employee with a
    payslip in the run: bank account, routing/sort identifier, net amount,
    currency, employee reference and pay-run reference. The file is returned
    as a downloadable attachment with a deterministic filename.

    Slice 3 — India: ?format=nacha|neft (jurisdiction auto-selects default:
    IN→neft, else nacha). NACHA path unchanged. NEFT emits header "NEFT"
    plus India fields sourced from employees + pay profiles.
    """
    # The file carries bank account and IFSC data, so it is limited to the
    # roles the bank and tax field policy admits (HR and SuperAdmin).
    if not can_access_bank_tax(u.role):
        raise forbidden("Your role does not permit generating a bank payment file.")
    run = db.query(PayRun).filter(PayRun.id == run_id).first()
    if not run:
        raise not_found(f"Pay run {run_id}")
    if run.status != "Approved":
        raise validation(
            "invalid_state_transition",
            f"Payment file is only available for approved runs; run is {run.status}",
            from_state=run.status,
            to_state="Approved",
        )

    slips = (
        db.query(PaySlip)
        .filter(PaySlip.pay_run_id == run.id)
        .order_by(PaySlip.id.asc())
        .all()
    )
    if not slips:
        raise validation(
            "invalid_state_transition",
            "Cannot generate a payment file for a run with no payslips",
            from_state=run.status,
            to_state="Approved",
        )

    # Resolve format: explicit ?format wins; otherwise jurisdiction auto-selects.
    _fmt_raw = (format or "").strip().lower() if format else None
    if _fmt_raw is None:
        _fmt_raw = "neft" if (run.jurisdiction or "").strip().upper() == "IN" else "nacha"
    # Normalize rtgs as neft (same India wire)
    if _fmt_raw == "rtgs":
        _fmt_raw = "neft"
    is_neft = _fmt_raw == "neft"
    currency = run.currency or settings.DEFAULT_CURRENCY
    total_net = str(sum(slip.net_pay for slip in slips))
    if is_neft:
        # --- Slice 6 hardening: decrypt + validate before emitting NEFT ---
        from app.core.encryption import (
            validate_ifsc as _validate_ifsc,
            validate_account_number as _validate_acct,
            validate_beneficiary_name as _validate_name,
            sanitize_beneficiary_name as _sanitize_name,
            decrypt_field as _decrypt,
        )
        def _decrypt_if_needed(val: str | None) -> str:
            if not val:
                return ""
            try:
                if isinstance(val, str) and val.startswith("ENCv1:"):
                    dec = _decrypt(val)
                    return dec or ""
            except Exception:
                pass
            return str(val)

        lines = ["NEFT", f"RUN_ID={run.id}", f"CURRENCY={currency}", f"TOTAL_NET={total_net}"]
        field_errors: list[dict] = []
        pending_rows: list[tuple] = []
        for slip in slips:
            employee = db.get(Employee, slip.employee_id)
            profile = (
                db.query(EmployeePayProfile)
                .filter(EmployeePayProfile.employee_id == slip.employee_id)
                .first()
            )
            raw_bank = profile.bank_account if profile else ""
            bank_account = _decrypt_if_needed(raw_bank)
            raw_ifsc = (getattr(employee, "ifsc_code", None) or "") if employee else ""
            ifsc_code = _decrypt_if_needed(raw_ifsc)
            # Aadhaar is server-side only, not in NEFT but validated for completeness if present
            pf_uan = (getattr(employee, "pf_uan", None) or "") if employee else ""
            pf_uan = _decrypt_if_needed(pf_uan)
            raw_name = (
                f"{employee.first_name} {employee.last_name}" if employee and employee.first_name else str(slip.employee_id)
            )
            # Check raw name for illegal chars before sanitization -> 422.
            # PII-safe: field_errors carry no raw values — only field,
            # employee_id, error and value length. Raw bank account / IFSC /
            # beneficiary names must never appear in a 422 body.
            ok_name, err_name = _validate_name(raw_name)
            if not ok_name:
                field_errors.append({"field": "beneficiary_name", "employee_id": slip.employee_id, "error": err_name, "value_len": len(raw_name or "")})
            # Also validate IFSC/account
            ok_ifsc, err_ifsc = _validate_ifsc(ifsc_code)
            if not ok_ifsc:
                field_errors.append({"field": "ifsc_code", "employee_id": slip.employee_id, "error": err_ifsc, "value_len": len(ifsc_code or "")})
            ok_acct, err_acct = _validate_acct(bank_account)
            if not ok_acct:
                field_errors.append({"field": "bank_account", "employee_id": slip.employee_id, "error": err_acct, "value_len": len(bank_account or "")})
            # Sanitize name for output (strip |/newlines)
            beneficiary_name, _ = _sanitize_name(raw_name)
            employee_ref = employee.employee_id if employee else ""
            pending_rows.append((beneficiary_name, bank_account or "", ifsc_code or "", str(slip.net_pay), currency, employee_ref or str(slip.employee_id), pf_uan or ""))
        if field_errors:
            raise validation(
                "payment_validation_failed",
                "NEFT validation failed",
                field_errors=field_errors,
            )
        for row in pending_rows:
            lines.append("|".join(str(part) for part in row))
        content = "\n".join(lines) + "\n"
        filename = f"payroll_run_{run_id}_neft.txt"
        import hashlib as _hashlib
        _payment_hash = _hashlib.sha256(content.encode("utf-8")).hexdigest()
    else:
        # Decrypt at rest even for NACHA — bytes unchanged when decrypted equals plaintext
        def _decrypt_plain(val):
            if not val or not isinstance(val, str) or not val.startswith("ENCv1:"):
                return val
            try:
                from app.core.encryption import decrypt_field as _d
                return _d(val) or val
            except Exception:
                return val
        lines = ["PAYMENT_FILE", f"RUN_ID={run.id}", f"CURRENCY={currency}", f"TOTAL_NET={total_net}"]
        for slip in slips:
            employee = db.get(Employee, slip.employee_id)
            profile = (
                db.query(EmployeePayProfile)
                .filter(EmployeePayProfile.employee_id == slip.employee_id)
                .first()
            )
            bank_account = _decrypt_plain(profile.bank_account if profile else None)
            lines.append(
                "|".join(
                    str(part)
                    for part in [
                        slip.employee_id,
                        employee.employee_id if employee else "",
                        bank_account or "",
                        "",
                        str(slip.net_pay),
                        currency,
                        str(run.id),
                    ]
                )
            )
        content = "\n".join(lines) + "\n"
        filename = f"payroll_run_{run_id}_payment.txt"
        import hashlib as _hashlib2
        _payment_hash = _hashlib2.sha256(content.encode("utf-8")).hexdigest()
    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Payment-Hash": _payment_hash,
        },
    )


@router.post("/runs/{run_id}/process", response_model=PayRunOut, operation_id="payrollProcessRun")
def process_run(
    run_id: int,
    dry_run: bool | None = Query(default=None, description="When true, validate gate without writing payslips"),
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
    idem_key: str | None = Depends(idempotency_key),
):
    """Calculate payslips for active employees who have a pay profile.

    Processing money is the most consequential side effect in the product, so
    this accepts `Idempotency-Key`. The status guard alone already refuses a
    second run; the key additionally makes a *concurrent* double-submit and a
    retry-after-timeout safe, returning the original run instead of a 400.

    A run is calculated only from a rule pack that is `verified` and in force
    on the pay date of its period. A jurisdiction without such a pack is
    refused with `rule_pack_not_verified`, and the refusal writes nothing:
    no payslip, no change to the run, no audit row that claims work was done.
    """
    with IdempotencyGuard(
        db, idem_key, f"payroll.runs.process:{run_id}", {"run_id": run_id}
    ) as guard:
        run = db.query(PayRun).filter(PayRun.id == run_id).first()
        if not run:
            raise not_found(f"Pay run {run_id}")

        if guard.replayed:
            # Already done by the original call; no second calculation.
            return run

        if dry_run:
            # Dry-run preview: validate the gate and compute an in-memory
            # preview without writing anything. Zero writes: no payslip, no
            # run mutation, no audit row, no commit. Refusals raise directly
            # (no _record_refusal) so AuditLog is unchanged. The preview is
            # returned as a response-model copy — the ORM object is never
            # mutated (no run.warning assign).
            from app.rules.resolver import resolve_rule_pack
            from app.rules.engine import rate_table_problems
            from app.schemas.payroll import PayRunOut as _PayRunOut
            period = db.query(PayrollPeriod).filter(PayrollPeriod.id == run.period_id).first()
            jurisdiction = (run.jurisdiction or "").strip().upper()
            if period:
                resolution = resolve_rule_pack(jurisdiction, period.pay_date)
                if not resolution.is_verified:
                    details = resolution.details()
                    if not jurisdiction:
                        details["required"] = ["this pay run does not record a jurisdiction, so no rule pack can be resolved for it"]
                    from app.api.v1.endpoints.payroll import _refusal_message
                    from app.core.errors import validation as _validation
                    raise _validation("rule_pack_not_verified", _refusal_message(resolution), **details)
                unreadable = rate_table_problems(resolution.pack) if resolution.pack else []
                if unreadable:
                    details = resolution.details()
                    details["required"] = list(unreadable)
                    from app.api.v1.endpoints.payroll import _unreadable_pack_message
                    from app.core.errors import validation as _validation2
                    raise _validation2("rule_pack_not_verified", _unreadable_pack_message(resolution, resolution.pack.meta.pack_id), **details)
                # In-memory preview: headcount + totals from the pack, no writes.
                try:
                    from app.models.employee import Employee as _Emp
                    _active = db.query(_Emp).filter(_Emp.status.in_(("Active", "On Leave"))).count()
                    _profiles = db.query(EmployeePayProfile).count()
                    _preview_headcount = min(_active, _profiles)
                except Exception:
                    _preview_headcount = 0
                try:
                    _pack = resolution.pack
                    _cur = run.currency or settings.DEFAULT_CURRENCY
                    _preview_warning = (
                        f"dry-run preview: headcount~{_preview_headcount}, "
                        f"pack {_pack.meta.pack_id} v{_pack.meta.version} verified, "
                        f"currency {_cur}; zero writes"
                    )
                except Exception:
                    _preview_warning = "dry-run preview: gate passed; zero writes"
                # Schema copy only: the ORM run is never mutated, nothing is
                # flushed or committed on this branch.
                db.rollback()
                preview = _PayRunOut.model_validate(run)
                preview.warning = _preview_warning
                return preview
            db.rollback()
            return _PayRunOut.model_validate(run)

        if (run.status or "Draft") in ("Finalized", "Paid"):
            raise conflict(
                "pay_run_already_finalised",
                f"Pay run {run_id} is {run.status}; locked runs cannot be reprocessed. "
                "Create an adjustment run with reversal_of_run_id instead.",
                pay_run_id=run_id,
            )
        _assert_transition(run, "Processing")
        _calculate_payslips(db, run, u)
        # Success only: every refusal above raises before this line, and a
        # dry run returns before it too. Committed explicitly: when the
        # caller sends no Idempotency-Key the guard's __exit__ has nothing
        # to write and returns without committing.
        _notify_pay_run(
            db, run, u.id,
            f"Pay run #{run.id} processed",
            f"Pay run #{run.id} calculated {run.headcount or 0} payslip(s).",
        )
        db.commit()
        guard.store({"pay_run_id": run.id})
        return run


# --- Full & Final (India slice 5) ------------------------------------------- #

@router.get("/runs/{run_id}/fnf", operation_id="payrollGetFnf")
@router.post("/runs/{run_id}/fnf", operation_id="payrollPostFnf")
def get_fnf(
    run_id: int,
    employee_id: int = Query(..., description="Employee ID for the settlement"),
    notice_days: float | None = Query(default=None),
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*REPORTS_ROLES)),
):
    """Full & Final settlement — reads stored payslip lines, does not mutate.

    Returns structured settlement: notice_pay, leave_encashment,
    gratuity_payable (if eligible), lop_recovery, bonus_pro_rata,
    net_settlement; reads from deductions_json/earnings_json accounting
    but does not mutate run. UI tab F&F Settlement renders it read-only.
    """
    from decimal import Decimal
    from app.services.fnf_calculator import calculate_fnf, settlement_to_dict

    run = db.query(PayRun).filter(PayRun.id == run_id).first()
    if not run:
        raise not_found(f"Pay run {run_id}")
    # Only for processed runs with a payslip
    if run.status == "Draft":
        raise validation(
            "invalid_state_transition",
            "F&F is not available for draft pay runs",
            from_state=run.status,
            to_state="fnf",
        )
    # F&F is terminated-only and read-only: active employees have no
    # settlement to read, and the endpoint never mutates the run.
    # Employee is imported at module top; a missing employee is 404.
    _emp_row = db.get(Employee, employee_id)
    if _emp_row is None:
        raise not_found(f"Employee {employee_id}")
    if getattr(_emp_row, "status", None) in ("Active", "On Leave"):
        raise validation(
            "fnf_not_terminated",
            "Full & Final is only available for terminated employees; "
            f"employee {employee_id} is '{_emp_row.status}'.",
            employee_id=employee_id,
            employee_status=getattr(_emp_row, "status", None),
        )
    try:
        nd = Decimal(str(notice_days)) if notice_days is not None else Decimal("0")
    except Exception:
        nd = Decimal("0")
    try:
        settlement = calculate_fnf(db, run_id, employee_id, notice_days=nd)
        return settlement_to_dict(settlement)
    except ValueError as e:
        raise not_found(str(e))


# --- Reconciliation --------------------------------------------------------- #

@router.get("/runs/{run_id}/reconciliation", operation_id="payrollGetReconciliation")
def get_reconciliation(
    run_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*REPORTS_ROLES)),
):
    """Get the reconciliation report for a pay run.

    The reconciliation compares the computed payslip values against the
    rule pack recalculation. It returns matched=true if all values agree,
    and a list of discrepancies if they don't.
    """
    run = db.query(PayRun).filter(PayRun.id == run_id).first()
    if not run:
        raise not_found(f"Pay run {run_id}")

    # Only allow reconciliation for processed runs
    if run.status == "Draft":
        raise validation(
            "invalid_state_transition",
            "Reconciliation is not available for draft pay runs",
            from_state=run.status,
            to_state="reconciled",
        )

    try:
        report = build_pay_run_reconciliation(db, run_id)
        payload = report.to_dict()
        # Hash match: deterministic sha256 over the canonical totals so the
        # bank file and the reconciliation can be compared by hash.
        try:
            import hashlib as _hl
            import json as _js
            _canon = _js.dumps(
                {
                    "run_id": payload.get("run_id"),
                    "rule_pack_id": payload.get("rule_pack_id"),
                    "rule_pack_version": payload.get("rule_pack_version"),
                    "totals": payload.get("totals", {}),
                    "matched": payload.get("matched"),
                },
                sort_keys=True,
                default=str,
            )
            payload["content_hash"] = _hl.sha256(_canon.encode("utf-8")).hexdigest()
        except Exception:
            payload["content_hash"] = None
        return payload
    except ValueError as e:
        raise validation("reconciliation_failed", str(e))


@router.get("/runs/{run_id}/history", operation_id="payrollGetRunHistory")
def get_run_history(
    run_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*REPORTS_ROLES)),
):
    """Ordered audit history for a pay run (oldest first).

    Returns the chained audit rows that name this run, ordered by id so the
    pipeline (create -> process -> approve -> finalize) reads in order.
    """
    from app.models.audit import AuditLog

    run = db.query(PayRun).filter(PayRun.id == run_id).first()
    if not run:
        raise not_found(f"Pay run {run_id}")
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "PayRun", AuditLog.entity_id == run.id)
        .order_by(AuditLog.id.asc())
        .all()
    )
    return {
        "run_id": run.id,
        "run_type": getattr(run, "run_type", None) or "regular",
        "reversal_of_run_id": getattr(run, "reversal_of_run_id", None),
        "status": run.status,
        "history": [
            {
                "id": r.id,
                "action": r.action,
                "actor_id": r.actor_id,
                "actor_name": r.actor_name,
                "details": r.details,
                "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None,
            }
            for r in rows
        ],
    }


def _lines_as_json(lines) -> str:
    """The payslip lines, with the rule that produced each one.

    Every line carries the rule id and the rule version that produced it,
    the input it came from and the calculation itself. A payslip line that
    cannot be traced to a rule is a line nobody can defend, so the trace is
    part of the line and not a separate report.

    The amount is written as its exact decimal string. The money is
    `Decimal` all the way (PR-002), and a binary float in the stored trace
    would put the drift back.
    """
    import json

    return json.dumps(
        [
            {
                "code": line.code,
                "name": line.name,
                "amount": str(line.amount),
                "type": line.line_type,
                "rule_id": line.rule_id,
                "rule_version": line.rule_version,
                "input_source": line.input_source,
                "calculation": line.calculation,
            }
            for line in lines
        ]
    )


def _refusal_message(resolution) -> str:
    """The message that is shown with the refusal.

    It says what happened and that nothing was calculated. It carries no
    salary, no personal data and nothing about the contents of a rule pack.
    """
    jurisdiction = resolution.jurisdiction or "(none recorded)"
    return (
        f"Payroll for jurisdiction '{jurisdiction}' cannot be calculated on "
        f"{resolution.pay_date.isoformat()}: no verified rule pack is in "
        f"force. Nothing was calculated and the pay run was not changed."
    )


def _unreadable_pack_message(resolution, pack_id: str) -> str:
    """The message for a pack that is verified but cannot be read.

    The pack is in force and it has been verified, and the engine still
    cannot calculate from it: the table it needs is written in a way the
    engine does not read. The message says that, and it says that nothing
    was calculated. It carries no rate, no bound and no threshold: what is
    wrong with the pack is in the ``required`` list, which names the table
    and the band and not the values.
    """
    jurisdiction = resolution.jurisdiction or "(none recorded)"
    return (
        f"Payroll for jurisdiction '{jurisdiction}' cannot be calculated on "
        f"{resolution.pay_date.isoformat()}: the rule pack '{pack_id}' is "
        f"verified, but the engine cannot read its rate tables. Nothing was "
        f"calculated and the pay run was not changed."
    )


def _record_refusal(db: Session, run: PayRun, u: User, details: dict) -> None:
    """Write the audit row that records the refusal.

    This is the only thing the refusal writes. The row says that the
    calculation was refused and why; it carries no pay figure, because
    nothing was calculated.
    """
    record_audit(
        db,
        u,
        "refuse_pay_run_calculation",
        "PayRun",
        run.id,
        details=(
            f"refused: jurisdiction={details.get('jurisdiction') or '(none)'} "
            f"pay_date={details.get('pay_date')} "
            f"pack_status={details.get('pack_status')}"
        ),
    )
    db.commit()


def _record_payslip_refusal(db: Session, run: PayRun, u: User, code: str, details: dict) -> None:
    """Write the audit row that records a refused direct payslip write.

    The row names the code and the state found. It carries no amount: the
    caller-supplied figure was refused and is not written anywhere.
    """
    record_audit(
        db,
        u,
        "refuse_payslip_create",
        "PayRun",
        run.id,
        details=(
            f"refused: code={code} jurisdiction={details.get('jurisdiction') or '(none)'} "
            f"pay_date={details.get('pay_date')} "
            f"pack_status={details.get('pack_status')}"
        ),
    )
    db.commit()


def _approved_inputs(
    db: Session,
    employee_id: int,
    start: date,
    end: date,
) -> dict[str, Any]:
    """The approved time and leave of a period that a payslip may pay from.

    Only rows an approver has accepted are returned as inputs. A time entry
    still in draft is counted separately and **excluded**: a payslip that
    paid unapproved hours is exactly the defect this function closes, so the
    count is recorded as an exception rather than silently ignored.

    Leave is pro-rated to the part of the request that falls inside the
    period, because a request may straddle two pay periods and paying the
    whole of it twice would overstate the deduction. Paid leave is recorded
    for traceability but is not deducted — only leave of an unpaid type
    reduces pay.
    """
    approved = (
        db.query(TimeEntry)
        .filter(
            TimeEntry.employee_id == employee_id,
            TimeEntry.work_date >= start,
            TimeEntry.work_date <= end,
            TimeEntry.status == "Approved",
        )
        .all()
    )
    pending = (
        db.query(TimeEntry)
        .filter(
            TimeEntry.employee_id == employee_id,
            TimeEntry.work_date >= start,
            TimeEntry.work_date <= end,
            TimeEntry.status != "Approved",
        )
        .count()
    )

    requests = (
        db.query(LeaveRequest, LeaveType.is_paid)
        .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "Approved",
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
        .all()
    )

    paid_days = Decimal("0")
    unpaid_days = Decimal("0")
    for request, is_paid in requests:
        span = (request.end_date - request.start_date).days + 1
        overlap_start = max(request.start_date, start)
        overlap_end = min(request.end_date, end)
        overlap = (overlap_end - overlap_start).days + 1
        share = Decimal(str(request.working_days or 0)) * Decimal(overlap) / Decimal(max(span, 1))
        if is_paid:
            paid_days += share
        else:
            unpaid_days += share

    # Summed in Decimal: the hours are money inputs and a float sum is the
    # one place a rounding artefact could enter before the engine sees them.
    worked_hours = sum(
        (Decimal(str(entry.worked_hours or 0)) for entry in approved), Decimal("0")
    )
    overtime_hours = sum(
        (Decimal(str(entry.overtime_hours or 0)) for entry in approved), Decimal("0")
    )

    return {
        "approved_time_entries": len(approved),
        "approved_worked_hours": float(worked_hours),
        "approved_overtime_hours": float(overtime_hours),
        "unapproved_time_entries": pending,
        "approved_leave_requests": len(requests),
        "paid_leave_days": float(paid_days.quantize(Decimal("0.01"))),
        "unpaid_leave_days": float(unpaid_days.quantize(Decimal("0.01"))),
    }


def _proration_for_employee(
    db: Session,
    employee_id: int,
    period_start: date,
    period_end: date,
    base_salary: Decimal,
) -> tuple[Decimal, dict[str, Any] | None]:
    """Prorate a period salary when the employee's record changed mid-period.

    Effective-dated employment history rows for ``base_salary``, ``pay_frequency``
    or ``status`` whose ``effective_from`` falls inside the period mean the
    employee was not on this salary for the whole period. The base is prorated
    by days worked: days from the change date to the period end, divided by
    the period's days.

    Returns the (possibly prorated) base salary and an optional proration basis
    record to merge into ``inputs_json``. When no mid-period change exists the
    base is unchanged and the basis is ``None``.
    """
    period_days = Decimal((period_end - period_start).days + 1)
    if period_days <= 0:
        return base_salary, None

    changes = (
        db.query(EmployeeHistory)
        .filter(
            EmployeeHistory.employee_id == employee_id,
            EmployeeHistory.field.in_(("base_salary", "pay_frequency", "status")),
            EmployeeHistory.effective_from >= period_start,
            EmployeeHistory.effective_from <= period_end,
        )
        .order_by(EmployeeHistory.effective_from.asc())
        .all()
    )

    if not changes:
        return base_salary, None

    # The first change within the period is the one that splits the period.
    # Days worked are counted from the change date to the period end inclusive.
    change_date = changes[0].effective_from
    days_worked = Decimal((period_end - change_date).days + 1)
    if days_worked < 0:
        days_worked = Decimal("0")

    prorated_base = (base_salary * days_worked / period_days).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    basis = {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "days_worked": float(days_worked),
        "period_days": float(period_days),
        "salary_effective_date": change_date.isoformat(),
        "prorated_base": str(prorated_base),
        "original_base": str(base_salary),
    }
    return prorated_base, basis


def _calculate_payslips(db: Session, run: PayRun, u: User) -> PayRun:
    """Generate payslips for a Draft pay run. See process_run for the wrapper.

    The payslips are computed from the rule pack that is in force for the
    run's jurisdiction on the pay date of its period, and only from a pack
    that is `verified`. A jurisdiction without such a pack is refused before
    anything is calculated, and the refusal writes nothing but the audit row
    that records it.
    """
    from app.models.employee import Employee
    from app.rules.engine import (
        calculate_payslip_from_pack,
        period_hours,
        rate_table_problems,
    )
    from app.rules.money import ZERO, to_decimal
    from app.rules.resolver import resolve_rule_pack

    period = db.query(PayrollPeriod).filter(PayrollPeriod.id == run.period_id).first()
    if not period:
        raise not_found(f"Payroll period {run.period_id}")

    # --- The gate ---------------------------------------------------------- #
    #
    # A pay figure computed without a verified rule is a figure the product
    # cannot stand behind, so the pack is resolved before anything is
    # calculated and the run is refused when there is not one.
    jurisdiction = (run.jurisdiction or "").strip().upper()
    resolution = resolve_rule_pack(jurisdiction, period.pay_date)
    if not resolution.is_verified:
        details = resolution.details()
        if not jurisdiction:
            # A run that predates the jurisdiction cannot name one, and no
            # pack can be resolved for it. It is refused rather than
            # calculated against a guess.
            details["required"] = [
                "this pay run does not record a jurisdiction, so no rule pack "
                "can be resolved for it: it was created before a pay run named "
                "its jurisdiction. Create a new run that names the "
                "jurisdiction whose rules apply to it."
            ]
        _record_refusal(db, run, u, details)
        raise validation(
            "rule_pack_not_verified",
            _refusal_message(resolution),
            **details,
        )

    pack = resolution.pack
    assert pack is not None  # resolution.is_verified says there is one

    # A pack the engine cannot read exactly is refused before anything is
    # calculated. The pack may be verified and still be unusable: a band
    # table that states no rate, or a tax table written as a flat map, says
    # something the engine cannot turn into a figure. A wrong pay figure is
    # worse than a refusal, so the run is refused.
    unreadable = rate_table_problems(pack)
    if unreadable:
        details = resolution.details()
        details["required"] = list(unreadable)
        _record_refusal(db, run, u, details)
        raise validation(
            "rule_pack_not_verified",
            _unreadable_pack_message(resolution, pack.meta.pack_id),
            **details,
        )

    # Refuse to run twice and leave duplicate payslips. The unique constraint
    # on (pay_run_id, employee_id) is the database-level backstop.
    existing = db.query(PaySlip).filter(PaySlip.pay_run_id == run.id).count()
    if existing:
        raise conflict(
            "pay_run_already_processed",
            f"Pay run already has {existing} payslip(s); it cannot be reprocessed",
            pay_run_id=run.id,
        )

    # Only employees who are currently employed are paid. Terminated staff keep
    # their historical slips but must not receive new ones.
    employees = {
        e.id: e
        for e in db.query(Employee)
        .filter(Employee.status.in_(("Active", "On Leave")))
        .all()
    }
    all_profiles = db.query(EmployeePayProfile).all()
    profiles = [p for p in all_profiles if p.employee_id in employees]

    # Employees with a pay profile but no active record are reported rather
    # than silently dropped.
    skipped = [p.employee_id for p in all_profiles if p.employee_id not in employees]

    total_gross = ZERO
    total_deductions = ZERO
    total_net = ZERO

    for profile in profiles:
        frequency = (profile.pay_frequency or "Monthly").strip().lower()
        inputs = _approved_inputs(
            db, profile.employee_id, period.start_date, period.end_date
        )
        base = to_decimal(profile.base_salary)
        # Proration: if the employee's salary, frequency or status changed
        # mid-period, prorate the base by days worked and record the basis
        # traceably in inputs_json.
        prorated_base, proration_basis = _proration_for_employee(
            db,
            profile.employee_id,
            period.start_date,
            period.end_date,
            base,
        )
        if proration_basis is not None:
            base = prorated_base
            inputs = {**inputs, **proration_basis}
        # The hourly rate is the period salary spread over the period's hours,
        # so overtime is paid at the employee's own rate rather than a number
        # the product invented.
        hourly_rate = (
            (base / period_hours(frequency)).quantize(Decimal("0.01"))
            if base > 0
            else Decimal("0")
        )
        # --- India slice 5: Basic+DA split + tenure for gratuity ---------------
        basic_pct = getattr(profile, "basic_pct", None)
        # Tenure for gratuity: pay_date - hire_date in years
        tenure_years = None
        try:
            emp = employees.get(profile.employee_id)
            if emp and emp.hire_date and period.pay_date:
                days = (period.pay_date - emp.hire_date).days
                # Guard against future hire dates
                if days < 0:
                    days = 0
                tenure_years = Decimal(days) / Decimal("365.25")
        except Exception:
            tenure_years = None
        # Also surface tenure/basic_pct in inputs_json for audit/F&F
        if tenure_years is not None:
            inputs = {**inputs, "tenure_years": float(tenure_years)}
        if basic_pct is not None:
            try:
                inputs = {**inputs, "basic_pct": float(basic_pct)}
            except Exception:
                pass
        # Optional arrears/encashment days from inputs (default 0)
        arrears_days = to_decimal(inputs.get("arrears_days", 0))
        leave_encashment_days = to_decimal(inputs.get("leave_encashment_days", 0))
        result = calculate_payslip_from_pack(
            pack=pack,
            base_salary=base,
            pay_frequency=frequency,
            # Only approved time and leave are consumed. Draft entries are
            # counted in the inputs record and excluded from the figure.
            hours_worked=to_decimal(inputs["approved_worked_hours"]),
            overtime_hours=to_decimal(inputs["approved_overtime_hours"]),
            overtime_hourly_rate=hourly_rate,
            leave_days=to_decimal(inputs["unpaid_leave_days"]),
            # The pack's own tax table governs when it has one. The rate on
            # the profile is the customer's configured fallback, used only
            # when the pack says nothing about tax.
            tax_withholding_override=to_decimal(profile.tax_withholding),
            pt_state=getattr(profile, "pt_state", None),
            basic_pct=to_decimal(basic_pct) if basic_pct is not None else None,
            tenure_years=tenure_years,
            leave_encashment_days=leave_encashment_days,
            arrears_days=arrears_days,
            jurisdiction=jurisdiction,
        )

        db.add(
            PaySlip(
                pay_run_id=run.id,
                employee_id=profile.employee_id,
                gross_pay=result.gross,
                net_pay=result.net,
                total_deductions=result.total_deductions,
                # The statutory contributions the pack computed. The
                # employer's money is not part of the employee's pay, and it
                # is not in the deductions either: without a column of its
                # own it is lost the moment the payslip is written.
                employee_contributions=result.total_employee_contributions,
                employer_contributions=result.total_employer_contributions,
                earnings_json=_lines_as_json(result.earnings),
                deductions_json=_lines_as_json(result.deductions),
                inputs_json=json.dumps(inputs, sort_keys=True),
                status="Draft",
                currency=run.currency,
            )
        )
        total_gross += result.gross
        total_deductions += result.total_deductions
        total_net += result.net

    run.status = "Processing"
    run.processed_by = u.id
    run.processed_at = datetime.now(timezone.utc)
    run.total_gross = total_gross
    run.total_deductions = total_deductions
    run.total_net = total_net
    run.headcount = len(profiles)
    run.rule_pack_id = pack.meta.pack_id
    if skipped:
        # Surfaced to the operator so inactive employees are never a silent gap.
        run.warning = (
            f"{len(skipped)} employee(s) with a pay profile were not active and "
            f"were excluded: {skipped}"
        )
    db.add(run)
    db.commit()
    db.refresh(run)
    record_audit(
        db,
        u,
        "process_pay_run",
        "PayRun",
        run.id,
        details=(
            f"{len(profiles)} payslips, {len(skipped)} skipped, "
            f"rule pack {pack.meta.pack_id} v{pack.meta.version}"
        ),
    )
    db.commit()
    return run


@router.get("/payslips", response_model=list[PaySlipOut], operation_id="payrollListPayslips")
def list_payslips(
    pay_run_id: int | None = None,
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ALL_ROLES)),
):
    q = db.query(PaySlip)
    q = apply_visibility(q, PaySlip.employee_id, u, db)
    if pay_run_id:
        q = q.filter(PaySlip.pay_run_id == pay_run_id)
    if employee_id:
        ensure_can_view_employee(db, u, employee_id)
        q = q.filter(PaySlip.employee_id == employee_id)
    return q.order_by(PaySlip.id.desc()).all()


@router.get("/payslips/{slip_id}", response_model=PaySlipOut, operation_id="payrollGetPayslip")
def get_payslip(
    slip_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ALL_ROLES)),
):
    slip = db.query(PaySlip).filter(PaySlip.id == slip_id).first()
    if not slip:
        raise not_found(f"Payslip {slip_id}")
    ensure_can_view_employee(db, u, slip.employee_id)
    return slip


def _stored_pack_for_payslip(run: PayRun | None, jurisdiction: str, pay_date: date):
    """The rule pack a payslip was calculated from, or None when it cannot be found.

    The pack is the one the run recorded (``run.rule_pack_id``), matched by id,
    jurisdiction and effective period in the pack directory. Exactly one match
    is required; anything else is None, and the caller refuses.
    """
    from app.rules.resolver import load_packs, pack_directory

    if run is None or not run.rule_pack_id:
        return None
    packs, _failures = load_packs(pack_directory())
    matches = [
        pack
        for pack in packs
        if pack.meta.pack_id == run.rule_pack_id
        and pack.meta.jurisdiction_country.upper() == jurisdiction
        and pack.is_effective_on(pay_date)
    ]
    return matches[0] if len(matches) == 1 else None


@router.get("/payslips/{slip_id}/pdf", operation_id="payrollGetPayslipPdf")
def get_payslip_pdf(
    slip_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ALL_ROLES)),
):
    """Render a printable payslip (HTML) with India statutory breakdown.

    The content is the same data the run wrote (deductions_json/earnings_json),
    not a recalculation. When the governing pack is pending_verification the
    page carries the watermark prescribed in docs/PAYROLL.md §3.3.
    US payslips render without PT/TDS lines — the pack simply has no such
    lines, so nothing is invented in the browser.
    """
    slip = db.query(PaySlip).filter(PaySlip.id == slip_id).first()
    if not slip:
        raise not_found(f"Payslip {slip_id}")
    ensure_can_view_employee(db, u, slip.employee_id)

    run = db.query(PayRun).filter(PayRun.id == slip.pay_run_id).first()
    period = None
    if run:
        period = db.query(PayrollPeriod).filter(PayrollPeriod.id == run.period_id).first()
    employee = db.get(Employee, slip.employee_id)

    jurisdiction = (run.jurisdiction or "").strip().upper() if run else ""
    pay_date = period.pay_date if period and period.pay_date else date.today()
    # Fail closed. The page shows the stored pack: the one the run recorded
    # when it was processed (run.rule_pack_id), found by id in the pack
    # directory. It is never replaced by a hard-coded id and version. When
    # that pack cannot be found, the page is refused.
    unresolved_details = {
        "jurisdiction": jurisdiction,
        "pay_date": pay_date.isoformat(),
    }
    stored_pack = _stored_pack_for_payslip(run, jurisdiction, pay_date)
    if stored_pack is None:
        raise validation(
            "rule_pack_not_verified",
            "This payslip cannot be rendered: the rule pack it was calculated "
            "from cannot be found. Nothing was rendered.",
            **unresolved_details,
            pack_status="absent",
        )
    pack_status = "verified" if stored_pack.is_verified() else stored_pack.meta.status
    # A pending or draft pack is rendered with the documented watermark
    # (docs/PAYROLL.md §3.3). Any other state that is not verified is refused.
    if pack_status not in ("verified", "pending_verification", "draft"):
        raise validation(
            "rule_pack_not_verified",
            "This payslip cannot be rendered: the rule pack it names is not in a "
            "state that can be shown. Nothing was rendered.",
            **unresolved_details,
            pack_status=pack_status,
        )
    is_pending = pack_status != "verified"
    pack_id = stored_pack.meta.pack_id
    pack_version = stored_pack.meta.version
    pack_effective_from = stored_pack.meta.effective_from.isoformat() if stored_pack.meta.effective_from else ""
    pack_effective_to = stored_pack.meta.effective_to.isoformat() if stored_pack.meta.effective_to else ""

    # Parse stored lines — same data as deductions_json/earnings_json, not recomputed
    earnings_lines = []
    deductions_lines = []
    try:
        if slip.earnings_json:
            earnings_lines = json.loads(slip.earnings_json)
    except Exception:
        earnings_lines = []
    try:
        if slip.deductions_json:
            deductions_lines = json.loads(slip.deductions_json)
    except Exception:
        deductions_lines = []

    # Statutory grouping for display
    # Display parity: format stored 2dp Decimals for PDF.
    # Stored slip totals/line amounts are already quantised to cents via
    # money() (ROUND_HALF_UP), so str() is the canonical 2dp text and CSV
    # carries it verbatim. This formatter only renders that text (f"{d:.2f}");
    # it must never requantise: Python's format uses round-half-even while
    # money() uses HALF_UP, so they differ on unquantised x.xx5 inputs
    # (e.g. "2.675" -> HALF_UP "2.68" vs format "2.67"). Stored values are
    # already 2dp, hence no divergence in practice — the edge is pinned by
    # test_display_parity.py. Scope is IN-INR only; JPY/KWD Intl defaults
    # are out of scope (verified IN runs are INR-gated).
    def _money(v):
        try:
            d = Decimal(str(v))
            return f"{d:.2f}"
        except Exception:
            return str(v)

    emp_name = f"{employee.first_name} {employee.last_name}" if employee and employee.first_name else f"Employee #{slip.employee_id}"
    emp_code = employee.employee_id if employee else str(slip.employee_id)
    period_name = period.name if period else f"Period #{run.period_id if run else '?'}"
    period_dates = f"{period.start_date.isoformat()} – {period.end_date.isoformat()}" if period and period.start_date and period.end_date else ""
    pay_date_str = period.pay_date.isoformat() if period and period.pay_date else pay_date.isoformat()

    watermark_html = ""
    if is_pending:
        watermark_html = (
            '<div data-testid="pdf-watermark" style="border:2px dashed #d97706; color:#92400e; background:#fef3c7; padding:8px 12px; text-align:center; font-weight:700; letter-spacing:0.04em; margin:12px 0;">'
            'configurable calculation — pending_verification — not statutory/filing-ready'
            '</div>'
            '<div style="position:fixed; inset:0; display:flex; align-items:center; justify-content:center; opacity:0.07; font-size:72px; font-weight:900; color:#b45309; transform:rotate(-18deg); pointer-events:none; z-index:0;">PENDING VERIFICATION</div>'
        )
    verified_badge = ""
    if not is_pending and pack_id and pack_version:
        verified_badge = f'<span style="font-family:monospace; background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0; padding:2px 6px; border-radius:4px;">{pack_id} v{pack_version}</span>'
    elif is_pending and pack_id:
        verified_badge = f'<span style="font-family:monospace; background:#fef3c7; color:#92400e; border:1px solid #fcd34d; padding:2px 6px; border-radius:4px;">{pack_id} v{pack_version} · pending_verification</span>'

    def _line_rows(lines):
        rows = ""
        for ln in lines:
            code = ln.get("code","")
            name = ln.get("name","")
            amt = _money(ln.get("amount","0"))
            rule_id = ln.get("rule_id") or "—"
            calc = ln.get("calculation") or ln.get("input_source") or "—"
            rows += f"<tr><td style='font-family:monospace; font-size:11px;'>{code}</td><td>{name}</td><td style='text-align:right; font-variant-numeric:tabular-nums;'>{amt}</td><td style='font-size:11px; color:#6b7280;'>{rule_id}</td><td style='font-size:11px; color:#6b7280;'>{calc}</td></tr>"
        return rows or "<tr><td colspan='5' style='color:#6b7280; text-align:center;'>No lines</td></tr>"

    earnings_rows = _line_rows(earnings_lines)
    deductions_rows = _line_rows(deductions_lines)

    # Statutory summary chips
    statutory_chips = ""
    has_tax = any(str(l.get("code","")).startswith("TAX_") for l in deductions_lines)
    has_rebate = any(str(l.get("code",""))=="REBATE_87A" for l in deductions_lines)
    has_pf_ee = any(str(l.get("code",""))=="PF_EE" for l in deductions_lines)
    has_pf_er = False
    # employer contributions are in deductions_json? Actually employer lines are separate but we include deductions only; for pdf we also render employer contributions if present in slip.employer_contributions
    pt_codes = [str(l.get("code","")) for l in deductions_lines if str(l.get("code","")).startswith("PT_")]
    statutory_items = []
    if any(str(l.get("code",""))=="BASIC" for l in earnings_lines):
        statutory_items.append("BASIC")
    if has_tax:
        statutory_items.append("TAX_* (bands)")
    if has_rebate:
        statutory_items.append("REBATE_87A")
    if has_pf_ee:
        statutory_items.append("PF_EE/ER")
    # ESI
    if any(str(l.get("code","")).startswith("ESI_") for l in deductions_lines):
        statutory_items.append("ESI_EE/ER")
    if pt_codes:
        statutory_items.extend(pt_codes)
    if statutory_items:
        statutory_chips = "<p style='font-size:11px; color:#374151; background:#f9fafb; border:1px solid #e5e7eb; padding:6px 8px; border-radius:6px;'>Statutory breakdown: " + " · ".join(statutory_items) + "</p>"

    inputs_pretty = ""
    if slip.inputs_json:
        try:
            inputs_obj = json.loads(slip.inputs_json)
            inputs_pretty = json.dumps(inputs_obj, indent=2, sort_keys=True)
        except Exception:
            inputs_pretty = slip.inputs_json

    gross_str = _money(slip.gross_pay)
    ded_str = _money(slip.total_deductions)
    net_str = _money(slip.net_pay)
    cur = slip.currency or (run.currency if run else "") or ("INR" if jurisdiction=="IN" else "USD")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Payslip #{slip.id} — {emp_name}</title>
<style>
 @media print {{ @page {{ margin: 16mm; }} .no-print {{ display:none; }} }}
 body {{ font-family: ui-sans-system, system-ui, -apple-system, sans-serif; color:#111827; line-height:1.5; max-width:860px; margin:0 auto; padding:24px; position:relative; }}
 table {{ border-collapse: collapse; width:100%; }}
 th,td {{ border:1px solid #e5e7eb; padding:6px 8px; text-align:left; font-size:12px; }}
 th {{ background:#f9fafb; font-size:11px; text-transform:uppercase; letter-spacing:0.03em; color:#374151; }}
 .num {{ text-align:right; }}
</style>
</head>
<body>
<div class="no-print" style="margin-bottom:12px;"><button onclick="window.print()" style="padding:8px 14px; border:1px solid #d1d5db; border-radius:6px; background:#fff; cursor:pointer;">Print / Save as PDF</button> <span style="font-size:12px; color:#6b7280; margin-left:8px;">Use browser Print → Save as PDF</span></div>
{watermark_html}
<header style="border-bottom:2px solid #111827; padding-bottom:12px; margin-bottom:16px;">
  <h1 style="margin:0; font-size:20px;">Payslip #{slip.id} · {emp_name} <span style="font-weight:400; color:#6b7280;">({emp_code})</span></h1>
  <p style="margin:4px 0 0; font-size:12px; color:#6b7280;">Period: {period_name} · {period_dates} · Pay date: {pay_date_str} · Jurisdiction: {jurisdiction or "—"} · Currency: {cur} · Status: {slip.status} {verified_badge}</p>
  <p style="margin:6px 0 0; font-size:11px; color:#6b7280;">The figures below are what the run wrote (deductions_json / earnings_json). Nothing on this page is recalculated in the browser.</p>
</header>

<section style="display:grid; grid-template-columns: repeat(4,1fr); gap:12px; margin-bottom:16px;">
  <div style="border:1px solid #e5e7eb; border-radius:8px; padding:12px; text-align:center;"><div style="font-size:11px; color:#6b7280; text-transform:uppercase;">Gross</div><div style="font-size:18px; font-weight:700; font-variant-numeric:tabular-nums;">{gross_str} <span style="font-size:11px; color:#6b7280;">{cur}</span></div></div>
  <div style="border:1px solid #e5e7eb; border-radius:8px; padding:12px; text-align:center;"><div style="font-size:11px; color:#6b7280; text-transform:uppercase;">Deductions</div><div style="font-size:18px; font-weight:700; font-variant-numeric:tabular-nums;">{ded_str} <span style="font-size:11px; color:#6b7280;">{cur}</span></div></div>
  <div style="border:1px solid #e5e7eb; border-radius:8px; padding:12px; text-align:center;"><div style="font-size:11px; color:#6b7280; text-transform:uppercase;">Net</div><div style="font-size:18px; font-weight:700; font-variant-numeric:tabular-nums;">{net_str} <span style="font-size:11px; color:#6b7280;">{cur}</span></div></div>
  <div style="border:1px solid #e5e7eb; border-radius:8px; padding:12px; text-align:center;"><div style="font-size:11px; color:#6b7280; text-transform:uppercase;">Employee ER</div><div style="font-size:14px; font-weight:600; font-variant-numeric:tabular-nums;">{ _money(slip.employer_contributions) if slip.employer_contributions is not None else "—"} <span style="font-size:11px; color:#6b7280;">{cur}</span></div><div style="font-size:10px; color:#6b7280;">Employer contributions</div></div>
</section>

{statutory_chips}

<section style="margin-top:16px;">
  <h2 style="font-size:14px; margin:0 0 6px;">Earnings</h2>
  <table><thead><tr><th>Code</th><th>Name</th><th class="num">Amount</th><th>Rule</th><th>Calculation</th></tr></thead><tbody>{earnings_rows}</tbody></table>
</section>

<section style="margin-top:16px;">
  <h2 style="font-size:14px; margin:0 0 6px;">Deductions — statutory breakdown (TDS bands + rebate, PF/ESI EE, PT)</h2>
  <table><thead><tr><th>Code</th><th>Name</th><th class="num">Amount</th><th>Rule</th><th>Calculation</th></tr></thead><tbody>{deductions_rows}</tbody></table>
  <p style="font-size:11px; color:#6b7280; margin-top:6px;">Includes BASIC (earnings), TAX_* per band, REBATE_87A (negative), PF_EE/ESI_EE (employee), PT_&#123;STATE&#125; where applicable; employer PF_ER/ESI_ER shown in summary above. Amounts are exact decimal strings from the run.</p>
</section>

<section style="margin-top:16px; border:1px solid #e5e7eb; border-radius:8px; padding:12px;">
  <h2 style="font-size:12px; margin:0 0 6px; text-transform:uppercase; letter-spacing:0.04em; color:#374151;">Lineage</h2>
  <dl style="display:grid; grid-template-columns: 160px 1fr; gap:6px 12px; font-size:12px; margin:0;">
    <dt style="color:#6b7280;">Rule pack</dt><dd style="margin:0; font-family:monospace;">{pack_id or "—"} v{pack_version or "?"}</dd>
    <dt style="color:#6b7280;">Effective</dt><dd style="margin:0; font-family:monospace;">{pack_effective_from or "—"} → {pack_effective_to or "open"}</dd>
    <dt style="color:#6b7280;">Jurisdiction / Currency</dt><dd style="margin:0;">{jurisdiction or "—"} · {cur}</dd>
    <dt style="color:#6b7280;">Pay run / Payslip</dt><dd style="margin:0;">Run #{run.id if run else "?"} · Slip #{slip.id} · Period #{period.id if period else "?"}</dd>
    <dt style="color:#6b7280;">Inputs</dt><dd style="margin:0;"><pre style="background:#f9fafb; border:1px solid #e5e7eb; padding:8px; border-radius:6px; overflow:auto; font-size:11px; max-height:220px;">{inputs_pretty or "— (no inputs_json; written before the record existed)"}</pre></dd>
  </dl>
  <p style="font-size:11px; color:#6b7280; margin-top:8px;">India FY 2025-26: TDS as per §115BAC new regime; PF/ESI as per EPF/ESI Acts; PT as per state Acts; Gratuity not included. Employer PF 12% flat is v1 simplification — see verification checklist in the rule pack.</p>
</section>

<footer style="margin-top:18px; padding-top:12px; border-top:1px solid #e5e7eb; font-size:10px; color:#6b7280; text-align:center;">This document was rendered from stored payslip lines. No amount was recalculated in the browser.</footer>
</body>
</html>
"""
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="payslip_{slip_id}.pdf"'},
    )


def _run_is_locked(db: Session, pay_run_id: int) -> PayRun | None:
    """Return the run if it is finalized/paid, else None."""
    run = db.query(PayRun).filter(PayRun.id == pay_run_id).first()
    if run and run.status in ("Finalized", "Paid"):
        return run
    return None


@router.post("/payslips", response_model=PaySlipOut, status_code=201, operation_id="payrollCreatePayrollpayslips")
def create_payslip(payload: PaySlipCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    # A finalized run is immutable: no silent edits to paid results.
    locked = _run_is_locked(db, payload.pay_run_id)
    if locked:
        raise conflict(
            "pay_run_already_finalised",
            f"Pay run {payload.pay_run_id} is {locked.status}; payslips can no longer be added",
            pay_run_id=payload.pay_run_id,
        )
    # Database-level uniqueness is enforced too; this gives a clean 409 instead
    # of an IntegrityError bubbling out as a 500.
    dupe = (
        db.query(PaySlip)
        .filter(
            PaySlip.pay_run_id == payload.pay_run_id,
            PaySlip.employee_id == payload.employee_id,
        )
        .first()
    )
    if dupe:
        raise conflict(
            "duplicate_natural_key",
            "A payslip already exists for this employee in this pay run",
            entity="payslip",
            field="employee_id",
            value=payload.employee_id,
        )
    run = db.get(PayRun, payload.pay_run_id)
    if run is None:
        raise not_found(f"Pay run {payload.pay_run_id}")

    # --- The gate ---------------------------------------------------------- #
    #
    # This endpoint writes a payslip from amounts the caller supplies. No rule
    # pack is consulted to produce them, so a pay figure written here is not
    # one the product can stand behind. Two refusals, both before any write:
    #   1. the jurisdiction has no verified pack in force on the pay date:
    #      refused with rule_pack_not_verified, as the pay-run path does;
    #   2. the pack is verified, but the amounts still came from the caller:
    #      refused with caller_supplied_amounts_refused, in every case.
    # A refusal writes no payslip and changes nothing on the run. It records
    # an audit row that says the write was refused and carries no amount.
    period = db.get(PayrollPeriod, run.period_id)
    if period is None:
        raise not_found(f"Payroll period {run.period_id}")
    jurisdiction = (run.jurisdiction or "").strip().upper()
    from app.rules.resolver import resolve_rule_pack

    resolution = resolve_rule_pack(jurisdiction, period.pay_date)
    if not resolution.is_verified:
        details = resolution.details()
        if not jurisdiction:
            details["required"] = [
                "this pay run does not record a jurisdiction, so no rule pack "
                "can be resolved for it: it was created before a pay run named "
                "its jurisdiction. Create a new run that names the "
                "jurisdiction whose rules apply to it."
            ]
        _record_payslip_refusal(db, run, u, "rule_pack_not_verified", details)
        raise validation(
            "rule_pack_not_verified",
            _refusal_message(resolution),
            **details,
        )
    _record_payslip_refusal(
        db,
        run,
        u,
        "caller_supplied_amounts_refused",
        {
            "jurisdiction": jurisdiction,
            "pay_date": period.pay_date.isoformat() if period.pay_date else None,
            "pack_status": resolution.pack_status,
            "required": [
                "payslip amounts must be calculated from the verified rule pack by "
                "processing the pay run; amounts supplied by the caller are not accepted"
            ],
        },
    )
    raise validation(
        "caller_supplied_amounts_refused",
        "Payslip amounts supplied by the caller are not accepted. Process the pay "
        "run so that the amounts are calculated from the verified rule pack. "
        "Nothing was written.",
        pay_run_id=run.id,
    )
