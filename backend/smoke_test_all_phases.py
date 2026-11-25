"""Local smoke test for Phases 8-14 using SQLite."""
import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.mkdtemp(prefix="smoke_p814_"), "smoke_p814.db"
)
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = "*"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

# The payroll section of this suite calculates a pay run, and a pay run is
# calculated only from a rule pack that is `verified` and in force on the
# pay date. The suite therefore points the resolver at the synthetic test
# fixture pack. The fixture is not a rule pack for any real jurisdiction:
# its country code is a user-assigned one, every number in it is invented,
# and it lives outside the `rule_packs/` directory the product ships.
os.environ["RULE_PACK_DIR"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "test_fixtures", "rule_packs"
)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.employee import Employee  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
if not db.query(User).filter(User.username == "admin").first():
    db.add(User(username="admin", email="admin@example.com", hashed_password=get_password_hash("secret123"), role="SuperAdmin", is_active=True, mfa_enabled=True))
    db.commit()
dept = db.query(Department).filter(Department.code == "OPS").first()
if not dept:
    dept = Department(name="Operations", code="OPS")
    db.add(dept); db.commit(); db.refresh(dept)
job = db.query(Job).filter(Job.code == "ASSOC").first()
if not job:
    job = Job(title="Associate", code="ASSOC", department_id=dept.id)
    db.add(job); db.commit(); db.refresh(job)
emp = db.query(Employee).filter(Employee.employee_id == "EMP1").first()
if not emp:
    emp = Employee(employee_id="EMP1", first_name="Test", last_name="User", email="test@example.com", hire_date=__import__("datetime").date.today(), job_id=job.id, department_id=dept.id)
    db.add(emp); db.commit(); db.refresh(emp)
db.close()

client = TestClient(app)
tok = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# Get fixture IDs via API
dept_id = client.get("/api/v1/departments/", headers=H).json()[0]["id"]
job_id = client.get("/api/v1/jobs/", headers=H).json()[0]["id"]
emp_id = client.get("/api/v1/employees/", headers=H).json()["items"][0]["id"]

PASS = FAIL = 0


def check(name, ok, extra=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS  {name} {extra}")
    else:
        FAIL += 1
        print(f"FAIL  {name} {extra}")


# --- Phase 8: Core HR ------------------------------------------------------- #
r = client.post("/api/v1/core-hr/locations", headers=H, json={"name": "HQ", "code": "HQ"})
check("8. create location", r.status_code == 201)
loc_id = r.json()["id"]

r = client.post("/api/v1/core-hr/cost-centers", headers=H, json={"code": "CC1", "name": "CC1", "department_id": dept_id})
check("8. create cost center", r.status_code == 201)

r = client.post("/api/v1/core-hr/positions", headers=H, json={"code": "P1", "title": "Position 1", "job_id": job_id, "department_id": dept_id, "location_id": loc_id, "fte": 1.0})
check("8. create position", r.status_code == 201)

r = client.post("/api/v1/core-hr/employee-documents", headers=H, json={"employee_id": emp_id, "document_type": "Contract", "file_name": "contract.pdf", "storage_url": "/files/contract.pdf"})
check("8. upload employee doc", r.status_code == 201)

r = client.post("/api/v1/core-hr/cases", headers=H, json={"employee_id": emp_id, "subject": "Payroll issue", "category": "Payroll", "priority": "High"})
check("8. create HR case", r.status_code == 201)
case_id = r.json()["id"]

r = client.post(f"/api/v1/core-hr/cases/{case_id}/comments", headers=H, json={"case_id": case_id, "author": "admin", "comment": "Looking into it"})
check("8. add case comment", r.status_code == 201)

r = client.get(f"/api/v1/core-hr/cases/{case_id}/comments", headers=H)
check("8. list case comments", r.status_code == 200 and len(r.json()) == 1)

# --- Phase 9: Payroll ------------------------------------------------------- #
r = client.post("/api/v1/payroll/periods", headers=H, json={"name": "Jan2026", "start_date": "2026-01-01", "end_date": "2026-01-31", "pay_date": "2026-02-05"})
check("9. create payroll period", r.status_code == 201)
period_id = r.json()["id"]

r = client.post("/api/v1/payroll/components", headers=H, json={"code": "BASIC", "name": "Basic", "component_type": "Earning"})
check("9. create pay component", r.status_code == 201)

r = client.post("/api/v1/payroll/pay-profiles", headers=H, json={"employee_id": emp_id, "base_salary": 50000, "pay_frequency": "Monthly", "tax_withholding": 10})
check("9. create pay profile", r.status_code == 201)

r = client.post("/api/v1/payroll/runs", headers=H,
                json={"period_id": period_id, "jurisdiction": "QQ", "currency": "USD"})
check("9. create pay run", r.status_code == 201)
run_id = r.json()["id"]

# A jurisdiction without a verified rule pack is refused, and the refusal
# writes nothing: no payslip, and the run does not move.
r = client.post("/api/v1/payroll/runs", headers=H,
                json={"period_id": period_id, "jurisdiction": "RR", "currency": "USD"})
blocked_id = r.json()["id"]
r = client.post(f"/api/v1/payroll/runs/{blocked_id}/process", headers=H)
check("9. a jurisdiction without a verified pack is refused",
      r.status_code == 422 and r.json()["error"]["code"] == "rule_pack_not_verified",
      f"got {r.status_code}: {r.text[:160]}")
r = client.get(f"/api/v1/payroll/payslips?pay_run_id={blocked_id}", headers=H)
check("9. the refused run has no payslips", len(r.json()) == 0)

r = client.post(f"/api/v1/payroll/runs/{run_id}/process", headers=H)
check("9. process pay run", r.status_code == 200 and r.json()["headcount"] == 1)
check("9. pay run gross", r.json()["total_gross"] == 50000)

r = client.get(f"/api/v1/payroll/payslips?pay_run_id={run_id}", headers=H)
check("9. payslips generated", r.status_code == 200 and len(r.json()) == 1)

# Segregation of duties: the operator who processed a run must not approve it.
r = client.post(f"/api/v1/payroll/runs/{run_id}/approve", headers=H)
check("9. processor cannot approve own run", r.status_code == 403 and "segregation" in r.text.lower())

_r2 = client.post("/api/v1/auth/login", json={"username": "approver", "password": "Segreg8Review45"})
if _r2.status_code != 200:
    client.post("/api/v1/auth/users", headers=H, json={"user_in": {"username": "approver", "email": "approver@example.com", "password": "Segreg8Review45", "role": "HR"}})
    # MFA-enforced world: the HR approver must be enrolled or approve is 403.
    _db_approver = db.query(User).filter(User.username == "approver").first()
    if _db_approver is not None and not getattr(_db_approver, "mfa_enabled", False):
        _db_approver.mfa_enabled = True
        db.commit()
    _r2 = client.post("/api/v1/auth/login", json={"username": "approver", "password": "Segreg8Review45"})
H2 = {"Authorization": f"Bearer {_r2.json()['access_token']}"}
r = client.post(f"/api/v1/payroll/runs/{run_id}/approve", headers=H2)
check("9. approve pay run", r.status_code == 200 and r.json()["status"] == "Approved")

r = client.post(f"/api/v1/payroll/runs/{run_id}/finalize", headers=H2)
check("9. finalize pay run", r.status_code == 200 and r.json()["status"] == "Finalized")

# --- Phase 10: Performance -------------------------------------------------- #
r = client.post("/api/v1/performance/goals", headers=H, json={"employee_id": emp_id, "title": "Increase sales", "weight": 50, "due_date": "2026-12-31"})
check("10. create goal", r.status_code == 201)
goal_id = r.json()["id"]

r = client.put(f"/api/v1/performance/goals/{goal_id}", headers=H, json={"progress": 50, "status": "In Progress"})
check("10. update goal", r.status_code == 200 and r.json()["progress"] == 50)

r = client.post("/api/v1/performance/reviews", headers=H, json={"employee_id": emp_id, "period": "2026-H1", "status": "Draft"})
check("10. create review", r.status_code == 201)
review_id = r.json()["id"]

r = client.post("/api/v1/performance/feedback", headers=H, json={"review_id": review_id, "feedback_type": "Manager", "rating": 4.5, "comments": "Great work"})
check("10. add feedback", r.status_code == 201)

r = client.post("/api/v1/performance/reviews/{review_id}/finalize".format(review_id=review_id), headers=H)
check("10. finalize review", r.status_code == 200 and r.json()["status"] == "Finalized")

r = client.post("/api/v1/performance/compensation-bands", headers=H, json={"job_id": job_id, "level": "Mid", "min_salary": 30000, "mid_salary": 50000, "max_salary": 70000})
check("10. create comp band", r.status_code == 201)

r = client.post("/api/v1/performance/merit-cycles", headers=H, json={"name": "2026 Merit", "year": 2026, "budget_percent": 3.5, "start_date": "2026-01-01", "end_date": "2026-03-31"})
check("10. create merit cycle", r.status_code == 201)
cycle_id = r.json()["id"]

r = client.post("/api/v1/performance/merit-allocations", headers=H, json={"cycle_id": cycle_id, "employee_id": emp_id, "current_salary": 50000, "proposed_salary": 52500, "increase_percent": 5})
check("10. create merit allocation", r.status_code == 201)

# --- Phase 11: Benefits ----------------------------------------------------- #
r = client.post("/api/v1/benefits/benefit-plans", headers=H, json={"name": "Health", "code": "HLTH", "plan_type": "Health", "employer_contribution": 5000, "employee_contribution": 1000})
check("11. create benefit plan", r.status_code == 201)
plan_id = r.json()["id"]

r = client.post("/api/v1/benefits/benefit-enrollments", headers=H, json={"employee_id": emp_id, "plan_id": plan_id, "effective_date": "2026-01-01"})
check("11. enroll benefit", r.status_code == 201)

r = client.post("/api/v1/benefits/life-events", headers=H, json={"employee_id": emp_id, "event_type": "Marriage", "event_date": "2026-06-01"})
check("11. create life event", r.status_code == 201)

r = client.post("/api/v1/benefits/leaves-of-absence", headers=H, json={"employee_id": emp_id, "leave_type": "FMLA", "start_date": "2026-03-01", "end_date": "2026-03-31"})
check("11. create LOA", r.status_code == 201)
loa_id = r.json()["id"]

r = client.put(f"/api/v1/benefits/leaves-of-absence/{loa_id}/approve", headers=H)
check("11. approve LOA", r.status_code == 200 and r.json()["status"] == "Approved")

# --- Phase 12: Learning ----------------------------------------------------- #
r = client.post("/api/v1/learning/courses", headers=H, json={"title": "Safety Training", "code": "SAFE", "category": "Compliance", "duration_hours": 2, "is_mandatory": True})
check("12. create course", r.status_code == 201)
course_id = r.json()["id"]

r = client.post("/api/v1/learning/course-enrollments", headers=H, json={"employee_id": emp_id, "course_id": course_id})
check("12. enroll course", r.status_code == 201)
enr_id = r.json()["id"]

r = client.put(f"/api/v1/learning/course-enrollments/{enr_id}/complete", headers=H, params={"score": 95})
check("12. complete course", r.status_code == 200 and r.json()["status"] == "Completed")

r = client.post("/api/v1/learning/certifications", headers=H, json={"employee_id": emp_id, "name": "Safety Cert", "issuer": "OSHA", "issued_date": "2026-01-01", "expiry_date": "2027-01-01"})
check("12. create certification", r.status_code == 201)

r = client.post("/api/v1/learning/talent-pools", headers=H, json={"name": "High Potential"})
check("12. create talent pool", r.status_code == 201)
pool_id = r.json()["id"]

r = client.post("/api/v1/learning/talent-pool-members", headers=H, json={"pool_id": pool_id, "employee_id": emp_id, "readiness": "Ready Now"})
check("12. add pool member", r.status_code == 201)

r = client.post("/api/v1/learning/succession-plans", headers=H, json={"position_id": 1, "readiness": "Ready Now"})
check("12. create succession plan", r.status_code == 201)

# --- Phase 13: Platform ----------------------------------------------------- #
r = client.post("/api/v1/platform/webhooks", headers=H, json={"url": "https://httpbin.org/post", "events": "employee.created"})
check("13. create webhook", r.status_code == 201)
wh_id = r.json()["id"]

r = client.post(f"/api/v1/platform/webhooks/{wh_id}/deliver", headers=H, params={"event": "test"})
check("13. deliver webhook", r.status_code == 201)

r = client.get(f"/api/v1/platform/webhooks/{wh_id}/deliveries", headers=H)
check("13. list deliveries", r.status_code == 200 and len(r.json()) >= 1)

r = client.post("/api/v1/platform/sso-configs", headers=H, json={"provider": "SAML", "entity_id": "https://idp.example.com", "is_active": False})
check("13. create SSO config", r.status_code == 201)

r = client.post("/api/v1/platform/background-checks", headers=H, json={"candidate_id": 1, "provider": "manual", "status": "Pending"})
check("13. create bg check", r.status_code == 201)
bc_id = r.json()["id"]

r = client.put(f"/api/v1/platform/background-checks/{bc_id}/complete", headers=H, params={"result": "Clear", "status": "Clear"})
check("13. complete bg check", r.status_code == 200 and r.json()["status"] == "Clear")

r = client.post("/api/v1/platform/e-signatures", headers=H, json={"document_type": "Offer", "signer_email": "test@example.com"})
check("13. create e-signature", r.status_code == 201)
sig_id = r.json()["id"]

r = client.put(f"/api/v1/platform/e-signatures/{sig_id}/sign", headers=H)
check("13. sign document", r.status_code == 200 and r.json()["status"] == "Signed")

# --- Phase 14: Compliance --------------------------------------------------- #
r = client.post("/api/v1/compliance/compliance-rules", headers=H, json={"code": "MAXHRS", "name": "Max Hours", "category": "Labor Law", "severity": "High"})
check("14. create compliance rule", r.status_code == 201)
rule_id = r.json()["id"]

r = client.post("/api/v1/compliance/compliance-violations", headers=H, json={"employee_id": emp_id, "rule_id": rule_id, "status": "Open"})
check("14. create violation", r.status_code == 201)
viol_id = r.json()["id"]

r = client.put(f"/api/v1/compliance/compliance-violations/{viol_id}/resolve", headers=H)
check("14. resolve violation", r.status_code == 200 and r.json()["status"] == "Resolved")

r = client.post("/api/v1/compliance/headcount-plans", headers=H, json={"name": "2026 Plan", "year": 2026, "planned_headcount": 100})
check("14. create headcount plan", r.status_code == 201)

r = client.post("/api/v1/compliance/scenarios", headers=H, json={"name": "Growth", "description": "5% growth"})
check("14. create scenario", r.status_code == 201)

r = client.post("/api/v1/compliance/report-definitions", headers=H, json={"name": "Headcount", "query": "SELECT * FROM employees"})
check("14. create report def", r.status_code == 201)

r = client.post("/api/v1/compliance/saved-reports", headers=H, json={"name": "HC Report", "result_json": "{}"})
check("14. save report", r.status_code == 201)

# --- Import/Export ---------------------------------------------------------- #
r = client.get("/api/v1/import-export/entities", headers=H)
check("IE. list entities", r.status_code == 200 and len(r.json()["entities"]) >= 10)

csv = "name,code,description,is_active\nImpDept,IMP,desc,1\n"
r = client.post("/api/v1/import-export/import/departments", headers=H, files={"file": ("d.csv", csv, "text/csv")})
check("IE. import CSV", r.status_code == 200 and r.json()["created"] == 1)

r = client.get("/api/v1/import-export/export/departments", headers=H)
check("IE. export CSV", r.status_code == 200 and "ImpDept" in r.text)

# --- Client Onboarding ------------------------------------------------------ #
r = client.post("/api/v1/onboarding-portal/clients", headers=H, json={"name": "Test Co", "slug": "testco"})
check("CO. create client", r.status_code == 201)
cid = r.json()["id"]

r = client.get(f"/api/v1/onboarding-portal/clients/{cid}/feature-flags", headers=H)
check("CO. feature flags", r.status_code == 200 and len(r.json()) >= 10)

r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/integrations", headers=H, json={"name": "Test Int", "kind": "rest", "endpoint": "https://httpbin.org/get"})
check("CO. create integration", r.status_code == 201)
iid = r.json()["id"]

r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/integrations/{iid}/test", headers=H)
check("CO. test integration", r.status_code == 200)

r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/migrations", headers=H, json={"integration_id": iid, "entity": "employees", "total": 10})
check("CO. start migration", r.status_code == 201)
jid = r.json()["id"]

r = client.post(f"/api/v1/onboarding-portal/clients/{cid}/migrations/{jid}/run", headers=H)
check("CO. run migration", r.status_code == 200)

r = client.put(f"/api/v1/onboarding-portal/clients/{cid}/settings/test.key", headers=H, json={"key": "test.key", "value": "val"})
check("CO. upsert setting", r.status_code == 200)

r = client.get(f"/api/v1/onboarding-portal/clients/{cid}/onboarding", headers=H)
check("CO. onboarding progress", r.status_code == 200 and r.json()["total"] == 6)

r = client.get("/api/v1/onboarding-portal/docs/migration-api", headers=H)
check("CO. migration docs", r.status_code == 200 and len(r.json().get("content", "")) > 100)

# --- Reports ---------------------------------------------------------------- #
r = client.get("/api/v1/reports/dashboard", headers=H)
check("R. dashboard", r.status_code == 200)

r = client.get("/api/v1/reports/headcount", headers=H)
check("R. headcount", r.status_code == 200)

r = client.get("/api/v1/reports/audit?limit=10", headers=H)
check("R. audit", r.status_code == 200)

print(f"\n==== {PASS} passed, {FAIL} failed ====")
raise SystemExit(1 if FAIL else 0)
PY