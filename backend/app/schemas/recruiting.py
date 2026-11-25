from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime

from app.schemas.employee import EmployeeOut


# ---------- Job Requisition ----------
class RequisitionBase(BaseModel):
    req_number: str
    title: str
    department_id: int
    job_id: Optional[int] = None
    location: Optional[str] = None
    employment_type: str = "Full-time"
    openings: int = 1
    # `status` is a workflow state owned by the server (Draft -> Open -> ...
    # -> Closed). It is not accepted from the client on create.
    description: Optional[str] = None
    posted_date: Optional[date] = None
    closing_date: Optional[date] = None


class RequisitionCreate(RequisitionBase):
    pass


class RequisitionUpdate(BaseModel):
    title: Optional[str] = None
    department_id: Optional[int] = None
    job_id: Optional[int] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    openings: Optional[int] = None
    status: Optional[str] = None
    description: Optional[str] = None
    closing_date: Optional[date] = None


class RequisitionOut(RequisitionBase):
    id: int
    status: str = "Draft"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Candidate ----------
class CandidateBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    source: Optional[str] = None
    resume_url: Optional[str] = None
    # Server-owned pipeline stage; not accepted from the client on create.


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    resume_url: Optional[str] = None
    status: Optional[str] = None


class CandidateOut(CandidateBase):
    id: int
    status: str = "Applied"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Application ----------
class ApplicationBase(BaseModel):
    requisition_id: int
    candidate_id: int
    # Server-owned pipeline stage; not accepted from the client on create.
    notes: Optional[str] = None
    applied_date: date


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class ApplicationOut(ApplicationBase):
    id: int
    status: str = "Applied"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Offer ----------
class OfferBase(BaseModel):
    offer_number: str
    application_id: int
    job_id: Optional[int] = None
    salary_offered: Optional[float] = None
    start_date: date
    offer_date: date
    expiry_date: Optional[date] = None
    # Server-owned lifecycle state (Draft -> Sent -> Accepted/Rejected/...);
    # not accepted from the client on create.


class OfferCreate(OfferBase):
    pass


class OfferUpdate(BaseModel):
    salary_offered: Optional[float] = None
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None


class OfferOut(OfferBase):
    id: int
    status: str = "Draft"
    letter_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HireRequest(BaseModel):
    """Convert an accepted offer into an employee + onboarding checklist.

    Only `employee_id` is required; the rest is derived from the offer,
    application and requisition unless explicitly provided.
    """

    employee_id: str
    email: Optional[EmailStr] = None
    department_id: Optional[int] = None
    job_id: Optional[int] = None
    hire_date: Optional[date] = None
    salary: Optional[float] = None


class HireResult(BaseModel):
    employee: EmployeeOut
    onboarding_tasks_created: int
