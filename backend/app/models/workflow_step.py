from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Identity, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base

#: NFR-014 safe constraints. The SQL texts are shared with migration
#: 0050_workflow_steps — the models and the migration cannot disagree.
#: Dialect-portable plain comparisons: no regexp_like, no GLOB, no enums
#: (plain String keeps PostgreSQL free of CREATE TYPE checkfirst issues).
#: W1: the stage lifecycle the service walks.
STAGE_CHECK = "stage IN ('PENDING','APPROVED','REJECTED','RETURNED')"
#: W2: the only actions the service ever writes.
ACTION_CHECK = "action IN ('OPEN','L1_APPROVE','APPROVE','REJECT','RETURN','REASSIGN')"


class WorkflowStep(Base):
    """One row of an entity's decision trail (workflow engine core).

    The core never owns domain state: callers (expenses, HR cases,
    documents, assets) keep their own status columns and the core only
    records the decisions made about them. Rows are append-only — there is
    no update or delete route — so the rows behind an entity are its
    ordered history. The latest row's ``stage`` is the entity's current
    workflow position; ``due_at`` is caller-supplied and nullable
    (NULL = never overdue, per D3).
    """

    __tablename__ = "workflow_steps"
    __table_args__ = (
        Index("ix_workflow_steps_tenant_id_id", "tenant_id", "id"),
        CheckConstraint(STAGE_CHECK, name="ck_wf_stage_fsm"),
        CheckConstraint(ACTION_CHECK, name="ck_wf_action_fsm"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
