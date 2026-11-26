"""Schemas for the confidential Employee Relations module (gap #9)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ERCaseType = Literal["grievance", "discipline", "investigation", "whistleblowing"]
ERSeverity = Literal["Low", "Medium", "High", "Critical"]
ERStatus = Literal[
    "Open", "Triaged", "Investigating", "ActionTaken", "Resolved", "Closed"
]


class ERCaseCreate(BaseModel):
    case_type: ERCaseType
    subject_employee_id: Optional[int] = None
    severity: ERSeverity = "Medium"
    classification: Optional[str] = None
    assigned_to: Optional[str] = None


class ERCaseUpdate(BaseModel):
    severity: Optional[ERSeverity] = None
    status: Optional[ERStatus] = None
    assigned_to: Optional[str] = None
    classification: Optional[str] = None
    outcome: Optional[str] = None


class ERCaseOut(BaseModel):
    id: int
    tenant_id: Optional[str] = None
    case_type: str
    subject_employee_id: Optional[int] = None
    reported_by: str
    severity: str
    status: str
    assigned_to: Optional[str] = None
    classification: Optional[str] = None
    outcome: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ERCaseCommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=10000)


class ERCaseCommentOut(BaseModel):
    id: int
    case_id: int
    author: str
    comment: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ERCaseAttachmentCreate(BaseModel):
    #: The attachment's file name. Both-or-neither with ``file_key``: one
    #: without the other is refused with 422.
    filename: Optional[str] = None
    #: The attachment's opaque key inside the storage backend. It must name
    #: a key under the authorised ``/api/v1/files/`` route — anything else
    #: is refused with 422.
    file_key: Optional[str] = None


class ERCaseAttachmentOut(BaseModel):
    id: int
    case_id: int
    filename: str
    file_key: str
    uploaded_by: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ERSummaryOut(BaseModel):
    by_case_type: dict[str, int]
    by_status: dict[str, int]
    total: int
