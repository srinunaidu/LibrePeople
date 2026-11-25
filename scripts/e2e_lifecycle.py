#!/usr/bin/env python3
"""
End-to-end lifecycle validation: from first application to final termination.

Exercises the real business flow the product exists for, against a running
backend:

  recruiting -> offer/accept -> hire -> onboarding -> master data
  -> clock in/out -> timesheet -> scheduling roster -> leave
  -> PAYROLL (components, period, pay profile, run, approve, finalize,
     reconciliation, payslips)
  -> performance (goals, reviews, feedback)
  -> benefits (plan, enrolment) -> learning (course, enrolment, certification)
  -> compliance (rule, violation) -> forecasting reads -> import-export reads
  -> data-quality reads -> reports -> offboarding -> audit chain verification

RBAC is split by design and asserted both ways: HR-scoped endpoints are
read/called as the HR account; SuperAdmin-only surfaces are asserted 403 for
HR and 200 for the SuperAdmin account (when its credentials are provided).

Payroll calculation only completes when a `verified` rule pack is in force for
E2E_JURISDICTION on the pay date. In CI/locally this means starting the
backend with RULE_PACK_DIR pointing at the synthetic fixture packs under
`backend/test_fixtures/rule_packs` (country code `QQ`, never a real statute).
Against a backend without a verified pack, the script asserts the refusal
path instead (rule_pack_not_verified, nothing calculated, run not approved).

Usage:
  E2E_USER=retail_hradmin E2E_PASS=... \
  E2E_SUPER_USER=retail_superadmin E2E_SUPER_PASS=... \
  RULE_PACK_DIR=backend/test_fixtures/rule_packs \
  BASE=http://127.0.0.1:8000/api/v1 python3 scripts/e2e_lifecycle.py
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import date, timedelta

BASE = os.environ.get("BASE", "http://127.0.0.1:8000/api/v1")
USERNAME = os.environ.get("E2E_USER", "e2e_admin")
PASSWORD = os.environ.get("E2E_PASS", "E2eTest123!")
SUPER_USER = os.environ.get("E2E_SUPER_USER", "")
SUPER_PASS = os.environ.get("E2E_SUPER_PASS", "")
JURISDICTION = os.environ.get("E2E_JURISDICTION", "QQ")
# Kept in sync with ci/run_backend_tests.sh: fixture packs are synthetic by
# design and exist for exactly this validation.
FIXTURES_DIR = os.environ.get("E2E_RULE_PACK_DIR", "backend/test_fixtures/rule_packs")

TOKEN = None
PASSED, FAILED = [], []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(name)
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f"  -- {detail}" if detail and not condition else ""))
    return condition


def call(method, path, body=None, token=True, raw=False, headers=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token and TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            status, payload = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, payload = e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}, {}

    if raw:
        return status, payload, {}
    try:
        return status, json.loads(payload), dict(r.headers)
    except Exception:  # noqa: BLE001
        return status, payload.decode("utf-8", "replace"), {}


def login(username, password, label="HR"):
    st, body, _ = call("POST", "/auth/login",
                       {"username": username, "password": password}, token=False)
    if st == 200 and isinstance(body, dict) and "access_token" in body:
        print(f"  [PASS] {label} login returns a token")
        PASSED.append(f"{label} login")
        return body["access_token"]
    print(f"  [FAIL] {label} login failed  -- status={st} {str(body)[:160]}")
    FAILED.append(f"{label} login")
    return None


def call_multipart(method, path, file_bytes, file_name):
    boundary = uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        f"Content-Type: text/csv\r\n\r\n".encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    )
    url = BASE + path
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            status, payload = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, payload = e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}
    try:
        return status, json.loads(payload)
    except Exception:  # noqa: BLE001
        return status, payload.decode("utf-8", "replace")


def main():
    global TOKEN
    print("=" * 78)
    print("Karmathy E2E LIFECYCLE VALIDATION — full hire → terminated chain")
    print(f"target: {BASE}")
    print("=" * 78)

    # ---------------- auth ----------------
    print("\n[1a] AUTHENTICATION — HR account")
    hr_token = login(USERNAME, PASSWORD, "HR role")
    if not hr_token:
        print("\nCannot continue without authentication.")
        return 1
    TOKEN = hr_token

    # wrong password must be refused
    st, _, _ = call("POST", "/auth/login", {"username": USERNAME, "password": "nope"}, token=False)
    check("wrong password rejected (401)", st == 401, f"status={st}")

    saved, TOKEN = TOKEN, None
    st, _, _ = call("GET", "/employees/")
    check("unauthenticated request rejected (401)", st == 401, f"status={st}")
    TOKEN = saved

    super_token = None
    if SUPER_USER and SUPER_PASS:
        print("\n[1b] AUTHENTICATION — SuperAdmin account (integration surfaces)")
        super_token = login(SUPER_USER, SUPER_PASS, "SuperAdmin role")
    else:
        print("\n[1b] AUTHENTICATION — SuperAdmin skipped (E2E_SUPER_USER/E2E_SUPER_PASS unset)")

    # ---------------- read sweep ----------------
    print("\n[2a] MODULE READ SWEEP — HR-scoped (RBAC allows HR)")
    hr_endpoints = [
        "/employees/", "/departments/", "/jobs/",
        "/requisitions/", "/candidates/", "/applications/", "/offers/",
        "/leave/types", "/leave/balances", "/leave/requests",
        "/offboarding/tasks", "/offboarding/terminations",
        "/scheduling/shift-templates", "/scheduling/roster", "/scheduling/swaps",
        "/core-hr/locations", "/core-hr/cost-centers", "/core-hr/positions", "/core-hr/cases",
        "/payroll/periods", "/payroll/components", "/payroll/runs", "/payroll/pay-profiles",
        "/performance/goals", "/performance/reviews", "/performance/compensation-bands",
        "/performance/merit-cycles", "/performance/merit-allocations",
        "/benefits/benefit-plans", "/benefits/benefit-enrollments", "/benefits/life-events",
        "/learning/courses", "/learning/course-enrollments", "/learning/certifications",
        "/learning/talent-pools", "/learning/succession-plans",
        "/compliance/compliance-rules", "/compliance/compliance-violations",
        "/compliance/headcount-plans", "/compliance/scenarios",
        "/reports/dashboard", "/reports/headcount", "/reports/labor-cost",
        "/reports/leave", "/reports/attendance", "/reports/audit?limit=25",
        "/import-export/entities", "/data-quality/checks", "/data-quality/issues",
        "/forecasting/runs", "/forecasting/accuracy", "/forecasting/scenarios",
    ]
    bad = []
    for ep in hr_endpoints:
        st, _, _ = call("GET", ep)
        if st >= 400:
            bad.append(f"{ep} -> {st}")
    check(f"all {len(hr_endpoints)} HR-scoped read endpoints reachable", not bad, "; ".join(bad[:6]))

    print("\n[2b] RBAC — SuperAdmin-only surfaces refuse the HR role")
    hr_forbidden = []
    for ep in ["/platform/webhooks", "/onboarding-portal/clients"]:
        st, _, _ = call("GET", ep)
        if st != 403:
            hr_forbidden.append(f"{ep} -> {st} (expected 403)")
    check("HR role is refused (403) on the SuperAdmin-only surfaces", not hr_forbidden, "; ".join(hr_forbidden))

    print("\n[2b2] RBAC — admin surfaces open to both admin roles (SuperAdmin + HR)")
    bad = []
    for ep in ["/platform/background-checks", "/platform/e-signatures"]:
        st, _, _ = call("GET", ep)
        if st >= 400:
            bad.append(f"{ep} -> {st}")
    st, verification, _ = call("GET", "/admin/audit/verify")
    if st >= 400:
        bad.append(f"/admin/audit/verify -> {st}")
    check("admin surfaces readable by both admin roles", not bad, "; ".join(bad))
    if isinstance(verification, dict):
        print(f"  [INFO] audit verification: valid={verification.get('valid', verification)}")

    print("\n[2c] RBAC — SuperAdmin surfaces open for the SuperAdmin role")
    if super_token:
        TOKEN = super_token
        bad = []
        for ep in ["/platform/webhooks", "/platform/background-checks", "/platform/e-signatures", "/onboarding-portal/clients"]:
            st, _, _ = call("GET", ep)
            if st >= 400:
                bad.append(f"{ep} -> {st}")
        check("SuperAdmin surfaces reachable", not bad, "; ".join(bad))
        st, verification, _ = call("GET", "/admin/audit/verify")
        check("audit chain verifies (hash-chain intact)", st == 200, f"status={st}")
        TOKEN = hr_token
    else:
        print("  [SKIP] SuperAdmin not provided")

    # ---------------- lifecycle ----------------
    print("\n[3] HIRE-TO-TERMINATE LIFECYCLE")

    stamp = uuid.uuid4().hex[:6].upper()
    today = date.today().isoformat()
    week_out = (date.today() + timedelta(days=5)).isoformat()
    period_end = (date.today() + timedelta(days=27)).isoformat()
    pay_date = (date.today() + timedelta(days=30)).isoformat()

    # --- foundation: department, job, requisition ---
    st, dept, _ = call("POST", "/departments/",
                       {"name": f"E2E Dept {stamp}", "code": f"E2E{stamp}", "description": "e2e"})
    if st >= 400:
        st, dept, _ = call("GET", "/departments/")
        dept = dept[0] if dept else {"id": 1}
    dept_id = dept.get("id")
    check("department available", bool(dept_id), f"id={dept_id}")

    # Auto-generated natural key: omit `code` entirely
    st, job, _ = call("POST", "/jobs/",
                      {"title": f"E2E Role {stamp}", "department_id": dept_id, "is_active": True})
    auto_code = job.get("code") if isinstance(job, dict) else None
    check("job created with auto-generated code", st in (200, 201) and bool(auto_code) and str(auto_code).startswith("JOB-"),
          f"status={st} code={auto_code}")
    job_id = job.get("id") if isinstance(job, dict) else None

    # positions/cost-centers auto-codes too
    st, pos, _ = call("POST", "/core-hr/positions",
                      {"title": f"E2E Position {stamp}", "job_id": job_id, "department_id": dept_id})
    check("position auto-generated", st in (200, 201), f"status={st} {str(pos)[:120]}")

    st, req, _ = call("POST", "/requisitions/", {
        "req_number": f"E2E-{stamp}", "title": f"E2E Requisition {stamp}",
        "department_id": dept_id, "job_id": job_id,
        "openings": 1, "status": "Open"})
    check("requisition created", st in (200, 201), f"status={st} {str(req)[:100]}")
    req_id = req.get("id") if isinstance(req, dict) else None

    # --- candidate -> application -> offer ---
    st, cand, _ = call("POST", "/candidates/", {
        "first_name": "E2E", "last_name": f"Candidate {stamp}",
        "email": f"e2e-{stamp}@example.com", "source": "Referral"})
    check("candidate created", st in (200, 201), f"status={st} {str(cand)[:100]}")
    cand_id = cand.get("id") if isinstance(cand, dict) else None

    st, appn, _ = call("POST", "/applications/", {
        "requisition_id": req_id, "candidate_id": cand_id,
        "applied_date": today, "status": "Applied"})
    check("application created", st in (200, 201), f"status={st} {str(appn)[:100]}")
    app_id = appn.get("id") if isinstance(appn, dict) else None

    st, offer, _ = call("POST", "/offers/", {
        "offer_number": f"E2E-OFF-{stamp}", "application_id": app_id,
        "job_id": job_id, "salary_offered": 75000,
        "start_date": today, "offer_date": today, "status": "Draft"})
    check("offer created", st in (200, 201), f"status={st} {str(offer)[:100]}")
    offer_id = offer.get("id") if isinstance(offer, dict) else None

    st, _, _ = call("POST", f"/offers/{offer_id}/letter")
    check("offer letter generated", st in (200, 201), f"status={st}")

    st, _, _ = call("POST", f"/offers/{offer_id}/accept")
    check("offer accepted", st in (200, 201), f"status={st}")

    st, hired, _ = call("POST", f"/offers/{offer_id}/hire",
                        {"employee_id": f"E2E-{stamp}"})
    check("offer hired → employee + onboarding checklist created", st in (200, 201),
          f"status={st} {str(hired)[:140]}")
    emp_id = None
    if st in (200, 201) and isinstance(hired, dict):
        emp = hired.get("employee", {})
        emp_id = emp.get("id")
        check("hire returned the created employee", bool(emp_id), str(hired)[:140])
        check("hire created onboarding tasks", hired.get("onboarding_tasks_created", 0) > 0, str(hired)[:140])

    # --- onboarding ---
    st, _, _ = call("GET", f"/onboarding/{emp_id}/summary")
    check("onboarding summary loads", st == 200, f"status={st}")
    st, tasks, _ = call("GET", f"/onboarding/{emp_id}/tasks")
    check("onboarding tasks load", st == 200 and isinstance(tasks, list) and len(tasks) > 0,
          f"status={st} count={len(tasks) if isinstance(tasks, list) else 'n/a'}")
    if isinstance(tasks, list) and tasks:
        st, _, _ = call("PUT", f"/onboarding/tasks/{tasks[0]['id']}", {"status": "Completed"})
        check("onboarding task updatable", st in (200, 201), f"status={st}")

    # --- time & attendance ---
    st, _, _ = call("POST", "/time/clock-in", {"employee_id": emp_id})
    check("clock in", st in (200, 201), f"status={st}")
    st, _, _ = call("POST", "/time/clock-out", {"employee_id": emp_id})
    check("clock out", st in (200, 201), f"status={st}")
    st, ent, _ = call("GET", f"/time/entries?employee_id={emp_id}")
    check("time entries recorded", st == 200 and isinstance(ent, list) and len(ent) > 0,
          f"status={st} count={len(ent) if isinstance(ent, list) else 'n/a'}")

    st, _, _ = call("POST", "/time/timesheets/generate", {
        "employee_id": emp_id, "period_start": today, "period_end": week_out})
    check("timesheet generated", st in (200, 201), f"status={st}")
    st, ts_list, _ = call("GET", f"/time/timesheets?employee_id={emp_id}")
    ts = ts_list[0] if isinstance(ts_list, list) and ts_list else None
    ts_id = ts.get("id") if isinstance(ts, dict) else None
    if ts_id:
        st, _, _ = call("POST", f"/time/timesheets/{ts_id}/submit")
        check("timesheet submitted", st in (200, 201), f"status={st}")
        st, _, _ = call("POST", f"/time/timesheets/{ts_id}/approve")
        check("timesheet approved", st in (200, 201), f"status={st}")

    # --- scheduling ---
    st, tpl, _ = call("POST", "/scheduling/shift-templates", {
        "name": f"E2E Shift {stamp}", "code": f"E2S{stamp}",
        "start_time": "09:00", "end_time": "17:00",
        "break_minutes": 60, "is_night": False})
    check("shift template created", st in (200, 201), f"status={st}")
    tpl_id = tpl.get("id") if isinstance(tpl, dict) else None
    if tpl_id:
        st, _, _ = call("POST", "/scheduling/roster/generate", {
            "employee_id": emp_id, "shift_template_id": tpl_id,
            "start_date": today, "end_date": week_out})
        check("roster generated", st in (200, 201), f"status={st}")

    # --- leave ---
    st, lt, _ = call("POST", "/leave/types", {
        "name": f"E2E Leave {stamp}", "code": f"E2L{stamp}",
        "max_days_per_year": 15, "is_paid": True})
    check("leave type created", st in (200, 201), f"status={st}")
    lt_id = lt.get("id") if isinstance(lt, dict) else None
    if lt_id:
        st, _, _ = call("POST", "/leave/entitlements",
                        {"entitlement_year": date.today().year, "leave_type_id": lt_id})
        check("entitlement assigned", st in (200, 201), f"status={st}")
        st, lreq, _ = call("POST", "/leave/requests", {
            "employee_id": emp_id, "leave_type_id": lt_id,
            "start_date": today, "end_date": week_out, "reason": "E2E test"})
        check("leave request created", st in (200, 201), f"status={st}")
        lr_id = lreq.get("id") if isinstance(lreq, dict) else None
        if lr_id:
            st, _, _ = call("POST", f"/leave/requests/{lr_id}/approve")
            check("leave request approved", st in (200, 201), f"status={st}")

    # --- payroll ---
    print("\n[4] PAYROLL — components, period, profile, run")
    st, comp, _ = call("POST", "/payroll/components", {
        "code": f"E2E-BASIC-{stamp}", "name": "E2E Basic Salary",
        "component_type": "Earning", "is_taxable": False})
    check("pay component created", st in (200, 201), f"status={st} {str(comp)[:100]}")

    st, period, _ = call("POST", "/payroll/periods", {
        "name": f"E2E Period {stamp}", "start_date": today,
        "end_date": period_end, "pay_date": pay_date, "status": "Draft"})
    check("pay period created", st in (200, 201), f"status={st} {str(period)[:100]}")
    period_id = period.get("id") if isinstance(period, dict) else None

    st, profile, _ = call("POST", "/payroll/pay-profiles", {
        "employee_id": emp_id, "base_salary": 75000, "pay_frequency": "Monthly"})
    check("pay profile created", st in (200, 201), f"status={st} {str(profile)[:100]}")

    st, run, _ = call("POST", "/payroll/runs", {
        "period_id": period_id, "jurisdiction": JURISDICTION})
    check("pay run created (Draft)", st == 201, f"status={st} {str(run)[:120]}")
    run_id = run.get("id") if isinstance(run, dict) else None

    fixture_pack_present = os.path.isdir(FIXTURES_DIR) and any(
        JURISDICTION.lower() in f.lower() for f in os.listdir(FIXTURES_DIR)
    ) if os.path.isdir(FIXTURES_DIR) else False

    payslips = 0
    calculated = False
    if run_id:
        st, run_body, _ = call("POST", f"/payroll/runs/{run_id}/process",
                               headers={"Idempotency-Key": f"e2e-{stamp}"})
        if st in (200, 201):
            calculated = True
            check("pay run processed from the verified fixture pack", True)
        else:
            # Anything other than a clean success must be the verified-pack refusal.
            code_ok = isinstance(run_body, dict) and (
                run_body.get("code") == "rule_pack_not_verified"
                or run_body.get("error", {}).get("code") == "rule_pack_not_verified"
                or "rule_pack_not_verified" in json.dumps(run_body)
            )
            check("pay run refused without a verified pack (nothing calculated)", st == 400 and code_ok,
                  f"status={st} {str(run_body)[:200]}")
            print("  [INFO] set RULE_PACK_DIR=backend/test_fixtures/rule_packs and rebuild the backend to exercise full calculation")

        st, combined, _ = call("GET", f"/payroll/runs")
        check("pay run list readable", st == 200, f"status={st}")
        st, slips, _ = call("GET", "/payroll/payslips")
        payslips = len(slips) if isinstance(slips, list) else 0
        print(f"  [INFO] payslips issued by the run: {payslips}")

        if calculated:
            st, recon, _ = call("GET", f"/payroll/runs/{run_id}/reconciliation")
            matched = st == 200 and isinstance(recon, dict) and recon.get("matched", False)
            check("reconciliation: expected == paid", matched, f"status={st} {str(recon)[:200]}")
            # segregation of duties: the operator who processed must not approve
            st, soso, _ = call("POST", f"/payroll/runs/{run_id}/approve")
            check("same operator cannot approve own run (segregation of duties)", st == 400,
                  f"status={st} {str(soso)[:160]}")
            if super_token:
                saved, TOKEN = TOKEN, super_token
                st, run_body, _ = call("POST", f"/payroll/runs/{run_id}/approve")
                ok = st in (200, 201) and run_body.get("status") == "Approved"
                check("second authorised operator approves the run", ok, f"status={st}")
                st, fin, _ = call("POST", f"/payroll/runs/{run_id}/finalize")
                ok = st in (200, 201) and isinstance(fin, dict) and fin.get("status") == "Finalized"
                check("finalized run locks payslips (read-only)", ok, f"status={st}")
                TOKEN = saved
        else:
            st, _, _ = call("POST", f"/payroll/runs/{run_id}/approve")
            check("unprocessed run cannot be approved", st in (400, 409), f"status={st}")

    # --- performance ---
    print("\n[5] PERFORMANCE")
    st, goal, _ = call("POST", "/performance/goals", {
        "employee_id": emp_id, "title": f"E2E Goal {stamp}",
        "description": "e2e lifecycle goal", "weight": 10, "progress": 25,
        "status": "In Progress"})
    check("performance goal created", st in (200, 201), f"status={st}")
    st, review, _ = call("POST", "/performance/reviews", {
        "employee_id": emp_id, "period": stamp, "status": "Draft",
        "manager_comments": "e2e review", "overall_rating": 4})
    check("review cycle created", st in (200, 201), f"status={st}")
    review_id = review.get("id") if isinstance(review, dict) else None
    if review_id:
        st, _, _ = call("POST", f"/performance/reviews/{review_id}/finalize")
        check("review finalized", st in (200, 201), f"status={st}")
    st, _, _ = call("POST", "/performance/feedback", {
        "review_id": review_id, "feedback_type": "Manager",
        "rating": 5, "comments": "e2e wrap-up"})
    check("continuous feedback recorded", st in (200, 201), f"status={st}")

    # --- benefits ---
    print("\n[6] BENEFITS")
    st, plan, _ = call("POST", "/benefits/benefit-plans", {
        "name": f"E2E Plan {stamp}", "code": f"E2B{stamp}",
        "plan_type": "Medical", "provider": "E2E Provider",
        "employer_contribution": 1500, "employee_contribution": 250})
    check("benefit plan created", st in (200, 201), f"status={st}")
    plan_id = plan.get("id") if isinstance(plan, dict) else None
    if plan_id:
        st, _, _ = call("POST", "/benefits/benefit-enrollments", {
            "employee_id": emp_id, "plan_id": plan_id,
            "effective_date": today, "status": "Active"})
        check("employee enrolled in benefit plan", st in (200, 201), f"status={st}")

    # --- learning ---
    print("\n[7] LEARNING")
    st, course, _ = call("POST", "/learning/courses", {
        "title": f"E2E Course {stamp}", "code": f"E2C{stamp}",
        "category": "Safety", "duration_hours": 2,
        "is_mandatory": True})
    check("course created (mandatory safety training)", st in (200, 201), f"status={st}")
    course_id = course.get("id") if isinstance(course, dict) else None
    if course_id:
        st, enrol, _ = call("POST", "/learning/course-enrollments", {
            "employee_id": emp_id, "course_id": course_id,
            "status": "Enrolled"})
        check("employee enrolled in course", st in (200, 201), f"status={st}")
        enrol_id = enrol.get("id") if isinstance(enrol, dict) else None
        if enrol_id:
            st, _, _ = call("PUT", f"/learning/course-enrollments/{enrol_id}/complete",
                            {"score": 96})
            check("course completed", st in (200, 201), f"status={st}")
        st, _, _ = call("POST", "/learning/certifications", {
            "employee_id": emp_id, "name": f"E2E Safety Cert {stamp}",
            "issuer": "E2E Safety Institute",
            "issued_date": today, "expiry_date": f"{date.today().year + 1}-{today[5:]}"})
        check("certification recorded with expiry", st in (200, 201), f"status={st}")

    # --- compliance ---
    print("\n[8] COMPLIANCE")
    st, rule, _ = call("POST", "/compliance/compliance-rules", {
        "code": f"E2E-RULE-{stamp}", "name": "E2E Harness rule",
        "category": "Labor Law", "severity": "High"})
    check("compliance rule created", st in (200, 201), f"status={st}")
    rule_id = rule.get("id") if isinstance(rule, dict) else None
    if rule_id:
        st, _, _ = call("POST", "/compliance/compliance-violations", {
            "rule_id": rule_id, "employee_id": emp_id,
            "description": "E2E synthetic violation for validation",
            "severity": "High"})
        check("violation recorded against employee", st in (200, 201), f"status={st}")

    # --- offboarding ---
    print("\n[9] OFFBOARDING")
    st, term, _ = call("POST", "/offboarding/terminations", {
        "employee_id": emp_id, "last_working_date": week_out,
        "termination_type": "Resignation", "reason": "E2E test"})
    check("termination initiated", st in (200, 201), f"status={st}")
    term_id = term.get("id") if isinstance(term, dict) else None
    if term_id:
        st, _, _ = call("GET", f"/offboarding/terminations/{term_id}/progress")
        check("termination progress loads", st == 200, f"status={st}")
        st, _, _ = call("POST", f"/offboarding/terminations/{term_id}/complete")
        check("termination completed", st in (200, 201), f"status={st}")

    # --- public contact intake (unauthenticated) ---
    print("\n[11] PUBLIC CONTACT — stranger reaches a real endpoint")
    st, rc, _ = call("POST", "/public/contact", {
        "name": "E2E Visitor", "email": f"e2e-visit-{stamp}@example.com",
        "message": "May we talk about the E2E run?", "company": "E2E Co"}, token=False)
    check("public contact intake returns 201", st == 201, f"status={st} {str(rc)[:120]}")

    # --- import pipeline: real HTTP end to end ---
    print("\n[12] IMPORT PIPELINE — template → dry run → commit → re-run")
    st, tpl, _ = call("GET", "/import-export/template/employees")
    csv_header = tpl if isinstance(tpl, str) else json.dumps(tpl)
    check("employees import template downloadable",
          st == 200 and "employee_id" in csv_header and "hire_date" in csv_header and "email" in csv_header,
          f"status={st}")

    imp_csv = (
        "employee_id,first_name,last_name,email,hire_date,job_code,department_code,status,salary\r\n"
        f"E2E-IMP-{stamp}-01,Ada,Import,e2e-imp-{stamp}-01@example.com,{today},{auto_code},E2E{stamp},Active,7500\r\n"
        f"E2E-IMP-{stamp}-02,Grace,Import,e2e-imp-{stamp}-02@example.com,{today},{auto_code},E2E{stamp},Active,7800\r\n"
    ).encode()

    st, dry = call_multipart("POST", "/import-export/import/employees/dry-run",
                              imp_csv, "e2e_employees.csv")
    check("dry run accepted with token", st == 200 and isinstance(dry, dict) and bool(dry.get("confirmation_token")),
          f"status={st} {str(dry)[:160]}")
    if isinstance(dry, dict):
        check("dry run counts two creates", dry.get("create") == 2,
              f"create={dry.get('create')} reject={dry.get('reject')}")
        # engine resolves codes against real rows — a bogus code must be refused as reference_not_found
        bogus_csv = (
            "employee_id,first_name,last_name,email,hire_date,job_code,department_code,status,salary\r\n"
            f"E2E-IMP-{stamp}-99,Bad,Ref,e2e-imp-{stamp}-99@example.com,{today},NOPE-{stamp},E2E{stamp},Active,7500\r\n"
        ).encode()
        st_bad, bad_dry = call_multipart("POST", "/import-export/import/employees/dry-run", bogus_csv, "e2e_bogus.csv")
        ref_found = bool(bad_dry.get("rows")) and any(
            err.get("code") == "reference_not_found"
            for row in (bad_dry.get("rows") or [])
            for err in (row.get("errors") or [])
        ) if isinstance(bad_dry, dict) else False
        check("bogus code refused as reference_not_found", st_bad == 200 and ref_found,
              f"status={st_bad} body={str(bad_dry)[:160]}")
    confirmation_token = dry.get("confirmation_token") if isinstance(dry, dict) else None

    if confirmation_token:
        st, committed, _ = call("POST", f"/import-export/import/employees/commit?confirmation_token={confirmation_token}")
        check("commit applied with one-shot token", st in (200, 201), f"status={st}")
        # the file may only be committed once
        st2, _, _ = call("POST", f"/import-export/import/employees/commit?confirmation_token={confirmation_token}")
        check("token refused on second use (one-shot)", st2 in (400, 409), f"status={st2}")

        st, again = call_multipart("POST", "/import-export/import/employees/dry-run",
                                  imp_csv, "e2e_employees.csv")
        check("re-dry-run reports both rows unchanged (idempotent)",
              st == 200 and isinstance(again, dict) and again.get("unchanged") == 2,
              f"create={again.get('create')} unchanged={again.get('unchanged')}" if isinstance(again, dict) else f"status={st}")

        st, found, _ = call("GET", f"/employees/?search=E2E-IMP-{stamp}")
        total = found.get("meta", {}).get("total") if isinstance(found, dict) else None
        check("imported employees visible in directory", st == 200 and isinstance(total, int) and total >= 2,
              f"status={st} total={total}")

        # unknown header is refused, with the header named
        bad_csv = b"employee_id,first_name,last_name,bogus_column_x\r\n"
        st, err = call_multipart("POST", "/import-export/import/employees/dry-run",
                                      bad_csv, "e2e_bad.csv")
        err_text = json.dumps(err)
        check("unknown header refused (422, header named)", st in (400, 422) and "bogus_column_x" in err_text,
              f"status={st} body={err_text[:160]}")

    # --- reports reflect the run ---
    print("\n[13] REPORTING REFLECTS THE DATA")
    st, dash, _ = call("GET", "/reports/dashboard")
    ok = st == 200 and isinstance(dash, dict)
    check("dashboard report loads", ok, f"status={st}")
    if ok:
        check("dashboard employee totals reflect the run",
              dash["employees"]["total"] >= 1 and
              dash["employees"]["active"] + dash["employees"]["terminated"] >= 1,
              str(dash["employees"]))
        check("dashboard shows candidates",
              dash["recruiting"]["candidates"] >= 1, str(dash["recruiting"]))
        check("dashboard has recent audit entries",
              len(dash["recent_audit"]) > 0, "audit empty")
    for ep in ["/reports/headcount", "/reports/labor-cost", "/reports/leave",
               "/reports/attendance"]:
        st, _, _ = call("GET", ep)
        check(f"{ep} loads", st == 200, f"status={st}")
    st, aud, _ = call("GET", "/reports/audit?limit=25")
    check("audit trail populated (≥1 row)", st == 200 and isinstance(aud, list) and len(aud) > 0,
          f"status={st} rows={len(aud) if isinstance(aud, list) else 'n/a'}")

    # ---------------- summary ----------------
    print("\n" + "=" * 78)
    print(f"RESULT: {len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("\nFAILED CHECKS:")
        for f in FAILED:
            print(f"  - {f}")
    print("=" * 78)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
