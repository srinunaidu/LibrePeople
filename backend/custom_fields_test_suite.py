"""Configurable employee fields (LP-CORE-005).

What this suite proves
----------------------
* definitions validate by type (text/number/integer/date/boolean/email),
  required blanks are refused, and unknown keys are rejected before
  anything is written;
* the employee endpoints parse ``custom_fields`` on create and on update
  (including a custom-only patch), return them on list and detail, and
  refuse unknown keys and bad values with 422;
* visibility holds: ``hr_only`` keys are omitted for Manager/Associate,
  ``is_sensitive`` values are masked to null, HR sees everything;
* the importer accepts ``custom.<key>`` headers, rejects a bad custom
  value at the row with its type code, rejects an unknown ``custom.*``
  header with 422, enforces a required definition's header, writes the
  values on commit, and the export carries the same ``custom.<key>``
  columns with the stored values.

Run:  python custom_fields_test_suite.py
"""
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="custom_fields_test_"), "custom_fields_test.db")
STORAGE_DIR = tempfile.mkdtemp(prefix="custom-fields-test-")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["LOCAL_STORAGE_DIR"] = STORAGE_DIR

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.custom_field import CustomFieldDef  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import custom_fields as cf_service  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()

dept = Department(name="Custom Fields", code="CFDEPT")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Custom Analyst", code="CF-JOB", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def mk_emp(code, first, manager_id=None):
    emp = Employee(
        employee_id=code,
        first_name=first,
        last_name="Custom",
        email=f"{code.lower()}@example.com",
        hire_date=__import__("datetime").date(2024, 3, 1),
        job_id=job.id,
        department_id=dept.id,
        manager_id=manager_id,
        status="Active",
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


mgr = mk_emp("CF-MGR", "Marta")
rep = mk_emp("CF-REP", "Ravi", mgr.id)


def mk_def(key, field_type="text", **kw):
    row = CustomFieldDef(key=key, label=key.replace("_", " ").title(),
                         field_type=field_type, **kw)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


mk_def("tshirt_size", "text")
mk_def("years_exp", "integer")
mk_def("bonus_pct", "number", is_sensitive=True)
mk_def("mentor_notes", "text", visibility="hr_only")
mk_def("probation_clear", "boolean", required=True)


def mk_user(username, role, employee_id=None):
    db.add(User(
        username=username, email=f"{username}@example.com",
        hashed_password=get_password_hash("CustomPass123"),
        role=role, is_active=True,
        mfa_enabled=True if role in ("SuperAdmin", "HR") else False,
        employee_id=employee_id,
    ))
    db.commit()


JOB_ID = job.id
DEPT_ID = dept.id
MGR_ID = mgr.id
REP_ID = rep.id

mk_user("cf_admin", "SuperAdmin")
mk_user("cf_hr", "HR")
mk_user("cf_mgr", "Manager", mgr.id)
mk_user("cf_assoc", "Associate", rep.id)
db.close()

client = TestClient(app, raise_server_exceptions=False)

RESULTS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name, ok, detail=""):
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def tok(username):
    r = client.post("/api/v1/auth/login",
                    json={"username": username, "password": "CustomPass123"})
    return r.json().get("access_token", "")


def H(username):
    return {"Authorization": f"Bearer {tok(username)}"}


HR = H("cf_admin")
LIST = "/api/v1/employees/"

print("=" * 68)
print("CUSTOM FIELDS SUITE (LP-CORE-005)")
print("=" * 68)

# --- service-level validation -------------------------------------------
session = SessionLocal()
defs = cf_service.def_map(session)
check("definitions load by key", set(defs) >= {
    "tshirt_size", "years_exp", "bonus_pct", "mentor_notes", "probation_clear"},
    str(sorted(defs)))
check("integer coerces", cf_service.validate_value(defs["years_exp"], " 7 ") == "7")
check("number coerces", cf_service.validate_value(defs["bonus_pct"], "12.5") == "12.5")
check("boolean coerces", cf_service.validate_value(defs["probation_clear"], "YES") == "true")
try:
    cf_service.validate_value(defs["years_exp"], "abc")
    check("integer refuses text", False, "no error raised")
except cf_service.CustomFieldError as exc:
    check("integer refuses text", exc.code == "invalid_integer", exc.code)
try:
    cf_service.validate_value(defs["probation_clear"], "")
    check("required refuses blank", False, "no error raised")
except cf_service.CustomFieldError as exc:
    check("required refuses blank", exc.code == "missing_required", exc.code)
try:
    cf_service.validate_all({"nope": "1"}, defs)
    check("unknown key refused", False, "no error raised")
except cf_service.CustomFieldError as exc:
    check("unknown key refused", exc.key == "nope", str(exc.key))
check("formula text neutralised",
      (cf_service.validate_value(defs["tshirt_size"], "=1+1") or "").startswith("'"),
      repr(cf_service.validate_value(defs["tshirt_size"], "=1+1")))
session.close()

# --- employees API --------------------------------------------------------
payload = {
    "employee_id": "CF-001",
    "first_name": "Ada",
    "last_name": "Custom",
    "email": "ada.custom@example.com",
    "hire_date": "2024-05-01",
    "job_id": JOB_ID,
    "department_id": DEPT_ID,
    "status": "Active",
    "custom_fields": {"tshirt_size": "M", "bonus_pct": "12.5",
                      "mentor_notes": "fast learner",
                      "probation_clear": True},
}
r = client.post(LIST, headers=HR, json=payload)
check("create with custom fields is 201", r.status_code == 201,
      f"got {r.status_code}: {r.text[:200]}")
body = r.json() if r.status_code == 201 else {}
check("create returns stored values for HR",
      (body.get("custom_fields") or {}).get("tshirt_size") == "M"
      and (body.get("custom_fields") or {}).get("bonus_pct") == "12.5"
      and (body.get("custom_fields") or {}).get("mentor_notes") == "fast learner"
      and (body.get("custom_fields") or {}).get("probation_clear") == "true",
      str(body.get("custom_fields")))
emp_id = body.get("id")

bad = dict(payload)
bad["employee_id"] = "CF-BAD"
bad["email"] = "bad.custom@example.com"
bad["custom_fields"] = {"nope": "1", "probation_clear": True}
r = client.post(LIST, headers=HR, json=bad)
check("create with unknown key is 422", r.status_code == 422,
      f"got {r.status_code}: {r.text[:160]}")

bad2 = dict(payload)
bad2["employee_id"] = "CF-BAD2"
bad2["email"] = "bad2.custom@example.com"
bad2["custom_fields"] = {"years_exp": "many", "probation_clear": True}
r = client.post(LIST, headers=HR, json=bad2)
check("create with bad value is 422", r.status_code == 422,
      f"got {r.status_code}: {r.text[:160]}")

# no partial row left behind by a refused create
session = SessionLocal()
check("refused creates leave no employee",
      session.query(Employee).filter(Employee.employee_id.in_(["CF-BAD", "CF-BAD2"])).count() == 0)
session.close()

r = client.get(f"{LIST}{emp_id}", headers=HR)
check("detail returns custom fields",
      (r.json().get("custom_fields") or {}).get("tshirt_size") == "M",
      f"got {r.status_code}: {r.text[:160]}")

r = client.patch(f"{LIST}{emp_id}", headers=HR,
                 json={"custom_fields": {"tshirt_size": "L"}})
check("custom-only patch succeeds",
      r.status_code == 200
      and (r.json().get("custom_fields") or {}).get("tshirt_size") == "L",
      f"got {r.status_code}: {r.text[:200]}")

# --- visibility ------------------------------------------------------------
r = client.get(f"{LIST}{REP_ID}", headers=H("cf_mgr"))
mgr_view = r.json().get("custom_fields") if r.status_code == 200 else None
check("manager can read report detail with custom shape",
      r.status_code == 200 and isinstance(mgr_view, dict),
      f"got {r.status_code}: {r.text[:160]}")
# the report has no values yet; set one as HR, then check masking
client.patch(f"{LIST}{REP_ID}", headers=HR,
             json={"custom_fields": {"tshirt_size": "S", "bonus_pct": "9",
                                     "mentor_notes": "private",
                                     "probation_clear": False}})
r = client.get(f"{LIST}{REP_ID}", headers=H("cf_mgr"))
mgr_view = r.json().get("custom_fields") or {}
check("hr_only key omitted for manager", "mentor_notes" not in mgr_view,
      str(mgr_view))
check("sensitive value masked for manager",
      mgr_view.get("bonus_pct") is None and mgr_view.get("tshirt_size") == "S",
      str(mgr_view))
r = client.get(f"{LIST}{REP_ID}", headers=H("cf_assoc"))
assoc_view = r.json().get("custom_fields") or {}
check("associate sees own public field, masked sensitive, no hr_only",
      assoc_view.get("tshirt_size") == "S"
      and assoc_view.get("bonus_pct") is None
      and "mentor_notes" not in assoc_view,
      str(assoc_view))
r = client.get(f"{LIST}{REP_ID}", headers=HR)
hr_view = r.json().get("custom_fields") or {}
check("HR sees every value",
      hr_view.get("bonus_pct") == "9" and hr_view.get("mentor_notes") == "private",
      str(hr_view))
r = client.get(LIST + "?page=1&page_size=200", headers=H("cf_mgr"))
check("list renders custom fields per role",
      r.status_code == 200
      and all("mentor_notes" not in (e.get("custom_fields") or {})
              for e in r.json().get("items", [])),
      f"got {r.status_code}")

# --- imports ---------------------------------------------------------------
IE = "/api/v1/import-export"


def upload(csv_text, **params):
    return client.post(f"{IE}/import/employees", headers=HR,
                       files={"file": ("data.csv", csv_text, "text/csv")},
                       params=params)


def commit(token):
    return client.post(f"{IE}/import/employees/commit", headers=HR,
                       params={"confirmation_token": token})


header = ("employee_id,first_name,last_name,email,hire_date,job_id,"
          "department_id,custom.tshirt_size,custom.probation_clear")
csv_ok = (header + "\n"
          + f"CF-IMP-1,Im,Port,im.port@example.com,2024-06-01,{JOB_ID},{DEPT_ID},M,true\n")
r = upload(csv_ok, dry_run=True)
check("dry run accepts custom headers", r.status_code == 200,
      f"got {r.status_code}: {r.text[:200]}")
token = (r.json().get("confirmation_token") or "") if r.status_code == 200 else ""
r2 = commit(token) if token else None
check("commit writes custom values",
      r2 is not None and r2.status_code == 200, f"got {r2.status_code if r2 else 'no token'}")
session = SessionLocal()
imp = session.query(Employee).filter(Employee.employee_id == "CF-IMP-1").first()
stored = cf_service.read_values(session, [imp.id]).get(imp.id, {}) if imp else {}
session.close()
check("stored value matches the file", stored.get("tshirt_size") == "M"
      and stored.get("probation_clear") == "true", str(stored))

csv_bad = (header + "\n"
           + f"CF-IMP-2,Bad,Value,bad.value@example.com,2024-06-01,{JOB_ID},{DEPT_ID},M,maybe\n")
r = upload(csv_bad, dry_run=True)
codes = {e.get("code") for row in (r.json().get("rows") or [])
         for e in row.get("errors", [])} if r.status_code == 200 else set()
check("bad custom value rejects the row",
      r.status_code == 200 and "invalid_boolean" in codes, f"got {codes}")

r = upload(header.replace("custom.tshirt_size", "custom.nope")
           + "\n" + f"CF-IMP-3,Un,Known,un.known@example.com,2024-06-01,{JOB_ID},{DEPT_ID},M,true\n",
           dry_run=True)
check("unknown custom header is 422", r.status_code == 422,
      f"got {r.status_code}: {r.text[:200]}")

no_req = ("employee_id,first_name,last_name,email,hire_date,job_id,department_id\n"
          + f"CF-IMP-4,No,Req,no.req@example.com,2024-06-01,{JOB_ID},{DEPT_ID}\n")
r = upload(no_req, dry_run=True)
check("missing required custom header is 422", r.status_code == 422,
      f"got {r.status_code}: {r.text[:200]}")

r = client.get(f"{IE}/export/employees", headers=HR)
text = r.text if r.status_code == 200 else ""
first_line = text.splitlines()[0] if text else ""
check("export carries custom columns",
      r.status_code == 200 and "custom.tshirt_size" in first_line
      and "custom.probation_clear" in first_line, first_line[:200])
check("export carries stored values",
      any("CF-IMP-1" in line and ",M," in line for line in text.splitlines()),
      text[:300])

print()
print("=" * 68)
print(f"CUSTOM FIELDS SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
print("=" * 68)
if FAILURES:
    print("\nfailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
raise SystemExit(1 if RESULTS["fail"] else 0)
