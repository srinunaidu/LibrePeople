"""Data-quality API.

Exposes the check engine over HTTP with severity, ownership and remediation
guidance. Restricted to HR / SuperAdmin: the report names employees who are
missing payroll data or have invalid dates, which is not something any
employee should see.
"""
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.observability import get_logger
from app.models.user import User
from app.services import data_quality as dq

router = APIRouter()
log = get_logger("librepeople.data_quality")

SEVERITIES = ("critical", "warning", "info")


@router.get("/checks", operation_id="dataQualityListDataqualitychecks")
def list_checks(_: User = Depends(require_roles(*ADMIN_ROLES))) -> Any:
    """Which data-quality rules are registered."""
    return {
        "checks": dq.registered_codes(),
        "severities": list(SEVERITIES),
        "note": (
            "Checks are read-only. Nothing in this capability modifies a "
            "record; remediation is a separate, audited action."
        ),
    }


@router.get("/issues", operation_id="dataQualityListDataqualityissues")
def list_issues(
    severity: str | None = Query(default=None, description="Filter by severity"),
    code: str | None = Query(default=None, description="Filter by rule code"),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Run every data-quality check and return the findings, worst first.

    A non-empty report is not an error state. An *empty* report means the
    checks ran and found nothing; it is never used to mask a check that failed
    to execute — those surface as `<rule>.check_failed` issues.
    """
    if severity and severity not in SEVERITIES:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=f"severity must be one of {', '.join(SEVERITIES)}",
        )

    issues = dq.run_all(db)

    if severity:
        issues = [i for i in issues if i.severity == severity]
    if code:
        issues = [i for i in issues if i.code == code]

    truncated = issues[:limit]
    summary = dq.summarise(issues)

    return {
        "summary": summary,
        "returned": len(truncated),
        "truncated": len(issues) > limit,
        "issues": [i.as_dict() for i in truncated],
    }


@router.post("/scan", operation_id="dataQualityCreateDataqualityscan")
def trigger_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Run a full scan and record it in the audit trail.

    Used before go-live and after a bulk import, so there is a record of what
    the data looked like at a point in time.
    """
    issues = dq.run_all(db)
    summary = dq.summarise(issues)
    record_audit(
        db,
        current_user,
        "data_quality_scan",
        "System",
        None,
        details=(
            f"total={summary['total']} "
            f"critical={summary['by_severity'].get('critical', 0)} "
            f"warning={summary['by_severity'].get('warning', 0)} "
            f"info={summary['by_severity'].get('info', 0)}"
        ),
    )
    db.commit()
    log.info("data quality scan", **summary["by_severity"], total=summary["total"])
    return {"summary": summary, "scanned": True}