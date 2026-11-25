from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    """A new asset. ``status`` is not settable: every asset starts
    ``in_stock`` and moves only through the explicit lifecycle endpoints."""

    tag: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(default="General", min_length=1, max_length=60)
    description: Optional[str] = None
    serial_number: Optional[str] = Field(default=None, max_length=120)


class AssetUpdate(BaseModel):
    """A partial metadata edit. Only the fields sent are changed; ``status``
    is deliberately absent — lifecycle moves are endpoints, not edits."""

    tag: Optional[str] = Field(default=None, min_length=1, max_length=40)
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    category: Optional[str] = Field(default=None, min_length=1, max_length=60)
    description: Optional[str] = None
    serial_number: Optional[str] = Field(default=None, max_length=120)


class AssetOut(BaseModel):
    id: int
    tenant_id: Optional[str] = None
    tag: str
    name: str
    category: str
    description: Optional[str] = None
    serial_number: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssetAssign(BaseModel):
    employee_id: int
    notes: Optional[str] = None


class AssetTransfer(BaseModel):
    """Move custody to another employee: the open assignment closes and a
    new, unacknowledged one opens in the same transaction."""

    employee_id: int
    notes: Optional[str] = None


class AssetReturn(BaseModel):
    """The condition decides the asset's next status:
    good -> in_stock, damaged -> maintenance, lost -> lost."""

    condition: Literal["good", "damaged", "lost"]
    notes: Optional[str] = None


class AssetMaintenance(BaseModel):
    notes: Optional[str] = None


class AssetRetire(BaseModel):
    reason: Optional[str] = None


class AssetAssignmentOut(BaseModel):
    id: int
    tenant_id: Optional[str] = None
    asset_id: int
    employee_id: int
    status: str
    notes: Optional[str] = None
    assigned_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    close_reason: Optional[str] = None
    return_condition: Optional[str] = None

    class Config:
        from_attributes = True


class AssetClearanceItem(BaseModel):
    assignment_id: int
    asset_id: int
    tag: str
    name: str
    assigned_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None


class AssetClearanceOut(BaseModel):
    """Read-only asset clearance for offboarding: the open custody spells
    an employee must settle before separation. Consuming this never writes
    anything on the offboarding side."""

    employee_id: int
    clear: bool
    outstanding_count: int
    outstanding: list[AssetClearanceItem]