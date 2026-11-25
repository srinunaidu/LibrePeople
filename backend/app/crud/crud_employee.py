from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.query(Employee).filter(Employee.id == employee_id).first()


def get_employee_by_code(db: Session, employee_code: str) -> Employee | None:
    return db.query(Employee).filter(Employee.employee_id == employee_code).first()


def get_employees(db: Session, skip: int = 0, limit: int = 100) -> list[Employee]:
    return db.query(Employee).offset(skip).limit(limit).all()


def create_employee(db: Session, employee_in: EmployeeCreate) -> Employee:
    # LP-CORE-005: configurable attributes ride the schema but are not
    # columns. The endpoint stores them via the custom-fields service.
    db_obj = Employee(**employee_in.model_dump(exclude={"custom_fields"}))
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def stage_employee(db: Session, employee_in: EmployeeCreate) -> Employee:
    """Add an employee to the session without committing it.

    A caller that needs the employee and something else to land together —
    the offer-to-hire flow creates an employee, a checklist, two status
    changes and an audit row, and they must all succeed or all fail — uses
    this and commits once at the end.

    The row is flushed so that the database assigns its identity and the
    unique constraints are checked before the caller goes on to build the
    rest of the operation. The transaction is still open.
    """
    db_obj = Employee(**employee_in.model_dump(exclude={"custom_fields"}))
    db.add(db_obj)
    db.flush()
    return db_obj


def update_employee(db: Session, db_obj: Employee, employee_in: EmployeeUpdate) -> Employee:
    update_data = employee_in.model_dump(exclude_unset=True, exclude={"custom_fields"})
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
