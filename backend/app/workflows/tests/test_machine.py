"""Stage machine: PENDING -> APPROVED | REJECTED | RETURNED, forward-only."""
from .conftest import H_ADMIN, H_MGR, client


def test_l1_then_final_approve_reaches_approved():
    r = client.post(
        "/api/v1/workflows/expense_claim/101/decide",
        headers=H_MGR,
        json={"action": "approve", "comment": "looks good"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "PENDING"
    assert r.json()["action"] == "L1_APPROVE"

    r = client.post(
        "/api/v1/workflows/expense_claim/101/decide",
        headers=H_ADMIN,
        json={"action": "approve", "comment": "final ok"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "APPROVED"
    assert r.json()["action"] == "APPROVE"


def test_decision_on_terminal_trail_is_409():
    r = client.post(
        "/api/v1/workflows/expense_claim/101/decide",
        headers=H_ADMIN,
        json={"action": "approve", "comment": "again"},
    )
    assert r.status_code == 409, r.text


def test_illegal_transition_writes_nothing():
    before = client.get("/api/v1/workflows/expense_claim/101/history", headers=H_ADMIN)
    assert before.status_code == 200, before.text
    n = len(before.json())
    r = client.post(
        "/api/v1/workflows/expense_claim/101/decide",
        headers=H_ADMIN,
        json={"action": "reject", "comment": "late"},
    )
    assert r.status_code == 409, r.text
    after = client.get("/api/v1/workflows/expense_claim/101/history", headers=H_ADMIN)
    assert len(after.json()) == n


def test_reject_requires_comment():
    r = client.post(
        "/api/v1/workflows/hr_case/201/decide",
        headers=H_MGR,
        json={"action": "reject"},
    )
    assert r.status_code == 422, r.text
    r = client.post(
        "/api/v1/workflows/hr_case/201/decide",
        headers=H_MGR,
        json={"action": "reject", "comment": "missing evidence"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "REJECTED"


def test_return_requires_comment_and_is_terminal():
    r = client.post(
        "/api/v1/workflows/hr_case/202/decide",
        headers=H_MGR,
        json={"action": "return", "comment": ""},
    )
    assert r.status_code == 422, r.text
    r = client.post(
        "/api/v1/workflows/hr_case/202/decide",
        headers=H_MGR,
        json={"action": "return", "comment": "send back for rework"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "RETURNED"
    r = client.post(
        "/api/v1/workflows/hr_case/202/decide",
        headers=H_MGR,
        json={"action": "approve", "comment": "late approve"},
    )
    assert r.status_code == 409, r.text


def test_unknown_action_is_422():
    r = client.post(
        "/api/v1/workflows/document/301/decide",
        headers=H_MGR,
        json={"action": "escalate", "comment": "x"},
    )
    assert r.status_code == 422, r.text


def test_due_at_honoured_when_opening_trail():
    r = client.post(
        "/api/v1/workflows/asset/401/decide",
        headers=H_MGR,
        json={"action": "approve", "comment": "ok", "due_at": "2030-01-01T00:00:00Z"},
    )
    assert r.status_code == 200, r.text
    history = client.get("/api/v1/workflows/asset/401/history", headers=H_ADMIN)
    assert history.status_code == 200, history.text
    rows = history.json()
    assert rows[0]["action"] == "OPEN"
    assert rows[0]["due_at"] is not None
