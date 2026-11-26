"""HTTP surface for the workflow engine core.

Four routes, all tenant-scoped and fail-closed: another tenant's trail
reads as 404, a wrong role reads as 403, an illegal move reads as 409.
``/overdue`` is registered before the ``/{entity_type}`` routes so the
literal never parses as an entity type.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import WORKFORCE_ROLES, ADMIN_ROLES, get_db, require_roles
from app.models.user import User
from app.workflows import service as svc
from app.workflows.schemas import DecideIn, ReassignIn, WorkflowStepOut

router = APIRouter()


@router.get("/overdue", response_model=list[WorkflowStepOut], operation_id="workflowsListOverdue")
def list_overdue(
    entity_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    """Open caller-tenant trails whose caller-supplied ``due_at`` passed."""
    return svc.overdue(db, entity_type=entity_type)


@router.post(
    "/{entity_type}/{entity_id}/decide",
    response_model=WorkflowStepOut,
    operation_id="workflowsDecide",
)
def decide(
    entity_type: str,
    entity_id: int,
    payload: DecideIn,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    """Record one role-gated decision; the stage moves forward, at most once."""
    return svc.decide(
        db,
        actor=u,
        entity_type=entity_type,
        entity_id=entity_id,
        action=payload.action,
        comment=payload.comment,
        due_at=payload.due_at,
    )


@router.post(
    "/{entity_type}/{entity_id}/reassign",
    response_model=WorkflowStepOut,
    operation_id="workflowsReassign",
)
def reassign(
    entity_type: str,
    entity_id: int,
    payload: ReassignIn,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Hand an open trail to another user. Admin roles only."""
    return svc.reassign(
        db,
        actor=u,
        entity_type=entity_type,
        entity_id=entity_id,
        to_user_id=payload.to_user,
        comment=payload.comment,
    )


@router.get(
    "/{entity_type}/{entity_id}/history",
    response_model=list[WorkflowStepOut],
    operation_id="workflowsHistory",
)
def history(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    """The append-only, tenant-isolated trail behind an entity, oldest first."""
    return svc.history(db, entity_type=entity_type, entity_id=entity_id)
