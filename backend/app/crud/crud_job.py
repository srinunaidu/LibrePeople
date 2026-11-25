from sqlalchemy.orm import Session
from app.core.booleans import is_true
from app.models.job import Job
from app.schemas.employee import JobCreate


def get_job(db: Session, job_id: int) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()


def get_jobs(db: Session, skip: int = 0, limit: int = 100, include_inactive: bool = False) -> list[Job]:
    query = db.query(Job)
    if not include_inactive:
        query = query.filter(is_true(Job.is_active))
    return query.offset(skip).limit(limit).all()


def create_job(db: Session, job_in: JobCreate, code: str) -> Job:
    """Create a job row; `code` is the endpoint-resolved natural key."""
    data = job_in.model_dump(exclude={"code"})
    data["code"] = code
    db_obj = Job(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
