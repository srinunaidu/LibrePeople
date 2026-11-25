import json
import re
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, ALL_ROLES, MANAGER_ROLES, REPORTS_ROLES, get_db, require_roles
from app.core.errors import ApiError, ErrorCategory
from app.core.visibility import metric_visible_for_role
from app.crud import crud_reports as crud
from app.services import metrics
from app.models.user import User
from app.schemas.audit import AuditLogOut

router = APIRouter()


@router.get("/dashboard", operation_id="reportsGetReportsdashboard")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    """One-call summary used by the home dashboard."""
    return crud.dashboard(db)


@router.get("/headcount", operation_id="reportsGetReportsheadcount")
def headcount(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    return crud.headcount_report(db)


@router.get("/leave", operation_id="reportsGetReportsleave")
def leave(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    return crud.leave_report(db)


@router.get("/labor-cost", operation_id="reportsGetReportslaborcost")
def labor_cost(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    return crud.labor_cost_report(db)


@router.get("/attendance", operation_id="reportsGetReportsattendance")
def attendance(
    day: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Any:
    return crud.attendance(db, day or date.today())


@router.get("/audit", response_model=list[AuditLogOut], operation_id="reportsGetReportsaudit")
def audit(
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """The audit trail.

    Restricted to HR / SuperAdmin. It previously used
    `get_current_active_user`, which meant any Associate could read the whole
    system history — every actor, action and record id across every module.
    Administrators who need it during an investigation should be audited in
    turn; see docs/ENTERPRISE_AUDIT.md P1-3.
    """
    return crud.audit_report(db, limit=limit)

# ==========================================================================
# Metric catalogue
#
# Every figure below is served with its definition. The legacy endpoints above
# remain for existing screens; these add the contract the reporting brief asks
# for and fix three reconciliation defects in the old calculations.
# ==========================================================================


@router.get("/metrics/catalogue", operation_id="reportsGetReportsmetricscatalogue")
def metrics_catalogue(
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    """Every metric with its meaning, calculation, source and limitations."""
    return {"metrics": metrics.catalogue()}


@router.get("/metrics/{key}", operation_id="reportsGetReportsmetrics")
def metric_value(
    key: str,
    year: int | None = Query(default=None, description="Entitlement year for leave metrics"),
    day: date | None = Query(default=None, description="Work date for attendance metrics"),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """One metric's value together with its definition."""
    if key not in metrics.CATALOGUE:
        raise HTTPException(status_code=404, detail=f"Unknown metric: {key}")
    params: dict = {}
    if year is not None:
        params["year"] = year
    if day is not None:
        params["day"] = day

    # Compensation and workforce figures are HR-only. Attendance is visible to
    # managers; it is already scoped by the caller's visibility elsewhere.
    if not metric_visible_for_role(current_user.role, key):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this metric",
        )

    try:
        return metrics.compute(db, key, params)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown metric: {key}")


@router.get("/metrics", operation_id="reportsListReportsmetrics")
def metrics_summary(
    year: int | None = Query(default=None),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
    db: Session = Depends(get_db),
) -> Any:
    """A consistent headline set, each with its definition attached.

    Metrics the caller is not permitted to see are omitted rather than zeroed,
    so an absent metric is visibly different from a metric that is genuinely 0.
    """
    keys = [
        "headcount.active",
        "headcount.by_department",
        "headcount.terminated",
        "leave.entitled_days",
        "leave.used_days",
        "labor.monthly_cost",
        "attendance.hours",
        "approvals.pending",
    ]
    permitted, withheld = [], []
    for key in keys:
        if metric_visible_for_role(current_user.role, key):
            permitted.append(key)
        else:
            withheld.append(key)

    params = {"year": year} if year is not None else {}
    result = metrics.compute_many(db, permitted, params)
    return {
        "metrics": result,
        "withheld": withheld,
        "note": (
            "Metrics you are not permitted to see are listed under 'withheld' "
            "rather than returned as zero."
        ),
    }


# --------------------------------------------------------------------------
# Workforce movement + payroll summary (LP-REP-002)
#
# Joiners / leavers / attrition read stored employment facts through the
# LP-REP-001 queries; payroll-summary reads stored payslip/run rows. None
# of these endpoints imports or calls the payroll engine. CSV/XLSX exports
# mask identifiers per the caller's role and are audit-logged.
# --------------------------------------------------------------------------

#: Workforce movement is a team view as well as an HR view: managers see
#: their own reporting line (scoped below), HR/PayrollViewer see everything.
#: Associates are outside the set and get a 403 from ``require_roles``.
WORKFORCE_REPORT_ROLES = ("SuperAdmin", "HR", "Manager", "PayrollViewer")

_MOVEMENT_COLUMNS = [
    "employee_id",
    "first_name",
    "last_name",
    "email",
    "hire_date",
    "termination_date",
    "status",
    "department",
    "legal_entity",
]

_PAYROLL_SUMMARY_COLUMNS = [
    "payslip_id",
    "pay_run_id",
    "employee_id",
    "employee_name",
    "gross",
    "net",
    "total_deductions",
    "employee_contributions",
    "employer_contributions",
    "currency",
    "pan_number",
    "aadhaar",
]


def _parse_day(value: str | None, name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail=f"{name} must be YYYY-MM-DD")


def _parse_format(value: str | None) -> str:
    fmt = (value or "json").strip().lower()
    if fmt not in ("json", "csv", "xlsx"):
        raise HTTPException(status_code=422, detail="format must be one of json, csv, xlsx")
    return fmt


def _parse_year(value: int | None) -> int:
    year = value if value is not None else date.today().year
    if year < 1900 or year > 2100:
        raise HTTPException(status_code=422, detail="year must be between 1900 and 2100")
    return year


def _movement_scope(db: Session, current_user: User) -> set[int] | None:
    """Visible employee ids for the caller, or None for unrestricted roles."""
    from app.core.visibility import resolve_visible_employee_ids

    return resolve_visible_employee_ids(db, current_user)


def _tabular(
    db: Session,
    current_user: User,
    *,
    report: str,
    rows: list[dict],
    columns: list[str],
    fmt: str,
    payload: dict | None = None,
) -> Any:
    """Render rows as JSON, or as an audited CSV/XLSX download."""
    from app.core.audit import record_audit
    from app.services import report_exports as exports

    if fmt == "csv":
        record_audit(db, current_user, "export", report, None, details=f"{len(rows)} rows, format=csv")
        db.commit()
        # NOTE — CSV framing invariant (see report_exports.rows_to_csv):
        # the body always starts with the UTF-8 BOM so Excel detects UTF-8.
        # Clients must decode with utf-8-sig; the charset below advertises
        # the encoding, the BOM carries it for sniffers that ignore headers.
        return Response(
            content=exports.rows_to_csv(rows, columns),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{report}.csv"'},
        )
    if fmt == "xlsx":
        record_audit(db, current_user, "export", report, None, details=f"{len(rows)} rows, format=xlsx")
        db.commit()
        return Response(
            content=exports.rows_to_xlsx(rows, columns),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{report}.xlsx"'},
        )
    return payload if payload is not None else {"rows": rows, "count": len(rows)}


@router.get("/joiners", operation_id="reportsGetReportsjoiners")
def joiners(
    from_date: str | None = Query(default=None, alias="from", description="Range start as YYYY-MM-DD"),
    to_date: str | None = Query(default=None, alias="to", description="Range end as YYYY-MM-DD"),
    entity_id: int | None = Query(default=None),
    department_id: int | None = Query(default=None),
    location_id: int | None = Query(default=None),
    format: str | None = Query(default=None, description="json, csv or xlsx"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_REPORT_ROLES)),
) -> Any:
    """Employees hired in [from, to], scoped to what the caller may see."""
    from app.services import report_exports as exports

    start = _parse_day(from_date, "from") or date(date.today().year, 1, 1)
    end = _parse_day(to_date, "to") or date.today()
    if start > end:
        raise HTTPException(status_code=422, detail="from must be on or before to")
    fmt = _parse_format(format)
    rows = crud.joiners_report(
        db,
        from_date=start,
        to_date=end,
        entity_id=entity_id,
        department_id=department_id,
        location_id=location_id,
        visible_ids=_movement_scope(db, current_user),
    )
    rows = [exports.mask_movement_row(r, current_user.role) for r in rows]
    return _tabular(
        db,
        current_user,
        report="report_joiners",
        rows=rows,
        columns=_MOVEMENT_COLUMNS,
        fmt=fmt,
        payload={"rows": rows, "count": len(rows), "from": start.isoformat(), "to": end.isoformat()},
    )


@router.get("/leavers", operation_id="reportsGetReportsleavers")
def leavers(
    from_date: str | None = Query(default=None, alias="from", description="Range start as YYYY-MM-DD"),
    to_date: str | None = Query(default=None, alias="to", description="Range end as YYYY-MM-DD"),
    entity_id: int | None = Query(default=None),
    department_id: int | None = Query(default=None),
    location_id: int | None = Query(default=None),
    format: str | None = Query(default=None, description="json, csv or xlsx"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_REPORT_ROLES)),
) -> Any:
    """Employees terminated in [from, to], scoped to what the caller may see."""
    from app.services import report_exports as exports

    start = _parse_day(from_date, "from") or date(date.today().year, 1, 1)
    end = _parse_day(to_date, "to") or date.today()
    if start > end:
        raise HTTPException(status_code=422, detail="from must be on or before to")
    fmt = _parse_format(format)
    rows = crud.leavers_report(
        db,
        from_date=start,
        to_date=end,
        entity_id=entity_id,
        department_id=department_id,
        location_id=location_id,
        visible_ids=_movement_scope(db, current_user),
    )
    rows = [exports.mask_movement_row(r, current_user.role) for r in rows]
    return _tabular(
        db,
        current_user,
        report="report_leavers",
        rows=rows,
        columns=_MOVEMENT_COLUMNS,
        fmt=fmt,
        payload={"rows": rows, "count": len(rows), "from": start.isoformat(), "to": end.isoformat()},
    )


@router.get("/attrition", operation_id="reportsGetReportsattrition")
def attrition(
    year: int | None = Query(default=None, description="Calendar year, e.g. 2026"),
    entity_id: int | None = Query(default=None),
    department_id: int | None = Query(default=None),
    location_id: int | None = Query(default=None),
    format: str | None = Query(default=None, description="json, csv or xlsx"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WORKFORCE_REPORT_ROLES)),
) -> Any:
    """Annual attrition from stored facts, scoped to what the caller may see."""
    yr = _parse_year(year)
    fmt = _parse_format(format)
    result = crud.attrition_report(
        db,
        year=yr,
        entity_id=entity_id,
        department_id=department_id,
        location_id=location_id,
        visible_ids=_movement_scope(db, current_user),
    )
    if fmt == "json":
        return result
    rows = [{**result["filters"], **{k: v for k, v in result.items() if k != "filters"}}]
    columns = ["year", "joiners", "leavers", "headcount_start", "headcount_end", "average_headcount", "attrition_pct"]
    return _tabular(db, current_user, report="report_attrition", rows=rows, columns=columns, fmt=fmt)


@router.get("/payroll-summary", operation_id="reportsGetReportspayrollsummary")
def payroll_summary(
    from_date: str | None = Query(default=None, alias="from", description="Range start as YYYY-MM-DD"),
    to_date: str | None = Query(default=None, alias="to", description="Range end as YYYY-MM-DD"),
    entity_id: int | None = Query(default=None),
    department_id: int | None = Query(default=None),
    format: str | None = Query(default=None, description="json, csv or xlsx"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    """Stored payslip totals in a date range — read-only, never recalculated.

    Every figure comes from ``pay_slips``/``pay_runs`` rows as written. The
    payroll engine is neither imported nor called. Identifiers are masked
    per the caller's role; CSV/XLSX exports are audit-logged.
    """
    from app.models.employee import Employee
    from app.models.payroll import PayRun, PaySlip
    from app.services import report_exports as exports

    start = _parse_day(from_date, "from")
    end = _parse_day(to_date, "to")
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="from must be on or before to")
    fmt = _parse_format(format)

    q = (
        db.query(PaySlip, PayRun, Employee)
        .join(PayRun, PaySlip.pay_run_id == PayRun.id)
        .join(Employee, PaySlip.employee_id == Employee.id)
        .order_by(PaySlip.id.asc())
    )
    if entity_id is not None:
        q = q.filter(Employee.legal_entity_id == entity_id)
    if department_id is not None:
        q = q.filter(Employee.department_id == department_id)
    # NOTE: deliberately no engine import here — stored rows only.

    def _run_day(run: PayRun):
        period = getattr(run, "period", None)
        return getattr(period, "pay_date", None) if period is not None else None

    rows: list[dict] = []
    for slip, run, emp in q.all():
        day = _run_day(run)
        if start and (day is None or day < start):
            continue
        if end and (day is None or day > end):
            continue
        pan = getattr(emp, "pan_number", None)
        if pan and isinstance(pan, str) and pan.startswith("ENCv1:"):
            try:
                from app.core.encryption import decrypt_field

                pan = decrypt_field(pan)
            except Exception:
                pass
        aadhaar = getattr(emp, "aadhaar_masked", None) or (
            f"****-****-{emp.aadhaar_last4}" if getattr(emp, "aadhaar_last4", None) else None
        )
        rows.append(
            exports.mask_payroll_row(
                {
                    "payslip_id": slip.id,
                    "pay_run_id": slip.pay_run_id,
                    "employee_id": emp.employee_id,
                    "employee_name": f"{emp.first_name} {emp.last_name}",
                    "gross": str(slip.gross_pay),
                    "net": str(slip.net_pay),
                    "total_deductions": str(slip.total_deductions),
                    "employee_contributions": str(slip.employee_contributions)
                    if slip.employee_contributions is not None
                    else None,
                    "employer_contributions": str(slip.employer_contributions)
                    if slip.employer_contributions is not None
                    else None,
                    "currency": slip.currency,
                    "pan_number": pan,
                    "aadhaar_number": aadhaar,
                },
                current_user.role,
            )
        )
    return _tabular(
        db,
        current_user,
        report="report_payroll_summary",
        rows=rows,
        columns=_PAYROLL_SUMMARY_COLUMNS,
        fmt=fmt,
        payload={"rows": rows, "count": len(rows)},
    )
#
# GET /reports/payroll?jurisdiction=IN&period=YYYY-MM
# Reuses the existing reports module. Every India report is gated on a
# verified pack: when the pack for IN on the requested pay date is
# pending_verification the endpoint refuses with 409 rule_pack_not_verified,
# mirroring the payroll process gate (docs/PAYROLL.md §3.3). No new
# migration, no pack-rate change, no engine-band tweak.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# India compliance — payroll register / TDS / PF-ESI / PT (slice 4)
#
# GET /reports/payroll?jurisdiction=IN&period=YYYY-MM
# Reuses the existing reports module. Every India report is gated on a
# verified pack: when the pack for IN on the requested pay date is
# pending_verification the endpoint refuses with 409 rule_pack_not_verified,
# mirroring the payroll process gate (docs/PAYROLL.md §3.3). No new
# migration, no pack-rate change, no engine-band tweak.
# --------------------------------------------------------------------------

_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


def _parse_period(period: str | None) -> date | None:
    if not period:
        return None
    period = period.strip()
    if not _PERIOD_RE.match(period):
        raise HTTPException(status_code=422, detail="period must be YYYY-MM")
    try:
        y, m = period.split("-")
        return date(int(y), int(m), 1)
    except Exception:
        raise HTTPException(status_code=422, detail="period must be YYYY-MM")


def _payroll_reports_refusal(jurisdiction: str, pay_date: date):
    """Build the 409 envelope for an unverified IN pack (mirrors payroll.py gate)."""
    from app.rules.resolver import resolve_rule_pack

    resolution = resolve_rule_pack(jurisdiction, pay_date)
    # Reuse the resolver's details for the required list
    details = resolution.details()
    # Human message — same shape as payroll refusal (no values leaked)
    msg = (
        f"Payroll report for jurisdiction '{jurisdiction}' cannot be generated on "
        f"{pay_date.isoformat()}: no verified rule pack is in force. "
        f"The pack is {resolution.pack_status}."
    )
    raise ApiError(
        code="rule_pack_not_verified",
        message=msg,
        category=ErrorCategory.CONFLICT,
        status_code=409,
        details=details,
    )


def _aggregate_payslip_statutory(slip) -> dict:
    """Statutory columns for one payslip from stored JSON (no recalculation)."""
    earnings = []
    deductions = []
    try:
        earnings = json.loads(slip.earnings_json) if slip.earnings_json else []
    except Exception:
        earnings = []
    try:
        deductions = json.loads(slip.deductions_json) if slip.deductions_json else []
    except Exception:
        deductions = []

    def _sum(codes: list[str]) -> Decimal:
        total = Decimal("0")
        for ln in deductions:
            if ln.get("code") in codes:
                try:
                    total += Decimal(str(ln.get("amount", "0")))
                except Exception:
                    pass
        return total

    def _sum_prefix(prefix: str) -> Decimal:
        total = Decimal("0")
        for ln in deductions:
            code = str(ln.get("code", ""))
            if code.startswith(prefix):
                try:
                    total += Decimal(str(ln.get("amount", "0")))
                except Exception:
                    pass
        return total

    basic = Decimal("0")
    for ln in earnings:
        if ln.get("code") == "BASIC":
            try:
                basic = Decimal(str(ln.get("amount", "0")))
            except Exception:
                pass

    tax = _sum_prefix("TAX_")
    rebate = Decimal("0")
    for ln in deductions:
        if ln.get("code") == "REBATE_87A":
            try:
                rebate = Decimal(str(ln.get("amount", "0")))
            except Exception:
                pass
    pf_ee = _sum(["PF_EE"])
    esi_ee = _sum(["ESI_EE"])
    pt_total = _sum_prefix("PT_")
    # PT state: first PT code e.g. PT_KA
    pt_state = None
    for ln in deductions:
        code = str(ln.get("code", ""))
        if code.startswith("PT_"):
            pt_state = code[3:]
            break

    inputs = None
    try:
        inputs = json.loads(slip.inputs_json) if slip.inputs_json else None
    except Exception:
        inputs = None

    return {
        "payslip_id": slip.id,
        "pay_run_id": slip.pay_run_id,
        "employee_id": slip.employee_id,
        "gross": str(slip.gross_pay),
        "net": str(slip.net_pay),
        "total_deductions": str(slip.total_deductions),
        "employee_contributions": str(slip.employee_contributions) if slip.employee_contributions is not None else None,
        "employer_contributions": str(slip.employer_contributions) if slip.employer_contributions is not None else None,
        "currency": slip.currency,
        "basic": str(basic),
        "tax": str(tax),
        "rebate_87a": str(rebate),
        "pf_ee": str(pf_ee),
        "esi_ee": str(esi_ee),
        "pt_amount": str(pt_total),
        "pt_state": pt_state,
        "earnings_json": earnings,
        "deductions_json": deductions,
        "inputs": inputs,
    }


@router.get("/payroll", operation_id="reportsGetReportspayroll")
def payroll_reports(
    jurisdiction: str | None = Query(default=None, description="ISO 3166-1 alpha-2, e.g. IN"),
    period: str | None = Query(default=None, description="Pay period as YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
) -> Any:
    """Payroll compliance reports (India).

    Query params:
      jurisdiction=IN  — when IN, four India slices are returned and the
                         verified-pack gate is applied.
      period=YYYY-MM   — the pay month the reports are scoped to. The pay_date
                         used for pack resolution is the first day of that month.
                         When absent the whole jurisdiction history is returned
                         (still gated).

    Gating: when the pack for IN on the effective pay date is not verified,
    the endpoint raises 409 rule_pack_not_verified with the same details shape
    as the payroll process gate. No computed data is returned while pending.
    """
    from app.models.payroll import PayRun, PaySlip, PayrollPeriod
    from app.rules.resolver import resolve_rule_pack

    jur = (jurisdiction or "").strip().upper() or None
    pay_date = _parse_period(period)
    # For gating we need a concrete pay_date; if period absent use today, but
    # for IN we prefer the latest period's pay_date when available so the
    # check reflects the actual pack in force for IN runs.
    if jur == "IN":
        effective_pay_date = pay_date
        if effective_pay_date is None:
            # Look up latest IN period pay_date if available
            latest = (
                db.query(PayrollPeriod.pay_date)
                .join(PayRun, PayRun.period_id == PayrollPeriod.id)
                .filter(PayRun.jurisdiction == "IN")
                .order_by(PayrollPeriod.pay_date.desc())
                .first()
            )
            if latest and latest[0]:
                effective_pay_date = latest[0]
            else:
                effective_pay_date = date.today()
        # Gate: verified pack required
        resolution = resolve_rule_pack("IN", effective_pay_date)
        if not resolution.is_verified:
            details = resolution.details()
            msg = (
                f"Payroll report for jurisdiction 'IN' cannot be generated on "
                f"{effective_pay_date.isoformat()}: no verified rule pack is in force. "
                f"The pack is {resolution.pack_status}."
            )
            raise ApiError(
                code="rule_pack_not_verified",
                message=msg,
                category=ErrorCategory.CONFLICT,
                status_code=409,
                details=details,
            )
        # Lineage from the verified pack (or fallback to run's stored pack)
        pack_id = resolution.pack.meta.pack_id if resolution.pack else "in-standard"
        pack_version = resolution.pack.meta.version if resolution.pack else "1.0.0"
        pack_effective_from = resolution.pack.meta.effective_from.isoformat() if resolution.pack and resolution.pack.meta.effective_from else "2025-04-01"
        pack_effective_to = resolution.pack.meta.effective_to.isoformat() if resolution.pack and resolution.pack.meta.effective_to else "2026-03-31"

        # Scope payslips: IN runs whose period matches the requested month (if period given)
        q = db.query(PaySlip).join(PayRun, PaySlip.pay_run_id == PayRun.id).filter(PayRun.jurisdiction == "IN")
        if period:
            # Filter by pay_date year-month
            y, m = period.split("-")
            # Join period to filter
            q = q.join(PayrollPeriod, PayRun.period_id == PayrollPeriod.id).filter(
                PayrollPeriod.pay_date >= date(int(y), int(m), 1),
                PayrollPeriod.pay_date < date(int(y) + (1 if int(m) == 12 else 0), 1 if int(m) == 12 else int(m) + 1, 1),
            )
        slips = q.order_by(PaySlip.id.asc()).all()

        # Build four slices from stored lines (no engine call)
        register = [_aggregate_payslip_statutory(s) for s in slips]

        # TDS liability: sum of TAX_* and REBATE_87A (rebate is negative)
        tds_total = Decimal("0")
        rebate_total = Decimal("0")
        for r in register:
            tds_total += Decimal(r["tax"])
            rebate_total += Decimal(r["rebate_87a"])
        # PF/ESI summary (EE/ER and ceilings)
        pf_ee_total = Decimal("0")
        esi_ee_total = Decimal("0")
        pf_er_total = Decimal("0")
        esi_er_total = Decimal("0")
        for r in register:
            pf_ee_total += Decimal(r["pf_ee"])
            esi_ee_total += Decimal(r["esi_ee"])
            if r["employer_contributions"] is not None:
                # Employer total is aggregated; split by pack values is not stored per-line for ER,
                # so we attribute from deductions? For IN we can approximate from register employer_contributions
                pass
        # More precise PF/ER and ESI/ER: read employer lines from slips where they exist as employer_contributions
        # but pack split not stored per-code, so we expose totals from slips
        total_employer_contribs = sum((Decimal(str(s.employer_contributions or "0")) for s in slips), Decimal("0"))
        total_employee_contribs = sum((Decimal(str(s.employee_contributions or "0")) for s in slips), Decimal("0"))

        # PT by state
        pt_by_state: dict[str, Decimal] = {}
        pt_total = Decimal("0")
        for r in register:
            amt = Decimal(r["pt_amount"])
            if amt != Decimal("0"):
                state = r["pt_state"] or "UNKNOWN"
                pt_by_state[state] = pt_by_state.get(state, Decimal("0")) + amt
                pt_total += amt
            elif r["pt_state"]:
                # zero PT still counts as state entry
                state = r["pt_state"]
                pt_by_state.setdefault(state, Decimal("0"))

        return {
            "jurisdiction": "IN",
            "period": period,
            "pack_status": "verified",
            "lineage": {
                "rule_pack_id": pack_id,
                "version": pack_version,
                "effective_from": pack_effective_from,
                "effective_to": pack_effective_to,
            },
            "currency": "INR",
            "payroll_register": register,
            "payroll_register_count": len(register),
            "tds_liability": {
                "total_tds": str(tds_total),
                "total_rebate_87a": str(rebate_total),
                "net_tds": str(tds_total + rebate_total),
                "payslips": len(register),
            },
            "pf_esi_summary": {
                "total_pf_ee": str(pf_ee_total),
                "total_esi_ee": str(esi_ee_total),
                "total_employee_contributions": str(total_employee_contribs),
                "total_employer_contributions": str(total_employer_contribs),
                "ceilings": {
                    "pf_wage_ceiling": "15000",
                    "esi_wage_limit": "21000",
                },
                "payslips": len(register),
            },
            "pt_by_state": {
                "by_state": {k: str(v) for k, v in pt_by_state.items()},
                "total_pt": str(pt_total),
                "payslips": len(register),
            },
        }

    # Non-IN: return a minimal payroll history (no gate)
    from app.models.payroll import PayRun, PaySlip, PayrollPeriod

    q = db.query(PayRun)
    if jur:
        q = q.filter(PayRun.jurisdiction == jur)
    if period:
        y, m = period.split("-")
        q = q.join(PayrollPeriod, PayRun.period_id == PayrollPeriod.id).filter(
            PayrollPeriod.pay_date >= date(int(y), int(m), 1),
            PayrollPeriod.pay_date < date(int(y) + (1 if int(m) == 12 else 0), 1 if int(m) == 12 else int(m) + 1, 1),
        )
    runs = q.order_by(PayRun.created_at.desc()).all()
    return {
        "jurisdiction": jur,
        "period": period,
        "runs": [
            {
                "id": r.id,
                "period_id": r.period_id,
                "jurisdiction": r.jurisdiction,
                "rule_pack_id": r.rule_pack_id,
                "status": r.status,
                "currency": r.currency,
                "total_gross": str(r.total_gross),
                "total_net": str(r.total_net),
                "headcount": r.headcount,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
        "count": len(runs),
    }
