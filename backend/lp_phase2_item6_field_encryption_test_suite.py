"""LibrePeople Phase 2, item 6: field encryption without SECRET_KEY fallback.

Checks:

* Production refuses to start without FIELD_ENCRYPTION_KEYS or
  FIELD_ENCRYPTION_ACTIVE_KEY_ID.
* Production starts when both are set.
* encrypt_secret refuses to run without a registered key (no plaintext, no
  SECRET_KEY fallback).
* decrypt_secret rejects legacy (pre-versioning) values and unregistered
  key ids.
* Rotation still works: every registered key can decrypt, only the active
  key writes, and removing a key from the registry breaks its values.
* The key-rotation runbook exists.

Run:  python lp_phase2_item6_field_encryption_test_suite.py
"""
import base64
import hashlib
import os
import subprocess
import sys
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lp_item6_"), "item6_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

from cryptography.fernet import Fernet  # noqa: E402

from app.core import security  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.security import SecretDecryptionError  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNBOOK = os.path.join(REPO_ROOT, "docs", "runbooks", "field-key-rotation.md")

_PASS, _FAIL = [], []

TEST_KEYS = "lp-item6-test-key:lp-item6-test-secret-0123456789abcdef"


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        _FAIL.append((name, exc))
        print(f"FAIL  {name}: {exc!r}")
    else:
        _PASS.append(name)
        print(f"PASS  {name}")


def _run_startup(env_overrides):
    env = dict(os.environ)
    env.pop("FIELD_ENCRYPTION_KEYS", None)
    env.pop("FIELD_ENCRYPTION_ACTIVE_KEY_ID", None)
    env.update(env_overrides)
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.core.config import settings; print('started')",
        ],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env,
    )


def _set_encryption_env(keys, active):
    settings.FIELD_ENCRYPTION_KEYS = keys
    settings.FIELD_ENCRYPTION_ACTIVE_KEY_ID = active


def test_production_refuses_without_keys():
    r = _run_startup({"ENVIRONMENT": "production"})
    assert r.returncode != 0, "production must refuse to start without keys"
    assert "FIELD_ENCRYPTION_KEYS" in (r.stderr + r.stdout), r.stderr


def test_production_refuses_without_active_key_id():
    r = _run_startup(
        {
            "ENVIRONMENT": "production",
            "FIELD_ENCRYPTION_KEYS": "k1:lp-item6-test-secret-0123456789",
        }
    )
    assert r.returncode != 0, "production must refuse without active key id"
    assert "FIELD_ENCRYPTION_ACTIVE_KEY_ID" in (r.stderr + r.stdout), r.stderr


def test_production_starts_with_keys():
    r = _run_startup(
        {
            "ENVIRONMENT": "production",
            "FIELD_ENCRYPTION_KEYS": "k1:lp-item6-test-secret-0123456789",
            "FIELD_ENCRYPTION_ACTIVE_KEY_ID": "k1",
        }
    )
    assert r.returncode == 0, f"production must start with keys: {r.stderr}"


def test_encrypt_refuses_without_registered_key():
    saved = (settings.FIELD_ENCRYPTION_KEYS, settings.FIELD_ENCRYPTION_ACTIVE_KEY_ID)
    try:
        _set_encryption_env("", "")
        try:
            security.encrypt_secret("a secret")
        except SecretDecryptionError:
            pass
        else:
            raise AssertionError(
                "encrypt_secret must refuse without a registered key (no "
                "SECRET_KEY fallback, no plaintext)"
            )
    finally:
        _set_encryption_env(*saved)


def test_roundtrip_and_rotation():
    saved = (settings.FIELD_ENCRYPTION_KEYS, settings.FIELD_ENCRYPTION_ACTIVE_KEY_ID)
    try:
        _set_encryption_env("k1:lp-item6-test-secret-0123456789", "k1")
        value = security.encrypt_secret("hello world")
        assert value.startswith("ENCv1:k1:"), value
        assert security.decrypt_secret(value) == "hello world"

        # Add the second key; switch the active id.
        _set_encryption_env(
            "k2:lp-item6-test-secret-0123456789b,k1:lp-item6-test-secret-0123456789",
            "k2",
        )
        value2 = security.encrypt_secret("hello world")
        assert value2.startswith("ENCv1:k2:"), value2
        # Old values remain readable: every registered key can decrypt.
        assert security.decrypt_secret(value) == "hello world"
        assert security.decrypt_secret(value2) == "hello world"

        # Retire the old key: its values can no longer be decrypted.
        _set_encryption_env("k2:lp-item6-test-secret-0123456789b", "k2")
        try:
            security.decrypt_secret(value)
        except SecretDecryptionError:
            pass
        else:
            raise AssertionError("decrypt must fail for a retired key id")
    finally:
        _set_encryption_env(*saved)


def test_legacy_values_have_no_fallback():
    legacy_key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    )
    token = Fernet(legacy_key).encrypt(b"legacy-secret").decode("utf-8")
    try:
        security.decrypt_secret(token)
    except SecretDecryptionError:
        pass
    else:
        raise AssertionError(
            "legacy pre-versioning values must not decrypt: the SECRET_KEY "
            "fallback is removed"
        )
    try:
        security.decrypt_secret("ENCv1:unknown-id:AAAA")
    except SecretDecryptionError:
        pass
    else:
        raise AssertionError("decrypt must fail for unregistered key ids")


def test_status_reports_configured():
    saved = (settings.FIELD_ENCRYPTION_KEYS, settings.FIELD_ENCRYPTION_ACTIVE_KEY_ID)
    try:
        _set_encryption_env("k1:lp-item6-test-secret-0123456789", "k1")
        status = security.field_encryption_status()
        assert status["configured"] is True, status
        assert status["rotatable"] is True, status
        assert status["active_key_id"] == "k1", status
    finally:
        _set_encryption_env(*saved)


def test_rotation_runbook_exists():
    assert os.path.isfile(RUNBOOK), f"missing {RUNBOOK}"
    with open(RUNBOOK, encoding="utf-8") as fh:
        text = fh.read()
    assert "FIELD_ENCRYPTION_KEYS" in text, "runbook must name the registry"
    assert "rotat" in text.lower(), "runbook must document rotation"


def main():
    for name, fn in [
        ("production refuses to start without FIELD_ENCRYPTION_KEYS",
         test_production_refuses_without_keys),
        ("production refuses to start without FIELD_ENCRYPTION_ACTIVE_KEY_ID",
         test_production_refuses_without_active_key_id),
        ("production starts when FIELD_ENCRYPTION_KEYS and "
         "FIELD_ENCRYPTION_ACTIVE_KEY_ID are set", test_production_starts_with_keys),
        ("encrypt_secret refuses without a registered key",
         test_encrypt_refuses_without_registered_key),
        ("roundtrip and rotation with the key registry",
         test_roundtrip_and_rotation),
        ("legacy values have no SECRET_KEY fallback",
         test_legacy_values_have_no_fallback),
        ("field_encryption_status reports configured state",
         test_status_reports_configured),
        ("field-key-rotation.md runbook exists", test_rotation_runbook_exists),
    ]:
        check(name, fn)
    print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
    for name, exc in _FAIL:
        print(f"FAIL  {name}: {exc!r}")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
