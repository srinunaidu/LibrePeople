"""Shared fixtures for the workflow-engine slice tests.

Mirrors the standalone suite pattern: a scratch SQLite database, the
full metadata built via ``create_all``, and JWT header helpers including
per-tenant tokens. ``LOG_LEVEL=CRITICAL`` keeps the output readable.
"""
import datetime
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="workflow_tests_"), "workflow_tests.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=__import__("app.core.database", fromlist=["engine"]).engine)

PASSWORD = "WorkflowPass123"

TENANT_A = "tenant-wf-a"
TENANT_B = "tenant-wf-b"

db = SessionLocal()
dept = Department(name="Workflow Ops", code="WFO")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Workflow Analyst", code="WFAN", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str, manager_id: int | None = None) -> Employee:
    person = Employee(
        employee_id=code,
        first_name="Work",
        last_name=code,
        email=f"{code.lower()}@example.com",
        hire_date=datetime.date(2024, 1, 1),
        job_id=job.id,
        department_id=dept.id,
        manager_id=manager_id,
        status="Active",
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


emp_mgr = _employee("WF-MGR")
emp_a = _employee("WF-A", manager_id=emp_mgr.id)
emp_b = _employee("WF-B")


def _user(username: str, role: str, employee_id: int | None = None) -> None:
    db.add(
        User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            is_active=True,
            employee_id=employee_id,
            mfa_enabled=role in ("SuperAdmin", "HR"),
        )
    )
    db.commit()


_user("wf_admin", "SuperAdmin")
_user("wf_hr", "HR")
_user("wf_mgr", "Manager", emp_mgr.id)
_user("wf_mgr2", "Manager", emp_b.id)
_user("wf_assoc", "Associate", emp_a.id)
_user("wf_pay", "PayrollViewer")
db.close()

client = TestClient(app, raise_server_exceptions=False)


def _headers(username: str) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _tenant_headers(username: str, tenant: str) -> dict:
    token = create_access_token(subject=username, extra_claims={"tenant": tenant})
    return {"Authorization": f"Bearer {token}"}


H_ADMIN = _headers("wf_admin")
H_HR = _headers("wf_hr")
H_MGR = _headers("wf_mgr")
H_MGR2 = _headers("wf_mgr2")
H_ASSOC = _headers("wf_assoc")
H_PAY = _headers("wf_pay")
HA_ADMIN = _tenant_headers("wf_admin", TENANT_A)
HB_ADMIN = _tenant_headers("wf_admin", TENANT_B)
HA_MGR = _tenant_headers("wf_mgr", TENANT_A)


@pytest.fixture()
def client_fixture() -> TestClient:
    return client
