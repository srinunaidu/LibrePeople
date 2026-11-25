from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, get_db, require_roles
from app.core.audit import record_audit
from app.core.idempotency import IdempotencyGuard, idempotency_key
from app.models.user import User
from app.models.department import Department
from app.models.employee import Employee
from app.models.onboarding import OnboardingTask
from app.models.recruiting import Application, Candidate
from app.schemas.recruiting import (
    OfferCreate,
    OfferUpdate,
    OfferOut,
    HireRequest,
    HireResult,
)
from app.schemas.employee import EmployeeOut
from app.crud.crud_offer import (
    get_offer,
    get_offer_by_number,
    get_offers,
    create_offer,
    update_offer,
)
from app.crud.crud_application import get_application
from app.crud.crud_candidate import get_candidate
from app.crud.crud_requisition import get_requisition
from app.crud.crud_employee import (
    get_employee_by_code,
    create_employee,
    stage_employee,
)
from app.crud.crud_onboarding import apply_default_checklist
from app.schemas.employee import EmployeeCreate
from app.services.storage import get_storage
from app.services.offer_letter import render_offer_letter

router = APIRouter()


@router.get("/", response_model=list[OfferOut], operation_id="recruitingListOffers")
def read_offers(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    return get_offers(db, skip=skip, limit=limit, status=status)


@router.post("/", response_model=OfferOut, status_code=201, operation_id="recruitingCreateOffers")
def create_offer_endpoint(
    offer_in: OfferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    if get_offer_by_number(db, offer_in.offer_number):
        raise HTTPException(status_code=400, detail="Offer number already exists")
    if not get_application(db, offer_in.application_id):
        raise HTTPException(status_code=400, detail="Application not found")
    return create_offer(db=db, offer_in=offer_in)


@router.get("/{offer_id}", response_model=OfferOut, operation_id="recruitingGetOffers")
def read_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    offer = get_offer(db, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer


@router.put("/{offer_id}", response_model=OfferOut, operation_id="recruitingUpdateOffers")
def update_offer_endpoint(
    offer_id: int,
    offer_in: OfferUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    offer = get_offer(db, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return update_offer(db=db, db_obj=offer, offer_in=offer_in)


@router.post("/{offer_id}/letter", response_model=OfferOut, operation_id="recruitingCreateOffersletter")
def generate_offer_letter(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Generate the offer letter PDF, store it, and mark the offer as Sent."""
    offer = get_offer(db, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    application = get_application(db, offer.application_id)
    if not application:
        raise HTTPException(status_code=400, detail="Application not found")
    candidate = get_candidate(db, application.candidate_id)
    requisition = get_requisition(db, application.requisition_id)

    department_name = "General"
    if requisition:
        department = (
            db.query(Department).filter(Department.id == requisition.department_id).first()
        )
        if department:
            department_name = department.name

    candidate_name = (
        f"{candidate.first_name} {candidate.last_name}" if candidate else "Candidate"
    )
    job_title = requisition.title if requisition else "Team Member"

    pdf_bytes = render_offer_letter(
        candidate_name=candidate_name,
        job_title=job_title,
        department_name=department_name,
        salary=float(offer.salary_offered) if offer.salary_offered is not None else None,
        start_date=offer.start_date,
        offer_date=offer.offer_date,
        offer_number=offer.offer_number,
    )

    storage = get_storage()
    key = f"offers/{offer.offer_number}.pdf"
    url = storage.save(key, pdf_bytes, content_type="application/pdf")

    offer.letter_url = url
    offer.status = "Sent"
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/{offer_id}/accept", response_model=OfferOut, operation_id="recruitingCreateOffersaccept")
def accept_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
) -> Any:
    """Mark an offer (and its application/candidate) as Accepted."""
    offer = get_offer(db, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    offer.status = "Accepted"
    db.add(offer)

    application = get_application(db, offer.application_id)
    if application:
        application.status = "Offer"
        db.add(application)
        candidate = get_candidate(db, application.candidate_id)
        if candidate:
            candidate.status = "Offer"
            db.add(candidate)

    db.commit()
    db.refresh(offer)
    record_audit(db, current_user, "accept_offer", "Offer", offer.id)
    db.commit()
    return offer


@router.post("/{offer_id}/hire", response_model=HireResult, status_code=201, operation_id="recruitingCreateOffershire")
def hire_from_offer(
    offer_id: int,
    hire_in: HireRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    idem_key: str | None = Depends(idempotency_key),
) -> Any:
    """Convert an accepted offer into an employee + onboarding checklist.

    **One transaction.** The employee, the checklist, the candidate's and
    the application's status, and the audit row are written together and
    committed once. The previous implementation committed the employee
    first, so a failure in the checklist or the status change left a
    half-made hire behind: an employee the recruiter had to delete by
    hand, a candidate still marked as a candidate, and an onboarding
    checklist that belonged to nobody.

    **One idempotency key.** A retry with the same key replays the
    original result instead of creating a second employee.
    """
    with IdempotencyGuard(
        db,
        idem_key,
        f"offers.hire:{offer_id}",
        {"offer_id": offer_id, **hire_in.model_dump(mode="json")},
    ) as guard:
        offer = get_offer(db, offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Offer not found")
        if offer.status not in ("Accepted", "Sent"):
            raise HTTPException(
                status_code=400, detail="Offer must be Accepted (or Sent) before hiring"
            )

        if guard.replayed:
            # The original call already made this hire. Replaying the
            # stored result is better than making a second employee.
            existing = get_employee_by_code(db, hire_in.employee_id)
            if existing is not None:
                tasks = db.query(OnboardingTask).filter(
                    OnboardingTask.employee_id == existing.id
                ).count()
                return HireResult(
                    employee=EmployeeOut.model_validate(existing),
                    onboarding_tasks_created=tasks,
                )

        application = get_application(db, offer.application_id)
        if not application:
            raise HTTPException(status_code=400, detail="Application not found")
        candidate = get_candidate(db, application.candidate_id)
        if not candidate:
            raise HTTPException(status_code=400, detail="Candidate not found")
        requisition = get_requisition(db, application.requisition_id)

        department_id = (
            hire_in.department_id
            or (requisition.department_id if requisition else None)
        )
        job_id = hire_in.job_id or offer.job_id or (requisition.job_id if requisition else None)
        hire_date = hire_in.hire_date or offer.start_date
        email = hire_in.email or candidate.email
        salary = hire_in.salary
        if salary is None and offer.salary_offered is not None:
            salary = float(offer.salary_offered)

        if department_id is None:
            raise HTTPException(status_code=400, detail="department_id is required")
        if job_id is None:
            raise HTTPException(status_code=400, detail="job_id is required")

        if get_employee_by_code(db, hire_in.employee_id):
            raise HTTPException(status_code=400, detail="Employee ID already exists")

        try:
            employee = stage_employee(
                db=db,
                employee_in=EmployeeCreate(
                    employee_id=hire_in.employee_id,
                    first_name=candidate.first_name,
                    last_name=candidate.last_name,
                    email=email,
                    phone=candidate.phone,
                    hire_date=hire_date,
                    job_id=job_id,
                    department_id=department_id,
                    status="Active",
                    salary=salary,
                ),
            )

            tasks = apply_default_checklist(db, employee.id, commit=False)

            candidate.status = "Hired"
            application.status = "Hired"
            db.add(candidate)
            db.add(application)

            # The offer's own status is left alone. Its vocabulary is
            # Draft, Sent, Accepted, Declined, Expired, and adding a
            # value to it is a change to the recruiting module's state
            # machine, not this lane's. The hire is recorded on the
            # candidate and the application, where it already was.

            # The single most consequential recruiting event: one entry
            # records who converted which offer, and that it produced an
            # employee plus an onboarding checklist. It is written in the
            # same transaction as the rows it describes, so it cannot
            # claim a hire that did not happen.
            record_audit(
                db,
                current_user,
                "hire_from_offer",
                "Offer",
                offer.id,
                details=(
                    f"employee_id={employee.employee_id} "
                    f"candidate_id={candidate.id} "
                    f"onboarding_tasks={len(tasks)}"
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(employee)
        guard.store({"employee_id": employee.employee_id})
        return HireResult(
            employee=EmployeeOut.model_validate(employee),
            onboarding_tasks_created=len(tasks),
        )
