from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SSOConfigCreate(BaseModel):
    provider: str
    entity_id: Optional[str] = None
    sso_url: Optional[str] = None
    certificate: Optional[str] = None
    client_id_ext: Optional[str] = None
    client_secret: Optional[str] = None
    is_active: bool = False


class SSOConfigOut(SSOConfigCreate):
    id: int
    client_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WebhookCreate(BaseModel):
    url: str
    events: str
    secret: Optional[str] = None
    is_active: bool = True


class WebhookOut(WebhookCreate):
    id: int
    client_id: Optional[int] = None
    last_triggered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WebhookDeliveryOut(BaseModel):
    id: int
    webhook_id: int
    event: str
    status: str
    response_code: Optional[int] = None
    attempts: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BackgroundCheckCreate(BaseModel):
    candidate_id: int
    provider: str = "manual"
    status: str = "Pending"
    result: Optional[str] = None


class BackgroundCheckOut(BackgroundCheckCreate):
    id: int
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ESignatureCreate(BaseModel):
    document_type: str
    entity_id: Optional[int] = None
    signer_email: str
    signer_name: Optional[str] = None
    provider: str = "internal"


class ESignatureOut(ESignatureCreate):
    id: int
    status: str
    provider_ref: Optional[str] = None
    signed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
