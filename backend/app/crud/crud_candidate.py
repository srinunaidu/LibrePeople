from sqlalchemy.orm import Session
from app.models.recruiting import Candidate
from app.schemas.recruiting import CandidateCreate, CandidateUpdate


def get_candidate(db: Session, candidate_id: int) -> Candidate | None:
    return db.query(Candidate).filter(Candidate.id == candidate_id).first()


def get_candidate_by_email(db: Session, email: str) -> Candidate | None:
    return db.query(Candidate).filter(Candidate.email == email).first()


def get_candidates(
    db: Session, skip: int = 0, limit: int = 100, status: str | None = None
) -> list[Candidate]:
    query = db.query(Candidate)
    if status:
        query = query.filter(Candidate.status == status)
    return query.offset(skip).limit(limit).all()


def create_candidate(db: Session, candidate_in: CandidateCreate) -> Candidate:
    db_obj = Candidate(**candidate_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_candidate(
    db: Session, db_obj: Candidate, candidate_in: CandidateUpdate
) -> Candidate:
    update_data = candidate_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
