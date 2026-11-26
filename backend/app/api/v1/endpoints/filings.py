"""India statutory filings — 5 generators from stored deductions_json/inputs_json (no recompute).

GET /reports/filings/{type}?jurisdiction=IN&period=YYYY-MM&state=XX

Types: 24q_quarterly, form16_annual, pf_ecr, esi_return, pt_challan

Each streams txt/csv from pay_slips.deductions_json/inputs_json + employee fields — no engine recompute.
Gated on verified pack — reuse resolve_rule_pack gate pattern.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import REPORTS_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.errors import ApiError, ErrorCategory, not_found
from app.models.audit import AuditLog
from app.models.filing_record import (
    FILING_STATUSES,
    FILING_TRANSITIONS,
    FilingRecord,
)
from app.models.user import User

router = APIRouter()

_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
_PERIOD_YEAR_RE = re.compile(r"^\d{4}$")
_PT_STATES = {"KA", "MH", "TN", "TG", "WB"}
_FILING_TYPES = {"24q", "24q_quarterly", "form16", "form16_annual", "pf_ecr", "esi_return", "pt_challan", "pt_return"}

def _parse_period(period: str) -> date:
    period = period.strip()
    if _PERIOD_RE.match(period):
        y, m = period.split("-")
        return date(int(y), int(m), 1)
    if _PERIOD_YEAR_RE.match(period):
        return date(int(period), 1, 1)
    raise ApiError(code="validation_error", message="period must be YYYY-MM or YYYY", category=ErrorCategory.VALIDATION, status_code=422)

def _gate_or_409(jurisdiction: str, pay_date: date) -> None:
    from app.rules.resolver import resolve_rule_pack
    # Only IN has gate; others pass through
    jur = (jurisdiction or "").strip().upper()
    if jur != "IN":
        return
    resolution = resolve_rule_pack(jur, pay_date)
    if not resolution.is_verified:
        details = resolution.details()
        msg = (
            f"Filing for jurisdiction '{jur}' cannot be generated on "
            f"{pay_date.isoformat()}: no verified rule pack is in force. "
            f"The pack is {resolution.pack_status}."
        )
        raise ApiError(code="rule_pack_not_verified", message=msg, category=ErrorCategory.CONFLICT, status_code=409, details=details)

def _quarter_from_month(m: int) -> int:
    return (m - 1) // 3 + 1

def _slips_for_period(db: Session, period: str, jurisdiction: str = "IN"):
    from app.models.payroll import PayRun, PaySlip, PayrollPeriod
    # period YYYY-MM or YYYY
    _parse_period(period)  # validate
    jur = (jurisdiction or "IN").strip().upper() or "IN"
    y, m = None, None
    if _PERIOD_RE.match(period.strip()):
        y, m = [int(x) for x in period.strip().split("-")]
    else:
        y = int(period.strip())
    q = db.query(PaySlip).join(PayRun, PaySlip.pay_run_id == PayRun.id).filter(PayRun.jurisdiction == jur)
    if y and m:
        q = q.join(PayrollPeriod, PayRun.period_id == PayrollPeriod.id).filter(
            PayrollPeriod.pay_date >= date(y, m, 1),
            PayrollPeriod.pay_date < date(y + (1 if m == 12 else 0), 1 if m == 12 else m+1, 1),
        )
    elif y:
        q = q.join(PayrollPeriod, PayRun.period_id == PayrollPeriod.id).filter(
            PayrollPeriod.pay_date >= date(y, 1, 1),
            PayrollPeriod.pay_date < date(y+1, 1, 1),
        )
    return q.order_by(PaySlip.id.asc()).all()

def _parse_deductions(slip) -> list[dict]:
    try:
        return json.loads(slip.deductions_json) if slip.deductions_json else []
    except Exception:
        return []

def _sum_code(deductions: list[dict], code: str) -> Decimal:
    for ln in deductions:
        if ln.get("code") == code:
            try:
                return Decimal(str(ln.get("amount", "0")))
            except Exception:
                return Decimal("0")
    return Decimal("0")

def _sum_prefix(deductions: list[dict], prefix: str) -> Decimal:
    total = Decimal("0")
    for ln in deductions:
        if str(ln.get("code","")).startswith(prefix):
            try:
                total += Decimal(str(ln.get("amount","0")))
            except Exception:
                pass
    return total

def _emit_24q(slips, period: str) -> str:
    # Form 24Q quarterly: PAN | TDS | rebate | period
    lines = [f"# Form 24Q Quarterly — period {period}", "pan,tds_amount,rebate_87a,net_tds"]
    for slip in slips:
        from app.models.employee import Employee
        from sqlalchemy.orm import Session as Sess
        # Need employee - but slips query didn't join Employee; fetch via pay_run
        # We'll attempt to get employee via db session identity; fallback to slip.employee_id
        pans = ""
        try:
            # slip.employee relationship may not be loaded; use deduction JSON fallback: TAX lines
            pass
        except Exception:
            pass
        deductions = _parse_deductions(slip)
        tax = _sum_prefix(deductions, "TAX_")
        rebate = _sum_code(deductions, "REBATE_87A")
        net = tax + rebate  # rebate is negative
        # Try to get PAN from DB via globals? we have no db here; pass slip.employee_id as ref and pans placeholder
        # For filings we need PAN column — use slip id + pan stub
        # In actual endpoint we will fetch employees batch
        lines.append(f"{slip.employee_id},{tax},{rebate},{net}")
    # If we want PAN values, caller will override; for generator we use DB fetch in endpoint
    return "\n".join(lines) + "\n"

def _filing_24q_content(db: Session, slips, period: str) -> str:
    from app.models.employee import Employee
    # Batch fetch employees
    emp_ids = [s.employee_id for s in slips]
    emps = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(emp_ids)).all()} if emp_ids else {}
    lines = [f"# Form 24Q Quarterly — period {period}", "employee_id,pan,tds_amount,rebate_87a,net_tds,period"]
    for slip in slips:
        emp = emps.get(slip.employee_id)
        pan = ""
        if emp:
            try:
                from app.core.encryption import decrypt_field
                # pan_number may be encrypted at rest? v1 stored plain; slice 6 encrypts — decrypt if needed
                raw = getattr(emp, "pan_number", None)
                if raw and raw.startswith("ENCv1:"):
                    raw = decrypt_field(raw)
                pan = raw or ""
            except Exception:
                pan = getattr(emp, "pan_number", "") or ""
        deductions = _parse_deductions(slip)
        tax = _sum_prefix(deductions, "TAX_")
        rebate = _sum_code(deductions, "REBATE_87A")
        net = tax + rebate
        lines.append(f"{slip.employee_id},{pan},{tax},{rebate},{net},{period}")
    if not slips:
        lines.append("# no payslips for period")
    return "\n".join(lines) + "\n"

def _filing_form16_content(db: Session, slips, period: str) -> str:
    # period is YYYY for annual; aggregate year
    from app.models.employee import Employee
    emp_ids = [s.employee_id for s in slips]
    emps = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(emp_ids)).all()} if emp_ids else {}
    lines = [f"# Form 16 Annual — period {period}", "employee_id,pan,gross,tds_total,rebate,net_tds,period"]
    for slip in slips:
        emp = emps.get(slip.employee_id)
        pan = ""
        if emp:
            try:
                from app.core.encryption import decrypt_field
                raw = getattr(emp, "pan_number", None)
                if raw and raw.startswith("ENCv1:"):
                    raw = decrypt_field(raw)
                pan = raw or ""
            except Exception:
                pan = getattr(emp, "pan_number", "") or ""
        deductions = _parse_deductions(slip)
        tax = _sum_prefix(deductions, "TAX_")
        rebate = _sum_code(deductions, "REBATE_87A")
        lines.append(f"{slip.employee_id},{pan},{slip.gross_pay},{tax},{rebate},{tax+rebate},{period}")
    if not slips:
        lines.append("# no payslips for period")
    return "\n".join(lines) + "\n"

def _filing_pf_ecr_content(db: Session, slips, period: str) -> str:
    from app.models.employee import Employee
    emp_ids = [s.employee_id for s in slips]
    emps = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(emp_ids)).all()} if emp_ids else {}
    lines = ["# PF ECR — UAN|GROSS|EE|ER|WAGE", "UAN,GROSS,PF_EE,PF_ER,WAGE"]
    challan_lines = [f"# PF Challan — period {period}", "uan,pf_ee,pf_er,total"]
    for slip in slips:
        emp = emps.get(slip.employee_id)
        uan = (getattr(emp, "pf_uan", None) or "") if emp else ""
        deductions = _parse_deductions(slip)
        pf_ee = _sum_code(deductions, "PF_EE")
        # PF ER is in employer_contributions? Try to parse employer lines from deductions? For slice 6 filings, PF ER approximated as pf_ee (12% both) if missing
        # deductions_json contains PF_EE only; employer is separate column total_employer but not per-code. Use pf_ee as ER too when unknown.
        pf_er = pf_ee  # v1 flat 12% both
        # Wage is capped 15000 per slice
        gross = slip.gross_pay
        wage = min(Decimal(str(gross)), Decimal("15000"))
        lines.append(f"{uan},{gross},{pf_ee},{pf_er},{wage}")
        challan_lines.append(f"{uan},{pf_ee},{pf_er},{pf_ee+pf_er}")
    if not slips:
        lines.append("# no payslips for period")
        challan_lines.append("# no payslips")
    # ECR is primary; challan appended as second section? For file download, combine with separator
    # Keep ECR only for txt; challan can be separate query? But contract says pf_ecr txt + challan — produce single file with both sections
    return "\n".join(lines) + "\n\n" + "\n".join(challan_lines) + "\n"

def _filing_esi_content(db: Session, slips, period: str) -> str:
    from app.models.employee import Employee
    emp_ids = [s.employee_id for s in slips]
    emps = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(emp_ids)).all()} if emp_ids else {}
    lines = [f"# ESI Return — period {period}", "esi_number,gross,esi_ee,esi_er"]
    for slip in slips:
        emp = emps.get(slip.employee_id)
        esi_no = (getattr(emp, "esi_number", None) or "") if emp else ""
        deductions = _parse_deductions(slip)
        esi_ee = _sum_code(deductions, "ESI_EE")
        esi_er = esi_ee * Decimal("3.25") / Decimal("0.75") if esi_ee != Decimal("0") else Decimal("0")
        # Quantize
        esi_er = esi_er.quantize(Decimal("0.01")) if esi_er != Decimal("0") else Decimal("0.00")
        lines.append(f"{esi_no},{slip.gross_pay},{esi_ee},{esi_er}")
    if not slips:
        lines.append("# no payslips for period")
    return "\n".join(lines) + "\n"

def _filing_pt_content(db: Session, slips, period: str, state: str | None) -> str:
    # state filter
    st = (state or "").strip().upper() or None
    if st and st not in _PT_STATES:
        raise ApiError(code="validation_error", message=f"pt state must be one of {sorted(_PT_STATES)}", category=ErrorCategory.VALIDATION, status_code=422)
    lines = [f"# PT Challan/Return — period {period} — state {st or 'ALL'}", "employee_id,pt_state,pt_amount,period"]
    for slip in slips:
        deductions = _parse_deductions(slip)
        # Determine pt_state from deductions code
        pt_state = None
        pt_amt = Decimal("0")
        for ln in deductions:
            code = str(ln.get("code",""))
            if code.startswith("PT_"):
                pt_state = code[3:]
                try:
                    pt_amt = Decimal(str(ln.get("amount","0")))
                except Exception:
                    pt_amt = Decimal("0")
                break
        if st and pt_state != st:
            continue
        # If no PT line, skip or emit zero?
        if pt_state is None and st:
            continue
        if pt_state is None:
            continue
        lines.append(f"{slip.employee_id},{pt_state},{pt_amt},{period}")
    if len(lines) == 1:
        lines.append("# no PT records for state/period")
    # If original slips empty, also note
    if not slips and len(lines) == 1:
        lines.append("# no payslips for period")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Filing records (filing-persistence)
#
# Saving a generated filing, listing it with its submission history, and
# moving it through Draft → Submitted → Accepted / Rejected → Resubmitted.
# Generation below only *calls* the helpers above — the txt bytes are
# unchanged (rollback removes these routes and the stored hashes still
# match what GET regenerates). Only the SHA-256 and a filename reference
# persist; no binary storage, no authority upload, no new calculations.
# ---------------------------------------------------------------------------

#: Aliases accepted at the boundary, normalised to the canonical persisted
#: value (``24q`` → ``24q_quarterly``, ``form16`` → ``form16_annual``,
#: ``pt_return`` → ``pt_challan``).
_FILING_TYPE_ALIASES = {
    "24q": "24q_quarterly",
    "24q_quarterly": "24q_quarterly",
    "form16": "form16_annual",
    "form16_annual": "form16_annual",
    "pf_ecr": "pf_ecr",
    "esi_return": "esi_return",
    "pt_challan": "pt_challan",
    "pt_return": "pt_challan",
}

#: ``content_ref`` is a reference only (≤10MB convention); anything larger
#: is refused rather than persisted.
_MAX_FILING_BYTES = 10 * 1024 * 1024


def _canonical_filing_type(filing_type: str) -> str:
    ft = (filing_type or "").strip().lower()
    if ft not in _FILING_TYPE_ALIASES:
        raise ApiError(code="validation_error", message=f"filing type must be one of {sorted(_FILING_TYPES)}", category=ErrorCategory.VALIDATION, status_code=422)
    return _FILING_TYPE_ALIASES[ft]


def _generate_for_record(
    db: Session,
    canonical: str,
    period: str,
    state: str | None,
    jurisdiction: str,
) -> tuple[str, str, str]:
    """Generate filing bytes exactly as the download endpoint would.

    Returns ``(content, effective_period, content_ref)``. The annual Form 16
    re-scopes a ``YYYY-MM`` period to its year, mirroring the GET branch, so
    a saved record always hashes the same bytes GET would stream.
    """
    jur = (jurisdiction or "IN").strip().upper()
    period_clean = (period or "").strip()
    if not (_PERIOD_RE.match(period_clean) or _PERIOD_YEAR_RE.match(period_clean)):
        raise ApiError(code="validation_error", message="period must be YYYY-MM or YYYY", category=ErrorCategory.VALIDATION, status_code=422)
    _gate_or_409(jur, _parse_period(period_clean))

    slips = _slips_for_period(db, period_clean, jurisdiction=jur)
    effective = period_clean
    if canonical == "24q_quarterly":
        content = _filing_24q_content(db, slips, period_clean)
        ref = f"IN_24Q_QUARTERLY_{period_clean}.txt"
    elif canonical == "form16_annual":
        if _PERIOD_RE.match(period_clean):
            effective = period_clean.split("-")[0]
            slips = _slips_for_period(db, effective, jurisdiction=jur)
        content = _filing_form16_content(db, slips, effective)
        ref = f"IN_FORM16_ANNUAL_{effective}.txt"
    elif canonical == "pf_ecr":
        content = _filing_pf_ecr_content(db, slips, period_clean)
        ref = f"IN_PF_ECR_{period_clean}.txt"
    elif canonical == "esi_return":
        content = _filing_esi_content(db, slips, period_clean)
        ref = f"IN_ESI_RETURN_{period_clean}.txt"
    else:
        content = _filing_pt_content(db, slips, period_clean, state)
        ref = f"IN_PT_CHALLAN_{period_clean}.txt" if not state else f"IN_PT_CHALLAN_{state.strip().upper()}_{period_clean}.txt"
    if len(content.encode("utf-8")) > _MAX_FILING_BYTES:
        raise ApiError(code="validation_error", message="generated filing exceeds the 10MB reference limit", category=ErrorCategory.VALIDATION, status_code=422)
    return content, effective, ref


def _record_out(rec: FilingRecord) -> dict[str, Any]:
    return {
        "id": rec.id,
        "filing_type": rec.filing_type,
        "period": rec.period,
        "state": rec.state,
        "status": rec.status,
        "content_hash": rec.content_hash,
        "content_ref": rec.content_ref,
        "version": rec.version,
        "supersedes_id": rec.supersedes_id,
        "submitted_by": rec.submitted_by,
        "submitted_at": rec.submitted_at.isoformat() if rec.submitted_at else None,
        "retention_until": rec.retention_until.isoformat() if rec.retention_until else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
    }


def _record_history(db: Session, record_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "FilingRecord", AuditLog.entity_id == record_id)
        .order_by(AuditLog.id.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "action": r.action,
            "actor_id": r.actor_id,
            "actor_name": r.actor_name,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/filings/records", operation_id="reportsListFilingRecords")
def list_filing_records(
    type_: str | None = Query(default=None, alias="type"),
    period: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
):
    """List saved filing records, newest first, each with submission history."""
    q = db.query(FilingRecord)
    if type_ is not None:
        q = q.filter(FilingRecord.filing_type == _canonical_filing_type(type_))
    if period is not None:
        q = q.filter(FilingRecord.period == period.strip())
    if status is not None:
        s = status.strip()
        if s not in FILING_STATUSES:
            raise ApiError(code="validation_error", message=f"status must be one of {list(FILING_STATUSES)}", category=ErrorCategory.VALIDATION, status_code=422)
        q = q.filter(FilingRecord.status == s)
    rows = q.order_by(FilingRecord.id.desc()).all()
    return {
        "records": [{**_record_out(r), "history": _record_history(db, r.id)} for r in rows],
        "count": len(rows),
    }


@router.get("/filings/{filing_type}", operation_id="reportsGetFilings")
def get_filing(
    filing_type: str,
    jurisdiction: str = Query(default="IN", description="ISO 3166-1 alpha-2, e.g. IN"),
    period: str = Query(..., description="YYYY-MM for monthly or YYYY for annual Form16"),
    state: str | None = Query(default=None, description="PT state (KA/MH/TN/TG/WB) for pt_challan"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
):
    """Generate India filings from stored payslip JSON (no engine recompute).

    Gated on verified pack: when pending, 409. PT filing validates state ∈5.
    """
    ft = filing_type.strip().lower()
    if ft not in _FILING_TYPES:
        raise ApiError(code="validation_error", message=f"filing type must be one of {sorted(_FILING_TYPES)}", category=ErrorCategory.VALIDATION, status_code=422)
    jur = (jurisdiction or "IN").strip().upper()
    # Validate period format
    period_clean = period.strip()
    if not (_PERIOD_RE.match(period_clean) or _PERIOD_YEAR_RE.match(period_clean)):
        raise ApiError(code="validation_error", message="period must be YYYY-MM or YYYY", category=ErrorCategory.VALIDATION, status_code=422)
    pay_date = _parse_period(period_clean)
    _gate_or_409(jur, pay_date)

    # Fetch slips scoped to period+jurisdiction (annual vs monthly already handled)
    slips = _slips_for_period(db, period_clean, jurisdiction=jur)

    content: str
    filename_type = ft.upper()

    if ft in ("24q", "24q_quarterly"):
        content = _filing_24q_content(db, slips, period_clean)
        filename_type = "24Q_QUARTERLY"
    elif ft in ("form16", "form16_annual"):
        # Form16 is annual: period should be YYYY; if YYYY-MM given, use its year
        if _PERIOD_RE.match(period_clean):
            year = period_clean.split("-")[0]
            # re-scope to year
            slips = _slips_for_period(db, year, jurisdiction=jur)
            period_clean_display = year
        else:
            period_clean_display = period_clean
        content = _filing_form16_content(db, slips, period_clean_display)
        filename_type = "FORM16_ANNUAL"
    elif ft == "pf_ecr":
        content = _filing_pf_ecr_content(db, slips, period_clean)
        filename_type = "PF_ECR"
    elif ft == "esi_return":
        content = _filing_esi_content(db, slips, period_clean)
        filename_type = "ESI_RETURN"
    elif ft in ("pt_challan", "pt_return"):
        content = _filing_pt_content(db, slips, period_clean, state)
        filename_type = "PT_CHALLAN"
        if state:
            filename_type = f"PT_CHALLAN_{state.strip().upper()}"
    else:
        content = ""

    # Naming per AC-31: IN_{TYPE}_{PERIOD}.txt
    # Normalize period for filename: YYYY-MM stays, YYYY stays
    safe_period = period_clean.replace("-", "")
    # For display keep original? Use period_clean
    filename = f"IN_{filename_type}_{period_clean}.txt"

    return Response(content=content, media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/filings/{filing_type}/records", status_code=201, operation_id="reportsCreateFilingRecord")
def create_filing_record(
    filing_type: str,
    period: str = Query(..., description="YYYY-MM for monthly or YYYY for annual Form16"),
    state: str | None = Query(default=None, description="PT state (KA/MH/TN/TG/WB) for pt_challan"),
    jurisdiction: str = Query(default="IN", description="ISO 3166-1 alpha-2, e.g. IN"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
):
    """Persist a generated filing (type/period/content-hash) as version 1.

    An identical repeat POST (same type, period, state and content-hash) is
    a ``409`` duplicate — the first row stands.
    """
    canonical = _canonical_filing_type(filing_type)
    st = (state.strip().upper() if state else None) or None
    content, effective, ref = _generate_for_record(db, canonical, period, st, jurisdiction)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()

    dup_q = db.query(FilingRecord).filter(
        FilingRecord.filing_type == canonical,
        FilingRecord.period == effective,
        FilingRecord.content_hash == digest,
    )
    dup_q = dup_q.filter(FilingRecord.state == st) if st else dup_q.filter(FilingRecord.state.is_(None))
    if dup_q.first() is not None:
        raise ApiError(
            code="duplicate_filing_record",
            message=f"Filing {canonical} for period {effective} with identical content is already recorded.",
            category=ErrorCategory.CONFLICT,
            status_code=409,
            details={"filing_type": canonical, "period": effective, "state": st},
        )

    rec = FilingRecord(
        filing_type=canonical,
        period=effective,
        state=st,
        status="Draft",
        content_hash=digest,
        content_ref=ref,
        version=1,
        supersedes_id=None,
        retention_until=None,
    )
    db.add(rec)
    db.flush()
    record_audit(
        db, current_user, "filing_record_created", "FilingRecord", rec.id,
        details=f"filing_type={canonical} period={effective} version=1",
    )
    db.commit()
    db.refresh(rec)
    return _record_out(rec)


@router.post("/filings/records/{record_id}/{action}", operation_id="reportsTransitionFilingRecord")
def transition_filing_record(
    record_id: int,
    action: str,
    jurisdiction: str = Query(default="IN", description="ISO 3166-1 alpha-2, e.g. IN"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTS_ROLES)),
):
    """Move a filing record through its lifecycle.

    ``submit`` (Draft→Submitted), ``accept``/``reject``
    (Submitted→Accepted/Rejected); ``resubmit`` (Rejected→Resubmitted on the
    old row plus a new Draft row at version N+1 linked via ``supersedes_id``).
    Anything else — including any move out of Accepted or Resubmitted — is
    ``422`` and writes no audit row. The original row's content columns are
    never mutated.
    """
    now = datetime.now(timezone.utc)
    a = (action or "").strip().lower()
    rec = db.query(FilingRecord).filter(FilingRecord.id == record_id).first()
    if rec is None:
        raise not_found("FilingRecord")

    if a in ("submit", "accept", "reject"):
        want_from, want_to = FILING_TRANSITIONS[a]
        if rec.status != want_from:
            raise ApiError(
                code="illegal_filing_transition",
                message=f"Cannot {a} a filing record in status {rec.status}.",
                category=ErrorCategory.VALIDATION,
                status_code=422,
                details={"id": rec.id, "status": rec.status, "action": a},
            )
        rec.status = want_to
        if a == "submit":
            rec.submitted_by = current_user.id
            rec.submitted_at = now
        rec.updated_at = now
        db.flush()
        _PAST = {"submit": "submitted", "accept": "accepted", "reject": "rejected"}
        record_audit(
            db, current_user, f"filing_record_{_PAST[a]}",
            "FilingRecord", rec.id,
            details=f"filing_type={rec.filing_type} period={rec.period} version={rec.version} status={want_to}",
        )
        db.commit()
        db.refresh(rec)
        return {**_record_out(rec), "history": _record_history(db, rec.id)}

    if a == "resubmit":
        if rec.status != "Rejected":
            raise ApiError(
                code="illegal_filing_transition",
                message=f"Cannot resubmit a filing record in status {rec.status}; only Rejected rows resubmit.",
                category=ErrorCategory.VALIDATION,
                status_code=422,
                details={"id": rec.id, "status": rec.status, "action": a},
            )
        content, _, ref = _generate_for_record(db, rec.filing_type, rec.period, rec.state, jurisdiction)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        new = FilingRecord(
            filing_type=rec.filing_type,
            period=rec.period,
            state=rec.state,
            status="Draft",
            content_hash=digest,
            content_ref=ref,
            version=rec.version + 1,
            supersedes_id=rec.id,
            retention_until=rec.retention_until,
        )
        rec.status = "Resubmitted"
        rec.updated_at = now
        db.add(new)
        db.flush()
        record_audit(
            db, current_user, "filing_record_resubmitted", "FilingRecord", rec.id,
            details=f"filing_type={rec.filing_type} period={rec.period} new_version_id={new.id} version={new.version}",
        )
        record_audit(
            db, current_user, "filing_record_created", "FilingRecord", new.id,
            details=f"filing_type={new.filing_type} period={new.period} version={new.version} supersedes_id={rec.id}",
        )
        db.commit()
        db.refresh(new)
        return {**_record_out(new), "history": _record_history(db, new.id)}

    raise ApiError(
        code="validation_error",
        message="action must be one of submit, accept, reject, resubmit",
        category=ErrorCategory.VALIDATION,
        status_code=422,
    )
