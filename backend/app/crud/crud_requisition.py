from sqlalchemy.orm import Session
from app.models.recruiting import JobRequisition
from app.schemas.recruiting import RequisitionCreate, RequisitionUpdate


def get_requisition(db: Session, requisition_id: int) -> JobRequisition | None:
    return db.query(JobRequisition).filter(JobRequisition.id == requisition_id).first()


def get_requisition_by_number(db: Session, req_number: str) -> JobRequisition | None:
    return (
        db.query(JobRequisition)
        .filter(JobRequisition.req_number == req_number)
        .first()
    )


def get_requisitions(
    db: Session, skip: int = 0, limit: int = 100, status: str | None = None
) -> list[JobRequisition]:
    query = db.query(JobRequisition)
    if status:
        query = query.filter(JobRequisition.status == status)
    return query.offset(skip).limit(limit).all()


def create_requisition(db: Session, requisition_in: RequisitionCreate) -> JobRequisition:
    db_obj = JobRequisition(**requisition_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_requisition(
    db: Session, db_obj: JobRequisition, requisition_in: RequisitionUpdate
) -> JobRequisition:
    update_data = requisition_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
