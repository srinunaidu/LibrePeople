"""Persistence for interviews: the schedule behind a candidate's pipeline.

``interviewers`` arrives as a list and is stored as a JSON array in a
plain ``Text`` column; the read converts it back, tolerating the NULLs
that older rows (or a hand-written row) carry.
"""
import json

from sqlalchemy.orm import Session

from app.models.recruiting import Interview
from app.schemas.recruiting import (
    INTERVIEW_STATUSES,
    INTERVIEW_TERMINAL_STATUSES,
    InterviewCreate,
    InterviewUpdate,
)


def _dump_interviewers(interviewers: list[str] | None) -> str | None:
    if interviewers is None:
        return None
    return json.dumps(list(interviewers))


def _load_interviewers(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def serialise(interview: Interview) -> dict:
    """The row as the API serves it: ``interviewers`` as a list."""
    return {
        "id": interview.id,
        "candidate_id": interview.candidate_id,
        "requisition_id": interview.requisition_id,
        "stage": interview.stage,
        "scheduled_at": interview.scheduled_at,
        "interviewers": _load_interviewers(interview.interviewers),
        "status": interview.status,
        "feedback": interview.feedback,
        "created_at": interview.created_at,
    }


def get_interview(db: Session, interview_id: int) -> Interview | None:
    return db.query(Interview).filter(Interview.id == interview_id).first()


def get_interviews(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    candidate_id: int | None = None,
    requisition_id: int | None = None,
    status: str | None = None,
) -> list[Interview]:
    query = db.query(Interview)
    if candidate_id is not None:
        query = query.filter(Interview.candidate_id == candidate_id)
    if requisition_id is not None:
        query = query.filter(Interview.requisition_id == requisition_id)
    if status:
        query = query.filter(Interview.status == status)
    return query.order_by(Interview.id.desc()).offset(skip).limit(limit).all()


def create_interview(db: Session, interview_in: InterviewCreate) -> Interview:
    data = interview_in.model_dump()
    interviewers = data.pop("interviewers", None)
    db_obj = Interview(**data, interviewers=_dump_interviewers(interviewers))
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_interview(
    db: Session, db_obj: Interview, interview_in: InterviewUpdate
) -> Interview:
    update_data = interview_in.model_dump(exclude_unset=True)
    new_status = update_data.get("status")
    if new_status is not None and new_status not in INTERVIEW_STATUSES:
        raise ValueError(f"unknown interview status: {new_status!r}")
    if (
        new_status is not None
        and new_status != db_obj.status
        and db_obj.status in INTERVIEW_TERMINAL_STATUSES
    ):
        raise ValueError(
            f"a {db_obj.status} interview is decided: only its feedback may change"
        )
    if "interviewers" in update_data:
        update_data["interviewers"] = _dump_interviewers(update_data["interviewers"])
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
