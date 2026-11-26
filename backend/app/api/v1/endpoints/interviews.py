"""Interview scheduling reads and writes (recruiting lane).

Interviews are the schedule behind a candidate's pipeline: who meets whom,
when, at which stage, and what came of it. The role gate follows the rest
of the recruiting lane (admin-only): an interview names candidates and
hiring plans, which are not visible outside hiring administration.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.crud import crud_interview as crud
from app.crud.crud_candidate import get_candidate
from app.crud.crud_requisition import get_requisition
from app.models.user import User
from app.schemas.recruiting import (
    InterviewCreate,
    InterviewOut,
    InterviewUpdate,
)

router = APIRouter()


def _out(interview) -> dict:
    return crud.serialise(interview)


@router.get("/", response_model=list[InterviewOut], operation_id="recruitingListInterviews")
def read_interviews(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    candidate_id: int | None = None,
    requisition_id: int | None = None,
    status: str | None = None,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    return [
        _out(row)
        for row in crud.get_interviews(
            db,
            skip=skip,
            limit=limit,
            candidate_id=candidate_id,
            requisition_id=requisition_id,
            status=status,
        )
    ]


@router.post("/", response_model=InterviewOut, status_code=201, operation_id="recruitingCreateInterviews")
def create_interview_endpoint(
    interview_in: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if not get_candidate(db, interview_in.candidate_id):
        raise HTTPException(status_code=404, detail="Candidate not found")
    if interview_in.requisition_id is not None and not get_requisition(
        db, interview_in.requisition_id
    ):
        raise HTTPException(status_code=404, detail="Requisition not found")
    obj = crud.create_interview(db=db, interview_in=interview_in)
    record_audit(
        db, current_user, "create_interview", "Interview", obj.id,
        details=f"candidate={obj.candidate_id} stage={obj.stage}",
    )
    db.commit()
    return _out(obj)


@router.get("/{interview_id}", response_model=InterviewOut, operation_id="recruitingGetInterviews")
def read_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    interview = crud.get_interview(db, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return _out(interview)


@router.put("/{interview_id}", response_model=InterviewOut, operation_id="recruitingUpdateInterviews")
def update_interview_endpoint(
    interview_id: int,
    interview_in: InterviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    interview = crud.get_interview(db, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    try:
        obj = crud.update_interview(db=db, db_obj=interview, interview_in=interview_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record_audit(
        db, current_user, "update_interview", "Interview", obj.id,
        details=f"status={obj.status}",
    )
    db.commit()
    return _out(obj)
