from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    actor_id: int | None = None
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    details: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class AuditFirstBroken(BaseModel):
    """Where the chain stopped holding, in the contract's shape."""

    id: str | None = None
    #: 0-based position in the walk of the entry that failed. For a
    #: ``head_mismatch`` this is the first position that is missing.
    index: int
    reason: str


class AuditVerification(BaseModel):
    """The result of walking the audit chain (``adminVerifyAudit``)."""

    verified: bool
    checked_entries: int
    #: The head the walk compared against. Record it outside the database:
    #: a chain rebuilt from the first entry is internally consistent, and
    #: only an external anchor detects that.
    head: str | None = None
    head_id: int | None = None
    first_broken: AuditFirstBroken | None = None
    verified_at: datetime
