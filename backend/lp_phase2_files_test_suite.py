"""LibrePeople Phase 2, item 9: /files exposure and the authorised route.

Checks:

* The unauthenticated ``/files`` StaticFiles mount is gone.
* Stored documents are served through the authorised route
  ``GET /api/v1/files/{path}``: authenticated + path-safe (authorized path).
* Without a token the route refuses (unauthorised path).
* Path traversal is refused by the path resolver.
* ``url_for`` generates the authorised prefix.
* The migration logic rewrites stored ``/files/`` URLs on a temporary
  SQLite database, leaving other values untouched.
* The verification script reports the migrated state.

Run:  python lp_phase2_files_test_suite.py
"""
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lp_files_"), "files_test.db")
STORAGE_DIR = os.path.join(tempfile.mkdtemp(prefix="lp_files_storage_"), "storage")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"
os.environ["LOCAL_STORAGE_DIR"] = STORAGE_DIR

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app, _document_path  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.storage import LocalStorage, get_storage  # noqa: E402
from app.storage.url_rewrite import (  # noqa: E402
    NEW_PREFIX,
    OLD_PREFIX,
    count_legacy_files_urls,
    rewrite_prefix,
)

Base.metadata.create_all(bind=engine)
db = SessionLocal()
db.add(
    User(
        username="files_admin",
        email="files_admin@example.test",
        hashed_password=get_password_hash("AdminPass12345!"),
        role="SuperAdmin",
        is_active=True,
        mfa_enabled=True,  # item 10: privileged users are enrolled
        password_changed_at=datetime.now(timezone.utc),
    )
)
db.commit()
db.close()

client = TestClient(app)
_PASS, _FAIL = [], []


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        _FAIL.append((name, exc))
        print(f"FAIL  {name}: {exc!r}")
    else:
        _PASS.append(name)
        print(f"PASS  {name}")


def _headers():
    r = client.post(
        "/api/v1/auth/login", json={"username": "files_admin", "password": "AdminPass12345!"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_static_mount_removed():
    r = client.get("/files/anything.txt")
    assert r.status_code == 404, (
        f"GET /files/anything.txt returned {r.status_code}: the unauthenticated "
        "StaticFiles mount must be gone"
    )


def test_download_authorized():
    url = get_storage().save("docs/offer.pdf", b"offer-bytes", "application/pdf")
    assert url.startswith("/api/v1/files/"), url
    r = client.get(url, headers=_headers())
    assert r.status_code == 200, r.text
    assert r.content == b"offer-bytes"


def test_download_requires_auth():
    url = get_storage().save("docs/payslip.pdf", b"payslip-bytes")
    r = client.get(url)
    assert r.status_code == 401, (
        f"GET without a token returned {r.status_code}: the download route is "
        "unauthorised until a token is presented"
    )


def test_path_resolver_rejects_traversal():
    root = Path(settings.LOCAL_STORAGE_DIR).resolve()
    for bad in ("../etc/passwd", "/etc/passwd", "a/../../etc/passwd", "..", "\\\\server\\share"):
        assert _document_path(bad) is None, bad
    ok = _document_path("sub/dir/file.txt")
    assert ok is not None, "a normal relative key must resolve"
    assert ok == (root / "sub" / "dir" / "file.txt").resolve()


def test_url_for_uses_authorised_prefix():
    assert LocalStorage(settings.LOCAL_STORAGE_DIR).url_for("k") == "/api/v1/files/k"


def test_migration_rewrites_stored_urls():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    try:
        e = create_engine(f"sqlite:///{tmp}")
        with e.begin() as conn:
            conn.execute(
                text("CREATE TABLE documents (id INTEGER PRIMARY KEY, doc_url VARCHAR(255), notes TEXT)")
            )
            conn.execute(
                text(
                    "INSERT INTO documents (doc_url, notes) VALUES "
                    "('/files/a.pdf', 'x'), ('/files/b/c.pdf', NULL), "
                    "('plain.txt', 'keep'), ('/other/d.pdf', 'keep')"
                )
            )
        before = count_legacy_files_urls(e)
        assert len(before) == 1 and before[0]["rows"] == 2, before
        changed = rewrite_prefix(e, OLD_PREFIX, NEW_PREFIX)
        assert "documents.doc_url" in changed, changed
        with e.connect() as conn:
            rows = conn.execute(text("SELECT doc_url, notes FROM documents ORDER BY id")).all()
        assert [r[0] for r in rows] == [
            "/api/v1/files/a.pdf",
            "/api/v1/files/b/c.pdf",
            "plain.txt",
            "/other/d.pdf",
        ], rows
        assert [r[1] for r in rows][2] == "keep"
        assert count_legacy_files_urls(e) == []
        e.dispose()
    finally:
        os.unlink(tmp)


def test_verify_script_exit_zero_on_migrated_state():
    r = subprocess.run(
        [
            sys.executable,
            "scripts/verify_files_urls.py",
            "--database-url",
            f"sqlite:///{DB_PATH}",
        ],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_alembic_migration_rewrites_stored_urls():
    """The Alembic revision runs and rewrites stored URLs on temp SQLite."""
    import importlib.util
    from types import SimpleNamespace

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    e = create_engine(f"sqlite:///{tmp}")
    try:
        with e.begin() as conn:
            conn.execute(
                text("CREATE TABLE documents (id INTEGER PRIMARY KEY, doc_url VARCHAR(255), notes TEXT)")
            )
            conn.execute(
                text("INSERT INTO documents (doc_url, notes) VALUES ('/files/a.pdf', 'x'), ('/files/b/c.pdf', NULL)")
            )
        migration_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "migrations",
            "versions",
            "lp_files_url_rewrite.py",
        )
        spec = importlib.util.spec_from_file_location("lp_files_url_rewrite", migration_path)
        mig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mig)
        # Bind the migration's `op` proxy to the temporary engine.
        mig.op = SimpleNamespace(get_bind=lambda: e)
        mig.upgrade()
        with e.connect() as conn:
            rows = conn.execute(text("SELECT doc_url, notes FROM documents ORDER BY id")).all()
        assert [r[0] for r in rows] == ["/api/v1/files/a.pdf", "/api/v1/files/b/c.pdf"], rows
        assert count_legacy_files_urls(e) == []
    finally:
        e.dispose()
        os.unlink(tmp)


def main():
    for name, fn in [
        ("unauthenticated /files StaticFiles mount is gone", test_static_mount_removed),
        ("stored documents served through the authorised route (authorized path)", test_download_authorized),
        ("download route refuses without a token (unauthorised path)", test_download_requires_auth),
        ("path resolver rejects traversal", test_path_resolver_rejects_traversal),
        ("url_for generates the authorised prefix", test_url_for_uses_authorised_prefix),
        ("migration rewrites stored /files/ URLs on temporary SQLite", test_migration_rewrites_stored_urls),
        ("verification script exits 0 on the migrated state", test_verify_script_exit_zero_on_migrated_state),
        ("alembic migration rewrites stored /files/ URLs on temporary SQLite",
         test_alembic_migration_rewrites_stored_urls),
    ]:
        check(name, fn)
    print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
    for name, exc in _FAIL:
        print(f"FAIL  {name}: {exc!r}")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
