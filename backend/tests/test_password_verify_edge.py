"""Password-verify edge cases: non-str input must not crash.

verify_password() must return False (never raise AttributeError/TypeError)
for bytes/None/empty/int passwords, and password_hash_needs_upgrade() must
stay exception-free for non-str hashes. Normal and legacy-hash paths still
verify correctly.
"""

import bcrypt

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("SECRET_KEY", "local-test-secret-key-not-for-production-0123456789")
os.environ.setdefault("BACKEND_CORS_ORIGINS", "")
os.environ.setdefault("ALLOW_SELF_REGISTRATION", "false")
os.environ.setdefault("LOG_LEVEL", "CRITICAL")
os.environ.setdefault("FIELD_ENCRYPTION_KEYS", "lp-test-key:local-test-field-encryption-secret-0123456789")
os.environ.setdefault("FIELD_ENCRYPTION_ACTIVE_KEY_ID", "lp-test-key")

from app.core.security import (  # noqa: E402
    get_password_hash,
    password_hash_needs_upgrade,
    verify_password,
)


def _legacy_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def test_bytes_password_returns_false():
    hashed = get_password_hash("CorrectHorse123")
    assert verify_password(b"CorrectHorse123", hashed) is False


def test_none_password_returns_false():
    hashed = get_password_hash("CorrectHorse123")
    assert verify_password(None, hashed) is False  # type: ignore[arg-type]


def test_empty_password_returns_false():
    hashed = get_password_hash("CorrectHorse123")
    assert verify_password("", hashed) is False


def test_int_password_returns_false():
    hashed = get_password_hash("CorrectHorse123")
    assert verify_password(12345, hashed) is False  # type: ignore[arg-type]


def test_non_str_hash_never_raises():
    assert verify_password("anything", None) is False  # type: ignore[arg-type]
    assert verify_password("anything", b"") is False  # type: ignore[arg-type]
    assert verify_password("anything", 123) is False  # type: ignore[arg-type]
    assert password_hash_needs_upgrade(None) is True  # type: ignore[arg-type]
    assert password_hash_needs_upgrade(123) is True  # type: ignore[arg-type]


def test_normal_path_still_passes():
    hashed = get_password_hash("CorrectHorse123")
    assert verify_password("CorrectHorse123", hashed) is True
    assert verify_password("WrongPassword999", hashed) is False


def test_legacy_hash_path_still_passes():
    hashed = _legacy_hash("LegacyPass123")
    assert verify_password("LegacyPass123", hashed) is True
    assert verify_password("WrongPassword999", hashed) is False
    assert password_hash_needs_upgrade(hashed) is True
    assert password_hash_needs_upgrade(get_password_hash("x")) is False
