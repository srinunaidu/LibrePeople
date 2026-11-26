"""CORS fail-closed regression tests (Team A / Security).

Production must refuse to boot when BACKEND_CORS_ORIGINS is empty
(same-origin default, i.e. a misconfigured deploy) or contains a wildcard
entry (Starlette treats "*" anywhere in allow_origins as allow-all).
Development keeps the safe same-origin default and boots.
"""

import os
import sys
from pathlib import Path

import pytest

# Same bootstrap as the sibling suites: backend/ on sys.path, and dummy env
# so the import-time settings = Settings(); settings.validate() passes.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "local-test-secret-key-not-for-production-0123456789")
os.environ.setdefault("MIGRATE_ON_STARTUP", "false")
os.environ.setdefault("BACKEND_CORS_ORIGINS", "")
os.environ.setdefault("ALLOW_SELF_REGISTRATION", "false")
os.environ.setdefault("LOG_LEVEL", "CRITICAL")
os.environ.setdefault("FIELD_ENCRYPTION_KEYS", "lp-test-key:local-test-field-encryption-secret-0123456789")
os.environ.setdefault("FIELD_ENCRYPTION_ACTIVE_KEY_ID", "lp-test-key")

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.core.config import Settings

_PROD_BASE = {
    "SECRET_KEY": "test-secret-key-that-is-long-enough-0123456789",
    "ENVIRONMENT": "production",
    "FIELD_ENCRYPTION_KEYS": "k1:" + "s" * 32,
    "FIELD_ENCRYPTION_ACTIVE_KEY_ID": "k1",
}

_DEV_BASE = {
    "SECRET_KEY": "dev-secret",
    "ENVIRONMENT": "development",
}


def _settings(**overrides):
    base = dict(_DEV_BASE)
    base.update(overrides)
    return Settings(**base)


def _prod_settings(**overrides):
    base = dict(_PROD_BASE)
    base.update(overrides)
    return Settings(**base)


def test_prod_empty_allowlist_refuses_to_boot():
    with pytest.raises(RuntimeError, match="BACKEND_CORS_ORIGINS"):
        _prod_settings(BACKEND_CORS_ORIGINS="").validate()


def test_prod_bare_wildcard_refuses_to_boot():
    with pytest.raises(RuntimeError, match="BACKEND_CORS_ORIGINS"):
        _prod_settings(BACKEND_CORS_ORIGINS="*").validate()


def test_prod_embedded_wildcard_refuses_to_boot():
    with pytest.raises(RuntimeError, match="BACKEND_CORS_ORIGINS"):
        _prod_settings(
            BACKEND_CORS_ORIGINS="https://app.example.com, *"
        ).validate()


def test_prod_exact_origins_boot():
    s = _prod_settings(BACKEND_CORS_ORIGINS="https://app.example.com")
    s.validate()  # must not raise
    assert s.cors_origins == ["https://app.example.com"]


def test_dev_empty_allowlist_boots_same_origin():
    s = _settings(BACKEND_CORS_ORIGINS="")
    s.validate()  # must not raise
    assert s.cors_origins == []


def test_dev_wildcard_boots():
    # Dev keeps the old lenient behaviour; only production is fail-closed.
    s = _settings(BACKEND_CORS_ORIGINS="*")
    s.validate()  # must not raise
    assert s.cors_origins == ["*"]
