"""Expenses: categories, claims, receipts (LP-EXP-001+002).

What this suite proves
----------------------
* **Categories** — create (explicit and auto-generated `EXP-` code), read,
  patch, duplicate code refused (`409 duplicate_natural_key`), explicit
  null refused (`422`), Associate forbidden (`403`), and every write
  audited;
* **Claim lifecycle** — a draft is filed, submitted, L1-approved by the
  reporting line, finally approved by finance, and marked paid; each step
  records who and when, and the money is `Numeric(12, 2)`;
* **State machine** — approving a draft, submitting twice, paying before
  approval, paying twice, and editing after submit are all refused with
  the shared `invalid_state_transition` / locked codes; rejection carries
  a reason and rework returns the claim to draft;
* **Role guards** — an Associate files only their own claim, a PayrollViewer
  files nothing, a manager decides nothing outside their line, and only
  finance (Admin) gives final approval and marks paid;
* **Receipts** — uploads land under opaque keys, list with an authenticated
  download URL, attach only while the claim is a draft or submitted, and
  the bytes download only with a token (401 without one);
* **Tenant scope** — a caller sees only their own tenant's categories and
  claims; another tenant's rows read as 404, and creation stamps the
  request's tenant;
* **Migration 0037** — a fresh database reaches head with the three tables,
  `amount` as `Numeric(12, 2)` and the declared indexes; the downgrade
  removes exactly what the upgrade created.

Run:  python expenses_test_suite.py
"""
import datetime
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="expenses_test_suite_"), "expenses_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable
# Field encryption (item 6: no SECRET_KEY fallback) — expense claims touch
# employee identity fields through app.core.encryption.
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


# --- the fixtures ------------------------------------------------------------

PASSWORD = "ExpensePass123"

db = SessionLocal()
dept = Department(name="Field Ops", code="FLD")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Field Executive", code="FLDEX", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str, manager_id: int | None = None) -> Employee:
    person = Employee(
        employee_id=code,
        first_name="Exp",
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


emp_mgr = _employee("EXP-MGR")
emp_a = _employee("EXP-A", manager_id=emp_mgr.id)
emp_b = _employee("EXP-B")


def _user(username: str, role: str, employee_id: int | None = None) -> None:
    db.add(
        User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            is_active=True,
            employee_id=employee_id,
            # MFA-enforced world: privileged roles are enrolled, otherwise
            # every call below is refused before the handler runs.
            mfa_enabled=role in ("SuperAdmin", "HR"),
        )
    )
    db.commit()


_user("exp_admin", "SuperAdmin")
_user("exp_mgr", "Manager", emp_mgr.id)
_user("exp_mgr2", "Manager", emp_b.id)
_user("exp_assoc", "Associate", emp_a.id)
_user("exp_pay", "PayrollViewer")

EMP_MGR_ID = emp_mgr.id
EMP_A_ID = emp_a.id
EMP_B_ID = emp_b.id
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


H_ADMIN = _headers("exp_admin")
H_MGR = _headers("exp_mgr")
H_MGR2 = _headers("exp_mgr2")
H_ASSOC = _headers("exp_assoc")
H_PAY = _headers("exp_pay")
TENANT_A = "tenant-exp-a"
TENANT_B = "tenant-exp-b"
HA = _tenant_headers("exp_admin", TENANT_A)
HB = _tenant_headers("exp_admin", TENANT_B)

# ===========================================================================
print("\n[CATEGORY-1] The category master")
# ===========================================================================

r = client.post(
    "/api/v1/expenses/categories",
    headers=H_ADMIN,
    json={"code": "EXP-TRV", "name": "Travel", "description": "Outstation travel"},
)
check("finance creates a category with its code", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
check("the category reads back by code", r.json().get("code") == "EXP-TRV", str(r.json())[:200])
CAT_ID = r.json().get("id")

r = client.post(
    "/api/v1/expenses/categories", headers=H_ADMIN, json={"name": "Auto Code"}
)
check(
    "an omitted code is auto-generated in the EXP- household",
    r.status_code == 201 and str(r.json().get("code", "")).startswith("EXP-"),
    f"got {r.status_code}: {r.text[:200]}",
)
AUTO_CAT_ID = r.json().get("id") if r.status_code == 201 else None

r = client.post(
    "/api/v1/expenses/categories",
    headers=H_ADMIN,
    json={"code": "exp-trv", "name": "Travel Duplicate"},
)
check("a duplicate code is refused case-insensitively", r.status_code == 409, f"got {r.status_code}: {r.text[:200]}")
check(
    "the refusal names the duplicate key",
    r.json().get("error", {}).get("code") == "duplicate_natural_key",
    f"got {r.text[:200]}",
)

r = client.get("/api/v1/expenses/categories", headers=H_ADMIN)
check(
    "the list carries both categories",
    r.status_code == 200 and {CAT_ID, AUTO_CAT_ID} <= {row["id"] for row in r.json()},
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.get(f"/api/v1/expenses/categories/{CAT_ID}", headers=H_ADMIN)
check("read returns the category", r.status_code == 200 and r.json()["name"] == "Travel", f"got {r.status_code}")

r = client.get("/api/v1/expenses/categories/999999", headers=H_ADMIN)
check("an unknown category reads as 404", r.status_code == 404, f"got {r.status_code}")

r = client.patch(
    f"/api/v1/expenses/categories/{CAT_ID}", headers=H_ADMIN, json={"name": "Travel & Stay"}
)
check("patch renames the category", r.status_code == 200 and r.json()["name"] == "Travel & Stay", f"got {r.status_code}: {r.text[:200]}")

r = client.patch(
    f"/api/v1/expenses/categories/{CAT_ID}", headers=H_ADMIN, json={"name": None}
)
check("an explicit null for the name is refused", r.status_code == 422, f"got {r.status_code}")

for method, url, payload in [
    ("post", "/api/v1/expenses/categories", {"code": "EXP-X", "name": "Nope"}),
    ("patch", f"/api/v1/expenses/categories/{CAT_ID}", {"name": "Nope"}),
]:
    r = client.request(method, url, headers=H_ASSOC, json=payload)
    check(f"an Associate cannot write categories ({method})", r.status_code == 403, f"got {r.status_code}")

# ===========================================================================
print("\n[CLAIM-1] The full lifecycle: draft to paid")
# ===========================================================================

r = client.post(
    "/api/v1/expenses/claims",
    headers=H_ASSOC,
    json={
        "employee_id": EMP_A_ID,
        "category_id": CAT_ID,
        "expense_date": "2026-10-02",
        "amount": 1250.50,
        "currency": "INR",
        "description": "Client visit auto fare",
    },
)
check("an associate files a claim for their own expense", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
check("the claim starts as an unpaid draft", r.json().get("status") == "DRAFT" and r.json().get("payment_status") == "UNPAID", str(r.json())[:200])
check("the amount survives at two decimals", r.json().get("amount") == 1250.50, str(r.json())[:200])
CLAIM_ID = r.json().get("id")

r = client.post(
    "/api/v1/expenses/claims",
    headers=H_ASSOC,
    json={"employee_id": EMP_A_ID, "category_id": CAT_ID, "expense_date": "2026-10-02", "amount": 0},
)
check("a zero amount is refused by the schema", r.status_code == 422, f"got {r.status_code}")

r = client.post(f"/api/v1/expenses/claims/{CLAIM_ID}/approve", headers=H_ADMIN)
check(
    "approving a draft is refused as a bad transition",
    r.status_code == 422 and r.json().get("error", {}).get("code") == "invalid_state_transition",
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.patch(
    f"/api/v1/expenses/claims/{CLAIM_ID}", headers=H_ASSOC, json={"amount": 1300.00}
)
check("a draft edit moves the amount", r.status_code == 200 and r.json().get("amount") == 1300.00, f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/expenses/claims/{CLAIM_ID}/submit", headers=H_ASSOC)
check("the claimant submits the draft", r.status_code == 200 and r.json().get("status") == "SUBMITTED", f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/expenses/claims/{CLAIM_ID}/submit", headers=H_ASSOC)
check("submitting twice is refused", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")

r = client.patch(
    f"/api/v1/expenses/claims/{CLAIM_ID}", headers=H_ASSOC, json={"amount": 1400.00}
)
check("a submitted claim is frozen for edits", r.status_code == 409, f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/expenses/claims/{CLAIM_ID}/l1-approve", headers=H_MGR)
check(
    "the reporting-line manager gives the first approval",
    r.status_code == 200 and r.json().get("status") == "L1_APPROVED",
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.post(f"/api/v1/expenses/claims/{CLAIM_ID}/mark-paid", headers=H_ADMIN)
check("paying before final approval is refused", r.status_code == 409, f"got {r.status_code}: {r.text[:200]}")
check(
    "the payment refusal names its code",
    r.json().get("error", {}).get("code") == "expense_invalid_payment_state",
    f"got {r.text[:200]}",
)

r = client.post(f"/api/v1/expenses/claims/{CLAIM_ID}/approve", headers=H_MGR)
check("a manager cannot give the final approval", r.status_code == 403, f"got {r.status_code}")

r = client.post(f"/api/v1/expenses/claims/{CLAIM_ID}/approve", headers=H_ADMIN)
check(
    "finance gives the final approval",
    r.status_code == 200 and r.json().get("status") == "APPROVED",
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.post(f"/api/v1/expenses/claims/{CLAIM_ID}/mark-paid", headers=H_ADMIN)
check(
    "finance marks the approved claim paid",
    r.status_code == 200 and r.json().get("payment_status") == "PAID",
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.post(f"/api/v1/expenses/claims/{CLAIM_ID}/mark-paid", headers=H_ADMIN)
check("paying twice is refused", r.status_code == 409, f"got {r.status_code}: {r.text[:200]}")

# ===========================================================================
print("\n[CLAIM-2] Rejection, rework, and the guards")
# ===========================================================================

r = client.post(
    "/api/v1/expenses/claims",
    headers=H_ADMIN,
    json={"employee_id": EMP_A_ID, "category_id": CAT_ID, "expense_date": "2026-10-03", "amount": 500.00},
)
REJECT_ID = r.json().get("id") if r.status_code == 201 else None
check("finance files the second claim", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/expenses/claims/{REJECT_ID}/submit", headers=H_ADMIN)
check("the second claim is submitted", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/expenses/claims/{REJECT_ID}/reject", headers=H_MGR, json={"reason": "no bill attached"})
check(
    "the manager rejects with a reason",
    r.status_code == 200 and r.json().get("status") == "REJECTED",
    f"got {r.status_code}: {r.text[:200]}",
)
check("the reason is kept", r.json().get("rejection_reason") == "no bill attached", f"got {r.json().get('rejection_reason')}")

r = client.post(f"/api/v1/expenses/claims/{REJECT_ID}/l1-approve", headers=H_MGR)
check("a rejected claim cannot be approved", r.status_code == 422, f"got {r.status_code}")

r = client.post(f"/api/v1/expenses/claims/{REJECT_ID}/rework", headers=H_ASSOC)
check(
    "rework returns the claim to draft",
    r.status_code == 200 and r.json().get("status") == "DRAFT",
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.post(
    "/api/v1/expenses/claims",
    headers=H_PAY,
    json={"employee_id": EMP_A_ID, "category_id": CAT_ID, "expense_date": "2026-10-04", "amount": 100.00},
)
check("a payroll viewer cannot file a claim", r.status_code == 403, f"got {r.status_code}")

r = client.get("/api/v1/expenses/claims", headers=H_PAY)
check("a payroll viewer cannot list claims", r.status_code == 403, f"got {r.status_code}")

r = client.post(
    "/api/v1/expenses/claims",
    headers=H_ASSOC,
    json={"employee_id": EMP_B_ID, "category_id": CAT_ID, "expense_date": "2026-10-04", "amount": 100.00},
)
check("an associate cannot file for somebody else", r.status_code == 403, f"got {r.status_code}")

r = client.post(
    "/api/v1/expenses/claims",
    headers=H_MGR,
    json={"employee_id": EMP_B_ID, "category_id": CAT_ID, "expense_date": "2026-10-04", "amount": 200.00},
)
check(
    "a manager filing outside their line reads as not found (fail-closed)",
    r.status_code == 404,
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.post(
    "/api/v1/expenses/claims",
    headers=H_ADMIN,
    json={"employee_id": EMP_B_ID, "category_id": CAT_ID, "expense_date": "2026-10-04", "amount": 200.00},
)
OUTSIDER_ID = r.json().get("id") if r.status_code == 201 else None
check("finance files for an employee outside the manager's line", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/expenses/claims/{OUTSIDER_ID}/submit", headers=H_ADMIN)
check("it is submitted", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/expenses/claims/{OUTSIDER_ID}/l1-approve", headers=H_MGR)
check("a manager cannot decide outside their line", r.status_code == 403, f"got {r.status_code}")

r = client.post(f"/api/v1/expenses/claims/{OUTSIDER_ID}/l1-approve", headers=H_ASSOC)
check("an associate cannot approve at all", r.status_code == 403, f"got {r.status_code}")

r = client.post(f"/api/v1/expenses/claims/{OUTSIDER_ID}/mark-paid", headers=H_ASSOC)
check("an associate cannot mark paid", r.status_code == 403, f"got {r.status_code}")

r = client.get("/api/v1/expenses/claims", headers=H_ASSOC)
check("an associate lists the queue", r.status_code == 200, f"got {r.status_code}")

r = client.get(f"/api/v1/expenses/claims/{OUTSIDER_ID}", headers=H_ASSOC)
check("an associate cannot read somebody else's claim", r.status_code == 404, f"got {r.status_code}")

# ===========================================================================
print("\n[RECEIPT-1] Opaque keys, authenticated bytes")
# ===========================================================================

r = client.post(
    "/api/v1/expenses/claims",
    headers=H_ASSOC,
    json={"employee_id": EMP_A_ID, "category_id": CAT_ID, "expense_date": "2026-10-05", "amount": 750.25},
)
RCPT_CLAIM = r.json().get("id") if r.status_code == 201 else None
check("a claim is filed for the receipt checks", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

r = client.post(
    f"/api/v1/expenses/claims/{RCPT_CLAIM}/receipts",
    headers=H_ASSOC,
    files={"file": ("bill.pdf", b"%PDF-1.4 fake receipt bytes", "application/pdf")},
)
check("a receipt attaches to the draft", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")
KEY_ONE = r.json().get("download_url", "") if r.status_code == 201 else ""
check(
    "the download URL points at the authenticated files route",
    KEY_ONE.startswith("/api/v1/files/expenses/"),
    f"got {KEY_ONE[:120]}",
)

r = client.post(
    f"/api/v1/expenses/claims/{RCPT_CLAIM}/receipts",
    headers=H_ASSOC,
    files={"file": ("bill.pdf", b"%PDF-1.4 fake receipt bytes", "application/pdf")},
)
KEY_TWO = r.json().get("download_url", "") if r.status_code == 201 else ""
check("a second upload lands under its own key", r.status_code == 201 and KEY_TWO != KEY_ONE, f"got {KEY_TWO[:120]}")

r = client.post(
    f"/api/v1/expenses/claims/{RCPT_CLAIM}/receipts",
    headers=H_ASSOC,
    files={"file": ("empty.pdf", b"", "application/pdf")},
)
check("an empty file is refused", r.status_code == 422, f"got {r.status_code}")

r = client.get(f"/api/v1/expenses/claims/{RCPT_CLAIM}/receipts", headers=H_ASSOC)
check(
    "the claim lists its two receipts",
    r.status_code == 200 and len(r.json()) == 2,
    f"got {r.status_code}: {r.text[:200]}",
)

r = client.get(KEY_ONE)
check("the bytes need a token", r.status_code == 401, f"got {r.status_code}")

r = client.get(KEY_ONE, headers=H_ASSOC)
check(
    "the bytes download with a token",
    r.status_code == 200 and r.content == b"%PDF-1.4 fake receipt bytes",
    f"got {r.status_code}: {len(r.content)} bytes",
)

r = client.post(f"/api/v1/expenses/claims/{RCPT_CLAIM}/submit", headers=H_ASSOC)
check("the receipt claim is submitted", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

r = client.post(
    f"/api/v1/expenses/claims/{RCPT_CLAIM}/receipts",
    headers=H_ASSOC,
    files={"file": ("late.pdf", b"late", "application/pdf")},
)
check("a receipt still attaches while submitted", r.status_code == 201, f"got {r.status_code}: {r.text[:200]}")

r = client.post(f"/api/v1/expenses/claims/{RCPT_CLAIM}/l1-approve", headers=H_MGR)
check("the line approves", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

r = client.post(
    f"/api/v1/expenses/claims/{RCPT_CLAIM}/receipts",
    headers=H_ASSOC,
    files={"file": ("after.pdf", b"after approval", "application/pdf")},
)
check("attaching after the first approval is refused", r.status_code == 409, f"got {r.status_code}: {r.text[:200]}")

r = client.post(
    f"/api/v1/expenses/claims/{RCPT_CLAIM}/receipts",
    headers=H_PAY,
    files={"file": ("x.pdf", b"x", "application/pdf")},
)
check("a payroll viewer cannot attach receipts", r.status_code == 403, f"got {r.status_code}")

# ===========================================================================
print("\n[TENANT-1] Tenant scope")
# ===========================================================================

r = client.post(
    "/api/v1/expenses/categories", headers=HA, json={"code": "EXP-TA", "name": "Tenant A Travel"}
)
check("tenant A creates its category", r.status_code == 201, r.text[:200])
TA_CAT = r.json().get("id") if r.status_code == 201 else None
check("creation stamps the request tenant", r.json().get("tenant_id") == TENANT_A, r.text[:200])

r = client.get("/api/v1/expenses/categories", headers=HB)
check(
    "tenant B's list excludes tenant A's category",
    r.status_code == 200 and all(row["id"] != TA_CAT for row in r.json()),
    f"got {r.status_code}",
)

r = client.get(f"/api/v1/expenses/categories/{TA_CAT}", headers=HB)
check("tenant B reads tenant A's category as 404", r.status_code == 404, f"got {r.status_code}")

r = client.post(
    "/api/v1/expenses/claims",
    headers=HA,
    json={"employee_id": EMP_A_ID, "category_id": TA_CAT, "expense_date": "2026-10-06", "amount": 99.99},
)
TA_CLAIM = r.json().get("id") if r.status_code == 201 else None
check("tenant A files its claim", r.status_code == 201, r.text[:200])

r = client.get(f"/api/v1/expenses/claims/{TA_CLAIM}", headers=HB)
check("tenant B reads tenant A's claim as 404", r.status_code == 404, f"got {r.status_code}")

r = client.get("/api/v1/expenses/claims", headers=HB)
check(
    "tenant B's claim list excludes tenant A's claim",
    r.status_code == 200 and all(row["id"] != TA_CLAIM for row in r.json()),
    f"got {r.status_code}",
)

# A draft may only move within its own tenant: tenant A owns the claim, so
# pointing it at tenant B's category must fail closed before anything is
# applied — the same 422 the create endpoint answers for a foreign
# category, with no tenant signal beyond the reference name.
r = client.post(
    "/api/v1/expenses/categories", headers=HB, json={"code": "EXP-TB", "name": "Tenant B Travel"}
)
check("tenant B creates its category", r.status_code == 201, r.text[:200])
TB_CAT = r.json().get("id") if r.status_code == 201 else None

r = client.patch(
    f"/api/v1/expenses/claims/{TA_CLAIM}", headers=HA, json={"category_id": TB_CAT}
)
check("attaching another tenant's category is refused", r.status_code == 422, f"got {r.status_code}: {r.text[:200]}")
check(
    "the refusal names the reference, not the tenant",
    r.json().get("error", {}).get("code") == "reference_not_found",
    f"got {r.text[:200]}",
)

r = client.patch(
    f"/api/v1/expenses/claims/{TA_CLAIM}", headers=HA, json={"category_id": TA_CAT}
)
check("re-pointing at the claim's own category still works", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

# Tenant-scoped codes: the same code may exist once per tenant. A global
# uniqueness would refuse the second tenant's row (and leak its existence
# via 409), while a duplicate inside one tenant stays a 409.
r = client.post(
    "/api/v1/expenses/categories", headers=HA, json={"code": "EXP-SHARED", "name": "Shared A"}
)
check("tenant A creates the shared code", r.status_code == 201, r.text[:200])
r = client.post(
    "/api/v1/expenses/categories", headers=HB, json={"code": "EXP-SHARED", "name": "Shared B"}
)
check(
    "the same code in another tenant is allowed (tenant-scoped)",
    r.status_code == 201,
    f"got {r.status_code}: {r.text[:200]}",
)
r = client.post(
    "/api/v1/expenses/categories", headers=HA, json={"code": "exp-shared", "name": "Shared A Duplicate"}
)
check(
    "a duplicate code in the same tenant is refused (case-insensitive)",
    r.status_code == 409 and r.json().get("error", {}).get("code") == "duplicate_natural_key",
    f"got {r.status_code}: {r.text[:200]}",
)

# ===========================================================================
print("\n[AUDIT-1] Every write is attributable")
# ===========================================================================

_audit_db = SessionLocal()
_audit_rows = (
    _audit_db.query(AuditLog)
    .filter(AuditLog.entity_type.in_(["ExpenseCategory", "ExpenseClaim", "ExpenseReceipt"]))
    .all()
)
_audit_db.close()
_audit_actions = {row.action for row in _audit_rows}
check(
    "every expense write is audited",
    {
        "create_expense_category",
        "create_expense_claim",
        "submit_expense_claim",
        "l1_approve_expense_claim",
        "approve_expense_claim",
        "mark_expense_claim_paid",
        "reject_expense_claim",
        "upload_expense_receipt",
    }
    <= _audit_actions,
    str(sorted(_audit_actions)),
)

# ===========================================================================
print("\n[MIGRATION-1] Migration 0037, and its downgrade")
# ===========================================================================


def _run_migrations(db_path: str, target: str = "head", direction: str = "upgrade") -> None:
    """Run the migration CLI against a scratch database (the operator path)."""
    backend = Path(__file__).resolve().parent
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["ALEMBIC_DATABASE_URL"] = f"sqlite:///{db_path}"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.migrate", direction, target],
        cwd=str(backend),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]


def _tables(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def _columns(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def _column_type(db_path: str, table: str, column: str) -> str:
    conn = sqlite3.connect(db_path)
    try:
        for row in conn.execute(f"PRAGMA table_info({table})"):
            if row[1] == column:
                return str(row[2]).upper()
        return ""
    finally:
        conn.close()


def _indexes(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute(f"PRAGMA index_list({table})")}
    finally:
        conn.close()


workdir = tempfile.mkdtemp(prefix="expenses_migration_")
fresh = os.path.join(workdir, "fresh.db")
try:
    _run_migrations(fresh)
    check(
        "a fresh database reaches head with the category table",
        "expense_categories" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the claim table is created",
        "expense_claims" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the receipt table is created",
        "expense_receipts" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the claim table holds the columns the models declare",
        {
            "id", "tenant_id", "employee_id", "category_id", "expense_date",
            "amount", "currency", "description", "status", "payment_status",
            "submitted_by", "submitted_at", "l1_approved_by", "l1_approved_at",
            "approved_by", "approved_at", "rejected_by", "rejected_at",
            "rejection_reason", "paid_by", "paid_at", "created_at", "updated_at",
        }
        <= _columns(fresh, "expense_claims"),
        f"columns={sorted(_columns(fresh, 'expense_claims'))}",
    )
    check(
        "the amount is Numeric(12, 2)",
        "NUMERIC(12, 2)" in _column_type(fresh, "expense_claims", "amount"),
        f"type={_column_type(fresh, 'expense_claims', 'amount')}",
    )
    check(
        "the receipt table holds the opaque storage key",
        {"claim_id", "storage_key", "file_name", "content_type", "size_bytes"}
        <= _columns(fresh, "expense_receipts"),
        f"columns={sorted(_columns(fresh, 'expense_receipts'))}",
    )
    check(
        "the declared indexes exist",
        {
            "ix_expense_claims_employee_id",
            "ix_expense_claims_category_id",
            "ix_expense_receipts_claim_id",
        }
        <= _indexes(fresh, "expense_claims") | _indexes(fresh, "expense_receipts"),
        f"indexes={sorted(_indexes(fresh, 'expense_claims')) + sorted(_indexes(fresh, 'expense_receipts'))}",
    )

    _run_migrations(fresh, "0036_legal_entities", "downgrade")
    check(
        "the downgrade removes the category table",
        "expense_categories" not in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the downgrade removes the claim table",
        "expense_claims" not in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the downgrade removes the receipt table",
        "expense_receipts" not in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    check(
        "the downgrade leaves the employees table alone",
        "employees" in _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
    _run_migrations(fresh)
    check(
        "everything comes back on re-upgrade",
        {"expense_categories", "expense_claims", "expense_receipts"} <= _tables(fresh),
        f"tables={sorted(_tables(fresh))}",
    )
finally:
    shutil.rmtree(workdir, ignore_errors=True)

# ===========================================================================
print()
print("----------------------------------------------------------------")
print(f"expenses tests: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("----------------------------------------------------------------")
shutil.rmtree(os.path.dirname(DB_PATH), ignore_errors=True)
raise SystemExit(1 if RESULTS["fail"] else 0)
