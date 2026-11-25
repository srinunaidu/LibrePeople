"""Departments — one of the two structures every employee hangs off.

The department could be created and read and not corrected. `PATCH` and a
guarded `DELETE` are added here so that a mistyped code can be fixed and a
department that is no longer used can be taken out of the forms that offer it.

A department is the most referenced entity in the product — employees, jobs,
positions, cost centres, requisitions and compliance rules all point at it — so
deletion is refused while anything refers to it, and the refusal says what.
Archiving (`is_active=false`) is the operation that is always available.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.booleans import is_true
from app.api.deps import ADMIN_ROLES, ALL_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.ids import next_code
from app.core.master_data import (
    count_dependents,
    ensure_unique_natural_key,
    load_or_404,
    refuse_if_in_use,
    refuse_null_updates,
)
from app.crud.crud_department import (
    create_department,
    get_department,
    get_departments,
)
from app.models.compliance import HeadcountPlan
from app.models.core_hr import CostCenter, Position
from app.models.department import Department
from app.models.employee import Employee
from app.models.job import Job
from app.models.recruiting import JobRequisition
from app.models.user import User
from app.schemas.employee import DepartmentCreate, DepartmentOut, DepartmentUpdate

router = APIRouter()


_DEPARTMENT_DEPENDENTS = (
    ("employees", Employee, Employee.department_id),
    ("jobs", Job, Job.department_id),
    ("positions", Position, Position.department_id),
    ("cost_centers", CostCenter, CostCenter.department_id),
    ("requisitions", JobRequisition, JobRequisition.department_id),
    ("headcount_plans", HeadcountPlan, HeadcountPlan.department_id),
)


@router.get("/", response_model=list[DepartmentOut], operation_id="departmentsListDepartments")
def read_departments(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    """Departments, newest first.

    `include_inactive` exists because the forms that offer a department need
    the live ones, while the maintenance list has to be able to see an archived
    department in order to restore it.
    """
    query = db.query(Department)
    if not include_inactive:
        query = query.filter(is_true(Department.is_active))
    return query.order_by(Department.code).offset(skip).limit(limit).all()


@router.post("/", response_model=DepartmentOut, status_code=201, operation_id="departmentsCreateDepartments")
def create_department_endpoint(
    dept_in: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    # Auto-generate the code when the caller left it empty (Phase T/F1);
    # the uniqueness check then runs on the final value, so a generated
    # code that collides is refused the same way a typed one is.
    dept_code = (dept_in.code or "").strip() or next_code(
        db, Department, Department.code, "DEP-"
    )
    dept_in = dept_in.model_copy(update={"code": dept_code})
    ensure_unique_natural_key(
        db, Department, Department.code, dept_code, label="Department"
    )
    dept = create_department(db=db, dept_in=dept_in, code=dept_code)
    record_audit(
        db, current_user, "create_department", "Department", dept.id,
        details=f"code={dept.code}",
    )
    db.commit()
    return dept


@router.get("/{department_id}", response_model=DepartmentOut, operation_id="departmentsGetDepartments")
def read_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    dept = get_department(db=db, department_id=department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.patch("/{department_id}", response_model=DepartmentOut, operation_id="departmentsUpdateDepartment")
def update_department(
    department_id: int,
    dept_in: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Edit a department — including restoring an archived one."""
    dept = load_or_404(db, Department, department_id, "Department")

    changes = dept_in.model_dump(exclude_unset=True)
    refuse_null_updates(changes, ("name", "code", "is_active"), "Department")
    if "code" in changes:
        ensure_unique_natural_key(
            db,
            Department,
            Department.code,
            changes["code"],
            exclude_id=department_id,
            label="Department",
        )

    for field, value in changes.items():
        setattr(dept, field, value)
    db.add(dept)
    record_audit(
        db,
        current_user,
        "update_department",
        "Department",
        dept.id,
        details=",".join(sorted(changes)) or "no change",
    )
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{department_id}", status_code=204, operation_id="departmentsDeleteDepartment")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> None:
    """Delete a department nothing points at; refuse one that something does."""
    dept = load_or_404(db, Department, department_id, "Department")
    refuse_if_in_use(
        count_dependents(db, _DEPARTMENT_DEPENDENTS, department_id),
        "Department",
        department_id,
    )
    db.delete(dept)
    record_audit(
        db,
        current_user,
        "delete_department",
        "Department",
        department_id,
        details="deleted",
    )
    db.commit()
    return None
