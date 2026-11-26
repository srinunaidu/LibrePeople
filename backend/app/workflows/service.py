"""Minimum reusable workflow engine (stage core + adapters).

One small forward-only machine — ``PENDING -> APPROVED | REJECTED |
RETURNED`` — serving expenses, HR cases, documents and assets (D1). The
core records the decision trail and never owns domain state: callers keep
their own status columns, and the adapter helpers below only *mirror* a
decision the domain endpoint already made.

Transaction discipline (AC5): every mutating function stages its step row,
its chained audit row (via :func:`app.core.audit.record_audit`, staged not
committed) and its notification (via :func:`app.services.notifications.emit`,
which never commits) and then performs exactly one ``db.commit()``. A
worker crash before the commit leaves no half-write.

Escalation (D2) is notify-only: :func:`scan_overdue_for_escalation`
reuses the expired-lease *pattern* (rows whose deadline passed) and only
emits notifications — it never reassigns, never mutates a trail, never
commits (the caller owns the transaction, per the LP-NOT-001 rule), and no
new daemon is required.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, MANAGER_ROLES, tenant_id_for
from app.core.audit import record_audit
from app.core.errors import conflict, forbidden, not_found, validation
from app.core.observability import get_logger
from app.core.tenancy import tenant_matches
from app.models.employee import Employee
from app.models.ess_hr import Notification
from app.models.user import User
from app.models.workflow_step import WorkflowStep
from app.services import notifications as notify

log = get_logger("librepeople.workflows")

#: v1 entity allowlist (D1). ER joins when its module is built.
ENTITY_ALLOWLIST = frozenset({"expense_claim", "hr_case", "document", "asset"})

#: Stages. Forward-only: PENDING may leave once; a terminal stage never moves.
STAGE_PENDING = "PENDING"
STAGE_APPROVED = "APPROVED"
STAGE_REJECTED = "REJECTED"
STAGE_RETURNED = "RETURNED"
TERMINAL_STAGES = frozenset({STAGE_APPROVED, STAGE_REJECTED, STAGE_RETURNED})

#: Actions the core writes.
ACTION_OPEN = "OPEN"
ACTION_L1_APPROVE = "L1_APPROVE"
ACTION_APPROVE = "APPROVE"
ACTION_REJECT = "REJECT"
ACTION_RETURN = "RETURN"
ACTION_REASSIGN = "REASSIGN"

#: The machine-readable prefix of a reassignment row's comment. The row
#: carries no assignee column (contract columns are fixed), so the target
#: is encoded here and parsed back by :func:`assignee_of`.
_REASSIGN_PREFIX = re.compile(r"^reassigned_to:(\d+)\b")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_entity(entity_type: str) -> None:
    """Refuse an entity type outside the v1 allowlist, fail-closed."""
    if entity_type not in ENTITY_ALLOWLIST:
        raise not_found("Workflow entity")


def _trail(db: Session, tenant_id: str | None, entity_type: str, entity_id: int) -> list[WorkflowStep]:
    """The caller-tenant rows behind an entity, oldest first."""
    rows = (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.entity_type == entity_type,
            WorkflowStep.entity_id == entity_id,
        )
        .order_by(WorkflowStep.id.asc())
        .all()
    )
    if tenant_id is None:
        return rows
    return [r for r in rows if tenant_matches(getattr(r, "tenant_id", None), tenant_id)]


def _current(rows: list[WorkflowStep]) -> WorkflowStep | None:
    return rows[-1] if rows else None


def _l1_done(rows: list[WorkflowStep]) -> bool:
    """Whether the current cycle already carries the L1 approval."""
    return any(r.action == ACTION_L1_APPROVE for r in rows)


def assignee_of(rows: list[WorkflowStep]) -> int | None:
    """The latest reassignment target in a trail, if any."""
    for row in reversed(rows):
        if row.action == ACTION_REASSIGN and row.comment:
            match = _REASSIGN_PREFIX.match(row.comment)
            if match:
                return int(match.group(1))
    return None


def _notify_requester(db: Session, rows: list[WorkflowStep]) -> int | None:
    """Who to nudge about a trail: the assignee, else the opener."""
    target = assignee_of(rows)
    if target is not None:
        return target
    for row in rows:
        if row.action == ACTION_OPEN:
            return row.actor_id
    return rows[-1].actor_id if rows else None


def _resolve_user_tenant(db: Session, user: User | None) -> str | None:
    """The tenant a user belongs to, via their employee link (if any)."""
    if user is None or user.employee_id is None:
        return None
    employee = db.get(Employee, user.employee_id)
    return getattr(employee, "tenant_id", None) if employee is not None else None


def _finish(
    db: Session,
    actor: User,
    step: WorkflowStep,
    audit_action: str,
    recipient_user_id: int | None,
    notify_title: str,
    notify_message: str,
    notify_kind: str,
) -> WorkflowStep:
    """Stage audit + notification, then the single commit (AC5).

    ``receipt`` is logged when the decision is recorded; ``success`` when
    the notification row is written; ``warning`` when there is nobody to
    notify (or the recipient opted out) — the LP-NOT-001 pattern.
    """
    db.flush()
    record_audit(db, actor, audit_action, "WorkflowStep", step.id)
    log.info("workflow decision recorded", action=audit_action, step_id=step.id)
    if recipient_user_id is None:
        log.warning("workflow notification skipped: no recipient", step_id=step.id)
    else:
        emitted = notify.emit(
            db,
            recipient_user_id=recipient_user_id,
            title=notify_title,
            message=notify_message,
            notification_type=notify_kind,
            category="workflow",
            entity_type=step.entity_type,
            entity_id=step.entity_id,
        )
        if emitted is None:
            log.warning("workflow notification skipped: opted out", step_id=step.id)
        else:
            log.info("workflow notification emitted", step_id=step.id)
    db.commit()
    db.refresh(step)
    return step


def decide(
    db: Session,
    *,
    actor: User,
    entity_type: str,
    entity_id: int,
    action: str,
    comment: str | None = None,
    due_at: datetime | None = None,
) -> WorkflowStep:
    """Record one gated decision on an entity's trail.

    ``action`` is ``approve`` | ``reject`` | ``return``. The first approval
    is the L1 rung (MANAGER_ROLES); the second is final (ADMIN_ROLES).
    Reject/return need a comment and a MANAGER_ROLES-or-better role. A
    decision on a terminal trail, or a repeat final approval, is 409; a
    missing comment on reject/return is 422; a wrong role is 403; another
    tenant's trail reads as 404.
    """
    _require_entity(entity_type)
    tenant_id = tenant_id_for(db)
    rows = _trail(db, tenant_id, entity_type, entity_id)
    current = _current(rows)

    if action == "approve":
        if actor.role not in MANAGER_ROLES:
            raise forbidden("Your role does not permit this operation.")
    elif action in ("reject", "return"):
        if actor.role not in MANAGER_ROLES:
            raise forbidden("Your role does not permit this operation.")
    else:
        raise validation(
            "validation_error",
            f"Unknown decision action {action!r}.",
            entity="WorkflowStep",
            fields=["action"],
        )

    if current is not None and current.stage in TERMINAL_STAGES:
        raise conflict(
            "workflow_terminal",
            f"This {entity_type} already reached {current.stage}; it cannot move further.",
            entity_type=entity_type,
            entity_id=entity_id,
            stage=current.stage,
        )

    if not rows:
        opener = WorkflowStep(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            stage=STAGE_PENDING,
            action=ACTION_OPEN,
            actor_id=actor.id,
            comment=None,
            due_at=due_at,
        )
        db.add(opener)
        rows = [opener]

    #: The deadline belongs to the trail cycle, not to one row: every
    #: appended row inherits the current row's ``due_at`` so the overdue
    #: query (latest-row shaped, like the expired-lease scan) keeps seeing
    #: it until the trail terminates. A fresh cycle after a terminal stage
    #: starts from the caller's ``due_at`` again.
    inherited_due_at = current.due_at if current is not None else due_at

    if action == "approve":
        if not _l1_done(rows):
            step = WorkflowStep(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
                stage=STAGE_PENDING,
                action=ACTION_L1_APPROVE,
                actor_id=actor.id,
                comment=comment,
                due_at=inherited_due_at,
            )
            audit_action = "workflow_l1_approve"
        else:
            if actor.role not in ADMIN_ROLES:
                raise forbidden("Your role does not permit this operation.")
            step = WorkflowStep(
                tenant_id=tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
                stage=STAGE_APPROVED,
                action=ACTION_APPROVE,
                actor_id=actor.id,
                comment=comment,
                due_at=inherited_due_at,
            )
            audit_action = "workflow_approve"
    else:
        if not (comment or "").strip():
            raise validation(
                "comment_required",
                f"A {action} decision requires a comment.",
                entity="WorkflowStep",
                fields=["comment"],
            )
        stage = STAGE_REJECTED if action == "reject" else STAGE_RETURNED
        step = WorkflowStep(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            stage=stage,
            action=ACTION_REJECT if action == "reject" else ACTION_RETURN,
            actor_id=actor.id,
            comment=comment,
            due_at=inherited_due_at,
        )
        audit_action = f"workflow_{action}"

    db.add(step)
    recipient = _notify_requester(db, rows)
    return _finish(
        db,
        actor,
        step,
        audit_action,
        recipient,
        f"Workflow {step.action}: {entity_type} {entity_id}",
        (comment or "").strip() or f"{entity_type} {entity_id} moved by {step.action}.",
        "info" if action == "approve" else "warning",
    )


def reassign(
    db: Session,
    *,
    actor: User,
    entity_type: str,
    entity_id: int,
    to_user_id: int,
    comment: str | None = None,
) -> WorkflowStep:
    """Hand an open trail to another user (admin roles only).

    The trail must exist in the caller's tenant and still be open; the
    target user must exist and, when attributable to a tenant, belong to
    the same one (fail-closed 404). The target is encoded in the row's
    comment (see :data:`_REASSIGN_PREFIX`); the stage does not move.
    """
    _require_entity(entity_type)
    if actor.role not in ADMIN_ROLES:
        raise forbidden("Your role does not permit this operation.")
    tenant_id = tenant_id_for(db)
    rows = _trail(db, tenant_id, entity_type, entity_id)
    current = _current(rows)
    if current is None:
        raise not_found("Workflow entity")
    if current.stage in TERMINAL_STAGES:
        raise conflict(
            "workflow_terminal",
            f"This {entity_type} already reached {current.stage}; it cannot be reassigned.",
            entity_type=entity_type,
            entity_id=entity_id,
            stage=current.stage,
        )
    target = db.get(User, to_user_id)
    if target is None:
        raise not_found("User")
    if tenant_id is not None:
        target_tenant = _resolve_user_tenant(db, target)
        if target_tenant is not None and not tenant_matches(target_tenant, tenant_id):
            raise not_found("User")
    note = (comment or "").strip()
    stored = f"reassigned_to:{to_user_id}" + (f" note:{note}" if note else "")
    step = WorkflowStep(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        stage=STAGE_PENDING,
        action=ACTION_REASSIGN,
        actor_id=actor.id,
        comment=stored,
        due_at=current.due_at,
    )
    db.add(step)
    return _finish(
        db,
        actor,
        step,
        "workflow_reassign",
        to_user_id,
        f"Workflow assigned: {entity_type} {entity_id}",
        note or f"{entity_type} {entity_id} was assigned to you.",
        "info",
    )


def history(
    db: Session, *, entity_type: str, entity_id: int
) -> list[WorkflowStep]:
    """The caller-tenant trail behind an entity, oldest first.

    Append-only: there is no update or delete. An entity with no visible
    rows — unknown, or another tenant's — reads as 404, fail-closed.
    """
    _require_entity(entity_type)
    rows = _trail(db, tenant_id_for(db), entity_type, entity_id)
    if not rows:
        raise not_found("Workflow entity")
    return rows


def overdue(
    db: Session,
    *,
    entity_type: str | None = None,
    now: datetime | None = None,
) -> list[WorkflowStep]:
    """Open caller-tenant trails whose ``due_at`` has passed.

    Only the latest row per entity counts, and only when it is still
    PENDING with a non-NULL ``due_at`` in the past (NULL = never overdue,
    D3). Lease-expiry shaped: one query for the latest row per entity,
    then the deadline filter — the same shape as the job queue's expired
    lease scan.
    """
    moment = now or _utcnow()
    tenant_id = tenant_id_for(db)
    latest_ids: Any = db.query(func.max(WorkflowStep.id))
    if tenant_id is not None:
        from app.core.tenancy import tenant_column_criterion

        latest_ids = latest_ids.filter(
            tenant_column_criterion(WorkflowStep.tenant_id, tenant_id)
        )
    if entity_type is not None:
        _require_entity(entity_type)
        latest_ids = latest_ids.filter(WorkflowStep.entity_type == entity_type)
    latest_ids = latest_ids.group_by(WorkflowStep.entity_type, WorkflowStep.entity_id).subquery()
    return (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.id.in_(db.query(latest_ids)),
            WorkflowStep.stage == STAGE_PENDING,
            WorkflowStep.due_at.is_not(None),
            WorkflowStep.due_at < moment,
        )
        .order_by(WorkflowStep.due_at.asc())
        .all()
    )


def scan_overdue_for_escalation(
    db: Session, *, now: datetime | None = None, batch_limit: int = 200
) -> dict[str, int]:
    """Notify-only escalation scan over every tenant's overdue trails (D2).

    Reuses the expired-lease pattern: find open trails whose deadline
    passed and nudge the assignee (else the opener) once per trail — the
    notification duplicate guard (LP-NOT-001) makes a repeated scan a
    no-op. Never reassigns, never mutates a trail, never commits: the
    caller (operator job, existing worker lease cycle) owns the commit.
    """
    moment = now or _utcnow()
    latest_ids = (
        db.query(func.max(WorkflowStep.id))
        .group_by(WorkflowStep.entity_type, WorkflowStep.entity_id)
        .subquery()
    )
    rows = (
        db.query(WorkflowStep)
        .filter(
            WorkflowStep.id.in_(db.query(latest_ids)),
            WorkflowStep.stage == STAGE_PENDING,
            WorkflowStep.due_at.is_not(None),
            WorkflowStep.due_at < moment,
        )
        .order_by(WorkflowStep.due_at.asc())
        .limit(batch_limit)
        .all()
    )
    notified = 0
    skipped = 0
    for row in rows:
        trail = (
            db.query(WorkflowStep)
            .filter(
                WorkflowStep.entity_type == row.entity_type,
                WorkflowStep.entity_id == row.entity_id,
            )
            .order_by(WorkflowStep.id.asc())
            .all()
        )
        recipient = _notify_requester(db, trail)
        if recipient is None:
            skipped += 1
            log.warning("escalation skipped: no recipient", step_id=row.id)
            continue
        title = f"Overdue workflow: {row.entity_type} {row.entity_id}"
        already = (
            db.query(Notification)
            .filter(
                Notification.category == "workflow",
                Notification.title == title,
                Notification.recipient_id == recipient,
                Notification.entity_type == row.entity_type,
                Notification.entity_id == row.entity_id,
            )
            .first()
        )
        if already is not None:
            skipped += 1
            log.info("escalation skipped: already notified", step_id=row.id)
            continue
        emitted = notify.emit(
            db,
            recipient_user_id=recipient,
            title=title,
            message=f"{row.entity_type} {row.entity_id} is past its due date.",
            notification_type="warning",
            category="workflow",
            entity_type=row.entity_type,
            entity_id=row.entity_id,
        )
        if emitted is None:
            skipped += 1
            log.warning("escalation skipped: opted out", step_id=row.id)
        else:
            notified += 1
            log.info("escalation notified", step_id=row.id)
    return {"scanned": len(rows), "notified": notified, "skipped": skipped}


def record_mirror(
    db: Session,
    *,
    actor: User,
    entity_type: str,
    entity_id: int,
    action: str,
    stage: str,
    comment: str | None = None,
    due_at: datetime | None = None,
    recipient_user_id: int | None = None,
    audit_action: str,
) -> WorkflowStep:
    """Mirror a domain decision the caller already made and gated.

    Adapters use this: the domain endpoint enforced its own roles and
    state machine, so the core appends without re-gating — it records,
    audits and notifies in one commit, and never touches domain columns.
    """
    _require_entity(entity_type)
    if action not in (ACTION_OPEN, ACTION_L1_APPROVE, ACTION_APPROVE, ACTION_REJECT, ACTION_RETURN):
        raise validation(
            "validation_error",
            f"Unknown mirror action {action!r}.",
            entity="WorkflowStep",
            fields=["action"],
        )
    if stage not in (STAGE_PENDING, STAGE_APPROVED, STAGE_REJECTED, STAGE_RETURNED):
        raise validation(
            "validation_error",
            f"Unknown mirror stage {stage!r}.",
            entity="WorkflowStep",
            fields=["stage"],
        )
    tenant_id = tenant_id_for(db)
    step = WorkflowStep(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        stage=stage,
        action=action,
        actor_id=actor.id,
        comment=comment,
        due_at=due_at,
    )
    db.add(step)
    return _finish(
        db,
        actor,
        step,
        audit_action,
        recipient_user_id,
        f"Workflow update: {entity_type} {entity_id}",
        (comment or "").strip() or f"{entity_type} {entity_id} reached {stage}.",
        "info",
    )


__all__ = [
    "ENTITY_ALLOWLIST",
    "STAGE_PENDING",
    "STAGE_APPROVED",
    "STAGE_REJECTED",
    "STAGE_RETURNED",
    "ACTION_OPEN",
    "ACTION_L1_APPROVE",
    "ACTION_APPROVE",
    "ACTION_REJECT",
    "ACTION_RETURN",
    "ACTION_REASSIGN",
    "assignee_of",
    "decide",
    "history",
    "overdue",
    "reassign",
    "record_mirror",
    "scan_overdue_for_escalation",
]
