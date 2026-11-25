"""DST helpers slice: fold/gap/boundary/TZ-change + auto-create equality.

Run:  python tests/test_dst_helpers.py        (from backend/)
   or pytest tests/test_dst_helpers.py
"""
import datetime
import os
import sys
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="dst_helpers_suite_"), "dst_helpers_suite.db")
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime as dt, timedelta, timezone  # noqa: E402

UTC = timezone.utc

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.dst import as_utc_for_compare, wall_to_utc  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.scheduling import RosterEntry, RosterVersion  # noqa: E402
from app.models.user import User  # noqa: E402
from app.schemas.scheduling import AutoCreateAttendanceRequest  # noqa: E402
from app.services.scheduling import auto_create_attendance  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
dept = Department(name="DST", code="DST")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="DST", code="DST", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)


def _employee(code: str) -> Employee:
    person = Employee(
        employee_id=code,
        first_name="DST",
        last_name=code,
        email=f"{code}@example.com",
        department_id=dept.id,
        job_id=job.id,
        hire_date=datetime.date(2024, 1, 1),
        status="Active",
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


admin_user = User(
    username="dst-admin",
    email="dst-admin@example.com",
    hashed_password=get_password_hash("DstTestPass123"),
    role="SuperAdmin",
    is_active=True,
    mfa_enabled=True,
)
db.add(admin_user)
db.commit()
db.refresh(admin_user)

_RUNS = {"n": 0}


def _version_with(entries_spec):
    """entries_spec: [(employee, work_date, start, end)]. Returns version."""
    _RUNS["n"] += 1
    base = datetime.date(2027, 5, 4) + timedelta(weeks=_RUNS["n"])
    version = RosterVersion(
        location_code="DST",
        period_start=base,
        period_end=base + timedelta(days=6),
        status="published",
        published_by=admin_user.id,
        published_at=dt.utcnow(),
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    for emp, offset, start, end in entries_spec:
        db.add(RosterEntry(
            employee_id=emp.id,
            work_date=base + timedelta(days=offset),
            start_time=start,
            end_time=end,
            status="Confirmed",
        ))
    db.commit()
    return version, base


def _as_utc(v):
    # SQLite returns naive datetimes; stored values are already UTC
    # wall-equivalents (see spec migration-implications.md §1).
    return v if v.tzinfo is not None else v.replace(tzinfo=UTC)


# --- helper semantics -------------------------------------------------------

def test_fold_first_and_second_occurrence():
    # Europe/Berlin falls back 2026-10-25 03:00 -> 02:00: 02:30 happens twice.
    first = wall_to_utc(dt(2026, 10, 25, 2, 30), "Europe/Berlin", fold=0)
    second = wall_to_utc(dt(2026, 10, 25, 2, 30), "Europe/Berlin", fold=1)
    assert first == dt(2026, 10, 25, 0, 30, tzinfo=UTC), first
    assert second == dt(2026, 10, 25, 1, 30, tzinfo=UTC), second
    assert (second - first) == timedelta(hours=1)


def test_fold_ambiguous_requires_explicit_fold():
    try:
        wall_to_utc(dt(2026, 10, 25, 2, 30), "Europe/Berlin")
    except ValueError:
        pass
    else:
        raise AssertionError("ambiguous wall without fold must raise ValueError")
    try:
        as_utc_for_compare(dt(2026, 10, 25, 2, 30), "Europe/Berlin")
    except ValueError:
        pass
    else:
        raise AssertionError("as_utc_for_compare ambiguous wall must raise ValueError")
    try:
        wall_to_utc(dt(2026, 10, 25, 2, 30), "Europe/Berlin", fold=2)
    except ValueError:
        pass
    else:
        raise AssertionError("fold=2 must raise ValueError")


def test_gap_pushes_forward():
    # Europe/Berlin springs forward 2026-03-29 02:00 -> 03:00: 02:30 never existed.
    got = wall_to_utc(dt(2026, 3, 29, 2, 30), "Europe/Berlin")
    # First valid local time after the gap is 03:00 CEST (+02:00).
    assert got == dt(2026, 3, 29, 1, 0, tzinfo=UTC), got


def test_gap_push_bounded_beyond_3h():
    # A wall time more than 3h before any valid local time must not shift silently.
    import app.core.dst as dst_mod
    real_roundtrip = dst_mod._roundtrip_ok
    dst_mod._roundtrip_ok = lambda *a: False
    try:
        try:
            wall_to_utc(dt(2026, 3, 29, 2, 30), "Europe/Berlin")
        except ValueError:
            pass
        else:
            raise AssertionError("unresolvable gap must raise ValueError")
    finally:
        dst_mod._roundtrip_ok = real_roundtrip


def test_boundary_exact_transition_converts_without_shift():
    # 03:00 on the spring-forward day exists (CEST) and converts exactly.
    got = wall_to_utc(dt(2026, 3, 29, 3, 0), "Europe/Berlin")
    assert got == dt(2026, 3, 29, 1, 0, tzinfo=UTC), got
    # Unambiguous normal day converts exactly.
    assert wall_to_utc(dt(2026, 1, 15, 9, 0), "Europe/Berlin") == dt(2026, 1, 15, 8, 0, tzinfo=UTC)


def test_tz_change_same_wall_different_instant():
    a = wall_to_utc(dt(2026, 1, 15, 9, 0), "UTC")
    b = wall_to_utc(dt(2026, 1, 15, 9, 0), "America/New_York")
    assert b - a == timedelta(hours=5), (a, b)


def test_aware_input_rejected():
    aware = dt(2026, 1, 15, 9, 0, tzinfo=UTC)
    for fn in (wall_to_utc, as_utc_for_compare):
        try:
            fn(aware, "UTC")
        except ValueError:
            pass
        else:
            raise AssertionError(f"{fn.__name__} must reject aware input")


def test_unknown_zone_rejected():
    try:
        wall_to_utc(dt(2026, 1, 15, 9, 0), "Mars/Olympus")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown zone must raise ValueError")


def test_overnight_duration_across_fall_back():
    # 22:00 -> 06:00 next day across the Berlin fall-back is 9 real hours.
    start = as_utc_for_compare(dt(2026, 10, 24, 22, 0), "Europe/Berlin")
    end = as_utc_for_compare(dt(2026, 10, 25, 6, 0), "Europe/Berlin")
    assert (end - start) == timedelta(hours=9), (start, end)


# --- auto-create wiring -----------------------------------------------------

def test_auto_create_defaults_to_utc_legacy_values():
    emp = _employee("DST-E1")
    version, base = _version_with([(emp, 0, "09:00", "17:00")])
    result = auto_create_attendance(db, version.id, admin_user)
    assert result["created_count"] == 1, result
    te = result["entries"][0]
    assert _as_utc(te.clock_in) == dt.combine(base, datetime.time(9, 0, tzinfo=UTC)), te.clock_in
    assert _as_utc(te.clock_out) == dt.combine(base, datetime.time(17, 0, tzinfo=UTC)), te.clock_out


def test_auto_create_tz_shifts_instants():
    emp = _employee("DST-E2")
    version, base = _version_with([(emp, 0, "09:00", "17:00")])
    result = auto_create_attendance(db, version.id, admin_user, tz="Asia/Kolkata")
    assert result["created_count"] == 1, result
    te = result["entries"][0]
    assert _as_utc(te.clock_in) == dt(2026, 1, 1, 0, 0, tzinfo=UTC).replace(
        year=base.year, month=base.month, day=base.day, hour=3, minute=30), te.clock_in
    assert _as_utc(te.clock_out) == dt(2026, 1, 1, 0, 0, tzinfo=UTC).replace(
        year=base.year, month=base.month, day=base.day, hour=11, minute=30), te.clock_out


def test_auto_create_overnight_rolls_past_midnight():
    emp = _employee("DST-E3")
    version, base = _version_with([(emp, 0, "22:00", "06:00")])
    result = auto_create_attendance(db, version.id, admin_user)
    assert result["created_count"] == 1, result
    te = result["entries"][0]
    assert _as_utc(te.clock_in) == dt.combine(base, datetime.time(22, 0, tzinfo=UTC)), te.clock_in
    assert _as_utc(te.clock_out) == dt.combine(base + timedelta(days=1), datetime.time(6, 0, tzinfo=UTC)), te.clock_out
    assert (_as_utc(te.clock_out) - _as_utc(te.clock_in)) == timedelta(hours=8)


def test_auto_create_rejects_unknown_tz():
    emp = _employee("DST-E4")
    version, _ = _version_with([(emp, 0, "09:00", "17:00")])
    try:
        auto_create_attendance(db, version.id, admin_user, tz="Mars/Olympus")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown tz must raise ValueError")


def test_endpoint_request_accepts_optional_tz():
    assert AutoCreateAttendanceRequest().tz is None
    assert AutoCreateAttendanceRequest(tz="Europe/Berlin").tz == "Europe/Berlin"


def test_endpoint_unknown_tz_returns_422():
    # Endpoint-level: an unknown tz must be HTTP 422, a valid tz must pass.
    from fastapi.testclient import TestClient  # noqa: E402

    from app.core.security import create_access_token  # noqa: E402
    from app.main import app  # noqa: E402

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {create_access_token(subject='dst-admin')}"}

    emp_bad = _employee("DST-E5")
    version_bad, _ = _version_with([(emp_bad, 0, "09:00", "17:00")])
    r = client.post(
        f"/api/v1/scheduling/rosters/{version_bad.id}/attendance/auto-create",
        json={"tz": "Mars/Olympus"},
        headers=headers,
    )
    assert r.status_code == 422, (r.status_code, r.text[:500])

    emp_ok = _employee("DST-E6")
    version_ok, _ = _version_with([(emp_ok, 0, "09:00", "17:00")])
    r = client.post(
        f"/api/v1/scheduling/rosters/{version_ok.id}/attendance/auto-create",
        json={"tz": "Europe/Berlin"},
        headers=headers,
    )
    assert r.status_code == 200, (r.status_code, r.text[:500])
    assert r.json()["created_count"] == 1, r.text[:500]


TESTS = [
    test_fold_first_and_second_occurrence,
    test_fold_ambiguous_requires_explicit_fold,
    test_gap_pushes_forward,
    test_gap_push_bounded_beyond_3h,
    test_boundary_exact_transition_converts_without_shift,
    test_tz_change_same_wall_different_instant,
    test_aware_input_rejected,
    test_unknown_zone_rejected,
    test_overnight_duration_across_fall_back,
    test_auto_create_defaults_to_utc_legacy_values,
    test_auto_create_tz_shifts_instants,
    test_auto_create_overnight_rolls_past_midnight,
    test_auto_create_rejects_unknown_tz,
    test_endpoint_request_accepts_optional_tz,
    test_endpoint_unknown_tz_returns_422,
]


if __name__ == "__main__":
    passed, failed = 0, []
    for fn in TESTS:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            failed.append((fn.__name__, str(e)))
            print(f"  FAIL  {fn.__name__}  {e}")
        else:
            passed += 1
            print(f"  PASS  {fn.__name__}")
    print("----------------------------------------------------------------")
    print(f"dst helpers tests: {passed} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)
