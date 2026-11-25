from sqlalchemy.orm import Session
from app.models.recruiting import Application
from app.schemas.recruiting import ApplicationCreate, ApplicationUpdate


def get_application(db: Session, application_id: int) -> Application | None:
    return db.query(Application).filter(Application.id == application_id).first()


def get_applications(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    requisition_id: int | None = None,
    candidate_id: int | None = None,
) -> list[Application]:
    query = db.query(Application)
    if requisition_id is not None:
        query = query.filter(Application.requisition_id == requisition_id)
    if candidate_id is not None:
        query = query.filter(Application.candidate_id == candidate_id)
    return query.offset(skip).limit(limit).all()


def create_application(db: Session, application_in: ApplicationCreate) -> Application:
    db_obj = Application(**application_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_application(
    db: Session, db_obj: Application, application_in: ApplicationUpdate
) -> Application:
    update_data = application_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
