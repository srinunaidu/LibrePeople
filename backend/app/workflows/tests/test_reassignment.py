"""Assignment/reassignment: admin-only, tenant-scoped, audited, stage-preserving."""
from app.core.database import SessionLocal
from app.models.audit import AuditLog
from app.models.user import User

from .conftest import H_ADMIN, H_MGR, HA_ADMIN, HB_ADMIN, client


def _user_id(username: str) -> int:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).one().id
    finally:
        db.close()


def test_admin_reassign_keeps_stage_and_records_target():
    mgr2 = _user_id("wf_mgr2")
    r = client.post(
        "/api/v1/workflows/hr_case/601/decide",
        headers=H_MGR,
        json={"action": "approve", "comment": "l1"},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/api/v1/workflows/hr_case/601/reassign",
        headers=H_ADMIN,
        json={"to_user": mgr2, "comment": "workload rebalance"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stage"] == "PENDING"
    assert body["action"] == "REASSIGN"
    assert f"reassigned_to:{mgr2}" in (body["comment"] or "")
    history = client.get("/api/v1/workflows/hr_case/601/history", headers=H_ADMIN)
    assert [row["action"] for row in history.json()] == ["OPEN", "L1_APPROVE", "REASSIGN"]


def test_reassign_is_audited():
    db = SessionLocal()
    try:
        rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "workflow_reassign",
                AuditLog.entity_type == "WorkflowStep",
            )
            .all()
        )
    finally:
        db.close()
    assert len(rows) >= 1


def test_manager_reassign_is_403():
    mgr2 = _user_id("wf_mgr2")
    r = client.post(
        "/api/v1/workflows/hr_case/601/reassign",
        headers=H_MGR,
        json={"to_user": mgr2},
    )
    assert r.status_code == 403, r.text


def test_reassign_unknown_user_is_404():
    r = client.post(
        "/api/v1/workflows/hr_case/601/reassign",
        headers=H_ADMIN,
        json={"to_user": 987654321},
    )
    assert r.status_code == 404, r.text


def test_reassign_terminal_trail_is_409():
    mgr2 = _user_id("wf_mgr2")
    r = client.post(
        "/api/v1/workflows/hr_case/602/decide",
        headers=H_MGR,
        json={"action": "reject", "comment": "nope"},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/api/v1/workflows/hr_case/602/reassign",
        headers=H_ADMIN,
        json={"to_user": mgr2},
    )
    assert r.status_code == 409, r.text


def test_reassign_without_trail_is_404():
    mgr2 = _user_id("wf_mgr2")
    r = client.post(
        "/api/v1/workflows/asset/99992/reassign",
        headers=H_ADMIN,
        json={"to_user": mgr2},
    )
    assert r.status_code == 404, r.text


def test_reassign_cross_tenant_trail_is_404():
    mgr2 = _user_id("wf_mgr2")
    r = client.post(
        "/api/v1/workflows/document/603/decide",
        headers=HA_ADMIN,
        json={"action": "approve", "comment": "a l1"},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/api/v1/workflows/document/603/reassign",
        headers=HB_ADMIN,
        json={"to_user": mgr2},
    )
    assert r.status_code == 404, r.text
