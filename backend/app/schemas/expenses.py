from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExpenseCategoryBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool = True


class ExpenseCategoryCreate(ExpenseCategoryBase):
    """`code` optional — auto-generated (EXP-0007) when omitted."""

    code: Optional[str] = None


class ExpenseCategoryUpdate(BaseModel):
    """A partial edit of an expense category. Only the fields sent are changed."""

    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ExpenseCategoryOut(ExpenseCategoryBase):
    id: int
    tenant_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpenseClaimCreate(BaseModel):
    employee_id: int
    category_id: int
    expense_date: date
    amount: float = Field(gt=0, description="Reimbursable amount, greater than zero")
    currency: str = Field(default="INR", min_length=3, max_length=3)
    description: Optional[str] = None


class ExpenseClaimUpdate(BaseModel):
    """A draft-only edit. Only the fields sent are changed; the endpoint
    refuses anything once the claim has left DRAFT."""

    category_id: Optional[int] = None
    expense_date: Optional[date] = None
    amount: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    description: Optional[str] = None


class ExpenseClaimOut(BaseModel):
    id: int
    tenant_id: Optional[str] = None
    employee_id: int
    category_id: int
    expense_date: date
    amount: float
    currency: str
    description: Optional[str] = None
    status: str
    payment_status: str
    submitted_at: Optional[datetime] = None
    l1_approved_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpenseReject(BaseModel):
    reason: Optional[str] = None


class ExpenseReceiptOut(BaseModel):
    id: int
    tenant_id: Optional[str] = None
    claim_id: int
    file_name: str
    content_type: str
    size_bytes: int
    download_url: str
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True
