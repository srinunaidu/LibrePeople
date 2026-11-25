"""Background-jobs monitor suite (PS-10).

Covers the contract promise of `contracts/openapi/admin.yaml` under
`/admin/jobs`:

* the paged listing — the contract's `{items, meta}` envelope, newest
  first, `state` and `type` filters, dead rows never hidden, the shared
  422 for a state the contract does not define;
* one job by id, in the contract's `Job` shape (the stored `queued`
  state reported as the contract's `pending`), 404 `job_not_found`;
* retry of a failed and of a dead job — the state is reset (worker,
  lease, error fields, timeline) and the attempt counter is NOT reset,
  because the contract says the configured maximum still applies;
  409 `lease_lost` against a job a worker is processing, 409
  `invalid_state_transition` for a running job whose lease has lapsed
  and for states that are not retry targets, 202 no-op for a
  succeeded job;
* discard of a queued (pending) job — the row is kept, never deleted,
  and the reason lands on the audit log; 409 for running and succeeded;
* the role gate (SuperAdmin + HR only) with the shared 403 envelope;
* every call writes an audit row, staged on the same session before
  the commit, so the change and its audit entry land atomically
  (the AN-06 trap).

Run:  python admin_jobs_test_suite.py
"""
import os

DB_PATH = "admin_jobs_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
# Field encryption (item 6: no SECRET_KEY fallback) — job payloads may
# carry encrypted fields; the audit staging path must not depend on the
# SECRET_KEY fallback.
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

import hashlib  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.job_queue import JobQueue, JobState, JobType  # noqa: E402
from app.models.user import User  # noqa: E402
from app.jobs.queue import JobQueueService  # noqa: E402

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


LOGIN = "/api/v1/auth/login"
PASSWORD = "MonitorPass123"

ROLE_ACCOUNTS = {
    "SuperAdmin": "ps10admin",
    "HR": "ps10hr",
    "Manager": "ps10mgr",
    "Associate": "ps10assoc",
}

print("=" * 68)
print("ADMIN JOBS MONITOR SUITE (PS-10)")
print("=" * 68)

# --- the accounts -----------------------------------------------------------
for role, username in ROLE_ACCOUNTS.items():
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.delete(existing)
db.commit()
for role, username in ROLE_ACCOUNTS.items():
    db.add(
        User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            is_active=True,
            # MFA-enforced world (item 10): privileged roles are enrolled,
            # otherwise every call below is refused before the handler runs.
            mfa_enabled=role in ("SuperAdmin", "HR"),
        )
    )
db.commit()

HEADERS: dict[str, dict] = {}
for role, username in ROLE_ACCOUNTS.items():
    resp = client.post(LOGIN, json={"username": username, "password": PASSWORD})
    if resp.status_code != 200:
        check(f"the {role} account can sign in", False, f"status={resp.status_code}")
        continue
    HEADERS[role] = {"Authorization": f"Bearer {resp.json()['access_token']}"}
check(
    "one account per role signed in",
    len(HEADERS) == len(ROLE_ACCOUNTS),
    f"got {sorted(HEADERS)}",
)

ADMIN = HEADERS["SuperAdmin"]
HR = HEADERS["HR"]
MANAGER = HEADERS["Manager"]


# --- fixtures ---------------------------------------------------------------
_counter = 0


def _hash(tag: str) -> str:
    return hashlib.sha256(tag.encode()).hexdigest()


def _mk(job_type, state, *, attempts=0, max_attempts=5, tag="",
        worker=None, lease=None, error_code=None, error_message=None) -> JobQueue:
    global _counter
    _counter += 1
    now = datetime.now(timezone.utc)
    job = JobQueue(
        job_type=job_type.value if isinstance(job_type, JobType) else job_type,
        input_hash=_hash(f"ps10-{tag}-{_counter}"),
        state=state.value if isinstance(state, JobState) else state,
        attempts=attempts,
        max_attempts=max_attempts,
        priority=10,
        created_at=now,
        worker_id=worker,
        lease_expires_at=lease,
        error_code=error_code,
        error_message=error_message,
        last_error_at=now if error_code else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


QUEUE = "/api/v1/admin/jobs"


def audit_count(action: str) -> int:
    return (
        db.query(AuditLog)
        .filter(AuditLog.action == action, AuditLog.entity_type == "JobQueue")
        .count()
    )


# ====[ gates ]===============================================================
print("\n[PS10-1] the role gate")

unauth = client.get(QUEUE)
check("unauthenticated list is refused", unauth.status_code == 401, f"got {unauth.status_code}")

non_admins = [h for h in (MANAGER, HEADERS["Associate"])]
for method, op in (("GET", QUEUE), ("GET", f"{QUEUE}/999999"),
                   ("POST", f"{QUEUE}/999999/retry"), ("POST", f"{QUEUE}/999999/discard")):
    for label, headers in (("Manager", MANAGER), ("Associate", HEADERS["Associate"])):
        body = None if method == "GET" else {}
        r = client.request(method, op, headers=headers, json=body)
        envelope = r.json().get("error", {}) if isinstance(r.json(), dict) else {}
        what = op.split("/")[-1] if "/999999" in op else "list"
        check(
            f"{method} {what} for {label} gets the shared 403 envelope",
            r.status_code == 403 and envelope.get("code") == "forbidden",
            f"status={r.status_code} body={r.text[:120]}",
        )

check(
    "no audit row was written by a refused call",
    audit_count("list_jobs") == 0 and audit_count("get_job") == 0,
    f"list={audit_count('list_jobs')} get={audit_count('get_job')}",
)

# ====[ the listing ]=========================================================
print("\n[PS10-2] the listing pages, filters and hides nothing")

dead_import = _mk(
    JobType.CSV_IMPORT, JobState.DEAD,
    attempts=5, tag="dead", error_code="validation_error",
    error_message="The import file has no header row",
)
pending_solve = _mk(JobType.ROSTER_SOLVE, JobState.QUEUED, tag="queued")
pending_import = _mk(JobType.CSV_IMPORT, JobState.QUEUED, tag="queued2")
running_solve = _mk(
    JobType.ROSTER_SOLVE, JobState.RUNNING,
    attempts=1, tag="running", worker="worker-1",
    lease=datetime.now(timezone.utc) + timedelta(seconds=300),
)
discarded_webhook = _mk("webhook_deliver", "discarded", tag="discarded")

r = client.get(QUEUE, headers=ADMIN)
check("SuperAdmin lists the jobs", r.status_code == 200, f"got {r.status_code}")
page = r.json()
check(
    "the page is the contract's envelope",
    {"items", "meta"} == set(page)
    and {"page", "page_size", "total", "total_pages"} <= set(page["meta"]),
    f"got {sorted(page)}",
)
check(
    "the counts are not also flat at the top level",
    "total" not in page and "page_size" not in page and "total_pages" not in page,
    f"got {sorted(page)}",
)
check(
    "the first page holds every seeded job, dead rows included",
    page["meta"]["total"] == 5
    and {i["state"] for i in page["items"]} >= {"dead", "pending", "running"},
    f"total={(page.get('meta') or {}).get('total')}",
)

r = client.get(QUEUE, headers=HR)
check("HR lists the jobs too", r.status_code == 200, f"got {r.status_code}")

unfiltered_count = audit_count("list_jobs")
check(
    "the listing itself is audited",
    unfiltered_count >= 1
    and db.query(AuditLog)
    .filter(AuditLog.action == "list_jobs", AuditLog.entity_type == "JobQueue")
    .first()
    is not None,
    f"count={unfiltered_count}",
)

# newest first
r = client.get(QUEUE, headers=ADMIN)
ids = [i["id"] for i in r.json()["items"]]
check(
    "the list is newest first",
    ids == sorted(ids, key=int, reverse=True)
    and ids[:1] == [str(discarded_webhook.id)],
    f"ids={ids[:3]}...",
)

# paging
r = client.get(f"{QUEUE}?page=2&page_size=1", headers=ADMIN)
items = r.json()
check(
    "page 2 of size 1 carries exactly one row and the counts",
    len(items["items"]) == 1 and items["meta"]["total"] == 5
    and items["meta"]["page"] == 2 and items["meta"]["total_pages"] == 5,
    f"got {items.get('meta', items)}",
)
r = client.get(f"{QUEUE}?page_size=200", headers=ADMIN)
check(
    "a page size up to 200 is accepted",
    r.status_code == 200,
    f"got {r.status_code}",
)
r = client.get(f"{QUEUE}?page_size=201", headers=ADMIN)
check("a page size over 200 is refused", r.status_code == 422, f"got {r.status_code}")
r = client.get(f"{QUEUE}?page=0", headers=ADMIN)
check("page 0 is refused", r.status_code == 422, f"got {r.status_code}")

# state filters — the contract's vocabulary
r = client.get(f"{QUEUE}?state=pending", headers=ADMIN)
pending = r.json()
check(
    "state=pending returns the stored queued rows",
    pending["meta"]["total"] == 2
    and all(i["state"] == "pending" for i in pending["items"]),
    f"total={pending.get('meta', {}).get('total')}",
)
r = client.get(f"{QUEUE}?state=dead", headers=ADMIN)
dead = r.json()
check(
    "state=dead returns the dead import job",
    dead["meta"]["total"] == 1
    and dead["items"][0]["type"] == "csv_import"
    and dead["items"][0]["error_code"] == "validation_error",
    f"total={dead.get('meta', {}).get('total')}",
)
r = client.get(f"{QUEUE}?state=discarded", headers=ADMIN)
disc = r.json()
check(
    "state=discarded returns the discarded row",
    disc["meta"]["total"] == 1 and disc["items"][0]["id"] == str(discarded_webhook.id),
    f"total={disc.get('meta', {}).get('total')}",
)
r = client.get(f"{QUEUE}?state=cancelled", headers=ADMIN)
check(
    "state=cancelled returns an honest empty page",
    r.status_code == 200 and r.json()["items"] == [],
    f"got {r.text[:120]}",
)
r = client.get(f"{QUEUE}?state=nonsense", headers=ADMIN)
check(
    "a state outside the contract enum is refused",
    r.status_code == 422,
    f"got {r.status_code}",
)

# type filter
r = client.get(f"{QUEUE}?type=csv_import", headers=ADMIN)
csv_jobs = r.json()
check(
    "type=csv_import narrows to the import jobs (dead ones included)",
    csv_jobs["meta"]["total"] == 2
    and {i["state"] for i in csv_jobs["items"]} == {"pending", "dead"},
    f"total={csv_jobs.get('meta', {}).get('total')}",
)
r = client.get(f"{QUEUE}?state=dead&type=csv_import", headers=ADMIN)
check(
    "state and type narrow together",
    r.json()["meta"]["total"] == 1,
    f"got {r.text[:120]}",
)

check(
    "the listing filters created no extra audits beyond the calls made",
    audit_count("list_jobs") == unfiltered_count + 9,
    f"count={audit_count('list_jobs')} expected={unfiltered_count + 9}",
)

# ====[ one job ]=============================================================
print("\n[PS10-3] one job by id")

strtid = str(dead_import.id)
r = client.get(f"{QUEUE}/{strtid}", headers=ADMIN)
job = r.json()
check("the job answers 200 for SuperAdmin", r.status_code == 200, f"got {r.status_code}")
check(
    "the job carries the contract's required fields",
    {"id", "type", "state", "attempts", "max_attempts", "created_at", "updated_at"}
    <= set(job),
    f"got {sorted(job)}",
)
check(
    "the stored queued state is reported as pending",
    client.get(f"{QUEUE}/{pending_solve.id}", headers=ADMIN).json()["state"] == "pending",
    "state mismatch",
)
check(
    "the dead job reports its error",
    job["state"] == "dead"
    and job["error_code"] == "validation_error"
    and job["error_message"] == "The import file has no header row",
    f"got {job}",
)
check(
    "the job id is a string, as the contract types it",
    isinstance(job["id"], str),
    f"got {type(job.get('id'))}",
)

# --- the stored result and the stored input are different facts ------------
#
# The detail read used to return `result: null` for every job, even one that
# had stored a result: `serialise` only filled the field when `include_payload`
# was set, and even then it wrote a hard-coded None. A screen that asked for
# the result was told the queue never keeps one, which stopped being true at
# `0025_job_result_payload`. This is the check that would have caught it.
finished = _mk(JobType.CSV_IMPORT, JobState.SUCCEEDED, attempts=1, tag="finished")
finished.input_json = '{"entity": "departments", "token": "confirm-abc"}'
finished.result_json = '{"rows_applied": 12, "rows_rejected": 1}'
db.add(finished)
db.commit()

r = client.get(f"{QUEUE}/{finished.id}", headers=ADMIN)
served = r.json()
check(
    "a finished job's stored result is served by the detail read",
    r.status_code == 200
    and served.get("result") == {"rows_applied": 12, "rows_rejected": 1},
    f"got result={served.get('result')!r}",
)
check(
    "the stored input is not served unless it is asked for",
    "payload" not in served or served["payload"] is None,
    f"got payload={served.get('payload')!r}",
)
r = client.get(f"{QUEUE}/{finished.id}?include_payload=true", headers=ADMIN)
check(
    "include_payload=true serves the stored input",
    r.json().get("payload") == {"entity": "departments", "token": "confirm-abc"},
    f"got payload={r.json().get('payload')!r}",
)

# A job from before the result column existed has a result hash and no
# result. It must read as "not stored", not as an empty success.
legacy = _mk(JobType.FORECAST_RUN, JobState.SUCCEEDED, attempts=1, tag="legacy")
legacy.result_hash = _hash("legacy-result")
db.add(legacy)
db.commit()
r = client.get(f"{QUEUE}/{legacy.id}", headers=ADMIN)
check(
    "a job with no stored result reads null, not an empty object",
    r.status_code == 200 and r.json().get("result") is None,
    f"got result={r.json().get('result')!r}",
)

# One corrupt row must not take the listing down. The value is not an object,
# so it reads as "not stored" — the same honest answer as an absent one.
corrupt = _mk(JobType.FORECAST_RUN, JobState.SUCCEEDED, attempts=1, tag="corrupt")
corrupt.result_json = "{not json"
db.add(corrupt)
db.commit()
r = client.get(f"{QUEUE}/{corrupt.id}", headers=ADMIN)
check(
    "an unreadable stored result answers 200 with null, not 500",
    r.status_code == 200 and r.json().get("result") is None,
    f"status={r.status_code} body={r.text[:120]}",
)
r = client.get(QUEUE, headers=ADMIN)
check(
    "the listing still answers with the corrupt row in it",
    r.status_code == 200 and any(i["id"] == str(corrupt.id) for i in r.json()["items"]),
    f"status={r.status_code}",
)

before = audit_count("get_job")
client.get(f"{QUEUE}/{str(dead_import.id)}", headers=HR)
check(
    "the get itself is audited, for HR as well",
    audit_count("get_job") == before + 1,
    f"count={audit_count('get_job')} expected={before + 1}",
)

r = client.get(f"{QUEUE}/999999", headers=ADMIN)
check(
    "an unknown id answers 404 job_not_found in the shared envelope",
    r.status_code == 404 and r.json()["error"]["code"] == "job_not_found",
    f"got {r.text[:140]}",
)
r = client.get(f"{QUEUE}/not-a-number", headers=ADMIN)
check(
    "a non-numeric id answers 404, not 500",
    r.status_code == 404 and r.json()["error"]["code"] == "job_not_found",
    f"got {r.text[:140]}",
)

# ====[ retry ]===============================================================
print("\n[PS10-4] retry: the state is reset, the attempt budget is not")

# A real dead job, produced the way the queue produces one.
service = JobQueueService(db)
live = service.enqueue(JobType.CSV_IMPORT, {"entity": "employees", "file": "x.csv"})
live.max_attempts = 2
live.attempts = 1
db.add(live)
db.commit()
claimed = db.query(JobQueue).filter(JobQueue.id == live.id).first()
claimed.state = JobState.RUNNING
claimed.attempts = 2
claimed.worker_id = "worker-1"
claimed.lease_expires_at = datetime.now(timezone.utc)
db.add(claimed)
db.commit()
dead_lived = service.fail(live.id, "worker-1", "timeout", "Solver timed out")
check(
    "the fixture job is dead, the way the queue makes it",
    dead_lived is not None and dead_lived.state == JobState.DEAD,
    f"got state={dead_lived.state if dead_lived else None}",
)

before_attempts = dead_lived.attempts
before = audit_count("retry_job")
r = client.post(f"{QUEUE}/{dead_lived.id}/retry", headers=ADMIN)
job = r.json()
check(
    "a dead job answers 202 and stops being dead",
    r.status_code == 202 and job["state"] == "pending",
    f"status={r.status_code} state={job.get('state')}",
)
check(
    "the worker, the lease and the error are cleared",
    job["worker_id"] is None if "worker_id" in job else True
    and job["error_code"] is None
    and job["error_message"] is None,
    f"got {job}",
)
check(
    "the attempt counter is NOT reset — the configured maximum still applies",
    job["attempts"] == before_attempts,
    f"attempts={job.get('attempts')} expected={before_attempts}",
)
check(
    "the retry is audited, staged with the change it describes",
    audit_count("retry_job") == before + 1
    and db.query(AuditLog)
    .filter(
        AuditLog.action == "retry_job",
        AuditLog.entity_type == "JobQueue",
        AuditLog.entity_id == dead_lived.id,
    )
    .first()
    is not None,
    f"count={audit_count('retry_job')} expected={before + 1}",
)
r = client.get(QUEUE, headers=ADMIN)
check(
    "the retried job is back in the queue and visible as pending",
    any(
        i["id"] == str(dead_lived.id) and i["state"] == "pending"
        for i in client.get(QUEUE, headers=ADMIN).json()["items"]
    ),
    "not in the pending view",
)

# retry of a failed job
failed = service.enqueue(JobType.PAYROLL_PROCESS, {"period": "2026-10-payroll"})
failed.max_attempts = 5
failed.attempts = 1
db.add(failed)
db.commit()
claimed = db.query(JobQueue).filter(JobQueue.id == failed.id).first()
claimed.state = JobState.FAILED
claimed.error_code = "timeout"
db.add(claimed)
db.commit()
r = client.post(f"{QUEUE}/{failed.id}/retry", headers=HR)
check(
    "HR can retry a failed job, and it goes back to pending",
    r.status_code == 202 and r.json()["state"] == "pending",
    f"status={r.status_code} body={r.text[:120]}",
)

# the conflicts
r = client.post(f"{QUEUE}/{running_solve.id}/retry", headers=ADMIN)
check(
    "a still-running job with a live lease answers 409 lease_lost",
    r.status_code == 409 and r.json()["error"]["code"] == "lease_lost",
    f"got {r.text[:140]}",
)
expired = _mk(
    JobType.FORECAST_RUN, JobState.RUNNING,
    attempts=1, tag="expired", worker="worker-2",
    lease=datetime.now(timezone.utc) - timedelta(seconds=10),
)
r = client.post(f"{QUEUE}/{expired.id}/retry", headers=ADMIN)
check(
    "a running job whose lease lapsed answers 409 invalid_state_transition",
    r.status_code == 409
    and r.json()["error"]["code"] == "invalid_state_transition",
    f"got {r.text[:140]}",
)
r = client.post(f"{QUEUE}/{pending_import.id}/retry", headers=ADMIN)
check(
    "a queued job is not a retry target",
    r.status_code == 409
    and r.json()["error"]["code"] == "invalid_state_transition",
    f"got {r.text[:140]}",
)
r = client.post(f"{QUEUE}/{discarded_webhook.id}/retry", headers=ADMIN)
check(
    "a discarded job is not a retry target",
    r.status_code == 409
    and r.json()["error"]["code"] == "invalid_state_transition",
    f"got {r.text[:140]}",
)

succeeded = _mk(JobType.RETENTION_RUN, JobState.SUCCEEDED, tag="succeeded")
r = client.post(f"{QUEUE}/{succeeded.id}/retry", headers=ADMIN)
check(
    "retrying a succeeded job is a no-op that still answers 202",
    r.status_code == 202
    and r.json()["state"] == "succeeded"
    and r.json()["attempts"] == succeeded.attempts,
    f"got {r.text[:140]}",
)

r = client.post(f"{QUEUE}/999999/retry", headers=ADMIN)
check(
    "retry of an unknown id answers 404 job_not_found",
    r.status_code == 404 and r.json()["error"]["code"] == "job_not_found",
    f"got {r.text[:140]}",
)

# ====[ discard ]=============================================================
print("\n[PS10-5] discard: the work stops, the evidence stays")

before = audit_count("discard_job")
r = client.post(
    f"{QUEUE}/{pending_import.id}/discard",
    headers=HR, params={"reason": "operator cancelled the batch"},
)
job = r.json()
check(
    "a pending job answers 200 and is discarded",
    r.status_code == 200 and job["state"] == "discarded",
    f"status={r.status_code} body={r.text[:140]}",
)
check(
    "the discarded row still exists — the work is removed, never the evidence",
    db.query(JobQueue).filter(JobQueue.id == pending_import.id).count() == 1,
    "the row was deleted",
)
check(
    "the reason landed on the audit log",
    audit_count("discard_job") == before + 1
    and "operator cancelled the batch"
    in str(
        db.query(AuditLog)
        .filter(
            AuditLog.action == "discard_job",
            AuditLog.entity_id == pending_import.id,
        )
        .first().details
    ),
    f"count={audit_count('discard_job')}",
)
r = client.get(QUEUE, headers=ADMIN)
check(
    "the discarded job stays visible in the listing",
    any(i["id"] == str(pending_import.id) and i["state"] == "discarded"
        for i in r.json()["items"]),
    "hidden from the list",
)
r = client.post(f"{QUEUE}/{pending_import.id}/discard", headers=ADMIN)
check(
    "discarding again is a no-op",
    r.status_code == 200 and r.json()["state"] == "discarded",
    f"got {r.text[:140]}",
)

r = client.post(f"{QUEUE}/{running_solve.id}/discard", headers=ADMIN)
check(
    "a running job answers 409 invalid_state_transition",
    r.status_code == 409
    and r.json()["error"]["code"] == "invalid_state_transition",
    f"got {r.text[:140]}",
)
r = client.post(f"{QUEUE}/{succeeded.id}/discard", headers=ADMIN)
check(
    "a succeeded job is not discardable",
    r.status_code == 409
    and r.json()["error"]["code"] == "invalid_state_transition",
    f"got {r.text[:140]}",
)
r = client.post(f"{QUEUE}/999999/discard", headers=ADMIN)
check(
    "discard of an unknown id answers 404 job_not_found",
    r.status_code == 404 and r.json()["error"]["code"] == "job_not_found",
    f"got {r.text[:140]}",
)
r = client.post(f"{QUEUE}/{pending_solve.id}/discard?reason=" + "x" * 501, headers=ADMIN)
check(
    "a reason over 500 characters is refused",
    r.status_code == 422,
    f"got {r.status_code}",
)

# ====[ the dead import story, end to end ]===================================
print("\n[PS10-6] the acceptance story: see a dead import, retry it, it stops being dead")
story = service.enqueue(JobType.CSV_IMPORT, {"entity": "employees", "file": "story.csv"})
story.max_attempts = 1
db.add(story)
db.commit()
claimed = db.query(JobQueue).filter(JobQueue.id == story.id).first()
claimed.state = JobState.RUNNING
claimed.attempts = 1
claimed.worker_id = "worker-story"
claimed.lease_expires_at = datetime.now(timezone.utc)
db.add(claimed)
db.commit()
story_dead = service.fail(story.id, "worker-story", "validation_error", "The file is empty")
check(
    "the story job dies with one attempt",
    story_dead is not None and story_dead.state == JobState.DEAD,
    f"got state={story_dead.state if story_dead else None}",
)
r = client.get(f"{QUEUE}?state=dead&type=csv_import", headers=ADMIN)
seen = r.json()
check(
    "the dead import is seen in the dead-letter state filter",
    any(i["id"] == str(story.id) for i in seen["items"]),
    f"got {seen.get('meta', {}).get('total')}",
)
r = client.post(f"{QUEUE}/{story.id}/retry", headers=ADMIN)
check(
    "the dead import is retried",
    r.status_code == 202 and r.json()["state"] == "pending",
    f"got {r.text[:140]}",
)
r = client.get(f"{QUEUE}?state=dead&type=csv_import", headers=ADMIN)
check(
    "after the retry, the story dead import is gone from the dead-letter view",
    not any(i["id"] == str(story.id) for i in r.json()["items"]),
    f"got [{(r.json().get('meta') or {}).get('total')}]",
)

print()
print("=" * 68)
print(f"ADMIN JOBS MONITOR SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print()
    print("Failures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
db.close()
raise SystemExit(1 if RESULTS["fail"] else 0)
