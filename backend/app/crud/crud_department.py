from sqlalchemy.orm import Session
from app.models.department import Department
from app.schemas.employee import DepartmentCreate

def get_department(db: Session, department_id: int) -> Department | None:
    return db.query(Department).filter(Department.id == department_id).first()


def get_departments(db: Session, skip: int = 0, limit: int = 100) -> list[Department]:
    return db.query(Department).offset(skip).limit(limit).all()


def create_department(db: Session, dept_in: DepartmentCreate, code: str) -> Department:
    """Create a department row from a validated `DepartmentCreate`.

    `code` is the effective natural key — the endpoint resolves it (explicit
    value or auto-generated `DEP-####` via `app.core.ids.next_code`) before
    calling, so the row never receives an empty code.
    """
    data = dept_in.model_dump(exclude={"code"})
    data["code"] = code
    db_obj = Department(**data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
