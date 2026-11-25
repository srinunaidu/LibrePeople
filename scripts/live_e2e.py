#!/usr/bin/env python3
"""End-to-end test of the live Karmathy deployment.

Runs the complete hire-to-termination lifecycle against the deployed API:
recruiting -> onboarding -> time & attendance -> scheduling -> leave ->
offboarding -> reporting.

Usage:
    python3 scripts/live_e2e.py [base_url]
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://karmathy-backend.onrender.com").rstrip("/")
API = f"{BASE}/api/v1"

PASS = 0
FAIL = 0


def check(name: str, ok: bool, extra: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS  {name} {extra}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} {extra}")


def call(method: str, path: str, token: str | None = None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw) if raw else {}
        except Exception:
            return exc.code, {}


def login(username: str, password: str) -> str:
    status, data = call("POST", "/auth/login", body={"username": username, "password": password})
    return data.get("access_token", "") if status == 200 else ""


def main() -> int:
    run = int(time.time()) % 100000
    print(f"Live E2E against {API}  (run #{run})\n")

    # Credentials come from the environment. There is no default and no
    # hard-coded password: a published credential is how the previous
    # deployment was compromised.
    username = os.environ.get("KARMATHY_E2E_USERNAME", "admin")
    password = os.environ.get("KARMATHY_E2E_PASSWORD", "")
    if not password:
        print(
            "KARMATHY_E2E_PASSWORD is not set. Export the credentials for the "
            "account under test; this script has no default password."
        )
        return 1

    token = login(username, password)
    check("admin login", bool(token))
    if not token:
        print("Cannot continue without a token.")
        return 1
    H = token

    # --- fixtures ---------------------------------------------------------- #
    status, dept = call("POST", "/departments/", H, {"name": "E2E Ops", "code": f"E2E{run}"})
    check("create department", status == 201)
    dept_id = dept.get("id")

    status, job = call(
        "POST", "/jobs/", H,
        {"title": "E2E Associate", "code": f"E2EJ{run}", "department_id": dept_id,
         "min_salary": 20000, "max_salary": 50000},
    )
    check("create job", status == 201)
    job_id = job.get("id")

    # --- Phase 2: recruiting ------------------------------------------------ #
    print("\n[Recruiting]")
    status, req_ = call("POST", "/requisitions/", H, {
        "req_number": f"REQ{run}", "title": "E2E Associate", "department_id": dept_id,
        "job_id": job_id, "location": "Hyderabad", "openings": 1, "status": "Open",
    })
    check("create requisition", status == 201)
    req_id = req_.get("id")

    email = f"e2e{run}@example.com"
    status, cand = call("POST", "/candidates/", H, {
        "first_name": "E2E", "last_name": "Candidate", "email": email, "source": "Portal",
    })
    check("create candidate", status == 201)
    cand_id = cand.get("id")

    status, app = call("POST", "/applications/", H, {
        "requisition_id": req_id, "candidate_id": cand_id,
        "applied_date": date.today().isoformat(), "status": "Interview",
    })
    check("create application", status == 201)
    app_id = app.get("id")

    status, offer = call("POST", "/offers/", H, {
        "offer_number": f"OFF{run}", "application_id": app_id, "job_id": job_id,
        "salary_offered": 35000, "start_date": date.today().isoformat(),
        "offer_date": date.today().isoformat(), "status": "Draft",
    })
    check("create offer", status == 201)
    offer_id = offer.get("id")

    status, letter = call("POST", f"/offers/{offer_id}/letter", H)
    check("generate offer letter PDF", status == 200 and letter.get("status") == "Sent",
          letter.get("letter_url", ""))

    status, accepted = call("POST", f"/offers/{offer_id}/accept", H)
    check("accept offer", status == 200 and accepted.get("status") == "Accepted")

    emp_code = f"E2EEMP{run}"
    status, hired = call("POST", f"/offers/{offer_id}/hire", H, {"employee_id": emp_code})
    check("hire -> employee + checklist", status == 201 and hired.get("onboarding_tasks_created", 0) > 0)
    emp_id = hired.get("employee", {}).get("id")

    # --- Phase 2: onboarding ----------------------------------------------- #
    print("\n[Onboarding]")
    status, summary = call("GET", f"/onboarding/{emp_id}/summary", H)
    check("onboarding summary", status == 200 and summary.get("total_tasks", 0) > 0)

    status, tasks = call("GET", f"/onboarding/{emp_id}/tasks", H)
    if tasks:
        call("PUT", f"/onboarding/tasks/{tasks[0]['id']}", H, {"status": "Completed"})
    status, summary2 = call("GET", f"/onboarding/{emp_id}/summary", H)
    check("task completion reflected", summary2.get("completed_tasks", 0) >= 1)

    # --- Phase 3: time & attendance ---------------------------------------- #
    print("\n[Time & Attendance]")
    status, clockin = call("POST", "/time/clock-in", H, {"employee_id": emp_id, "source": "Web"})
    check("clock in", status == 201)
    status, clockout = call("POST", "/time/clock-out", H, {"employee_id": emp_id})
    check("clock out", status == 201)
    status, entries = call("GET", f"/time/entries?employee_id={emp_id}", H)
    check("time entries listed", status == 200 and len(entries) >= 1)

    period_start = date.today().replace(day=1).isoformat()
    period_end = (date.today() + timedelta(days=28)).isoformat()
    status, ts = call("POST", "/time/timesheets/generate", H, {
        "employee_id": emp_id, "period_start": period_start, "period_end": period_end,
    })
    check("generate timesheet", status == 201)
    ts_id = ts.get("id")
    call("POST", f"/time/timesheets/{ts_id}/submit", H)
    status, ts2 = call("POST", f"/time/timesheets/{ts_id}/approve", H)
    check("approve timesheet", status == 200 and ts2.get("status") == "Approved")

    # --- Phase 4: scheduling ------------------------------------------------ #
    print("\n[Scheduling]")
    status, tpl = call("POST", "/scheduling/shift-templates", H, {
        "name": "E2E Day", "code": f"E2ED{run}", "start_time": "09:00",
        "end_time": "17:00", "break_minutes": 60,
    })
    check("create shift template", status == 201)
    tpl_id = tpl.get("id")

    status, roster = call("POST", "/scheduling/roster/generate", H, {
        "employee_id": emp_id, "shift_template_id": tpl_id,
        "start_date": period_start, "end_date": period_end,
    })
    check("generate roster", status == 201 and len(roster) > 0, f"{len(roster)} entries")
    roster_id = roster[0].get("id") if roster else None

    # --- Phase 5: leave ----------------------------------------------------- #
    print("\n[Leave]")
    status, lt = call("POST", "/leave/types", H, {
        "name": "E2E Annual", "code": f"E2EAL{run}", "is_paid": True, "max_days_per_year": 18,
    })
    check("create leave type", status == 201)
    lt_id = lt.get("id")

    status, ent = call("POST", "/leave/entitlements", H, {
        "entitlement_year": date.today().year, "leave_type_id": lt_id,
    })
    check("assign entitlements", status == 201)

    status, bal = call("GET", f"/leave/balances?employee_id={emp_id}", H)
    check("balance created", status == 200 and len(bal) >= 1 and bal[0].get("entitled_days") == 18)

    s = (date.today() + timedelta(days=7)).isoformat()
    e = (date.today() + timedelta(days=9)).isoformat()
    status, leave_req = call("POST", "/leave/requests", H, {
        "employee_id": emp_id, "leave_type_id": lt_id,
        "start_date": s, "end_date": e, "reason": "E2E test",
    })
    check("create leave request", status == 201)
    lr_id = leave_req.get("id")
    status, lr2 = call("POST", f"/leave/requests/{lr_id}/approve", H)
    check("approve leave request", status == 200 and lr2.get("status") == "Approved")

    # --- Phase 6: offboarding ---------------------------------------------- #
    print("\n[Offboarding]")
    status, term = call("POST", "/offboarding/terminations", H, {
        "employee_id": emp_id,
        "last_working_date": (date.today() + timedelta(days=30)).isoformat(),
        "termination_type": "Resignation", "reason": "E2E test",
    })
    check("start termination", status == 201 and len(term.get("items", [])) > 0)
    term_id = term.get("id")

    status, prog = call("GET", f"/offboarding/terminations/{term_id}/progress", H)
    check("termination progress endpoint", status == 200)

    if term.get("items"):
        call("PUT", f"/offboarding/items/{term['items'][0]['id']}", H, {"status": "Completed"})

    status, done = call("POST", f"/offboarding/terminations/{term_id}/complete", H)
    check("complete termination", status == 200 and done.get("status") == "Completed")

    status, emp = call("GET", f"/employees/{emp_id}", H)
    check("employee marked Terminated", emp.get("status") == "Terminated")

    # --- Phase 7: reporting ------------------------------------------------- #
    print("\n[Reporting]")
    for name, path in [
        ("dashboard", "/reports/dashboard"),
        ("headcount", "/reports/headcount"),
        ("leave", "/reports/leave"),
        ("labor-cost", "/reports/labor-cost"),
        ("attendance", "/reports/attendance"),
        ("audit", "/reports/audit?limit=50"),
    ]:
        status, data = call("GET", path, H)
        ok = status == 200 and data is not None
        check(f"report {name}", ok)

    status, dash = call("GET", "/reports/dashboard", H)
    check("dashboard shows terminated employee",
          dash.get("employees", {}).get("terminated", 0) >= 1)

    # --- RBAC --------------------------------------------------------------- #
    print("\n[RBAC]")
    user = f"e2euser{run}"
    pw = "E2eUserPass123"
    other = login(user, pw)
    if not other:
        # Self-service registration is disabled on purpose. Provision the
        # Associate through the admin-only endpoint instead.
        status, reg = call("POST", "/auth/register", body={
            "username": user, "email": f"{user}@example.com",
            "password": pw, "role": "Associate",
        })
        check("public self-registration is disabled", status == 403)
        status, reg = call("POST", "/auth/users", token, {"user_in": {
            "username": user, "email": f"{user}@example.com",
            "password": pw, "role": "Associate",
        }})
        check("admin provisions associate", status == 201, f"status={status} {str(reg)[:120]}")
        other = login(user, pw)
        check("associate can log in", bool(other))

    status, _ = call("POST", "/departments/", other, {"name": "Nope", "code": f"NO{run}"})
    check("associate cannot create department", status == 403)

    status, _ = call("POST", "/auth/users", other, {"user_in": {
        "username": f"esc{run}", "email": f"esc{run}@example.com",
        "password": "Escalated123", "role": "SuperAdmin",
    }})
    check("associate cannot provision privileged users", status == 403)

    print(f"\n==== LIVE E2E: {PASS} passed, {FAIL} failed ====")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
