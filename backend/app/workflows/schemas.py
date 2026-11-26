"""Request/response shapes for the workflow engine core."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DecideIn(BaseModel):
    """One decision on an entity's trail."""

    action: Literal["approve", "reject", "return"]
    comment: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = Field(
        default=None,
        description="Caller-supplied deadline (D3). Only honoured when the decision opens the trail; nullable, NULL = never overdue.",
    )


class ReassignIn(BaseModel):
    """Hand an open trail to another user."""

    to_user: int
    comment: str | None = Field(default=None, max_length=2000)


class WorkflowStepOut(BaseModel):
    """One row of a decision trail."""

    id: int
    tenant_id: str | None = None
    entity_type: str
    entity_id: int
    stage: str
    action: str
    actor_id: int | None = None
    comment: str | None = None
    due_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
