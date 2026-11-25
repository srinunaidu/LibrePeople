"""Create the first SuperAdmin account.

Usage (after DATABASE_URL is configured):

    ADMIN_INITIAL_PASSWORD='<a strong password>' python -m scripts.seed_admin

The password **must** be supplied by the environment. This script has no
default, and there is deliberately no fallback: an earlier revision of this
file hardcoded a password, printed it, and repeated it in the deployment
documentation. That credential was published, and it authenticated against
the live production backend until it was rotated.

The account created here is left in a ``must_change_password`` state. It can
sign in, read its own profile and set a new password — nothing else. That
means the bootstrap secret is only ever useful for the one task it was
created for.

Schema
------
Alembic is the only schema change path. This script runs the migrations
before creating the user, so it never calls ``create_all()`` and never
diverges from the models.

Sample data
-----------
This script creates no departments, jobs or employees. Synthetic data for
development lives in ``seed/dev/``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import inspect  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.migrations import run_pending_migrations  # noqa: E402
from app.core.password_policy import check_password  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402

#: The environment variable that supplies the bootstrap password.
PASSWORD_ENV_VAR = "ADMIN_INITIAL_PASSWORD"

SEED_ADMIN_USERNAME = os.environ.get("ADMIN_INITIAL_USERNAME", "admin")
# The default address is on a reserved domain, so it is never deliverable
# and cannot reach a real inbox. It is a placeholder for a local
# installation, not a working address: set ADMIN_INITIAL_EMAIL to a real
# one before seeding a deployment.
SEED_ADMIN_EMAIL = os.environ.get("ADMIN_INITIAL_EMAIL", "admin@karmathy.example")


def _fail(message: str) -> None:
    print(f"[seed_admin] ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def run() -> None:
    password = os.environ.get(PASSWORD_ENV_VAR)
    if not password:
        _fail(
            f"{PASSWORD_ENV_VAR} is not set. The first administrator's "
            "password must be supplied by the environment — this script has "
            "no default and never prints a password.\n"
            "           Generate one with:\n"
            "             python -c \"import secrets; "
            "print(secrets.token_urlsafe(24))\""
        )

    result = check_password(
        password,
        username=SEED_ADMIN_USERNAME,
        email=SEED_ADMIN_EMAIL,
        min_length=settings.PASSWORD_MIN_LENGTH,
    )
    if not result.ok:
        _fail(
            "The supplied password does not meet the password policy:\n  - "
            + "\n  - ".join(result.messages)
        )

    # Bring the schema up to date first. Alembic is the only schema change
    # path; this script must not create tables itself.
    print("[seed_admin] Applying migrations...")
    state = run_pending_migrations()
    if state.get("legacy_schema_adopted"):
        print(
            "[seed_admin] Adopted a pre-Alembic database by stamping the "
            "baseline. The inherited tables were already present.",
            file=sys.stderr,
        )
    print(f"[seed_admin] Schema at revision {state.get('current_revision')}.")

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == SEED_ADMIN_USERNAME).first()
        if existing:
            print(
                f"[seed_admin] SuperAdmin '{SEED_ADMIN_USERNAME}' already "
                "exists. Nothing to do."
            )
            return

        db.add(
            User(
                username=SEED_ADMIN_USERNAME,
                email=SEED_ADMIN_EMAIL,
                hashed_password=get_password_hash(password),
                role="SuperAdmin",
                is_active=True,
                # The bootstrap secret is only for the first sign-in.
                must_change_password=True,
            )
        )
        db.commit()
        print(
            f"[seed_admin] Created SuperAdmin '{SEED_ADMIN_USERNAME}'. "
            "The account must change its password at first sign-in."
        )
        print(
            "[seed_admin] The password was read from the environment and is "
            "not printed. Remove it from the environment now."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
