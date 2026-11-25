from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import ADMIN_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.models.user import User
from app.schemas.recruiting import (
    RequisitionCreate,
    RequisitionUpdate,
    RequisitionOut,
)
from app.crud.crud_requisition import (
    get_requisition,
    get_requisition_by_number,
    get_requisitions,
    create_requisition,
    update_requisition,
)

router = APIRouter()


@router.get("/", response_model=list[RequisitionOut], operation_id="recruitingListRequisitions")
def read_requisitions(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    return get_requisitions(db, skip=skip, limit=limit, status=status)


@router.post("/", response_model=RequisitionOut, status_code=201, operation_id="recruitingCreateRequisitions")
def create_requisition_endpoint(
    requisition_in: RequisitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if get_requisition_by_number(db, requisition_in.req_number):
        raise HTTPException(status_code=400, detail="Requisition number already exists")
    obj = create_requisition(db=db, requisition_in=requisition_in)
    record_audit(
        db, current_user, "create_requisition", "JobRequisition", obj.id,
        details=str(getattr(obj, 'status', '')) or None,
    )
    db.commit()
    return obj


@router.get("/{requisition_id}", response_model=RequisitionOut, operation_id="recruitingGetRequisitions")
def read_requisition(
    requisition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    requisition = get_requisition(db, requisition_id)
    if not requisition:
        raise HTTPException(status_code=404, detail="Requisition not found")
    return requisition


@router.put("/{requisition_id}", response_model=RequisitionOut, operation_id="recruitingUpdateRequisitions")
def update_requisition_endpoint(
    requisition_id: int,
    requisition_in: RequisitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    requisition = get_requisition(db, requisition_id)
    if not requisition:
        raise HTTPException(status_code=404, detail="Requisition not found")
    obj = update_requisition(db=db, db_obj=requisition, requisition_in=requisition_in)
    record_audit(
        db, current_user, "update_requisition", "JobRequisition", obj.id,
        details=f"status={obj.status}",
    )
    db.commit()
    return obj
