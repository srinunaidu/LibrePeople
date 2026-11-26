"""The R2/S3 storage backend suite.

What is proven here
-------------------
* A save/read round-trip through ``S3CompatibleStorage`` (against moto's
  in-memory S3, no network) returns the exact bytes.
* The checksum travels as object metadata and ``save_verified`` passes.
* ``save_verified`` raises ``ChecksumMismatch`` when the read-back differs
  (simulated by corrupting the object after the write).
* ``exists``/``delete`` behave, and oversized or content-type-less uploads
  are refused before they reach the network.
* ``get_storage`` with ``STORAGE_BACKEND=s3`` and full R2 configuration
  returns the S3 backend; with missing R2 values it falls back to local
  instead of crashing the boot.

Run:  PYTHONPATH=/tmp/r2deps:. python r2_storage_test_suite.py
Requires boto3 + moto (scratch installs under /tmp/r2deps, not the repo).
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["STORAGE_BACKEND"] = "local"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import boto3  # noqa: F401
    from moto import mock_aws  # noqa: F401
except ModuleNotFoundError as _s3_import_error:
    _S3_IMPORT_ERROR = _s3_import_error
else:
    _S3_IMPORT_ERROR = None


def _require_s3_deps():
    # moto/boto3 are scratch-only deps (see docstring: /tmp/r2deps). Shared
    # envs are never pip-installed into, so their absence skips, not fails.
    if _S3_IMPORT_ERROR is not None:
        raise _SuiteSkipped(
            f"optional scratch deps unavailable ({_S3_IMPORT_ERROR}); install "
            "boto3+moto under /tmp/r2deps per the suite docstring"
        )


passed = 0
failed = 0
skipped = 0


class _SuiteSkipped(Exception):
    """The suite cannot prove anything without its optional scratch deps."""


def check(name, fn):
    global passed, failed, skipped
    try:
        fn()
    except _SuiteSkipped as exc:
        skipped += 1
        print(f"SKIP {name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        failed += 1
        print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    else:
        passed += 1
        print(f"ok {name}")


def make_storage():
    _require_s3_deps()
    from moto import mock_aws
    from app.storage.s3 import S3CompatibleStorage

    mock = mock_aws()
    mock.start()
    import boto3

    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
    storage = S3CompatibleStorage(
        endpoint_url=None,  # default endpoint: moto intercepts it; a real
        # R2 URL would bypass the mock and hit the network.
        bucket="test-bucket",
        access_key_id="test-key",
        secret_access_key="test-secret",
        region="auto",
    )
    return mock, storage


def test_round_trip():
    mock, storage = make_storage()
    try:
        data = b"offer letter bytes \xe2\x82\xb9"
        storage.save("docs/offer-1.pdf", data, "application/pdf")
        assert storage.read("docs/offer-1.pdf") == data
        assert storage.exists("docs/offer-1.pdf")
    finally:
        mock.stop()


def test_checksum_metadata_and_save_verified():
    mock, storage = make_storage()
    try:
        from app.storage.backends import checksum

        data = b"verified payload"
        storage.save_verified("docs/verified.csv", data, "text/csv")
        assert storage.checksum("docs/verified.csv") == checksum(data)
    finally:
        mock.stop()


def test_save_verified_mismatch_raises():
    mock, storage = make_storage()
    try:
        from app.storage.backends import ChecksumMismatch

        data = b"original bytes"
        real_head = storage.client.head_object

        def wrong_metadata(**kwargs):
            response = real_head(**kwargs)
            response["Metadata"] = {"sha256": "0" * 64}
            return response

        storage.client.head_object = wrong_metadata
        try:
            storage.save_verified("docs/fragile.bin", data)
        except ChecksumMismatch:
            return
        finally:
            storage.client.head_object = real_head
        raise AssertionError("save_verified did not raise ChecksumMismatch")
    finally:
        mock.stop()


def test_delete_and_exists():
    mock, storage = make_storage()
    try:
        from app.storage.backends import StorageError

        assert not storage.exists("docs/gone.txt")
        storage.save("docs/gone.txt", b"bye", "text/plain")
        assert storage.exists("docs/gone.txt")
        assert storage.delete("docs/gone.txt")
        assert not storage.exists("docs/gone.txt")
        try:
            storage.read("docs/gone.txt")
        except StorageError:
            return
        raise AssertionError("read after delete did not raise StorageError")
    finally:
        mock.stop()


def test_validation_hooks():
    mock, storage = make_storage()
    try:
        from app.storage.backends import StorageError
        from app.storage.s3 import MAX_OBJECT_BYTES

        for key, data, ctype in (
            ("/absolute.txt", b"x", "text/plain"),
            ("", b"x", "text/plain"),
            ("docs/big.bin", b"x" * (MAX_OBJECT_BYTES + 1), "application/octet-stream"),
            ("docs/nocontent.bin", b"x", ""),
        ):
            try:
                storage.save(key, data, ctype)
            except StorageError:
                continue
            raise AssertionError(f"save accepted invalid input: {key!r}")
    finally:
        mock.stop()


def test_url_for_is_presigned():
    mock, storage = make_storage()
    try:
        storage.save("docs/secret.pdf", b"private", "application/pdf")
        url = storage.url_for("docs/secret.pdf")
        assert "test-bucket" in url and "docs/secret.pdf" in url
        assert not url.startswith("s3://"), "expected a presigned https URL"
    finally:
        mock.stop()


def test_get_storage_wiring():
    _require_s3_deps()
    from app.core.config import settings
    from app.storage.backends import LocalStorage, get_storage
    from app.storage.s3 import S3CompatibleStorage

    old = (
        settings.STORAGE_BACKEND,
        settings.R2_ENDPOINT_URL,
        settings.R2_BUCKET,
        settings.R2_ACCESS_KEY_ID,
        settings.R2_SECRET_ACCESS_KEY,
    )
    try:
        # Missing R2 values: fall back to local, never crash.
        settings.STORAGE_BACKEND = "s3"
        settings.R2_ENDPOINT_URL = None
        settings.R2_BUCKET = None
        settings.R2_ACCESS_KEY_ID = None
        settings.R2_SECRET_ACCESS_KEY = None
        assert isinstance(get_storage(), LocalStorage)

        # Full R2 configuration: the S3 backend (boto3 client build needs
        # no network, so this works offline).
        settings.R2_ENDPOINT_URL = "https://r2.test.invalid"
        settings.R2_BUCKET = "test-bucket"
        settings.R2_ACCESS_KEY_ID = "test-key"
        settings.R2_SECRET_ACCESS_KEY = "test-secret"
        assert isinstance(get_storage(), S3CompatibleStorage)
    finally:
        (
            settings.STORAGE_BACKEND,
            settings.R2_ENDPOINT_URL,
            settings.R2_BUCKET,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
        ) = old


if __name__ == "__main__":
    for name, fn in sorted(
        {k: v for k, v in globals().items() if k.startswith("test_")}.items()
    ):
        check(name, fn)
    print(f"\n{passed} passed, {skipped} skipped, {failed} failed")
    sys.exit(1 if failed else 0)
