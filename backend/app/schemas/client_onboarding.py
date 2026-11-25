from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class ClientCreate(BaseModel):
    name: str
    slug: str
    industry: Optional[str] = None
    country: Optional[str] = None
    timezone: str = "UTC"
    locale: str = "en"
    currency: Optional[str] = None  # ISO 4217
    date_format: Optional[str] = None
    working_week: Optional[str] = None
    primary_color: str = "#2563EB"
    secondary_color: str = "#1F2937"
    logo_url: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    status: str = "Draft"  # Draft | Provisioning | Active | Suspended | Read-only | Deprovisioning | Archived


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    currency: Optional[str] = None
    date_format: Optional[str] = None
    working_week: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    logo_url: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    status: Optional[str] = None


class ClientOut(ClientCreate):
    id: int
    deprovisioned_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClientSettingCreate(BaseModel):
    key: str
    value: Optional[str] = None


class ClientSettingOut(ClientSettingCreate):
    id: int
    client_id: int

    class Config:
        from_attributes = True


class FeatureFlagOut(BaseModel):
    id: int
    client_id: int
    key: str
    name: str
    description: Optional[str] = None
    enabled: bool
    config: Optional[str] = None

    class Config:
        from_attributes = True


class FeatureFlagUpdate(BaseModel):
    enabled: Optional[bool] = None
    config: Optional[str] = None


class IntegrationCreate(BaseModel):
    name: str
    kind: str
    endpoint: Optional[str] = None
    username: Optional[str] = None
    secret: Optional[str] = None
    notes: Optional[str] = None


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    endpoint: Optional[str] = None
    username: Optional[str] = None
    secret: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class IntegrationOut(BaseModel):
    id: int
    client_id: int
    name: str
    kind: str
    endpoint: Optional[str] = None
    username: Optional[str] = None
    status: str
    last_tested_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    notes: Optional[str] = None
    has_secret: bool = False

    class Config:
        from_attributes = True


class MigrationJobOut(BaseModel):
    id: int
    client_id: int
    integration_id: Optional[int] = None
    entity: str
    status: str
    total: int
    processed: int
    succeeded: int
    failed: int
    error_log: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MigrationStart(BaseModel):
    integration_id: Optional[int] = None
    entity: str
    total: int = 0


class OnboardingStepCreate(BaseModel):
    key: str
    title: str
    description: Optional[str] = None
    order_index: int = 0
    owner: Optional[str] = None


class OnboardingStepOut(BaseModel):
    id: int
    client_id: int
    key: str
    title: str
    description: Optional[str] = None
    order_index: int
    completed: bool
    completed_at: Optional[datetime] = None
    owner: Optional[str] = None

    class Config:
        from_attributes = True


class OnboardingProgress(BaseModel):
    client_id: int
    total: int
    completed: int
    percent: int
    steps: list[OnboardingStepOut]
