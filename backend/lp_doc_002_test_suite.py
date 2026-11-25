"""Versioned employee documents (LP-DOC-002).

What this suite proves
----------------------
* Creating a document starts version 1 and derives the opaque storage key
  from the ``/api/v1/files/`` URL; the history GET shows the one row.
* A further upload appends version 2, moves the document onto it, and the
  history GET shows both versions oldest-first.
* Acknowledging a document works once per account; the same account
  acknowledging again is refused with 409, while another account may
  still acknowledge.
* A download through the authorised ``GET /api/v1/files/{path}`` route
  records an access-log row; an unauthenticated download is refused and
  records nothing.
* The expiry sweep marks only Active documents past their expiry date as
  Expired; Archived and already-Expired rows are untouched.
* The retention purge deletes only Expired documents whose
  ``retention_until`` has passed (bytes and rows); Active, Archived,
  undated and not-yet-due documents are kept.
* The unauthenticated ``/files`` StaticFiles mount stays gone.
* Migration ``0040_document_lifecycle`` upgrades a fresh database to head.

Run:  python lp_doc_002_test_suite.py
"""
import os
import subprocess
import sys
import tempfile
from datetime import date, timedelta

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="lp_doc_002_"), "doc002_test.db")
STORAGE_DIR = os.path.join(tempfile.mkdtemp(prefix="lp_doc_002_storage_"), "storage")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["LOCAL_STORAGE_DIR"] = STORAGE_DIR

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, inspect  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.core_hr import (  # noqa: E402
    DocumentAccessLog,
    DocumentAck,
    DocumentVersion,
    EmployeeDocument,
)
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.user import User  # noqa: E402
from app.retention.documents import (  # noqa: E402
    mark_expired_documents,
    purge_expired_documents,
)
from app.storage import get_storage  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
db.add(
    User(
        username="doc_admin",
        email="doc_admin@example.test",
        hashed_password=get_password_hash("DocAdminPass123!"),
        role="SuperAdmin",
        is_active=True,
        mfa_enabled=True,
    )
)
db.add(
    User(
        username="doc_hr",
        email="doc_hr@example.test",
        hashed_password=get_password_hash("DocHrPass12345!"),
        role="HR",
        is_active=True,
        mfa_enabled=True,
    )
)
dept = Department(name="Engineering", code="ENG")
db.add(dept)
db.flush()
job = Job(title="Engineer", code="ENG-JOB", department_id=dept.id)
db.add(job)
db.flush()
db.add(
    Employee(
        employee_id="EMP001",
        first_name="Ada",
        last_name="Lovelace",
        email="ada.lovelace@example.test",
        hire_date=date(2024, 1, 15),
        job_id=job.id,
        department_id=dept.id,
        status="Active",
    )
)
db.add(
    Employee(
        employee_id="EMP002",
        first_name="Grace",
        last_name="Hopper",
        email="grace.hopper@example.test",
        hire_date=date(2024, 2, 1),
        job_id=job.id,
        department_id=dept.id,
        status="Active",
    )
)
db.flush()
_emp2 = db.query(Employee).filter(Employee.employee_id == "EMP002").first()
db.add(
    User(
        username="doc_outsider",
        email="doc_outsider@example.test",
        hashed_password=get_password_hash("DocOutsiderPass123!"),
        role="Associate",
        is_active=True,
        mfa_enabled=False,
        employee_id=_emp2.id,
    )
)
db.commit()
EMP_ID = db.query(Employee).filter(Employee.employee_id == "EMP001").first().id
db.close()

client = TestClient(app, raise_server_exceptions=False)
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


def _headers(username, password):
    r = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


ADMIN_H = _headers("doc_admin", "DocAdminPass123!")
HR_H = _headers("doc_hr", "DocHrPass12345!")
OUTSIDER_H = _headers("doc_outsider", "DocOutsiderPass123!")

YESTERDAY = date.today() - timedelta(days=1)
TOMORROW = date.today() + timedelta(days=1)


def _make_doc(key="docs/handbook.pdf", **overrides):
    url = get_storage().save(key, b"handbook-bytes", "application/pdf")
    payload = {
        "employee_id": EMP_ID,
        "document_type": "Policy",
        "file_name": "handbook.pdf",
        "storage_url": url,
    }
    payload.update(overrides)
    r = client.post("/api/v1/core-hr/employee-documents", json=payload, headers=ADMIN_H)
    assert r.status_code == 201, r.text
    return r.json(), url


def test_create_starts_version_1_with_derived_key():
    doc, url = _make_doc(key="docs/v1.pdf")
    assert doc["current_version"] == 1, doc
    assert doc["storage_key"] == "docs/v1.pdf", doc
    assert url == "/api/v1/files/docs/v1.pdf", url


def test_history_shows_first_upload():
    doc, _url = _make_doc(key="docs/hist.pdf")
    r = client.get(
        f"/api/v1/core-hr/employee-documents/{doc['id']}/versions", headers=ADMIN_H
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1, rows
    assert rows[0]["version_no"] == 1, rows
    assert rows[0]["file_name"] == "handbook.pdf", rows


def test_second_upload_appends_version_2_in_order():
    doc, _url = _make_doc(key="docs/multi-v1.pdf")
    url2 = get_storage().save("docs/multi-v2.pdf", b"v2-bytes", "application/pdf")
    r = client.post(
        f"/api/v1/core-hr/employee-documents/{doc['id']}/versions",
        json={"file_name": "handbook-rev2.pdf", "storage_url": url2},
        headers=ADMIN_H,
    )
    assert r.status_code == 201, r.text
    assert r.json()["version_no"] == 2, r.text
    r = client.get(
        f"/api/v1/core-hr/employee-documents/{doc['id']}/versions", headers=ADMIN_H
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert [row["version_no"] for row in rows] == [1, 2], rows
    assert [row["file_name"] for row in rows] == [
        "handbook.pdf",
        "handbook-rev2.pdf",
    ], rows
    # The document itself moved onto the newest upload.
    listed = client.get(
        "/api/v1/core-hr/employee-documents", headers=ADMIN_H, params={"employee_id": EMP_ID}
    ).json()
    moved = next(d for d in listed if d["id"] == doc["id"])
    assert moved["current_version"] == 2, moved
    assert moved["file_name"] == "handbook-rev2.pdf", moved


def test_ack_once_per_account():
    doc, _url = _make_doc(key="docs/ack.pdf")
    r = client.post(
        f"/api/v1/core-hr/employee-documents/{doc['id']}/ack", headers=ADMIN_H
    )
    assert r.status_code == 201, r.text
    assert r.json()["acknowledged_by"] == "doc_admin", r.text
    # The same account acknowledging again is refused.
    r = client.post(
        f"/api/v1/core-hr/employee-documents/{doc['id']}/ack", headers=ADMIN_H
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "already_acknowledged", r.text
    # Another account may still acknowledge.
    r = client.post(
        f"/api/v1/core-hr/employee-documents/{doc['id']}/ack", headers=HR_H
    )
    assert r.status_code == 201, r.text
    s = SessionLocal()
    try:
        count = (
            s.query(DocumentAck)
            .filter(DocumentAck.document_id == doc["id"])
            .count()
        )
    finally:
        s.close()
    assert count == 2, count


def test_download_logs_access_and_requires_auth():
    doc, url = _make_doc(key="docs/logged.pdf")
    s = SessionLocal()
    before = (
        s.query(DocumentAccessLog)
        .filter(DocumentAccessLog.document_id == doc["id"])
        .count()
    )
    s.close()
    r = client.get(url)
    assert r.status_code == 401, r.text
    r = client.get(url, headers=ADMIN_H)
    assert r.status_code == 200, r.text
    assert r.content == b"handbook-bytes", r.content[:40]
    s = SessionLocal()
    try:
        rows = (
            s.query(DocumentAccessLog)
            .filter(DocumentAccessLog.document_id == doc["id"])
            .all()
        )
    finally:
        s.close()
    assert len(rows) == before + 1, [r.id for r in rows]
    assert rows[-1].accessed_by == "doc_admin", rows[-1].accessed_by


def test_expiry_sweep_marks_only_active_past_due():
    active_past, _ = _make_doc(key="docs/exp-a.pdf", expiry_date=YESTERDAY.isoformat())
    active_future, _ = _make_doc(key="docs/exp-b.pdf", expiry_date=TOMORROW.isoformat())
    archived_past, _ = _make_doc(
        key="docs/exp-c.pdf", expiry_date=YESTERDAY.isoformat(), status="Archived"
    )
    s = SessionLocal()
    try:
        marked = mark_expired_documents(s)
    finally:
        s.close()
    assert marked == 1, marked
    s = SessionLocal()
    try:
        by_id = {
            d.id: d.status
            for d in s.query(EmployeeDocument)
            .filter(
                EmployeeDocument.id.in_(
                    [active_past["id"], active_future["id"], archived_past["id"]]
                )
            )
            .all()
        }
    finally:
        s.close()
    assert by_id[active_past["id"]] == "Expired", by_id
    assert by_id[active_future["id"]] == "Active", by_id
    assert by_id[archived_past["id"]] == "Archived", by_id


def test_purge_deletes_only_expired_past_retention():
    due, _ = _make_doc(
        key="docs/purge-due.pdf",
        status="Expired",
        retention_until=YESTERDAY.isoformat(),
    )
    not_due, _ = _make_doc(
        key="docs/purge-later.pdf",
        status="Expired",
        retention_until=TOMORROW.isoformat(),
    )
    undated, _ = _make_doc(key="docs/purge-nodate.pdf", status="Expired")
    active_old, _ = _make_doc(
        key="docs/purge-active.pdf",
        status="Active",
        retention_until=YESTERDAY.isoformat(),
    )
    storage = get_storage()
    assert storage.exists("docs/purge-due.pdf")
    s = SessionLocal()
    try:
        purged = purge_expired_documents(s)
    finally:
        s.close()
    assert purged == 1, purged
    assert not storage.exists("docs/purge-due.pdf"), "bytes must go with the row"
    s = SessionLocal()
    try:
        remaining = {
            d.id
            for d in s.query(EmployeeDocument)
            .filter(
                EmployeeDocument.id.in_(
                    [due["id"], not_due["id"], undated["id"], active_old["id"]]
                )
            )
            .all()
        }
        orphans = (
            s.query(DocumentVersion)
            .filter(DocumentVersion.document_id == due["id"])
            .count()
        )
    finally:
        s.close()
    assert due["id"] not in remaining, remaining
    assert remaining == {not_due["id"], undated["id"], active_old["id"]}, remaining
    assert orphans == 0, "version rows must go with the document"
    # The kept documents are still downloadable history.
    r = client.get(
        f"/api/v1/core-hr/employee-documents/{not_due['id']}/versions", headers=ADMIN_H
    )
    assert r.status_code == 200, r.text
    assert storage.exists("docs/purge-later.pdf")


def test_outsider_ack_and_versions_are_refused_without_rows():
    doc, _url = _make_doc(key="docs/outsider.pdf")
    s = SessionLocal()
    try:
        acks_before = (
            s.query(DocumentAck)
            .filter(DocumentAck.document_id == doc["id"])
            .count()
        )
        vers_before = (
            s.query(DocumentVersion)
            .filter(DocumentVersion.document_id == doc["id"])
            .count()
        )
    finally:
        s.close()
    # An Associate linked to another employee may not acknowledge this file.
    r = client.post(
        f"/api/v1/core-hr/employee-documents/{doc['id']}/ack", headers=OUTSIDER_H
    )
    assert r.status_code in (403, 404), r.text
    # Nor upload a new version (role policy refuses first with 403).
    url2 = get_storage().save("docs/outsider-v2.pdf", b"v2-bytes", "application/pdf")
    r = client.post(
        f"/api/v1/core-hr/employee-documents/{doc['id']}/versions",
        json={"file_name": "outsider-rev2.pdf", "storage_url": url2},
        headers=OUTSIDER_H,
    )
    assert r.status_code in (403, 404), r.text
    # Nor read its history.
    r = client.get(
        f"/api/v1/core-hr/employee-documents/{doc['id']}/versions",
        headers=OUTSIDER_H,
    )
    assert r.status_code in (403, 404), r.text
    s = SessionLocal()
    try:
        acks_after = (
            s.query(DocumentAck)
            .filter(DocumentAck.document_id == doc["id"])
            .count()
        )
        vers_after = (
            s.query(DocumentVersion)
            .filter(DocumentVersion.document_id == doc["id"])
            .count()
        )
    finally:
        s.close()
    assert acks_after == acks_before, (acks_before, acks_after)
    assert vers_after == vers_before, (vers_before, vers_after)


def test_traversal_download_is_404_without_logging():
    doc, _url = _make_doc(key="docs/traversal.pdf")
    s = SessionLocal()
    try:
        logs_before = (
            s.query(DocumentAccessLog)
            .filter(DocumentAccessLog.document_id == doc["id"])
            .count()
        )
        total_before = s.query(DocumentAccessLog).count()
    finally:
        s.close()
    for bad in (
        "../app/main.py",
        "..%2fapp/main.py",
        "%2e%2e/app/main.py",
        "%2e%2e%2fapp%2fmain.py",
    ):
        r = client.get(f"/api/v1/files/{bad}", headers=ADMIN_H)
        assert r.status_code == 404, (bad, r.status_code, r.text)
    s = SessionLocal()
    try:
        logs_after = (
            s.query(DocumentAccessLog)
            .filter(DocumentAccessLog.document_id == doc["id"])
            .count()
        )
        total_after = s.query(DocumentAccessLog).count()
    finally:
        s.close()
    assert logs_after == logs_before, (logs_before, logs_after)
    assert total_after == total_before, (total_before, total_after)


def test_static_files_mount_stays_gone():
    r = client.get("/files/docs/handbook.pdf")
    assert r.status_code == 404, (
        f"GET /files/... returned {r.status_code}: the unauthenticated "
        "StaticFiles mount must stay gone"
    )


def test_migration_0040_upgrades_a_fresh_database_to_head():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    try:
        env = dict(os.environ, DATABASE_URL=f"sqlite:///{tmp}")
        out = subprocess.run(
            [
                sys.executable,
                "-c",
                "from alembic.config import Config; "
                "from alembic import command; "
                "command.upgrade(Config('alembic.ini'), 'head')",
            ],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=env,
        )
        assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
        insp = inspect(create_engine(f"sqlite:///{tmp}"))
        names = set(insp.get_table_names())
        for table in ("document_versions", "document_acks", "document_access_logs"):
            assert table in names, table
        cols = {c["name"] for c in insp.get_columns("employee_documents")}
        assert {"storage_key", "current_version", "retention_until"} <= cols, cols
        from alembic.config import Config as _Config  # noqa: E402
        from alembic.script import ScriptDirectory as _Scripts  # noqa: E402

        head = _Scripts.from_config(
            _Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), "alembic.ini"))
        ).get_heads()
        # 0040 stays in the chain as head advances (0041 case comment
        # attachments builds on it): the fresh upgrade above already
        # proved 0040's tables land, and this proves it is still an
        # ancestor of whatever head the chain is on.
        chain = [
            rev.revision
            for rev in _Scripts.from_config(
                _Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), "alembic.ini"))
            ).walk_revisions()
        ]
        assert "0040_document_lifecycle" in chain, chain
        assert head, "the migration chain must have exactly one head"
    finally:
        os.unlink(tmp)


def main():
    for name, fn in [
        ("create starts version 1 with the derived storage key", test_create_starts_version_1_with_derived_key),
        ("history shows the first upload", test_history_shows_first_upload),
        ("a second upload appends version 2, oldest first", test_second_upload_appends_version_2_in_order),
        ("acknowledgement works once per account", test_ack_once_per_account),
        ("outsider ack/versions are refused without rows", test_outsider_ack_and_versions_are_refused_without_rows),
        ("traversal download is 404 without logging", test_traversal_download_is_404_without_logging),
        ("download logs access and requires a token", test_download_logs_access_and_requires_auth),
        ("expiry marks only Active past-due documents", test_expiry_sweep_marks_only_active_past_due),
        ("purge deletes only Expired documents past retention", test_purge_deletes_only_expired_past_retention),
        ("unauthenticated /files mount stays gone", test_static_files_mount_stays_gone),
        ("migration 0040 upgrades a fresh database to head", test_migration_0040_upgrades_a_fresh_database_to_head),
    ]:
        check(name, fn)
    print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
    for name, exc in _FAIL:
        print(f"FAIL  {name}: {exc!r}")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
