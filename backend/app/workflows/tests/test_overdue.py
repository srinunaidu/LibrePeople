"""Overdue/escalation: caller-supplied due_at, NULL never overdue, notify-only scan."""
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models.ess_hr import Notification

from app.workflows import service as svc

from .conftest import (
    HA_ADMIN,
    HA_MGR,
    HB_ADMIN,
    H_ADMIN,
    H_MGR,
    TENANT_A,
    client,
)


def _past() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()


def _future() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()


def test_overdue_lists_only_caller_tenant_past_due():
    r = client.post(
        "/api/v1/workflows/expense_claim/701/decide",
        headers=HA_MGR,
        json={"action": "approve", "comment": "l1", "due_at": _past()},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/api/v1/workflows/expense_claim/702/decide",
        headers=HB_ADMIN,
        json={"action": "approve", "comment": "l1", "due_at": _past()},
    )
    assert r.status_code == 200, r.text

    r = client.get("/api/v1/workflows/overdue", headers=HA_ADMIN)
    assert r.status_code == 200, r.text
    ids = {(row["entity_type"], row["entity_id"]) for row in r.json()}
    assert ("expense_claim", 701) in ids
    assert ("expense_claim", 702) not in ids

    r = client.get("/api/v1/workflows/overdue?entity_type=hr_case", headers=HA_ADMIN)
    assert r.status_code == 200, r.text
    assert all(row["entity_type"] == "hr_case" for row in r.json())


def test_null_due_at_never_overdue():
    r = client.post(
        "/api/v1/workflows/document/703/decide",
        headers=H_MGR,
        json={"action": "approve", "comment": "no deadline"},
    )
    assert r.status_code == 200, r.text
    r = client.get("/api/v1/workflows/overdue", headers=H_ADMIN)
    assert r.status_code == 200, r.text
    assert ("document", 703) not in {
        (row["entity_type"], row["entity_id"]) for row in r.json()
    }


def test_future_due_at_not_overdue_terminal_not_overdue():
    r = client.post(
        "/api/v1/workflows/asset/704/decide",
        headers=H_MGR,
        json={"action": "approve", "comment": "l1", "due_at": _future()},
    )
    assert r.status_code == 200, r.text
    r = client.get("/api/v1/workflows/overdue", headers=H_ADMIN)
    assert ("asset", 704) not in {
        (row["entity_type"], row["entity_id"]) for row in r.json()
    }
    r = client.post(
        "/api/v1/workflows/expense_claim/701/decide",
        headers=HA_ADMIN,
        json={"action": "approve", "comment": "final"},
    )
    assert r.status_code == 200, r.text
    r = client.get("/api/v1/workflows/overdue", headers=HA_ADMIN)
    assert ("expense_claim", 701) not in {
        (row["entity_type"], row["entity_id"]) for row in r.json()
    }


def test_escalation_scan_is_notify_only_and_once():
    r = client.post(
        "/api/v1/workflows/hr_case/705/decide",
        headers=HA_MGR,
        json={"action": "approve", "comment": "l1", "due_at": _past()},
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        first = svc.scan_overdue_for_escalation(db)
        db.commit()
        assert first["scanned"] >= 1 and first["notified"] >= 1, first
        before = {
            (n.recipient_id, n.title, n.entity_type, n.entity_id)
            for n in db.query(Notification).filter(Notification.category == "workflow").all()
        }
        second = svc.scan_overdue_for_escalation(db)
        db.commit()
        after = {
            (n.recipient_id, n.title, n.entity_type, n.entity_id)
            for n in db.query(Notification).filter(Notification.category == "workflow").all()
        }
        assert before == after
        assert second["notified"] == 0, second
        from app.models.workflow_step import WorkflowStep

        actions = {
            row.action
            for row in db.query(WorkflowStep)
            .filter(
                WorkflowStep.entity_type == "hr_case",
                WorkflowStep.entity_id == 705,
            )
            .all()
        }
        assert actions == {"OPEN", "L1_APPROVE"}
    finally:
        db.close()


def test_every_decision_emits_exactly_one_notification():
    r = client.post(
        "/api/v1/workflows/document/706/decide",
        headers=H_MGR,
        json={"action": "approve", "comment": "l1"},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/api/v1/workflows/document/706/decide",
        headers=H_ADMIN,
        json={"action": "approve", "comment": "final"},
    )
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        count = (
            db.query(Notification)
            .filter(
                Notification.category == "workflow",
                Notification.entity_type == "document",
                Notification.entity_id == 706,
                Notification.title.like("Workflow %APPROVE:%"),
            )
            .count()
        )
    finally:
        db.close()
    assert count == 2, count
