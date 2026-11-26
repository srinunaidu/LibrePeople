"""Expense categories, claims and receipts (LP-EXP-001+002).

Money moves only through explicit endpoints: clients cannot set ``status``
or ``payment_status`` directly (neither schema exposes them), so a claim can
only travel ``DRAFT -> SUBMITTED -> L1_APPROVED -> APPROVED`` (with
``REJECTED`` out of the two middle states and back to ``DRAFT`` for rework),
and ``UNPAID -> PAID`` only via an explicit mark-paid on an ``APPROVED``
claim. Every write is audited, every read is tenant-scoped, and receipt
bytes are stored under opaque keys served only through the authenticated
``GET /api/v1/files/{key}`` route.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import (
    ADMIN_ROLES,
    ALL_ROLES,
    MANAGER_ROLES,
    WORKFORCE_ROLES,
    get_db,
    require_roles,
    tenant_id_for,
)
from app.core.audit import record_audit
from app.core.booleans import is_true
from app.core.errors import ApiError, ErrorCategory, conflict, forbidden, not_found, validation
from app.core.ids import next_code
from app.core.master_data import (
    ensure_reference,
    load_or_404,
    refuse_null_updates,
)
from app.core.tenancy import DEFAULT_TENANT_SLUG, tenant_column_criterion, tenant_matches
from app.core.visibility import (
    apply_visibility,
    ensure_can_view_employee,
    ensure_can_view_employee_or_403,
)
from app.models.employee import Employee
from app.models.expenses import ExpenseCategory, ExpenseClaim, ExpenseReceipt
from app.models.user import User
from app.services.notifications import user_id_for_employee
from app.workflows import service as wf_service
from app.schemas.expenses import (
    ExpenseCategoryCreate,
    ExpenseCategoryOut,
    ExpenseCategoryUpdate,
    ExpenseClaimCreate,
    ExpenseClaimOut,
    ExpenseClaimUpdate,
    ExpenseReceiptOut,
    ExpenseReject,
)
from app.storage.backends import get_storage

router = APIRouter()

#: The largest receipt the endpoint accepts. Ten megabytes holds a phone
#: photo of a receipt; anything larger is refused before it is stored.
RECEIPT_MAX_BYTES = 10 * 1024 * 1024


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_unique_expense_category_code(
    db: Session, code: str, exclude_id: int | None = None
) -> None:
    """Refuse a second expense category carrying the same code in one tenant.

    Tenant-scoped: the same code may exist in two tenants, but never twice
    in one. The comparison is case-insensitive. A NULL ``tenant_id``
    denotes a pre-backfill row belonging to the legacy default tenant, so
    a default-tenant request matches both NULL and ``"default"`` rows,
    while any other tenant matches only its own rows. A global check would
    leak existence across tenants (a 409 for a code the caller may not
    see); this check only ever compares within the caller's bucket.
    """
    if code is None:
        return
    wanted = str(code).strip()
    if not wanted:
        return
    query = (
        db.query(func.count())
        .select_from(ExpenseCategory)
        .filter(func.lower(ExpenseCategory.code) == func.lower(wanted))
    )
    if exclude_id is not None:
        query = query.filter(ExpenseCategory.id != exclude_id)
    tenant_id = tenant_id_for(db)
    if tenant_id is None:
        tenant_id = DEFAULT_TENANT_SLUG
    if tenant_id == DEFAULT_TENANT_SLUG:
        query = query.filter(
            or_(
                ExpenseCategory.tenant_id == tenant_id,
                ExpenseCategory.tenant_id.is_(None),
            )
        )
    else:
        query = query.filter(ExpenseCategory.tenant_id == tenant_id)
    if query.scalar():
        raise conflict(
            "duplicate_natural_key",
            f"ExpenseCategory already uses the code {wanted!r}. Codes are unique.",
            entity="expensecategory",
            value=wanted,
        )


def _load_category(db: Session, category_id: int) -> ExpenseCategory:
    """Load one category, refusing another tenant's row fail-closed."""
    obj = load_or_404(db, ExpenseCategory, category_id, "ExpenseCategory")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(getattr(obj, "tenant_id", None), tenant_id):
        raise not_found("ExpenseCategory")
    return obj


def _load_claim(db: Session, claim_id: int) -> ExpenseClaim:
    """Load one claim, refusing another tenant's row fail-closed."""
    obj = load_or_404(db, ExpenseClaim, claim_id, "ExpenseClaim")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not tenant_matches(getattr(obj, "tenant_id", None), tenant_id):
        raise not_found("ExpenseClaim")
    return obj


def _require_status(claim: ExpenseClaim, allowed: tuple[str, ...], target: str) -> None:
    """Refuse a claim move that is not on the state machine."""
    if claim.status not in allowed:
        raise validation(
            "invalid_state_transition",
            f"Cannot move expense claim from '{claim.status}' to '{target}'. "
            f"Allowed next states: {list(allowed) or 'none (final)'}",
            from_state=claim.status,
            to_state=target,
        )


def _ensure_owner(db: Session, u: User, employee_id: int) -> None:
    """Associates act only on their own claims; everyone else needs the
    reporting-line visibility the rest of the product uses."""
    if u.role == "Associate" and u.employee_id != employee_id:
        raise forbidden("Associates may only act on their own expense claims.")
    ensure_can_view_employee(db, u, employee_id)


def _receipt_out(receipt: ExpenseReceipt) -> ExpenseReceiptOut:
    return ExpenseReceiptOut(
        id=receipt.id,
        tenant_id=receipt.tenant_id,
        claim_id=receipt.claim_id,
        file_name=receipt.file_name,
        content_type=receipt.content_type,
        size_bytes=receipt.size_bytes,
        download_url=f"/api/v1/files/{receipt.storage_key}",
        uploaded_at=receipt.uploaded_at,
    )


# --- Categories ------------------------------------------------------------- #


@router.get("/categories", response_model=list[ExpenseCategoryOut], operation_id="expensesListCategories")
def list_categories(
    db: Session = Depends(get_db),
    include_inactive: bool = False,
    u: User = Depends(require_roles(*ALL_ROLES)),
):
    """Expense categories, by code.

    Tenant-scoped: a caller sees only their own tenant's categories (plus
    pre-backfill rows for the legacy default tenant). `include_inactive`
    lets the maintenance list see an archived category so it can restore it.
    """
    query = db.query(ExpenseCategory)
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        query = query.filter(tenant_column_criterion(ExpenseCategory.tenant_id, tenant_id))
    if not include_inactive:
        query = query.filter(is_true(ExpenseCategory.is_active))
    return query.order_by(ExpenseCategory.code).all()


@router.post("/categories", response_model=ExpenseCategoryOut, status_code=201, operation_id="expensesCreateCategory")
def create_category(
    payload: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    category_code = (payload.code or "").strip() or next_code(db, ExpenseCategory, ExpenseCategory.code, "EXP-")
    payload = payload.model_copy(update={"code": category_code})
    _ensure_unique_expense_category_code(db, category_code)
    obj = ExpenseCategory(**payload.model_dump())
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not getattr(obj, "tenant_id", None):
        obj.tenant_id = tenant_id
    db.add(obj)
    db.commit()
    db.refresh(obj)
    record_audit(db, u, "create_expense_category", "ExpenseCategory", obj.id, details=f"code={obj.code}")
    db.commit()
    return obj


@router.get("/categories/{category_id}", response_model=ExpenseCategoryOut, operation_id="expensesGetCategory")
def read_category(
    category_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ALL_ROLES)),
):
    return _load_category(db, category_id)


@router.patch("/categories/{category_id}", response_model=ExpenseCategoryOut, operation_id="expensesUpdateCategory")
def update_category(
    category_id: int,
    payload: ExpenseCategoryUpdate,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Edit a category, including archiving it (`is_active: false`) and
    restoring it (`is_active: true`). Archiving never deletes the row, so
    claims filed under it keep their history."""
    obj = _load_category(db, category_id)
    changes = payload.model_dump(exclude_unset=True)
    refuse_null_updates(changes, ("name", "code", "is_active"), "ExpenseCategory")
    if "code" in changes:
        _ensure_unique_expense_category_code(
            db, changes["code"], exclude_id=category_id
        )
    for field, value in changes.items():
        setattr(obj, field, value)
    db.add(obj)
    record_audit(db, u, "update_expense_category", "ExpenseCategory", obj.id, details=",".join(sorted(changes)) or "no change")
    db.commit()
    db.refresh(obj)
    return obj


# --- Claims ----------------------------------------------------------------- #


@router.get("/claims", response_model=list[ExpenseClaimOut], operation_id="expensesListClaims")
def list_claims(
    employee_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
) -> Any:
    """Expense claims, scoped to the caller's visibility and tenant."""
    query = db.query(ExpenseClaim)
    query = apply_visibility(query, ExpenseClaim.employee_id, u, db)
    if employee_id is not None:
        query = query.filter(ExpenseClaim.employee_id == employee_id)
    if status:
        query = query.filter(ExpenseClaim.status == status)
    return query.order_by(ExpenseClaim.id.desc()).all()


@router.post("/claims", response_model=ExpenseClaimOut, status_code=201, operation_id="expensesCreateClaim")
def create_claim(
    payload: ExpenseClaimCreate,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    _ensure_owner(db, u, payload.employee_id)
    ensure_reference(db, Employee, payload.employee_id, "Employee")
    category = ensure_reference(db, ExpenseCategory, payload.category_id, "ExpenseCategory")
    tenant_id = tenant_id_for(db)
    if tenant_id is not None:
        if not tenant_matches(getattr(category, "tenant_id", None), tenant_id):
            raise validation(
                "reference_not_found",
                f"ExpenseCategory {payload.category_id} does not exist.",
                entity="ExpenseCategory",
                id=payload.category_id,
            )
    if not is_true(category.is_active):
        raise validation(
            "expense_category_inactive",
            f"ExpenseCategory {category.code!r} is archived and no longer accepts claims.",
            entity="ExpenseCategory",
            id=category.id,
        )
    obj = ExpenseClaim(
        employee_id=payload.employee_id,
        category_id=payload.category_id,
        expense_date=payload.expense_date,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        status="DRAFT",
        payment_status="UNPAID",
    )
    if tenant_id is not None and not getattr(obj, "tenant_id", None):
        obj.tenant_id = tenant_id
    db.add(obj)
    db.commit()
    db.refresh(obj)
    record_audit(db, u, "create_expense_claim", "ExpenseClaim", obj.id, details=f"amount={obj.amount}")
    db.commit()
    return obj


@router.get("/claims/{claim_id}", response_model=ExpenseClaimOut, operation_id="expensesGetClaim")
def read_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    obj = _load_claim(db, claim_id)
    ensure_can_view_employee(db, u, obj.employee_id)
    return obj


@router.patch("/claims/{claim_id}", response_model=ExpenseClaimOut, operation_id="expensesUpdateClaim")
def update_claim(
    claim_id: int,
    payload: ExpenseClaimUpdate,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    """Edit a draft. Once the claim has been submitted the numbers are
    frozen: the decision trail must describe what was actually decided."""
    obj = _load_claim(db, claim_id)
    _ensure_owner(db, u, obj.employee_id)
    if obj.status != "DRAFT":
        raise conflict(
            "expense_claim_locked",
            f"Only a draft claim can be edited; claim {claim_id} is {obj.status}.",
            id=claim_id,
            status=obj.status,
        )
    changes = payload.model_dump(exclude_unset=True)
    refuse_null_updates(changes, ("category_id", "expense_date", "amount", "currency"), "ExpenseClaim")
    if "category_id" in changes:
        category = ensure_reference(db, ExpenseCategory, changes["category_id"], "ExpenseCategory")
        tenant_id = tenant_id_for(db)
        if tenant_id is not None:
            if not tenant_matches(getattr(category, "tenant_id", None), tenant_id):
                raise validation(
                    "reference_not_found",
                    f"ExpenseCategory {changes['category_id']} does not exist.",
                    entity="ExpenseCategory",
                    id=changes["category_id"],
                )
        if not is_true(category.is_active):
            raise validation(
                "expense_category_inactive",
                f"ExpenseCategory {category.code!r} is archived and no longer accepts claims.",
                entity="ExpenseCategory",
                id=category.id,
            )
    for field, value in changes.items():
        setattr(obj, field, value)
    db.add(obj)
    record_audit(db, u, "update_expense_claim", "ExpenseClaim", obj.id, details=",".join(sorted(changes)) or "no change")
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/claims/{claim_id}/submit", response_model=ExpenseClaimOut, operation_id="expensesSubmitClaim")
def submit_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    obj = _load_claim(db, claim_id)
    _ensure_owner(db, u, obj.employee_id)
    _require_status(obj, ("DRAFT",), "SUBMITTED")
    if not is_true(obj.category.is_active):
        raise conflict(
            "expense_category_inactive",
            f"ExpenseCategory {obj.category.code!r} was archived; restore it before submitting.",
            id=obj.category_id,
        )
    obj.status = "SUBMITTED"
    obj.submitted_by = u.id
    obj.submitted_at = _utcnow()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    record_audit(db, u, "submit_expense_claim", "ExpenseClaim", obj.id)
    db.commit()
    return obj


@router.post("/claims/{claim_id}/l1-approve", response_model=ExpenseClaimOut, operation_id="expensesL1ApproveClaim")
def l1_approve_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*MANAGER_ROLES)),
):
    """First approval rung: the claimant's reporting line signs off."""
    obj = _load_claim(db, claim_id)
    ensure_can_view_employee_or_403(db, u, obj.employee_id)
    _require_status(obj, ("SUBMITTED",), "L1_APPROVED")
    obj.status = "L1_APPROVED"
    obj.l1_approved_by = u.id
    obj.l1_approved_at = _utcnow()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    record_audit(db, u, "l1_approve_expense_claim", "ExpenseClaim", obj.id)
    db.commit()
    wf_service.record_mirror(
        db, actor=u, entity_type="expense_claim", entity_id=obj.id,
        action="L1_APPROVE", stage="PENDING",
        comment="L1 approval mirrored from the expense claim.",
        recipient_user_id=user_id_for_employee(db, obj.employee_id),
        audit_action="workflow_mirror_expense_l1",
    )
    return obj


@router.post("/claims/{claim_id}/approve", response_model=ExpenseClaimOut, operation_id="expensesApproveClaim")
def approve_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Final approval: finance confirms a claim the line already approved."""
    obj = _load_claim(db, claim_id)
    _require_status(obj, ("L1_APPROVED",), "APPROVED")
    obj.status = "APPROVED"
    obj.approved_by = u.id
    obj.approved_at = _utcnow()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    record_audit(db, u, "approve_expense_claim", "ExpenseClaim", obj.id)
    db.commit()
    wf_service.record_mirror(
        db, actor=u, entity_type="expense_claim", entity_id=obj.id,
        action="APPROVE", stage="APPROVED",
        comment="Final approval mirrored from the expense claim.",
        recipient_user_id=user_id_for_employee(db, obj.employee_id),
        audit_action="workflow_mirror_expense_final",
    )
    return obj


@router.post("/claims/{claim_id}/reject", response_model=ExpenseClaimOut, operation_id="expensesRejectClaim")
def reject_claim(
    claim_id: int,
    payload: ExpenseReject,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*MANAGER_ROLES)),
):
    obj = _load_claim(db, claim_id)
    ensure_can_view_employee_or_403(db, u, obj.employee_id)
    _require_status(obj, ("SUBMITTED", "L1_APPROVED"), "REJECTED")
    obj.status = "REJECTED"
    obj.rejected_by = u.id
    obj.rejected_at = _utcnow()
    obj.rejection_reason = payload.reason
    db.add(obj)
    db.commit()
    db.refresh(obj)
    record_audit(db, u, "reject_expense_claim", "ExpenseClaim", obj.id, details=(payload.reason or "")[:200])
    db.commit()
    return obj


@router.post("/claims/{claim_id}/rework", response_model=ExpenseClaimOut, operation_id="expensesReworkClaim")
def rework_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    """Send a rejected claim back to draft so the claimant can fix it."""
    obj = _load_claim(db, claim_id)
    _ensure_owner(db, u, obj.employee_id)
    _require_status(obj, ("REJECTED",), "DRAFT")
    obj.status = "DRAFT"
    obj.rejected_by = None
    obj.rejected_at = None
    obj.rejection_reason = None
    db.add(obj)
    db.commit()
    db.refresh(obj)
    record_audit(db, u, "rework_expense_claim", "ExpenseClaim", obj.id)
    db.commit()
    return obj


@router.post("/claims/{claim_id}/mark-paid", response_model=ExpenseClaimOut, operation_id="expensesMarkClaimPaid")
def mark_claim_paid(
    claim_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*ADMIN_ROLES)),
):
    """Record that finance paid an approved claim.

    Payment is not a claim status: it flips ``payment_status`` only, and
    only on an ``APPROVED`` claim that is still ``UNPAID``. Paying twice,
    or paying something that was never approved, is refused.
    """
    obj = _load_claim(db, claim_id)
    if obj.status != "APPROVED":
        raise conflict(
            "expense_invalid_payment_state",
            f"Only an approved claim can be marked paid; claim {claim_id} is {obj.status}.",
            id=claim_id,
            status=obj.status,
            payment_status=obj.payment_status,
        )
    if obj.payment_status != "UNPAID":
        raise conflict(
            "expense_invalid_payment_state",
            f"Claim {claim_id} is already {obj.payment_status}.",
            id=claim_id,
            status=obj.status,
            payment_status=obj.payment_status,
        )
    obj.payment_status = "PAID"
    obj.paid_by = u.id
    obj.paid_at = _utcnow()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    record_audit(db, u, "mark_expense_claim_paid", "ExpenseClaim", obj.id, details=f"amount={obj.amount}")
    db.commit()
    return obj


# --- Receipts --------------------------------------------------------------- #


def _opaque_receipt_key(claim_id: int, file_name: str) -> str:
    """Build the storage key for a receipt upload.

    The key carries a random component, so it is opaque: knowing one
    receipt's key reveals nothing about any other, and there is no
    employee name, amount or sequential id to walk. The extension is kept
    (sanitised) so the authenticated download serves the right type.
    """
    _, ext = os.path.splitext(file_name or "")
    ext = ext.lower()
    if not ext or len(ext) > 11 or not ext[1:].isalnum():
        ext = ""
    return f"expenses/{claim_id}/{uuid.uuid4().hex}{ext}"


@router.post("/claims/{claim_id}/receipts", response_model=ExpenseReceiptOut, status_code=201, operation_id="expensesUploadReceipt")
async def upload_receipt(
    claim_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    """Attach a receipt to a claim that is still being put together.

    Once the claim has passed the first approval the papers are frozen:
    attaching to ``L1_APPROVED`` or later is refused, so the approvers'
    paper trail cannot change under them.
    """
    obj = _load_claim(db, claim_id)
    _ensure_owner(db, u, obj.employee_id)
    if obj.status not in ("DRAFT", "SUBMITTED"):
        raise conflict(
            "expense_claim_locked",
            f"Receipts can only be attached while a claim is a draft or submitted; claim {claim_id} is {obj.status}.",
            id=claim_id,
            status=obj.status,
        )
    data = await file.read()
    if len(data) > RECEIPT_MAX_BYTES:
        raise ApiError(
            "file_too_large",
            f"Receipts are at most {RECEIPT_MAX_BYTES // (1024 * 1024)} MB.",
            ErrorCategory.VALIDATION,
            status_code=413,
        )
    if not data:
        raise validation("validation_error", "The receipt file is empty.", entity="ExpenseReceipt")
    key = _opaque_receipt_key(claim_id, file.filename or "")
    get_storage().save(key, data, content_type=file.content_type or "application/octet-stream")
    receipt = ExpenseReceipt(
        claim_id=claim_id,
        storage_key=key,
        file_name=file.filename or key,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        uploaded_by=u.id,
    )
    tenant_id = tenant_id_for(db)
    if tenant_id is not None and not getattr(receipt, "tenant_id", None):
        receipt.tenant_id = tenant_id
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    record_audit(db, u, "upload_expense_receipt", "ExpenseReceipt", receipt.id, details=f"claim={claim_id}")
    db.commit()
    return _receipt_out(receipt)


@router.get("/claims/{claim_id}/receipts", response_model=list[ExpenseReceiptOut], operation_id="expensesListReceipts")
def list_receipts(
    claim_id: int,
    db: Session = Depends(get_db),
    u: User = Depends(require_roles(*WORKFORCE_ROLES)),
):
    """A claim's receipts. The rows (and their download URLs) are
    visibility-scoped; the bytes themselves download only through the
    authenticated ``GET /api/v1/files/{key}`` route."""
    obj = _load_claim(db, claim_id)
    ensure_can_view_employee(db, u, obj.employee_id)
    rows = (
        db.query(ExpenseReceipt)
        .filter(ExpenseReceipt.claim_id == claim_id)
        .order_by(ExpenseReceipt.id)
        .all()
    )
    return [_receipt_out(row) for row in rows]
