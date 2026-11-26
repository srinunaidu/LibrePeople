"""Confidential Employee Relations cases (gap #9).

Why this file exists instead of extending ``core_hr.py``: the helpdesk's
``_ensure_can_access_case`` grants the requester (subject) visibility of
their own case — the exact semantic ER must NOT inherit. An ER subject
must never see, or infer, a case about themselves. So this module is
deny-by-default:

* HR and SuperAdmin (``ADMIN_ROLES``) work the whole queue.
* Anyone else sees only the cases assigned to them (``assigned_to``) —
  never the queue, never a colleague's case, never a case about
  themselves. Anything else is refused with 404, never 403, so the
  response cannot confirm the case exists.
* Comments and attachments are append-only: there is no update or delete
  route for them, so the rows behind a case are its history — kept after
  close (lead decision D3).
* The reporter is always the authenticated account (lead decision D1):
  ``reported_by`` is set server-side. There is no anonymous intake in v1.
* The summary endpoint returns aggregates only — no ids, names or
  narratives — so the figures can be shared without leaking who or what.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, WORKFORCE_ROLES, get_db, require_roles, tenant_id_for
from app.core.audit import record_audit
from app.core.errors import validation
from app.core.tenancy import tenant_column_criterion, tenant_matches
from app.core.visibility import ensure_can_view_employee
from app.models.er_case import ERCase, ERCaseAttachment, ERCaseComment
from app.models.user import User
from app.storage.backends import AUTHORISED_FILES_PREFIX
from app.schemas.er_cases import (
    ERCaseAttachmentCreate,
    ERCaseAttachmentOut,
    ERCaseCommentCreate,
    ERCaseCommentOut,
    ERCaseCreate,
    ERCaseOut,
    ERCaseUpdate,
    ERSummaryOut,
)

router = APIRouter()

#: The forward-only status machine. One step at a time:
#: Open > Triaged > Investigating > ActionTaken > Resolved > Closed.
ER_NEXT_STATUS: dict[str, set[str]] = {
    "Open": {"Triaged"},
    "Triaged": {"Investigating"},
    "Investigating": {"ActionTaken"},
    "ActionTaken": {"Resolved"},
    "Resolved": {"Closed"},
    "Closed": set(),
}


def _is_er_admin(u: User) -> bool:
    """True when this account works the whole ER queue (HR/SuperAdmin)."""
    return u.role in ADMIN_ROLES


def _check_tenant(u: User, case: ERCase, db: Session) -> None:
    """Refuse with 404 when the case belongs to another tenant.

    Runs after the participant check so that neither check leaks across
    the other's boundary: a cross-tenant HR admin — who passes the role
    check — still learns nothing.
    """
    tid = tenant_id_for(db)
    if tid is not None and not tenant_matches(case.tenant_id, tid):
        raise HTTPException(status_code=404, detail="Case not found")


def _ensure_can_access_er_case(u: User, case: ERCase) -> None:
    """Raise 404 unless `u` may read this ER case.

    HR sees every case. Anyone else sees only the cases assigned to them.
    Unlike the helpdesk, the subject sees NOTHING — not even a case about
    themselves. A 404 — not a 403 — avoids confirming the case exists.
    """
    if _is_er_admin(u):
        return
    if case.assigned_to and case.assigned_to == u.username:
        return
    raise HTTPException(status_code=404, detail="Case not found")


def _validate_er_attachment(payload: ERCaseAttachmentCreate) -> None:
    """Refuse an attachment that is half-formed or mis-pointed."""
    filename, key = payload.filename, payload.file_key
    if (filename is None) != (key is None):
        raise validation(
            "validation_error",
            "filename and file_key must be sent together.",
            entity="ERCaseAttachment",
            fields=["filename", "file_key"],
        )
    if key is None:
        return
    if not filename or not filename.strip():
        raise validation(
            "validation_error",
            "filename must not be blank when file_key is sent.",
            entity="ERCaseAttachment",
            fields=["filename"],
        )
    if not key.startswith(AUTHORISED_FILES_PREFIX):
        raise validation(
            "validation_error",
            f"file_key must name a key under {AUTHORISED_FILES_PREFIX}.",
            entity="ERCaseAttachment",
            fields=["file_key"],
        )


def _scope_to_tenant(query, db: Session):
    """Limit an ER query to the current request's tenant, if any."""
    tid = tenant_id_for(db)
    if tid is not None:
        query = query.filter(tenant_column_criterion(ERCase.tenant_id, tid))
    return query


@router.get("/summary", response_model=ERSummaryOut, operation_id="erCasesSummary")
def er_summary(db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))):
    """Aggregate counts only — no ids, names or narratives (HR-only)."""
    q = _scope_to_tenant(db.query(ERCase), db)
    by_type = dict(
        q.with_entities(ERCase.case_type, func.count(ERCase.id))
        .group_by(ERCase.case_type)
        .all()
    )
    by_status = dict(
        _scope_to_tenant(db.query(ERCase), db)
        .with_entities(ERCase.status, func.count(ERCase.id))
        .group_by(ERCase.status)
        .all()
    )
    total = _scope_to_tenant(db.query(func.count(ERCase.id)), db).scalar() or 0
    return ERSummaryOut(by_case_type=by_type, by_status=by_status, total=total)


@router.get("", response_model=list[ERCaseOut], operation_id="erCasesList")
def list_er_cases(
    status: str | None = None,
    case_type: str | None = None,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    """The ER queue — HR only.

    The route accepts any workforce role so that a non-admin (including an
    assignee) is answered with 404 rather than 403: confirming "forbidden"
    would confirm the queue exists to someone who must not infer it.
    """
    if not _is_er_admin(u):
        raise HTTPException(status_code=404, detail="Case not found")
    q = _scope_to_tenant(db.query(ERCase), db)
    if status:
        q = q.filter(ERCase.status == status)
    if case_type:
        q = q.filter(ERCase.case_type == case_type)
    return q.order_by(ERCase.created_at.desc()).all()


@router.post("", response_model=ERCaseOut, status_code=201, operation_id="erCasesCreate")
def create_er_case(
    payload: ERCaseCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))
):
    """Open an ER case (HR-only; D1: the reporter is the authenticated account)."""
    if payload.subject_employee_id is not None:
        ensure_can_view_employee(db, u, payload.subject_employee_id)
    obj = ERCase(
        case_type=payload.case_type,
        subject_employee_id=payload.subject_employee_id,
        reported_by=u.username,
        severity=payload.severity,
        status="Open",
        assigned_to=payload.assigned_to,
        classification=payload.classification,
        tenant_id=tenant_id_for(db),
    )
    db.add(obj); db.commit(); db.refresh(obj)
    # The audit row names the case and its routing, never the narrative:
    # the audit trail is read by more people than the queue is.
    record_audit(
        db, u, "create_er_case", "ERCase", obj.id,
        details=f"case_type={obj.case_type} severity={obj.severity}",
    ); db.commit()
    return obj


@router.get("/{case_id}", response_model=ERCaseOut, operation_id="erCasesGet")
def read_er_case(
    case_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))
):
    obj = db.query(ERCase).filter(ERCase.id == case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    _ensure_can_access_er_case(u, obj)
    _check_tenant(u, obj, db)
    return obj


@router.put("/{case_id}", response_model=ERCaseOut, operation_id="erCasesUpdate")
def update_er_case(
    case_id: int, payload: ERCaseUpdate, db: Session = Depends(get_db), u: User = Depends(require_roles(*ADMIN_ROLES))
):
    """Classify, assign, advance or resolve an ER case (HR-only).

    An assignee who is not HR cannot move the case — the update route is
    role-gated, so a scoped participant is refused with 403.
    """
    obj = db.query(ERCase).filter(ERCase.id == case_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Case not found")
    _check_tenant(u, obj, db)
    changes = payload.model_dump(exclude_unset=True)
    target = changes.get("status")
    if target is not None and target != obj.status:
        if target not in ER_NEXT_STATUS.get(obj.status, set()):
            raise validation(
                "invalid_status_transition",
                f"Case cannot move from {obj.status} to {target}.",
                entity="ERCase",
                fields=["status"],
                case_id=case_id,
            )
        if target == "Resolved":
            effective = changes.get("outcome", obj.outcome)
            if not effective or not str(effective).strip():
                raise validation(
                    "outcome_required",
                    "Resolving a case requires an outcome.",
                    entity="ERCase",
                    fields=["outcome"],
                    case_id=case_id,
                )
    for f, v in changes.items():
        setattr(obj, f, v)
    if obj.status in ("Resolved", "Closed") and not obj.resolved_at:
        from datetime import datetime, timezone
        obj.resolved_at = datetime.now(timezone.utc)
    db.add(obj); db.commit(); db.refresh(obj)
    action = (
        "triage_er_case" if obj.status == "Triaged"
        else "assign_er_case" if "assigned_to" in changes
        else "resolve_er_case" if obj.status in ("Resolved", "Closed")
        else "update_er_case"
    )
    record_audit(
        db, u, action, "ERCase", obj.id, details=f"status={obj.status}",
    ); db.commit()
    return obj


@router.get("/{case_id}/comments", response_model=list[ERCaseCommentOut], operation_id="erCasesListComments")
def list_er_comments(
    case_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))
):
    """The investigation history of a case — participants only (kept after close, D3)."""
    case = db.query(ERCase).filter(ERCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _ensure_can_access_er_case(u, case)
    _check_tenant(u, case, db)
    return (
        db.query(ERCaseComment)
        .filter(ERCaseComment.case_id == case_id)
        .order_by(ERCaseComment.created_at)
        .all()
    )


@router.post("/{case_id}/comments", response_model=ERCaseCommentOut, status_code=201, operation_id="erCasesAddComment")
def add_er_comment(
    case_id: int, payload: ERCaseCommentCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))
):
    """Append a comment to a case (participants only; append-only, no edit/delete).

    The author is the authenticated account — never taken from the payload.
    """
    case = db.query(ERCase).filter(ERCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _ensure_can_access_er_case(u, case)
    _check_tenant(u, case, db)
    obj = ERCaseComment(case_id=case_id, author=u.username, comment=payload.comment)
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "add_er_comment", "ERCaseComment", obj.id); db.commit()
    return obj


@router.get("/{case_id}/attachments", response_model=list[ERCaseAttachmentOut], operation_id="erCasesListAttachments")
def list_er_attachments(
    case_id: int, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))
):
    case = db.query(ERCase).filter(ERCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _ensure_can_access_er_case(u, case)
    _check_tenant(u, case, db)
    return (
        db.query(ERCaseAttachment)
        .filter(ERCaseAttachment.case_id == case_id)
        .order_by(ERCaseAttachment.created_at)
        .all()
    )


@router.post("/{case_id}/attachments", response_model=ERCaseAttachmentOut, status_code=201, operation_id="erCasesAddAttachment")
def add_er_attachment(
    case_id: int, payload: ERCaseAttachmentCreate, db: Session = Depends(get_db), u: User = Depends(require_roles(*WORKFORCE_ROLES))
):
    """Attach a file reference to a case (participants only; append-only)."""
    _validate_er_attachment(payload)
    case = db.query(ERCase).filter(ERCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    _ensure_can_access_er_case(u, case)
    _check_tenant(u, case, db)
    obj = ERCaseAttachment(
        case_id=case_id,
        filename=payload.filename.strip(),
        file_key=payload.file_key,
        uploaded_by=u.username,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    record_audit(db, u, "add_er_attachment", "ERCaseAttachment", obj.id); db.commit()
    return obj
