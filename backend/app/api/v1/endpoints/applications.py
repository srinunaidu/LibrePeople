from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import ADMIN_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.models.user import User
from app.schemas.recruiting import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationOut,
)
from app.crud.crud_application import (
    get_application,
    get_applications,
    create_application,
    update_application,
)
from app.crud.crud_requisition import get_requisition
from app.crud.crud_candidate import get_candidate

router = APIRouter()


@router.get("/", response_model=list[ApplicationOut], operation_id="recruitingListApplications")
def read_applications(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    requisition_id: int | None = None,
    candidate_id: int | None = None,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    return get_applications(
        db,
        skip=skip,
        limit=limit,
        requisition_id=requisition_id,
        candidate_id=candidate_id,
    )


@router.post("/", response_model=ApplicationOut, status_code=201, operation_id="recruitingCreateApplications")
def create_application_endpoint(
    application_in: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if not get_requisition(db, application_in.requisition_id):
        raise HTTPException(status_code=400, detail="Requisition not found")
    if not get_candidate(db, application_in.candidate_id):
        raise HTTPException(status_code=400, detail="Candidate not found")
    obj = create_application(db=db, application_in=application_in)
    record_audit(
        db, current_user, "create_application", "Application", obj.id,
        details=str(getattr(obj, 'status', '')) or None,
    )
    db.commit()
    return obj


@router.get("/{application_id}", response_model=ApplicationOut, operation_id="recruitingGetApplications")
def read_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    application = get_application(db, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.put("/{application_id}", response_model=ApplicationOut, operation_id="recruitingUpdateApplications")
def update_application_endpoint(
    application_id: int,
    application_in: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    application = get_application(db, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    obj = update_application(db=db, db_obj=application, application_in=application_in)
    record_audit(
        db, current_user, "update_application", "Application", obj.id,
        details=f"status={obj.status}",
    )
    db.commit()
    return obj
