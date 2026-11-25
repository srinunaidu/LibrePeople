from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# --- ESS Profile ----------------------------------------------------------- #

class ESSProfileCreate(BaseModel):
    employee_id: int
    preferred_name: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    bank_routing: Optional[str] = None
    tax_id: Optional[str] = None
    direct_deposit_enabled: bool = False
    notification_email: bool = True
    notification_sms: bool = False
    notification_push: bool = True
    language: str = "en"
    theme_preference: str = "light"


class ESSProfileOut(ESSProfileCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Notifications ---------------------------------------------------------- #

class NotificationCreate(BaseModel):
    recipient_id: int
    title: str
    message: str
    notification_type: str = "info"
    category: str = "system"
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None


class NotificationOut(NotificationCreate):
    id: int
    is_read: bool
    read_at: Optional[datetime] = None
    email_sent: bool
    delivery_status: str = "queued"
    delivery_attempts: int = 0
    delivery_error: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    """Partial update of the caller's own channel flags (LP-NOT-003).

    Every field is optional; only the flags present are changed. There
    is no target selector: the endpoint always writes the caller's own
    ESS profile, so it is owner-only by construction.
    """

    email: Optional[bool] = None
    sms: Optional[bool] = None
    push: Optional[bool] = None


# --- Employee Files --------------------------------------------------------- #

class EmployeeFileCreate(BaseModel):
    employee_id: int
    document_type: str
    file_name: str
    storage_url: str
    status: str = "Active"
    expiry_date: Optional[date] = None
    uploaded_by: Optional[str] = None
    notes: Optional[str] = None


class EmployeeFileOut(EmployeeFileCreate):
    id: int
    version: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Announcements ---------------------------------------------------------- #

class AnnouncementCreate(BaseModel):
    title: str
    content: str
    category: str = "General"
    priority: str = "Normal"
    target_audience: str = "All"
    target_value: Optional[str] = None
    published: bool = False
    expires_at: Optional[datetime] = None


class AnnouncementOut(AnnouncementCreate):
    id: int
    published_at: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Employee Directory ----------------------------------------------------- #

class DirectoryEntryOut(BaseModel):
    id: int
    employee_id: int
    full_name: str
    email: str
    department: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# --- Org Chart -------------------------------------------------------------- #

class OrgNodeOut(BaseModel):
    employee_id: int
    manager_id: Optional[int] = None
    depth: int
    path: Optional[str] = None

    class Config:
        from_attributes = True


# --- Goal Alignment (OKR) --------------------------------------------------- #

class GoalAlignmentCreate(BaseModel):
    goal_id: int
    parent_goal_id: Optional[int] = None


class GoalAlignmentOut(GoalAlignmentCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Continuous Feedback ---------------------------------------------------- #

class ContinuousFeedbackCreate(BaseModel):
    from_employee_id: int
    to_employee_id: int
    feedback_type: str = "Praise"
    message: str
    is_private: bool = False


class ContinuousFeedbackOut(ContinuousFeedbackCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Compliance Check ------------------------------------------------------- #

class ComplianceCheckOut(BaseModel):
    id: int
    rule_id: int
    run_at: Optional[datetime] = None
    passed: bool
    details: Optional[str] = None

    class Config:
        from_attributes = True
