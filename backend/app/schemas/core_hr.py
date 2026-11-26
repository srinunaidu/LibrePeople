from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

#: The HR helpdesk case categories (LP-SVC-001). The closed set the queue
#: triages on. An intake case carries no category of its own: the public
#: form writes the default, and the queue tells those cases apart by
#: status ("Intake") and source ("public_contact").
CaseCategory = Literal[
    "Payroll", "Benefits", "IT", "Facilities", "Policy", "General",
]

#: The HR helpdesk case priorities (LP-SVC-001). No SLA engine reads them
#: (LP-SVC-002 is out of scope): they order the queue, nothing more.
CasePriority = Literal["Low", "Medium", "High", "Urgent"]

#: The HR helpdesk case statuses (LP-SVC-001). The machine is
#: ``Open > InProgress > Resolved > Closed`` — forward only, one step at a
#: time, with a resolution required to resolve. ``Intake`` is the public
#: form's lane: the queue reads it by name and never transitions into or
#: out of it through this machine.
CaseStatus = Literal["Open", "InProgress", "Resolved", "Closed", "Intake"]


class LocationBase(BaseModel):
    name: str
    code: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: str = "UTC"
    is_active: bool = True


class LocationCreate(LocationBase):
    """`code` optional — auto-generated (LOC-0007) when omitted."""

    code: Optional[str] = None


class LocationUpdate(BaseModel):
    """A partial edit of a location. Only the fields sent are changed."""

    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class LocationOut(LocationBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CostCenterBase(BaseModel):
    code: str
    name: str
    department_id: Optional[int] = None
    is_active: bool = True


class CostCenterCreate(CostCenterBase):
    """`code` optional — auto-generated (CC-0007) when omitted."""

    code: Optional[str] = None


class CostCenterUpdate(BaseModel):
    """A partial edit of a cost centre. Only the fields sent are changed."""

    code: Optional[str] = None
    name: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class CostCenterOut(CostCenterBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PositionBase(BaseModel):
    code: str
    title: str
    job_id: int
    department_id: int
    location_id: Optional[int] = None
    reports_to_position_id: Optional[int] = None
    fte: float = 1.0
    is_active: bool = True


class PositionCreate(PositionBase):
    """`code` optional — auto-generated (POS-0007) when omitted."""

    code: Optional[str] = None


class PositionUpdate(BaseModel):
    """A partial edit of a position. Only the fields sent are changed."""

    code: Optional[str] = None
    title: Optional[str] = None
    job_id: Optional[int] = None
    department_id: Optional[int] = None
    location_id: Optional[int] = None
    reports_to_position_id: Optional[int] = None
    fte: Optional[float] = None
    is_active: Optional[bool] = None


class PositionOut(PositionBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LegalEntityBase(BaseModel):
    name: str
    code: str
    country: Optional[str] = None
    registration_number: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True


class LegalEntityCreate(LegalEntityBase):
    """`code` optional — auto-generated (LE-0007) when omitted."""

    code: Optional[str] = None


class LegalEntityUpdate(BaseModel):
    """A partial edit of a legal entity. Only the fields sent are changed."""

    name: Optional[str] = None
    code: Optional[str] = None
    country: Optional[str] = None
    registration_number: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class LegalEntityOut(LegalEntityBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmployeeDocumentCreate(BaseModel):
    employee_id: int
    document_type: str
    file_name: str
    storage_url: str
    # LP-DOC-002: the opaque key inside the storage backend. When omitted
    # it is derived from ``storage_url`` (the ``/api/v1/files/`` prefix is
    # stripped); the download route and the retention sweep key off it.
    storage_key: Optional[str] = None
    # LP-DOC-002: keep-until date once the document is Expired. The purge
    # deletes only Expired documents on or past this date.
    retention_until: Optional[date] = None
    status: str = "Active"
    expiry_date: Optional[date] = None


class EmployeeDocumentOut(EmployeeDocumentCreate):
    id: int
    # LP-DOC-002: the newest version number; 1 after the first upload.
    current_version: int = 1
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentVersionCreate(BaseModel):
    """A further upload of a document's content (LP-DOC-002)."""

    file_name: str
    storage_url: str
    storage_key: Optional[str] = None


class DocumentVersionOut(BaseModel):
    id: int
    document_id: int
    version_no: int
    file_name: str
    storage_key: Optional[str] = None
    storage_url: str
    uploaded_by: Optional[str] = None
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentAckOut(BaseModel):
    """One acknowledgement of a document (LP-DOC-002)."""

    id: int
    document_id: int
    acknowledged_by: str
    acknowledged_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentAccessLogOut(BaseModel):
    """One authenticated download of a document (LP-DOC-002)."""

    id: int
    document_id: int
    accessed_by: str
    accessed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HRCaseCreate(BaseModel):
    employee_id: Optional[int] = None
    subject: str
    category: CaseCategory = "General"
    priority: CasePriority = "Medium"
    assigned_to: Optional[str] = None
    sla_due: Optional[datetime] = None


class HRCaseUpdate(BaseModel):
    subject: Optional[str] = None
    category: Optional[CaseCategory] = None
    priority: Optional[CasePriority] = None
    status: Optional[CaseStatus] = None
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None


class HRCaseOut(HRCaseCreate):
    id: int
    status: str
    resolution: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PublicContactCreate(BaseModel):
    """Fields the public contact form sends — the demo / lead funnel.

    The schema is **closed**: a field that is not listed is refused rather
    than ignored, so a request that carries an employee id, a tenant id or a
    comment never reaches the database. A public form is the one place where
    a client gets to choose the shape of a request, so the shape is fixed
    here rather than negotiated.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field(min_length=1, max_length=4000)
    company: str | None = Field(default=None, max_length=120)
    company_size: str | None = Field(default=None, max_length=20)
    interest: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=30)


class PublicContactAccepted(BaseModel):
    """What the sender is told.

    A receipt, and nothing else: the case id is not returned, because a
    sequential id is a thing a visitor can walk, and the queue is not the
    visitor's business.
    """

    received: bool = True


class CaseCommentCreate(BaseModel):
    case_id: int
    author: str
    comment: str
    #: The attachment's file name (LP-SVC-001). Both-or-neither with
    #: ``attachment_key``: one without the other is refused with 422.
    attachment_filename: Optional[str] = None
    #: The attachment's opaque key inside the storage backend (LP-SVC-001).
    #: It must name a key under the authorised ``/api/v1/files/`` route —
    #: anything else is refused with 422, so a comment can never point at
    #: an unserved or guessable location.
    attachment_key: Optional[str] = None


class CaseCommentOut(CaseCommentCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
