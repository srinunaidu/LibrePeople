from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import ADMIN_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.models.user import User
from app.schemas.recruiting import CandidateCreate, CandidateUpdate, CandidateOut
from app.crud.crud_candidate import (
    get_candidate,
    get_candidate_by_email,
    get_candidates,
    create_candidate,
    update_candidate,
)

router = APIRouter()


@router.get("/", response_model=list[CandidateOut], operation_id="recruitingListCandidates")
def read_candidates(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    return get_candidates(db, skip=skip, limit=limit, status=status)


@router.post("/", response_model=CandidateOut, status_code=201, operation_id="recruitingCreateCandidates")
def create_candidate_endpoint(
    candidate_in: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if get_candidate_by_email(db, candidate_in.email):
        raise HTTPException(status_code=400, detail="Candidate email already exists")
    obj = create_candidate(db=db, candidate_in=candidate_in)
    record_audit(
        db, current_user, "create_candidate", "Candidate", obj.id,
        details=str(getattr(obj, 'status', '')) or None,
    )
    db.commit()
    return obj


@router.get("/{candidate_id}", response_model=CandidateOut, operation_id="recruitingGetCandidates")
def read_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    candidate = get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.put("/{candidate_id}", response_model=CandidateOut, operation_id="recruitingUpdateCandidates")
def update_candidate_endpoint(
    candidate_id: int,
    candidate_in: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    candidate = get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    obj = update_candidate(db=db, db_obj=candidate, candidate_in=candidate_in)
    record_audit(
        db, current_user, "update_candidate", "Candidate", obj.id,
        details=f"status={obj.status}",
    )
    db.commit()
    return obj
