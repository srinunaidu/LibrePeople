from pydantic import BaseModel
from typing import Optional


class CustomFieldDefBase(BaseModel):
    key: str
    label: str
    field_type: str = "text"
    required: bool = False
    is_sensitive: bool = False
    visibility: str = "all"
    options_json: Optional[str] = None
    is_active: bool = True


class CustomFieldDefCreate(CustomFieldDefBase):
    """Create a tenant-configured employee attribute (LP-CORE-005)."""


class CustomFieldDefUpdate(BaseModel):
    """A partial edit of a definition. Only the fields sent are changed."""

    label: Optional[str] = None
    field_type: Optional[str] = None
    required: Optional[bool] = None
    is_sensitive: Optional[bool] = None
    visibility: Optional[str] = None
    options_json: Optional[str] = None
    is_active: Optional[bool] = None


class CustomFieldDefOut(CustomFieldDefBase):
    id: int

    class Config:
        from_attributes = True
