"""Password policy, breach blocklist and reuse prevention.

Design follows NIST SP 800-63B: length and a blocklist are the primary
controls; composition rules are a secondary control and are deliberately loose
so they do not push people towards predictable substitutions.

What this module enforces
-------------------------
1. **Length** — at least ``PASSWORD_MIN_LENGTH`` characters (default 12).
2. **Not a common or breached password** — checked against a *local* blocklist
   shipped with the repository. See the scope note below.
3. **No reuse** — the candidate must not match any of the last N passwords
   the account has used. The history is stored as bcrypt hashes, so this is a
   verification, not a comparison.
4. **Not derived from the account** — the candidate must not contain the
   username or the local part of the email address.
5. **Composition** — at least three of the four character classes
   (lower, upper, digit, symbol).

Scope note on the blocklist
--------------------------
``data/breached_passwords.txt`` is a **curated local list**, not the full
HaveIBeenPwned corpus and not a live service call. It covers the passwords
that appear most often in credential-stuffing wordlists. This is a real
control, but a deployment that wants stronger coverage should extend the file
(or point ``BREACHED_PASSWORD_LIST_PATH`` at a larger corpus) rather than
assume the shipped list is exhaustive. The file is read once at import and
cached; changing it requires a restart.

The check is done on a normalised form (case-folded) so that ``Password1!`` and
``password1!`` are treated as the same entry.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.errors import ApiError, ErrorCategory

#: Minimum accepted password length.
PASSWORD_MIN_LENGTH = 12

#: Maximum accepted password length. Bcrypt is used for hashing (after a
#: pre-hash, so this is a DoS guard rather than a bcrypt limit).
PASSWORD_MAX_LENGTH = 200

#: How many previous passwords may not be reused.
PASSWORD_HISTORY_DEPTH = 5

#: Characters counted towards the composition requirement.
_LOWER = re.compile(r"[a-z]")
_UPPER = re.compile(r"[A-Z]")
_DIGIT = re.compile(r"[0-9]")
_SYMBOL = re.compile(r"[^A-Za-z0-9]")

_LIST_PATH = Path(__file__).with_name("data") / "breached_passwords.txt"


class PasswordPolicyError(ApiError):
    """Raised when a candidate password fails the policy.

    Subclasses :class:`ApiError` so it renders through the shared error
    envelope. The ``code`` identifies the specific failure so the UI can
    explain what to fix.
    """

    def __init__(self, code: str, message: str, violations: list[str] | None = None):
        super().__init__(
            code,
            message,
            ErrorCategory.VALIDATION,
            details={"violations": violations or []},
        )


@dataclass(frozen=True)
class PasswordCheck:
    """Outcome of evaluating a candidate password against the policy."""

    ok: bool
    violations: list[str]
    messages: list[str]

    def raise_if_failed(self) -> None:
        if self.ok:
            return
        first = self.messages[0] if self.messages else "Password does not meet policy"
        # The specific code is the first violation's code, so clients can
        # branch on e.g. `password_breached` versus `password_policy_violation`.
        raise PasswordPolicyError(self.violations[0], first, self.messages)


@lru_cache(maxsize=1)
def _blocked_passwords() -> frozenset[str]:
    """Normalised set of blocked passwords from the local list."""
    try:
        raw = _LIST_PATH.read_text(encoding="utf-8")
    except OSError:
        # A missing list must not silently disable the control. Fail closed by
        # blocking nothing but recording the fact, rather than pretending the
        # check ran.
        return frozenset()
    out: set[str] = set()
    for line in raw.splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        out.add(_normalise(entry))
    return frozenset(out)


def _normalise(password: str) -> str:
    """Case-folded, NFKC-normalised form used for blocklist comparison."""
    return unicodedata.normalize("NFKC", password).casefold()


def blocked_password_count() -> int:
    """Size of the loaded blocklist. Exposed for the admin config screen."""
    return len(_blocked_passwords())


def is_breached(password: str) -> bool:
    """True when the password appears in the local blocklist."""
    return _normalise(password) in _blocked_passwords()


def check_password(
    password: str,
    *,
    username: str | None = None,
    email: str | None = None,
    history_hashes: list[str] | None = None,
    min_length: int = PASSWORD_MIN_LENGTH,
) -> PasswordCheck:
    """Evaluate a candidate password.

    Parameters
    ----------
    password:
        The candidate, exactly as the user typed it.
    username, email:
        Used to reject passwords derived from the account identity.
    history_hashes:
        bcrypt hashes of the account's previous passwords, newest first. The
        candidate is verified against each; any match is a reuse violation.
    """
    violations: list[str] = []
    messages: list[str] = []

    def fail(code: str, message: str) -> None:
        violations.append(code)
        messages.append(message)

    if not isinstance(password, str) or not password:
        fail("password_policy_violation", "A password is required.")
        return PasswordCheck(False, violations, messages)

    if len(password) < min_length:
        fail(
            "password_policy_violation",
            f"Password must be at least {min_length} characters.",
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        fail(
            "password_policy_violation",
            f"Password must be at most {PASSWORD_MAX_LENGTH} characters.",
        )

    classes = sum(
        1
        for pattern in (_LOWER, _UPPER, _DIGIT, _SYMBOL)
        if pattern.search(password)
    )
    if classes < 3:
        fail(
            "password_policy_violation",
            "Password must combine at least three of: lower case, upper case, "
            "digits, symbols.",
        )

    if is_breached(password):
        fail(
            "password_breached",
            "This password appears in the list of commonly used and breached "
            "passwords. Choose a different one.",
        )

    normalised = _normalise(password)
    if username and len(username) >= 3 and _normalise(username) in normalised:
        fail(
            "password_policy_violation",
            "Password must not contain your username.",
        )
    if email:
        local_part = email.split("@", 1)[0]
        if len(local_part) >= 3 and _normalise(local_part) in normalised:
            fail(
                "password_policy_violation",
                "Password must not contain your email address.",
            )

    # Reuse check. History entries are bcrypt hashes, so the candidate has to
    # be *verified* against each one rather than compared.
    if history_hashes:
        from app.core.security import verify_password

        for old_hash in history_hashes[:PASSWORD_HISTORY_DEPTH]:
            try:
                if verify_password(password, old_hash):
                    fail(
                        "password_reuse",
                        "This password has been used recently. Choose one you "
                        "have not used before.",
                    )
                    break
            except Exception:  # noqa: BLE001
                # A corrupt history entry must not lock the user out of
                # changing their password. Skip it.
                continue

    return PasswordCheck(not violations, violations, messages)
