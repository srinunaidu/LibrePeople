"""Job titles — the catalogue employees, positions and requisitions point at.

Two operations were missing and are added here: **edit** and **archive/delete**.
Until now a job could be created and read and never corrected: a mistyped code
was permanent, and a job nobody used any more stayed in every form that offers
it, because nothing could take it out.

The rules are the ones every master-data entity shares, applied through
`app.core.master_data`:

* the code is a unique natural key, refused as `409 duplicate_natural_key`;
* the department it names has to exist, refused as `422 reference_not_found`;
* a band whose minimum exceeds its maximum is a payload error, never a stored row;
* a job still pointed at cannot be deleted — it is archived (`is_active=false`)
  instead, and the refusal names what points at it and how many rows.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, ALL_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.errors import validation
from app.core.master_data import (
    count_dependents,
    ensure_reference,
    ensure_unique_natural_key,
    load_or_404,
    refuse_if_in_use,
    refuse_null_updates,
)
from app.core.ids import next_code
from app.crud.crud_job import create_job, get_job, get_jobs
from app.models.core_hr import Position
from app.models.department import Department
from app.models.employee import Employee
from app.models.job import Job
from app.models.performance import CompensationBand
from app.models.recruiting import JobRequisition, Offer
from app.models.user import User
from app.schemas.employee import JobCreate, JobOut, JobUpdate

router = APIRouter()


def _check_band(min_salary: Any, max_salary: Any) -> None:
    """A band whose floor is above its ceiling is a payload error."""
    if min_salary is None or max_salary is None:
        return
    if float(min_salary) > float(max_salary):
        raise validation(
            "validation_error",
            "min_salary may not be greater than max_salary.",
            entity="Job",
            fields=["min_salary", "max_salary"],
            min_salary=float(min_salary),
            max_salary=float(max_salary),
        )


#: What a job must not be deleted while it still has: employees in it,
#: positions built on it, compensation bands priced on it, and open recruiting demand.
_JOB_DEPENDENTS = (
    ("employees", Employee, Employee.job_id),
    ("positions", Position, Position.job_id),
    ("compensation_bands", CompensationBand, CompensationBand.job_id),
    ("requisitions", JobRequisition, JobRequisition.job_id),
    ("offers", Offer, Offer.job_id),
)


@router.get("/", response_model=list[JobOut], operation_id="recruitingListJobs")
def read_jobs(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    """Jobs, by code.

    `include_inactive` lets the maintenance list see an archived job so that
    it can restore it; the forms that offer a job want the live ones.
    """
    return get_jobs(db, skip=skip, limit=limit, include_inactive=include_inactive)


@router.post("/", response_model=JobOut, status_code=201, operation_id="recruitingCreateJobs")
def create_job_endpoint(
    job_in: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    ensure_reference(db, Department, job_in.department_id, "Department")
    job_code = (job_in.code or "").strip() or next_code(db, Job, Job.code, "JOB-")
    job_in = job_in.model_copy(update={"code": job_code})
    ensure_unique_natural_key(db, Job, Job.code, job_code, label="Job")
    _check_band(job_in.min_salary, job_in.max_salary)
    job = create_job(db=db, job_in=job_in, code=job_code)
    record_audit(
        db, current_user, "create_job", "Job", job.id, details=f"code={job.code}"
    )
    db.commit()
    return job


@router.get("/{job_id}", response_model=JobOut, operation_id="recruitingGetJobs")
def read_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ALL_ROLES)),
) -> Any:
    job = get_job(db=db, job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobOut, operation_id="recruitingUpdateJob")
def update_job(
    job_id: int,
    job_in: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Edit a job. Only the fields the client actually sends are changed."""
    job = load_or_404(db, Job, job_id, "Job")

    changes = job_in.model_dump(exclude_unset=True)
    refuse_null_updates(
        changes, ("title", "code", "department_id", "is_active"), "Job"
    )
    if "department_id" in changes:
        ensure_reference(db, Department, changes["department_id"], "Department")
    if "code" in changes:
        ensure_unique_natural_key(
            db, Job, Job.code, changes["code"], exclude_id=job_id, label="Job"
        )
    if "min_salary" in changes or "max_salary" in changes:
        _check_band(
            changes.get("min_salary", job.min_salary),
            changes.get("max_salary", job.max_salary),
        )

    for field, value in changes.items():
        setattr(job, field, value)
    db.add(job)
    record_audit(
        db,
        current_user,
        "update_job",
        "Job",
        job.id,
        details=",".join(sorted(changes)) or "no change",
    )
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204, operation_id="recruitingDeleteJob")
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> None:
    """Delete a job nothing points at; refuse one that something still does.

    An archived job stays in the catalogue and stops being offered by forms that
    select active jobs only. Deletion is the stronger operation and is allowed
    only when nothing refers to it.
    """
    job = load_or_404(db, Job, job_id, "Job")
    refuse_if_in_use(
        count_dependents(db, _JOB_DEPENDENTS, job_id), "Job", job_id
    )
    db.delete(job)
    record_audit(db, current_user, "delete_job", "Job", job_id, details="deleted")
    db.commit()
    return None
