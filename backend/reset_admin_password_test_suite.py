"""Operator password reset — regression suite.

The reset lets an operator recover administrator access when the credential
is lost. It is a privileged capability, so the behaviour it must have is
pinned down here: it does nothing without an explicit environment
variable, it only ever touches a SuperAdmin account, it clears the lockout
and the failure counter, it leaves the account needing a password change,
it refuses a password that fails the policy, and it never prints the
password.

Run with:

    SECRET_KEY=... DATABASE_URL=sqlite:///./reset_test.db \\
        .venv/bin/python reset_admin_password_test_suite.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

NEW_PASSWORD = "Operator#Reset2026x"
OLD_PASSWORD = "SomeOtherPassword#1"
HR_PASSWORD = "HrPassword#2026x"

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


def run_reset(
    env_extra: dict[str, str],
    db_url: str,
    unset_env: tuple[str, ...] = (),
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(
        {
            "SECRET_KEY": "test_secret_key_for_development_32_chars",
            "DATABASE_URL": db_url,
            "PYTHONPATH": str(BACKEND_ROOT),
            # The production guard fails closed (item 6), so the
            # production-mode runs in this suite need a registered key pair.
            "FIELD_ENCRYPTION_KEYS": "lp-test-key:local-test-field-encryption-secret-0123456789",
            "FIELD_ENCRYPTION_ACTIVE_KEY_ID": "lp-test-key",
            # The production guard fails closed, so a test that expects the
            # reset to proceed has to say where it is running. Individual
            # calls override this.
            "ENVIRONMENT": "development",
            # The app config also fails closed on CORS in production, so
            # production-mode runs need a dummy origin the way they need a
            # dummy SECRET_KEY. This does not weaken anything: the value is
            # a test-only origin and the fail-closed logic is untouched.
            "BACKEND_CORS_ORIGINS": "https://app.example.com",
        }
    )
    env.update(env_extra)
    for name in unset_env:
        env.pop(name, None)
    return subprocess.run(
        [sys.executable, "-m", "scripts.reset_admin_password"],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def _files_in_backend() -> set[str]:
    """The files the script is allowed to leave behind.

    The script must never write the password to a file. Byte-code caches are
    not interesting here, so they are excluded.
    """
    found: set[str] = set()
    for path in BACKEND_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        found.add(str(path.relative_to(BACKEND_ROOT)))
    return found


def main() -> int:
    print("=" * 68)
    print("RESET ADMIN PASSWORD SUITE")
    print("=" * 68)

    workdir = tempfile.mkdtemp(prefix="karmathy-reset-")
    db_url = f"sqlite:///{workdir}/reset.db"

    # The engine is built at import time, so the variable has to point at
    # the throwaway database before the application modules are imported.
    os.environ["DATABASE_URL"] = db_url
    os.environ.setdefault("SECRET_KEY", "test_secret_key_for_development_32_chars")

    try:
        from app.core.database import SessionLocal
        from app.core.migrations import run_pending_migrations
        from app.core.security import get_password_hash, verify_password
        from app.models.audit import AuditLog
        from app.models.user import User

        run_pending_migrations()

        db = SessionLocal()
        db.add(
            User(
                username="admin",
                email="admin@karmathy.example",
                hashed_password=get_password_hash(OLD_PASSWORD),
                role="SuperAdmin",
                is_active=True,
                must_change_password=False,
                failed_login_count=7,
            )
        )
        db.add(
            User(
                username="hruser",
                email="hr@karmathy.example",
                hashed_password=get_password_hash(HR_PASSWORD),
                role="HR",
                is_active=True,
            )
        )
        db.commit()
        db.close()

        # --- without the variable it does nothing -------------------------
        result = run_reset({}, db_url)
        check(
            "without the variable the script is a no-op and succeeds",
            result.returncode == 0,
            result.stderr.strip()[-120:],
        )

        db = SessionLocal()
        user = db.query(User).filter(User.username == "admin").first()
        check(
            "the password is unchanged without the variable",
            verify_password(OLD_PASSWORD, user.hashed_password),
        )
        check(
            "the failure counter is untouched without the variable",
            (user.failed_login_count or 0) == 7,
            f"count={user.failed_login_count}",
        )
        db.close()

        # --- with the variable it resets the SuperAdmin -------------------
        result = run_reset({"ADMIN_RESET_PASSWORD": NEW_PASSWORD}, db_url)
        check(
            "with the variable the script succeeds",
            result.returncode == 0,
            result.stderr.strip()[-160:],
        )

        db = SessionLocal()
        user = db.query(User).filter(User.username == "admin").first()
        check("the new password verifies", verify_password(NEW_PASSWORD, user.hashed_password))
        check(
            "the old password no longer verifies",
            not verify_password(OLD_PASSWORD, user.hashed_password),
        )
        check(
            "the account must replace the password at first sign-in",
            user.must_change_password is True,
        )
        check(
            "the failure counter is cleared",
            (user.failed_login_count or 0) == 0,
            f"count={user.failed_login_count}",
        )
        check("the lockout is cleared", user.locked_until is None)
        check("the previous hash is kept in the history", bool(user.password_history))
        db.close()

        # --- it is idempotent ---------------------------------------------
        result = run_reset({"ADMIN_RESET_PASSWORD": NEW_PASSWORD}, db_url)
        check(
            "running it again with the same password changes nothing",
            result.returncode == 0 and "already uses this password" in result.stderr,
            result.stderr.strip()[-120:],
        )

        # --- it refuses an account that is not a SuperAdmin ----------------
        result = run_reset(
            {
                "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                "ADMIN_RESET_USERNAME": "hruser",
            },
            db_url,
        )
        check(
            "it refuses an account that is not a SuperAdmin",
            result.returncode == 1 and "only 'SuperAdmin'" in result.stderr,
            result.stderr.strip()[-140:],
        )

        db = SessionLocal()
        hr = db.query(User).filter(User.username == "hruser").first()
        check(
            "the other account's password is untouched",
            verify_password(HR_PASSWORD, hr.hashed_password),
        )
        db.close()

        # --- it refuses a password that fails the policy -------------------
        result = run_reset({"ADMIN_RESET_PASSWORD": "short"}, db_url)
        check(
            "it refuses a password that fails the policy",
            result.returncode == 1 and "password policy" in result.stderr,
            result.stderr.strip()[-140:],
        )

        # --- it never prints the password ---------------------------------
        result = run_reset({"ADMIN_RESET_PASSWORD": NEW_PASSWORD}, db_url)
        check(
            "it never prints the password",
            NEW_PASSWORD not in result.stdout and NEW_PASSWORD not in result.stderr,
        )

        # ==================================================================
        # The production guard.
        #
        # The script runs as a release step on every deploy. In production an
        # unattended reset silently takes the administrator account over, so
        # it must refuse without an explicit acknowledgement — and a refusal
        # must write nothing at all.
        # ==================================================================
        print()
        print("=" * 68)
        print("RESET ADMIN PASSWORD — production guard")
        print("=" * 68)

        # Two more SuperAdmin accounts, in the two states that matter:
        # one in normal use (a live, working credential) and one already
        # waiting for a password change.
        db = SessionLocal()
        db.add(
            User(
                username="prod_active",
                email="prod_active@karmathy.example",
                hashed_password=get_password_hash(OLD_PASSWORD),
                role="SuperAdmin",
                is_active=True,
                must_change_password=False,
            )
        )
        db.add(
            User(
                username="prod_pending",
                email="prod_pending@karmathy.example",
                hashed_password=get_password_hash(OLD_PASSWORD),
                role="SuperAdmin",
                is_active=True,
                must_change_password=True,
            )
        )
        db.commit()
        db.close()

        acknowledge = "reset-the-production-admin-password"

        def snapshot(username: str) -> tuple[str, int]:
            """The stored hash and the number of audit rows, for comparison."""
            s = SessionLocal()
            try:
                row = s.query(User).filter(User.username == username).first()
                return (row.hashed_password, s.query(AuditLog).count())
            finally:
                s.close()

        # --- 1. production, no acknowledgement ---------------------------
        before_hash, before_audit = snapshot("prod_active")
        result = run_reset(
            {
                "ENVIRONMENT": "production",
                "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                "ADMIN_RESET_USERNAME": "prod_active",
            },
            db_url,
        )
        check(
            "in production it refuses without the acknowledgement",
            result.returncode != 0 and "REFUSED" in result.stderr,
            f"exit={result.returncode} {result.stderr.strip()[-160:]}",
        )
        check(
            "the refusal explains itself on one line",
            len([line for line in result.stderr.splitlines() if line.strip()]) == 1,
            result.stderr.strip()[-160:],
        )
        after_hash, after_audit = snapshot("prod_active")
        check("the refusal left the stored hash unchanged", after_hash == before_hash)
        check("the refusal wrote no audit row", after_audit == before_audit)

        # --- 2. production, a wrong acknowledgement ----------------------
        result = run_reset(
            {
                "ENVIRONMENT": "production",
                "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                "ADMIN_RESET_USERNAME": "prod_active",
                "ADMIN_RESET_ACKNOWLEDGE": "yes",
            },
            db_url,
        )
        check(
            "in production it refuses a wrong acknowledgement",
            result.returncode != 0 and "REFUSED" in result.stderr,
            f"exit={result.returncode} {result.stderr.strip()[-160:]}",
        )
        after_hash, after_audit = snapshot("prod_active")
        check("the wrong acknowledgement left the hash unchanged", after_hash == before_hash)
        check("the wrong acknowledgement wrote no audit row", after_audit == before_audit)

        # --- 3. production, acknowledged, account in normal use -----------
        result = run_reset(
            {
                "ENVIRONMENT": "production",
                "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                "ADMIN_RESET_USERNAME": "prod_active",
                "ADMIN_RESET_ACKNOWLEDGE": acknowledge,
            },
            db_url,
        )
        check(
            "in production it refuses to overwrite a credential in normal use",
            result.returncode != 0 and "REFUSED" in result.stderr,
            f"exit={result.returncode} {result.stderr.strip()[-160:]}",
        )
        after_hash, after_audit = snapshot("prod_active")
        check("that refusal left the stored hash unchanged", after_hash == before_hash)
        check("that refusal wrote no audit row", after_audit == before_audit)

        # --- 4. production, acknowledged, account in normal use, allowed --
        files_before = _files_in_backend()
        # Rows written before the production guard section (e.g. the setup
        # reset above, whose deployment label falls back to this machine's
        # hostname) must not be mistaken for this reset's row.
        _s = SessionLocal()
        try:
            audit_ids_before = {r.id for r in _s.query(AuditLog.id).all()}
        finally:
            _s.close()
        result = run_reset(
            {
                "ENVIRONMENT": "production",
                "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                "ADMIN_RESET_USERNAME": "prod_active",
                "ADMIN_RESET_ACKNOWLEDGE": acknowledge,
                "ADMIN_RESET_ALLOW_ACTIVE": "1",
                "RENDER_SERVICE_NAME": "karmathy-backend-test",
            },
            db_url,
        )
        check(
            "with both acknowledgements the production reset succeeds",
            result.returncode == 0,
            f"exit={result.returncode} {result.stderr.strip()[-160:]}",
        )

        db = SessionLocal()
        row = db.query(User).filter(User.username == "prod_active").first()
        check(
            "the production reset set the new password",
            verify_password(NEW_PASSWORD, row.hashed_password),
        )
        check(
            "the production reset leaves the account needing a password change",
            row.must_change_password is True,
        )
        audit_rows = (
            db.query(AuditLog)
            .filter(AuditLog.action == "admin_password_reset_by_operator")
            .order_by(AuditLog.id)
            .all()
        )
        check(
            "the production reset wrote an audit row",
            len(audit_rows) >= 1,
            f"rows={len(audit_rows)}",
        )
        if audit_rows:
            # Only rows written by this section's reset count. The expected
            # label comes from the RENDER_SERVICE_NAME the suite passed in
            # its own environment — never from the machine hostname — so
            # this assertion is hostname-agnostic by construction.
            new_rows = [r for r in audit_rows if r.id not in audit_ids_before]
            latest = new_rows[-1] if new_rows else audit_rows[-1]
            check(
                "the audit row names the actor",
                latest.actor_name == "operator-reset-script",
                f"actor_name={latest.actor_name!r}",
            )
            check(
                "the audit row names the deployment",
                "karmathy-backend-test" in (latest.details or ""),
                f"details={latest.details!r}",
            )
            check(
                "the audit row carries no password",
                NEW_PASSWORD not in (latest.details or ""),
            )
        db.close()

        check(
            "the production reset wrote no file",
            _files_in_backend() == files_before,
        )

        # --- 5. production, acknowledged, account already pending ---------
        before_hash, before_audit = snapshot("prod_pending")
        result = run_reset(
            {
                "ENVIRONMENT": "production",
                "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                "ADMIN_RESET_USERNAME": "prod_pending",
                "ADMIN_RESET_ACKNOWLEDGE": acknowledge,
                "RENDER_SERVICE_NAME": "karmathy-backend-test",
            },
            db_url,
        )
        check(
            "an account already awaiting a password change resets without "
            "the second acknowledgement",
            result.returncode == 0,
            f"exit={result.returncode} {result.stderr.strip()[-160:]}",
        )
        after_hash, after_audit = snapshot("prod_pending")
        check("that reset changed the stored hash", after_hash != before_hash)
        check("that reset wrote exactly one audit row", after_audit == before_audit + 1)

        # --- 6. production, idempotence ----------------------------------
        result = run_reset(
            {
                "ENVIRONMENT": "production",
                "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                "ADMIN_RESET_USERNAME": "prod_pending",
                "ADMIN_RESET_ACKNOWLEDGE": acknowledge,
                "RENDER_SERVICE_NAME": "karmathy-backend-test",
            },
            db_url,
        )
        check(
            "running it again in production changes nothing",
            result.returncode == 0 and "already uses this password" in result.stderr,
            result.stderr.strip()[-140:],
        )
        final_hash, final_audit = snapshot("prod_pending")
        check("the second production run left the hash unchanged", final_hash == after_hash)
        check("the second production run wrote no audit row", final_audit == after_audit)

        # --- 7. the password never leaks in the production paths ----------
        leaked = [
            name
            for name, result in (
                ("refusal", run_reset(
                    {"ENVIRONMENT": "production", "ADMIN_RESET_PASSWORD": NEW_PASSWORD},
                    db_url,
                )),
                ("success", run_reset(
                    {
                        "ENVIRONMENT": "production",
                        "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                        "ADMIN_RESET_USERNAME": "prod_pending",
                        "ADMIN_RESET_ACKNOWLEDGE": acknowledge,
                        "ADMIN_RESET_ALLOW_ACTIVE": "1",
                    },
                    db_url,
                )),
            )
            if NEW_PASSWORD in result.stdout or NEW_PASSWORD in result.stderr
        ]
        check("no production path prints the password", not leaked, str(leaked))

        # --- 8. a non-production environment needs no acknowledgement ------
        result = run_reset(
            {
                "ENVIRONMENT": "development",
                "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                "ADMIN_RESET_USERNAME": "prod_pending",
            },
            db_url,
        )
        check(
            "outside production no acknowledgement is needed",
            result.returncode == 0,
            f"exit={result.returncode} {result.stderr.strip()[-140:]}",
        )

        # --- 9. the production check fails closed -------------------------
        before_hash, before_audit = snapshot("prod_active")
        result = run_reset(
            {
                "ADMIN_RESET_PASSWORD": NEW_PASSWORD,
                "ADMIN_RESET_USERNAME": "prod_active",
            },
            db_url,
            unset_env=("ENVIRONMENT",),
        )
        check(
            "an unset ENVIRONMENT is treated as production",
            result.returncode != 0 and "REFUSED" in result.stderr,
            f"exit={result.returncode} {result.stderr.strip()[-160:]}",
        )
        after_hash, after_audit = snapshot("prod_active")
        check("the fail-closed refusal left the hash unchanged", after_hash == before_hash)
        check("the fail-closed refusal wrote no audit row", after_audit == before_audit)

    finally:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)

    print()
    print("=" * 68)
    print(
        f"RESET ADMIN PASSWORD SUITE: {RESULTS['pass']} passed, "
        f"{RESULTS['fail']} failed"
    )
    if FAILURES:
        print()
        print("Failures:")
        for name, detail in FAILURES:
            print(f"  - {name}: {detail}")
    print("=" * 68)
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
