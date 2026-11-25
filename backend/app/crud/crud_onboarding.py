from sqlalchemy.orm import Session
from app.models.onboarding import OnboardingTask, OnboardingDocument
from app.schemas.onboarding import (
    OnboardingTaskCreate,
    OnboardingTaskUpdate,
    OnboardingDocumentUpdate,
)


def get_task(db: Session, task_id: int) -> OnboardingTask | None:
    return db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()


def get_tasks_for_employee(db: Session, employee_id: int) -> list[OnboardingTask]:
    return (
        db.query(OnboardingTask)
        .filter(OnboardingTask.employee_id == employee_id)
        .all()
    )


def create_task(db: Session, task_in: OnboardingTaskCreate) -> OnboardingTask:
    db_obj = OnboardingTask(**task_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_task(
    db: Session, db_obj: OnboardingTask, task_in: OnboardingTaskUpdate
) -> OnboardingTask:
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_document(db: Session, document_id: int) -> OnboardingDocument | None:
    return (
        db.query(OnboardingDocument)
        .filter(OnboardingDocument.id == document_id)
        .first()
    )


def get_documents_for_employee(
    db: Session, employee_id: int
) -> list[OnboardingDocument]:
    return (
        db.query(OnboardingDocument)
        .filter(OnboardingDocument.employee_id == employee_id)
        .all()
    )


def create_document(
    db: Session,
    employee_id: int,
    document_type: str,
    file_name: str,
    storage_url: str,
) -> OnboardingDocument:
    db_obj = OnboardingDocument(
        employee_id=employee_id,
        document_type=document_type,
        file_name=file_name,
        storage_url=storage_url,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_document(
    db: Session, db_obj: OnboardingDocument, document_in: OnboardingDocumentUpdate
) -> OnboardingDocument:
    update_data = document_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


# Default checklist applied to every new hire.
DEFAULT_ONBOARDING_TASKS: list[dict] = [
    {"title": "Collect signed offer letter", "category": "Documents"},
    {"title": "Collect ID proof", "category": "Documents"},
    {"title": "Collect tax / bank details", "category": "Documents"},
    {"title": "Issue laptop and email account", "category": "IT"},
    {"title": "Assign desk / access badge", "category": "Facilities"},
    {"title": "Complete induction and compliance training", "category": "Training"},
]


def apply_default_checklist(
    db: Session, employee_id: int, commit: bool = True
) -> list[OnboardingTask]:
    """Create the standard onboarding checklist for a new employee.

    ``commit=False`` stages the tasks without committing them, so that the
    checklist and the employee it belongs to land in the same transaction.
    A checklist without its employee, or an employee without its checklist,
    is a partial hire.
    """
    created = []
    for item in DEFAULT_ONBOARDING_TASKS:
        task = OnboardingTask(
            employee_id=employee_id,
            title=item["title"],
            category=item["category"],
            status="Pending",
        )
        db.add(task)
        created.append(task)
    if commit:
        db.commit()
        for task in created:
            db.refresh(task)
    else:
        db.flush()
    return created
