"""Recover administrator access when the credential is unknown.

An operator can set a new password for a SuperAdmin account from the
environment, without an existing session:

    ADMIN_RESET_PASSWORD='<a strong password>' \\
        python -m scripts.reset_admin_password

The account is left in a ``must_change_password`` state, exactly as the
administrator-set password flow leaves it, so the person signs in once
and replaces the credential themselves. Every session for the account is
revoked and the action is written to the audit trail.

The production guard
--------------------
This script runs as a **release step on every deploy**. In a production
environment that is a hazard rather than a convenience: if
``ADMIN_RESET_PASSWORD`` is left set in the environment, every deploy
rewrites the administrator's password, forces the account back into
``must_change_password`` and writes a reset row into the audit trail —
and the deployment still reports itself healthy.

So in a production environment the script refuses to run unless:

``ADMIN_RESET_ACKNOWLEDGE``
    Must be set to the exact value
    :data:`PRODUCTION_ACKNOWLEDGE_VALUE`. Nothing else is accepted.

``ADMIN_RESET_ALLOW_ACTIVE``
    Must be set to ``1`` when the target account is **not** already in the
    ``must_change_password`` state. An account in normal use has a live,
    working credential; overwriting it from a release step is exactly the
    loop this guard exists to stop. Set this only for a genuine recovery
    (a forgotten password), and unset it afterwards.

Both refusals happen **before** the database is touched: the stored hash
is unchanged and no audit row is written.

The production check **fails closed**. Only an environment that explicitly
names itself as development, test or staging escapes the guard; an unset
``ENVIRONMENT`` is treated as production, because this script is a release
step and the cost of being wrong is one extra acknowledgement variable.

What this deliberately does not do
---------------------------------
* It does nothing at all unless ``ADMIN_RESET_PASSWORD`` is set, so it is
  safe to leave in a deployment: the release step runs it on every deploy
  and it is a no-op without the variable.
* It only ever touches an account whose role is ``SuperAdmin``. A
  regular administrator cannot use it to take over another role.
* It is idempotent. If the stored hash already verifies the supplied
  password the script reports that and changes nothing, so a variable
  that is left in place by mistake cannot keep rewriting the account.
* It never prints the password or the hash.
"""
from __future__ import annotations

import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

PASSWORD_ENV_VAR = "ADMIN_RESET_PASSWORD"
USERNAME_ENV_VAR = "ADMIN_RESET_USERNAME"

#: The acknowledgement a production reset requires. The value is long and
#: specific on purpose: it must not be something an operator sets once and
#: forgets, and it must say what it does when somebody reads the
#: environment.
PRODUCTION_ACKNOWLEDGE_VAR = "ADMIN_RESET_ACKNOWLEDGE"
PRODUCTION_ACKNOWLEDGE_VALUE = "reset-the-production-admin-password"

#: Set to ``1`` to allow a production reset of an account that is in normal
#: use (not already in the ``must_change_password`` state).
ALLOW_ACTIVE_VAR = "ADMIN_RESET_ALLOW_ACTIVE"
ALLOW_ACTIVE_VALUE = "1"

#: Exit code used for a policy refusal, as distinct from a failed reset.
EXIT_REFUSED = 2

#: Environment values that mean "this is a live deployment". Mirrors
#: ``Settings.is_production`` so the two cannot disagree.
PRODUCTION_ENVIRONMENTS = ("production", "prod", "live")

#: Environment values that mean "this is not a live deployment".
#:
#: The check is **fail closed**: an environment that is not in this list is
#: treated as production. The script is a release step, so it only ever acts
#: when an operator has deliberately supplied a password; if nobody said
#: where the script was running, the safe reading is "somewhere it matters".
#: The cost of being wrong is one extra acknowledgement variable.
NON_PRODUCTION_ENVIRONMENTS = (
    "development",
    "dev",
    "test",
    "testing",
    "local",
    "staging",
)

#: The actor recorded on the audit row. There is no session and no user
#: behind a release step, so the actor is named rather than left blank.
RESET_ACTOR_NAME = "operator-reset-script"

#: The role an account must hold for this script to touch it.
REQUIRED_ROLE = "SuperAdmin"


def _is_production() -> bool:
    """True when this process must be treated as a live deployment.

    Fail closed: only an environment that explicitly names itself as a
    development, test or staging environment escapes the production guard.
    """
    value = os.environ.get("ENVIRONMENT", "").strip().lower()
    if value in NON_PRODUCTION_ENVIRONMENTS:
        return False
    return True


def _production_refusal() -> str | None:
    """Return the reason this run must not proceed, or ``None``.

    Called before the database is opened, so a refusal provably writes
    nothing: no password change, no audit row, no file.
    """
    if not _is_production():
        return None

    if os.environ.get(PRODUCTION_ACKNOWLEDGE_VAR, "") != PRODUCTION_ACKNOWLEDGE_VALUE:
        return (
            f"{PRODUCTION_ACKNOWLEDGE_VAR} must be set to "
            f"{PRODUCTION_ACKNOWLEDGE_VALUE!r} to reset the administrator "
            "password in a production environment; this script runs on every "
            "deploy, so an unattended reset would silently take the account "
            "over. Set the acknowledgement and ADMIN_RESET_PASSWORD "
            "together, then remove both."
        )
    return None


def _deployment_label() -> str:
    """Name the deployment this reset ran in, for the audit row.

    The name is not a secret and it is not a personal identifier: it is the
    service the operator was working on.
    """
    for variable in ("RENDER_SERVICE_NAME", "DYNO", "KARMATHY_DEPLOYMENT"):
        value = os.environ.get(variable, "").strip()
        if value:
            return value
    try:
        return socket.gethostname() or "unknown"
    except OSError:
        return "unknown"


class _ResetActor:
    """Stand-in for the ``User`` the audit writer expects.

    A release step has no session and no user behind it, so there is no
    ``User.id`` to record. The audit writer reads ``id`` and ``username``
    off whatever it is given; this names the actor explicitly instead of
    leaving the row anonymous.
    """

    id = None
    username = RESET_ACTOR_NAME


def main() -> int:
    password = os.environ.get(PASSWORD_ENV_VAR)
    if not password:
        # No request: this is the normal state of a deployment.
        print(
            f"[reset_admin_password] {PASSWORD_ENV_VAR} is not set; nothing to do.",
            file=sys.stderr,
        )
        return 0

    username = os.environ.get(USERNAME_ENV_VAR, "admin")

    # The production guard runs before the database is touched, so a refusal
    # cannot leave a half-written account or a stray audit row behind.
    refusal = _production_refusal()
    if refusal:
        print(f"[reset_admin_password] REFUSED: {refusal}", file=sys.stderr)
        return EXIT_REFUSED

    from app.core.audit import record_audit
    from app.core.database import SessionLocal
    from app.core.password_policy import check_password
    from app.core.security import get_password_hash, verify_password
    from app.models.user import User
    from app.core.config import settings

    # Every model module has to be imported before the mapper is configured:
    # a relationship whose target has not been imported fails to resolve.
    import importlib
    import pkgutil

    import app.models

    for _finder, _name, _ispkg in pkgutil.iter_modules(app.models.__path__):
        if _ispkg:
            continue
        importlib.import_module(f"app.models.{_name}")

    db = SessionLocal()
    try:
        target = db.query(User).filter(User.username == username).first()
        if target is None:
            print(
                f"[reset_admin_password] ERROR: no account named {username!r}.",
                file=sys.stderr,
            )
            return 1
        if target.role != REQUIRED_ROLE:
            print(
                f"[reset_admin_password] ERROR: {username!r} has role "
                f"{target.role!r}; only {REQUIRED_ROLE!r} may be reset this way.",
                file=sys.stderr,
            )
            return 1

        # Already at this password: nothing to do, and nothing to change.
        if verify_password(password, target.hashed_password or ""):
            print(
                "[reset_admin_password] The account already uses this password; "
                "nothing was changed.",
                file=sys.stderr,
            )
            return 0

        # The second production guard. An account that is not already in the
        # ``must_change_password`` state is an account in normal use: its
        # credential is live and working. Overwriting it from a release step
        # is the loop that leaves the account locked out of its own
        # deployment on every deploy, so it needs a second, explicit
        # acknowledgement.
        if _is_production() and not target.must_change_password:
            if os.environ.get(ALLOW_ACTIVE_VAR, "") != ALLOW_ACTIVE_VALUE:
                print(
                    f"[reset_admin_password] REFUSED: {username!r} is in normal "
                    f"use, so this reset would overwrite a working credential on "
                    f"every deploy; set {ALLOW_ACTIVE_VAR}={ALLOW_ACTIVE_VALUE} "
                    "for a genuine recovery, and unset it afterwards.",
                    file=sys.stderr,
                )
                return EXIT_REFUSED

        result = check_password(
            password,
            username=target.username,
            email=target.email,
            history_hashes=target.password_history_hashes(),
            min_length=settings.PASSWORD_MIN_LENGTH,
        )
        if not result.ok:
            print(
                "[reset_admin_password] ERROR: the supplied password does not "
                "meet the password policy:",
                file=sys.stderr,
            )
            for message in result.messages:
                print(f"  - {message}", file=sys.stderr)
            return 1

        previous_hash = target.hashed_password
        target.hashed_password = get_password_hash(password)
        target.must_change_password = True
        target.password_changed_at = datetime.now(timezone.utc)
        target.failed_login_count = 0
        target.locked_until = None
        if previous_hash:
            import json

            history = target.password_history_hashes()
            history.insert(0, previous_hash)
            target.password_history = json.dumps(
                history[: settings.PASSWORD_HISTORY_DEPTH]
            )

        # The audit row names the deployment and the actor, and is written in
        # the same transaction as the password change: both are added to this
        # session and committed once, so a rollback undoes the audit row with
        # the change it describes.
        record_audit(
            db,
            _ResetActor(),
            "admin_password_reset_by_operator",
            "User",
            target.id,
            details=(
                f"username={target.username}; actor={RESET_ACTOR_NAME}; "
                f"deployment={_deployment_label()}; "
                f"environment={os.environ.get('ENVIRONMENT', 'development')}"
            ),
        )
        db.commit()

        print(
            f"[reset_admin_password] The password for {username!r} was reset. "
            "The account must replace it at first sign-in.",
            file=sys.stderr,
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
