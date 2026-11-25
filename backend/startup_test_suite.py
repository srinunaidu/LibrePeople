"""Application startup and lifespan suite.

The application runs startup work — most importantly the schema migration —
inside FastAPI's startup event. A failure there stops the process from
serving, which in a container means the deploy fails with an unhelpful
"the health check never passed" message.

This suite exercises the **lifespan**, not just the routes. That distinction
matters: constructing a ``TestClient`` without a ``with`` block does not run
startup events at all, so an import error or a bad migration call in the
startup path can pass every other suite and still take the service down.

It also checks the things a deploy depends on:
  * the application starts and the health probe answers;
  * the schema migration runs, and is idempotent;
  * the database health probe reports the migration state;
  * a misconfigured application refuses to start rather than starting
    weakened.

Run:  python startup_test_suite.py
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault(
    "SECRET_KEY", "local-test-secret-key-not-for-production-0123456789"
)
os.environ.setdefault("BACKEND_CORS_ORIGINS", "")
os.environ.setdefault("LOG_LEVEL", "CRITICAL")
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
# The lifespan seed is fail-closed: it must create no users unless the
# ADMIN_INITIAL_* bootstrap variables are present. Pop them here so the
# lifespan leg of this suite always exercises the no-env path even when a
# developer's shell exports them; the env-seed leg below sets them
# explicitly per case and restores the originals afterwards.
_SAVED_BOOTSTRAP_ENV = {
    key: os.environ.pop(key, None)
    for key in (
        "ADMIN_INITIAL_USERNAME",
        "ADMIN_INITIAL_EMAIL",
        "ADMIN_INITIAL_PASSWORD",
    )
}

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


def _fresh_db() -> str:
    workdir = tempfile.mkdtemp(prefix="karmathy-startup-")
    return os.path.join(workdir, "startup.db")


def _tables(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()


def _run_seed_cases() -> None:
    """Fail-closed + env-seed cases for the startup bootstrap seed.

    Exercises ``app.main.seed_initial_admin`` — the same function the
    startup event calls — against throwaway SQLite databases, so each case
    is synchronous and deterministic:

    * no ``ADMIN_INITIAL_PASSWORD`` → ``skipped-no-env``, zero users;
    * env-supplied strong password → exactly one ``SuperAdmin`` in a
      ``must_change_password`` state, and a second call is a no-op
      (idempotent);
    * a password that fails the policy → ``rejected-policy``, zero users;
    * a database that already holds a user → ``already-exists``, untouched.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.database import Base
    from app.main import seed_initial_admin
    from app.models.user import User

    print("--- bootstrap seed cases ---")

    saved = {
        key: os.environ.get(key)
        for key in (
            "ADMIN_INITIAL_USERNAME",
            "ADMIN_INITIAL_EMAIL",
            "ADMIN_INITIAL_PASSWORD",
        )
    }

    def _set_env(username=None, email=None, password=None) -> None:
        for key, value in (
            ("ADMIN_INITIAL_USERNAME", username),
            ("ADMIN_INITIAL_EMAIL", email),
            ("ADMIN_INITIAL_PASSWORD", password),
        ):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _fresh_factory():
        workdir = tempfile.mkdtemp(prefix="karmathy-seed-")
        path = os.path.join(workdir, "seed.db")
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)
        return sessionmaker(bind=engine), workdir

    def _user_rows(factory) -> list:
        session = factory()
        try:
            return session.query(User).all()
        finally:
            session.close()

    try:
        # --- fail-closed: no password in the environment -------------------
        factory, workdir = _fresh_factory()
        _set_env()
        try:
            outcome = seed_initial_admin(session_factory=factory)
            rows = _user_rows(factory)
            check(
                "no ADMIN_INITIAL_PASSWORD means no users (fail-closed)",
                outcome == "skipped-no-env" and len(rows) == 0,
                f"outcome={outcome} users={len(rows)}",
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        # --- env-seed: a strong password creates one SuperAdmin ------------
        factory, workdir = _fresh_factory()
        _set_env(
            username="seedowner",
            email="seedowner@example.com",
            password="T7#qW9!zM4$xK2&vB8",
        )
        try:
            outcome = seed_initial_admin(session_factory=factory)
            rows = _user_rows(factory)
            check(
                "ADMIN_INITIAL_PASSWORD seeds a single SuperAdmin",
                outcome == "seeded"
                and len(rows) == 1
                and rows[0].role == "SuperAdmin"
                and rows[0].username == "seedowner"
                and rows[0].is_active
                and rows[0].must_change_password,
                f"outcome={outcome} users={len(rows)}",
            )
            # --- idempotent: seeding again changes nothing -----------------
            outcome_again = seed_initial_admin(session_factory=factory)
            rows_again = _user_rows(factory)
            check(
                "seeding twice leaves exactly one user (idempotent)",
                outcome_again == "already-exists" and len(rows_again) == 1,
                f"outcome={outcome_again} users={len(rows_again)}",
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        # --- a weak password is rejected and stores nothing ----------------
        factory, workdir = _fresh_factory()
        _set_env(
            username="seedowner",
            email="seedowner@example.com",
            password="weakpass1",
        )
        try:
            outcome = seed_initial_admin(session_factory=factory)
            rows = _user_rows(factory)
            check(
                "a policy-violating ADMIN_INITIAL_PASSWORD creates no users",
                outcome == "rejected-policy" and len(rows) == 0,
                f"outcome={outcome} users={len(rows)}",
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        # --- an existing user is never overwritten -------------------------
        factory, workdir = _fresh_factory()
        _set_env(
            username="seedowner",
            email="seedowner@example.com",
            password="T7#qW9!zM4$xK2&vB8",
        )
        try:
            session = factory()
            try:
                session.add(
                    User(
                        username="kept",
                        email="kept@example.com",
                        hashed_password="not-a-real-hash",
                        role="HR",
                        is_active=True,
                    )
                )
                session.commit()
            finally:
                session.close()
            outcome = seed_initial_admin(session_factory=factory)
            rows = _user_rows(factory)
            check(
                "an existing user stops the seed without changes",
                outcome == "already-exists"
                and len(rows) == 1
                and rows[0].username == "kept",
                f"outcome={outcome} users={[r.username for r in rows]}",
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
    finally:
        _set_env(
            username=saved["ADMIN_INITIAL_USERNAME"],
            email=saved["ADMIN_INITIAL_EMAIL"],
            password=saved["ADMIN_INITIAL_PASSWORD"],
        )


def main() -> int:
    print("=" * 68)
    print("STARTUP / LIFESPAN SUITE")
    print("=" * 68)

    db_path = _fresh_db()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    # The startup event is what is under test, so it must be enabled here.
    os.environ["MIGRATE_ON_STARTUP"] = "true"

    from fastapi.testclient import TestClient

    from app.main import app

    # --- the lifespan actually runs ---------------------------------------
    # `with TestClient(app)` is what triggers the startup event. Without the
    # context manager, startup never happens and this suite would test
    # nothing.
    startup_error = None
    try:
        with TestClient(app) as client:
            response = client.get("/health")
            check(
                "the application starts and the health probe answers",
                response.status_code == 200 and response.json().get("status") == "healthy",
                f"got {response.status_code}: {response.text[:120]}",
            )
    except Exception as exc:  # noqa: BLE001
        startup_error = f"{type(exc).__name__}: {exc}"
        check("the application starts", False, startup_error)

    if startup_error is None:
        check("no exception was raised by the startup event", True)

        # The startup migration runs in a background thread so the server can
        # bind immediately. Wait for it before asserting on the schema.
        from app.core.migrations import MIGRATION_STATE

        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if MIGRATION_STATE.get("status") in ("ok", "failed"):
                break
            time.sleep(0.25)

        # --- the migration ran --------------------------------------------
        tables = _tables(db_path)
        check(
            "the startup migration created the schema",
            "users" in tables and "alembic_version" in tables,
            f"tables={sorted(tables)[:8]}",
        )
        check(
            "the refresh token table was created",
            "refresh_tokens" in tables,
            "refresh_tokens missing",
        )
        conn = sqlite3.connect(db_path)
        try:
            revision = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        finally:
            conn.close()
        # The head is read from the migration scripts rather than written
        # down, so adding a revision does not make this check go stale.
        from app.core.migrations import head_revision

        expected_head = head_revision()
        check(
            "the database is at the head revision",
            bool(revision) and revision[0] == expected_head,
            f"revision={revision} expected={expected_head}",
        )

        # --- the health probe reports the migration state -----------------
        check(
            "the migration state is recorded",
            MIGRATION_STATE.get("status") == "ok",
            f"status={MIGRATION_STATE.get('status')}",
        )
        check(
            "the migration state reports no error",
            MIGRATION_STATE.get("last_error") is None,
            f"last_error={MIGRATION_STATE.get('last_error')}",
        )

    # --- starting twice is safe -------------------------------------------
    second_start_error = None
    try:
        with TestClient(app) as client:
            response = client.get("/health")
            if response.status_code != 200:
                second_start_error = f"health returned {response.status_code}"
    except Exception as exc:  # noqa: BLE001
        second_start_error = f"{type(exc).__name__}: {exc}"
    check(
        "the application starts again against the same database",
        second_start_error is None,
        second_start_error or "",
    )

    # --- the lifespan seed is fail-closed ----------------------------------
    # No ADMIN_INITIAL_PASSWORD was set, so the background seed must have
    # left the users table empty. The seed runs right after the migration in
    # the same background thread; the migration is done (checked above), so
    # give the single seed query a moment to settle before asserting.
    if startup_error is None:
        time.sleep(5)
        conn = sqlite3.connect(db_path)
        try:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        finally:
            conn.close()
        check(
            "startup creates no bootstrap users without ADMIN_INITIAL_PASSWORD"
            " (fail-closed)",
            user_count == 0,
            f"users={user_count}",
        )

    shutil.rmtree(os.path.dirname(db_path), ignore_errors=True)

    # --- env-gated bootstrap seed (direct cases) --------------------------
    _run_seed_cases()

    for key, value in _SAVED_BOOTSTRAP_ENV.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    # --- a weakened configuration refuses to start ------------------------
    from app.core.config import Settings

    weak = Settings(
        SECRET_KEY="short",
        ALGORITHM="HS256",
        ENVIRONMENT="production",
        DATABASE_URL="sqlite:///./startup_suite_scratch.db",
    )
    try:
        weak.validate()
        check(
            "a short SECRET_KEY is refused in production",
            False,
            "validate() accepted a 5-character secret",
        )
    except RuntimeError:
        check("a short SECRET_KEY is refused in production", True)

    wrong_alg = Settings(
        SECRET_KEY="x" * 40,
        ALGORITHM="none",
        ENVIRONMENT="production",
        DATABASE_URL="sqlite:///./startup_suite_scratch.db",
    )
    try:
        wrong_alg.validate()
        check(
            "a JWT algorithm other than HS256 is refused",
            False,
            "validate() accepted ALGORITHM=none",
        )
    except RuntimeError:
        check("a JWT algorithm other than HS256 is refused", True)

    print()
    print("=" * 68)
    print(f"STARTUP SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
    if FAILURES:
        print()
        print("Failures:")
        for name, detail in FAILURES:
            print(f"  - {name}: {detail}")
    print("=" * 68)
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
