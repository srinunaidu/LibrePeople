"""The employee directory implements its contract (D-040).

The defect this suite closes
----------------------------
`contracts/openapi/employees.yaml` promised a paged collection
(`PaginatedEmployees`: `items` + `meta`), `page`/`page_size`, a `search`, four
filters and newest-hire-first. The server returned a **bare list**, paged with
`skip`/`limit`, ignored every filter and sorted by id ascending. The contract
was the design; the code was a different, smaller thing.

What this suite proves
----------------------
* the answer is the contract's envelope, and `meta` counts what the caller may
  see, not the size of the table;
* paging is 1-based, a page beyond the end is empty (not an error), and the
  last page is short;
* `search` is case-insensitive across the employee number, first name, last
  name, full name and email address, and reaches a row the caller has not
  loaded;
* `department_id`, `status` and `manager_id` filter, and a status outside the
  stored vocabulary is refused rather than silently returning everything;
* `sort`/`order` work, `sort` omitted means newest hire first, and two people
  hired the same day keep a stable order across pages;
* the visibility scope applies to the filter and to the count (an Associate
  sees one, a Manager their line, HR everyone);
* a stored address the input rules would refuse is still returned — the
  response must not validate data the database already holds;
* the list does not claim fields the record does not have (`employee_number`,
  `location_id`, `position_id`);
* the search clause and the paged read compile against the **Oracle** dialect,
  because a green SQLite run is not evidence about production (DEC-031);
* the create operation keeps its half: the record's body is accepted and a
  duplicate number is the declared `409 duplicate_natural_key`.

Run:  python employees_test_suite.py
"""
import os

DB_PATH = "employees_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from datetime import date, timedelta  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.dialects import oracle  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.main import app  # noqa: E402
from app.api.v1.endpoints.employees import _SORT_COLUMNS, search_clause  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
client = TestClient(app, raise_server_exceptions=False)

RESULTS = {"pass": 0, "fail": 0}
FAILURES = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


LIST = "/api/v1/employees/"
LOGIN = "/api/v1/auth/login"
PASSWORD = "DirectoryPass123"

print("=" * 68)
print("EMPLOYEE DIRECTORY SUITE (D-040)")
print("=" * 68)

# --- the fixtures -----------------------------------------------------------
for name in ("Directory",):
    existing = db.query(Department).filter(Department.name == name).first()
    if existing:
        db.delete(existing)
db.commit()

dept_a = Department(name="Directory A", code="DIRA")
dept_b = Department(name="Directory B", code="DIRB")
db.add_all([dept_a, dept_b])
db.commit()
db.refresh(dept_a)
db.refresh(dept_b)

job_a = Job(title="Analyst", code="DIR-JOB-A", department_id=dept_a.id)
job_b = Job(title="Coordinator", code="DIR-JOB-B", department_id=dept_b.id)
db.add_all([job_a, job_b])
db.commit()
db.refresh(job_a)
db.refresh(job_b)

db.query(Employee).delete()
db.commit()

SURNAMES = [
    "Anderson", "Brown", "Clark", "Davis", "Evans",
    "Foster", "Garcia", "Harris", "Irwin", "Jones",
    "King", "Lopez", "Miller", "Nelson", "Owens",
    "Patel", "Quinn", "Reed", "Smith", "Turner",
]
FIRST_NAMES = [
    "Alice", "Bob", "Carol", "Dan", "Eve",
    "Frank", "Grace", "Henry", "Iris", "Jack",
    "Kate", "Liam", "Mia", "Noah", "Olivia",
    "Paul", "Quinn", "Rita", "Sam", "Tina",
]

rows: list[Employee] = []
for index, surname in enumerate(SURNAMES):
    number = f"EMP{index + 1:03d}"
    # EMP019 and EMP020 share a hire date, to prove the tiebreaker is stable.
    hire = date(2023, 1, 1) + timedelta(days=30 * min(index, 17))
    rows.append(
        Employee(
            employee_id=number,
            first_name=FIRST_NAMES[index],
            last_name=surname,
            email=(
                "odd@example.test"
                if number == "EMP018"
                else f"{FIRST_NAMES[index].lower()}.{surname.lower()}@example.com"
            ),
            hire_date=hire,
            job_id=(job_a if index % 2 == 0 else job_b).id,
            department_id=(dept_a if index % 3 != 2 else dept_b).id,
            status="Active",
            salary=50000 + index,
        )
    )
db.add_all(rows)
db.commit()

by_number = {row.employee_id: row for row in db.query(Employee).all()}
by_number["EMP003"].status = "On Leave"
by_number["EMP004"].status = "Terminated"
by_number["EMP019"].status = "Rehired"
by_number["EMP002"].manager_id = by_number["EMP001"].id
by_number["EMP003"].manager_id = by_number["EMP001"].id
by_number["EMP005"].manager_id = by_number["EMP001"].id
by_number["EMP004"].manager_id = by_number["EMP002"].id
db.commit()

TOTAL = len(rows)

# --- the accounts -----------------------------------------------------------
ACCOUNTS = {
    "SuperAdmin": ("e16admin", None),
    "HR": ("e16hr", None),
    "Manager": ("e16mgr", by_number["EMP001"].id),
    # EMP002 manages Dan in this fixture, so use a non-managing row: the
    # documented Associate scope is "themselves", and a row with reports
    # would measure the reporting-line walk instead.
    "Associate": ("e16assoc", by_number["EMP006"].id),
    "PayrollViewer": ("e16pay", None),
}
for username, employee_id in ACCOUNTS.values():
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.delete(existing)
db.commit()
for role, (username, employee_id) in ACCOUNTS.items():
    db.add(
        User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            employee_id=employee_id,
            is_active=True,
            mfa_enabled=role in ("SuperAdmin", "HR"),
        )
    )
db.commit()

HEADERS: dict[str, dict] = {}
for role, (username, _) in ACCOUNTS.items():
    response = client.post(LOGIN, json={"username": username, "password": PASSWORD})
    if response.status_code != 200:
        check(f"the {role} account can sign in", False, f"status={response.status_code}")
        continue
    HEADERS[role] = {"Authorization": f"Bearer {response.json()['access_token']}"}
check("one account per role signed in", len(HEADERS) == len(ACCOUNTS), f"got {sorted(HEADERS)}")

ADMIN = HEADERS["SuperAdmin"]
HR = HEADERS["HR"]
MANAGER = HEADERS["Manager"]
ASSOCIATE = HEADERS["Associate"]
PAYROLL = HEADERS["PayrollViewer"]


def get(headers: dict | None = None, **params):
    return client.get(LIST, headers=ADMIN if headers is None else headers, params=params)


def body(response):
    return response.json() if response.status_code == 200 else {}


# ====[ the envelope ]========================================================
print("\n[D040-1] the answer is the contract's envelope")

unauthenticated = client.get(LIST)
check("an unauthenticated read is refused", unauthenticated.status_code == 401,
      f"got {unauthenticated.status_code}")

response = get()
payload = body(response)
check("the list answers 200", response.status_code == 200,
      f"got {response.status_code}: {response.text[:160]}")
check("the answer is an object, not a bare list", isinstance(payload, dict),
      f"got {type(payload).__name__}")
check("the answer has items and meta",
      isinstance(payload.get("items"), list) and isinstance(payload.get("meta"), dict),
      f"got {sorted(payload) if isinstance(payload, dict) else payload!r}")
meta = payload.get("meta") or {}
check("meta carries page, page_size, total and total_pages",
      {"page", "page_size", "total", "total_pages"} <= set(meta),
      f"got {sorted(meta)}")
check("the default page is 1 and the default size 50",
      meta.get("page") == 1 and meta.get("page_size") == 50,
      f"got {meta.get('page')!r} / {meta.get('page_size')!r}")
check("meta.total counts every visible employee", meta.get("total") == TOTAL,
      f"got {meta.get('total')!r} expected {TOTAL}")
check("the default page holds everyone in this fixture",
      len(payload.get("items") or []) == TOTAL,
      f"got {len(payload.get('items') or [])}")

item = (payload.get("items") or [{}])[0]
check("an item carries the stored employee number and foreign keys",
      {"id", "employee_id", "job_id", "department_id", "status"} <= set(item),
      f"got {sorted(item)}")
check("the identity is an integer and the business key a string",
      isinstance(item.get("id"), int) and isinstance(item.get("employee_id"), str),
      f"id={item.get('id')!r} employee_id={item.get('employee_id')!r}")
check("the item does not claim a field the record lacks",
      not ({"employee_number", "location_id", "position_id"} & set(item)),
      f"got {sorted(set(item) & {'employee_number', 'location_id', 'position_id'})}")


# ====[ newest first and paging ]=============================================
print("\n[D040-2] newest hire first, and a page is a page")

numbers = [row["employee_id"] for row in payload["items"]]
check("the default order is newest hire first",
      numbers[0] == "EMP020" and numbers[1] == "EMP019",
      f"first two={numbers[:2]}")
check("the same-day hires keep a stable order (id descending)",
      [row["employee_id"] for row in payload["items"] if row["employee_id"] in ("EMP019", "EMP020")]
      == ["EMP020", "EMP019"],
      str([row["employee_id"] for row in payload["items"]][:4]))

page1 = body(get(page=1, page_size=3))
page2 = body(get(page=2, page_size=3))
check("page_size is honoured", len(page1["items"]) == 3, f"got {len(page1['items'])}")
check("meta reports the window and the page count",
      page1["meta"]["page"] == 1 and page1["meta"]["page_size"] == 3
      and page1["meta"]["total"] == TOTAL
      and page1["meta"]["total_pages"] == (TOTAL + 2) // 3,
      f"got {page1['meta']}")
check("the second page holds different rows",
      set(row["id"] for row in page1["items"]).isdisjoint(
          set(row["id"] for row in page2["items"])
      ),
      f"page1={[r['employee_id'] for r in page1['items']]} page2={[r['employee_id'] for r in page2['items']]}")

last_page_number = page1["meta"]["total_pages"]
last_page = body(get(page=last_page_number, page_size=3))
check("the last page is short, not padded",
      0 < len(last_page["items"]) <= 3 and len(last_page["items"]) < 3,
      f"got {len(last_page['items'])} of {TOTAL} at size 3")

beyond = body(get(page=last_page_number + 1, page_size=3))
check("a page beyond the end is empty, not an error",
      beyond.get("items") == [] and beyond.get("meta", {}).get("total") == TOTAL,
      f"got {beyond}")


# ====[ search ]==============================================================
print("\n[D040-3] search reaches beyond the loaded page")

for term, expected in (
    ("alice", "EMP001"),
    ("EMP003", "EMP003"),
    ("carol", "EMP003"),
    ("anderson", "EMP001"),
    ("alice anderson", "EMP001"),
    ("ALICE.ANDERSON@EXAMPLE.COM", "EMP001"),
    ("odd@example.test", "EMP018"),
):
    found = body(get(search=term, page_size=200))
    ids = [row["employee_id"] for row in found.get("items", [])]
    check(f"search {term!r} finds {expected}", ids == [expected], f"got {ids}")

empty = body(get(search="nobody-matches-this", page_size=200))
check("a search with no match is an empty page with zero total",
      empty.get("items") == [] and empty.get("meta", {}).get("total") == 0
      and empty.get("meta", {}).get("total_pages") == 0,
      f"got {empty.get('meta')}")

# A stored address the input rules refuse must not break the response. The
# row was written directly; the input would reject `@example.test`.
odd = body(get(search="odd@example.test", page_size=200))
check("a stored address the input would refuse is still readable",
      [row["email"] for row in odd.get("items", [])] == ["odd@example.test"],
      str([row.get("email") for row in odd.get("items", [])]))


# ====[ filters ]=============================================================
print("\n[D040-4] department, status and manager filters")

dept_a_rows = body(get(department_id=dept_a.id, page_size=200))["items"]
check("the department filter returns only that department",
      dept_a_rows and all(row["department_id"] == dept_a.id for row in dept_a_rows),
      f"got {sorted({row['department_id'] for row in dept_a_rows})}")
check("the department filter's total is the filtered count",
      body(get(department_id=dept_a.id, page_size=200))["meta"]["total"] == len(dept_a_rows),
      f"got {body(get(department_id=dept_a.id, page_size=200))['meta']['total']} vs {len(dept_a_rows)}")

on_leave = body(get(status="On Leave", page_size=200))
check("the status filter returns the matching employees",
      [row["employee_id"] for row in on_leave["items"]] == ["EMP003"],
      f"got {[row['employee_id'] for row in on_leave['items']]}")
terminated = body(get(status="Terminated", page_size=200))
check("a second status filter is independent",
      [row["employee_id"] for row in terminated["items"]] == ["EMP004"],
      f"got {[row['employee_id'] for row in terminated['items']]}")
rehired = body(get(status="Rehired", page_size=200))
check("the stored `Rehired` value is selectable",
      [row["employee_id"] for row in rehired["items"]] == ["EMP019"],
      f"got {[row['employee_id'] for row in rehired['items']]}")

alice_direct = body(get(manager_id=by_number["EMP001"].id, page_size=200))
check("the manager filter is the direct reporting line",
      {row["employee_id"] for row in alice_direct["items"]} == {"EMP002", "EMP003", "EMP005"},
      f"got {sorted(row['employee_id'] for row in alice_direct['items'])}")

combined = body(get(department_id=dept_a.id, status="Active", page_size=200))
check("filters combine with AND",
      all(row["department_id"] == dept_a.id and row["status"] == "Active"
          for row in combined["items"]),
      f"got {[(r['employee_id'], r['department_id'], r['status']) for r in combined['items']][:4]}")


# ====[ sorting ]=============================================================
print("\n[D040-5] sort and order")

by_last = body(get(sort="last_name", order="asc", page_size=200))["items"]
check("sort by last name ascending", by_last[0]["last_name"] == "Anderson"
      and by_last[-1]["last_name"] == "Turner",
      f"got {by_last[0]['last_name']} … {by_last[-1]['last_name']}")
by_last_desc = body(get(sort="last_name", order="desc", page_size=200))["items"]
check("sort by last name descending", by_last_desc[0]["last_name"] == "Turner"
      and by_last_desc[-1]["last_name"] == "Anderson",
      f"got {by_last_desc[0]['last_name']} … {by_last_desc[-1]['last_name']}")
by_number = body(get(sort="employee_number", order="asc", page_size=200))["items"]
check("sort by the employee number", by_number[0]["employee_id"] == "EMP001"
      and by_number[-1]["employee_id"] == "EMP020",
      f"got {by_number[0]['employee_id']} … {by_number[-1]['employee_id']}")
by_hire = body(get(sort="hire_date", order="asc", page_size=200))["items"]
check("sort by hire date ascending is oldest first", by_hire[0]["employee_id"] == "EMP001",
      f"got {by_hire[0]['employee_id']}")
check("sorting does not change the total",
      body(get(sort="last_name", page_size=200))["meta"]["total"] == TOTAL,
      "")


# ====[ the refusals ]=======================================================
print("\n[D040-6] a window or a value the contract does not define is refused")

for label, params in (
    ("page=0", {"page": 0}),
    ("page_size=0", {"page_size": 0}),
    ("page_size=201", {"page_size": 201}),
    ("status=Suspended", {"status": "Suspended"}),
    ("status=suspended (lowercase is not the stored vocabulary)", {"status": "suspended"}),
    ("sort=bogus", {"sort": "bogus"}),
    ("order=sideways", {"order": "sideways"}),
    ("search of 101 characters", {"search": "x" * 101}),
):
    response = get(**params)
    check(f"{label} answers 422", response.status_code == 422,
          f"got {response.status_code}: {response.text[:140]}")


# ====[ visibility ]=========================================================
print("\n[D040-7] the scope applies to the filter and to the count")

associate = body(get(ASSOCIATE, page_size=200))
check("an Associate sees only themselves",
      {row["employee_id"] for row in associate["items"]} == {"EMP006"},
      f"got {sorted(row['employee_id'] for row in associate['items'])}")
check("the Associate's total is their scope, not the directory",
      associate["meta"]["total"] == 1, f"got {associate['meta']['total']}")

manager = body(get(MANAGER, page_size=200))
check("a Manager sees themselves and their reporting line",
      {row["employee_id"] for row in manager["items"]} ==
      {"EMP001", "EMP002", "EMP003", "EMP004", "EMP005"},
      f"got {sorted(row['employee_id'] for row in manager['items'])}")
check("the Manager's total is their line, not the directory",
      manager["meta"]["total"] == 5, f"got {manager['meta']['total']}")

hr = body(get(HR, page_size=200))
check("HR sees the whole directory", hr["meta"]["total"] == TOTAL,
      f"got {hr['meta']['total']}")
payroll = body(get(PAYROLL, page_size=200))
check("a PayrollViewer sees the whole directory", payroll["meta"]["total"] == TOTAL,
      f"got {payroll['meta']['total']}")

scoped_search = body(get(MANAGER, search="carol", page_size=200))
check("a filter inside a scope cannot reach outside it",
      [row["employee_id"] for row in scoped_search["items"]] == ["EMP003"]
      and scoped_search["meta"]["total"] == 1,
      f"got {[r['employee_id'] for r in scoped_search['items']]} / {scoped_search['meta']['total']}")


# ====[ the Oracle dialect ]=================================================
print("\n[D040-8] the SQL is compiled for the database production uses")

search_sql = str(
    select(Employee).where(search_clause("Alice Anderson")).compile(
        dialect=oracle.dialect()
    )
)
check("the search clause compiles for Oracle", "LIKE" in search_sql.upper(),
      search_sql[:200])
check("the search clause does not use ILIKE", "ILIKE" not in search_sql.upper(),
      search_sql[:200])
check("the full-name match concatenates portably", "||" in search_sql,
      search_sql[:200])

paged = (
    select(Employee)
    .order_by(_SORT_COLUMNS["hire_date"].desc(), Employee.id.desc())
    .offset(0)
    .limit(10)
)
paged_sql = str(paged.compile(dialect=oracle.dialect()))
check("the paged read compiles for Oracle",
      "FETCH FIRST" in paged_sql.upper() or "ROWNUM" in paged_sql.upper(),
      paged_sql[:240])

count_sql = str(
    select(func.count())
    .select_from(select(Employee).where(search_clause("x")).subquery())
    .compile(dialect=oracle.dialect())
)
check("the count subquery compiles for Oracle", "COUNT" in count_sql.upper(),
      count_sql[:200])


# ====[ create keeps its half of the contract ]==============================
print("\n[D040-9] the create body and its duplicate refusal")

created_payload = {
    "employee_id": "EMP-CREATE-1",
    "first_name": "Created",
    "last_name": "Through The Api",
    "email": "created.through.api@example.com",
    "hire_date": "2026-01-05",
    "job_id": job_a.id,
    "department_id": dept_a.id,
    "status": "Active",
}
created = client.post(LIST, headers=HR, json=created_payload)
check("HR can create an employee with the record's shape",
      created.status_code == 201,
      f"got {created.status_code}: {created.text[:160]}")
check("the new employee is in the directory",
      body(get(search="EMP-CREATE-1", page_size=200))["meta"]["total"] == 1,
      str(body(get(search="EMP-CREATE-1", page_size=200))["meta"]))

duplicate = client.post(LIST, headers=HR, json=created_payload)
check("a duplicate employee number is 409 duplicate_natural_key",
      duplicate.status_code == 409
      and (duplicate.json().get("error") or {}).get("code") == "duplicate_natural_key",
      f"got {duplicate.status_code}: {duplicate.text[:160]}")

incomplete = client.post(LIST, headers=HR, json={"first_name": "No Number"})
check("a create missing required fields is 422", incomplete.status_code == 422,
      f"got {incomplete.status_code}: {incomplete.text[:140]}")


# ===========================================================================
print()
print("=" * 68)
print(f"EMPLOYEE DIRECTORY SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
print("=" * 68)
if FAILURES:
    print("\nfailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
    raise SystemExit(1)
