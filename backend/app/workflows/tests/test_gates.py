"""Role gates (MANAGER_ROLES L1 / ADMIN_ROLES final) and tenant isolation."""
from .conftest import (
    H_ADMIN,
    H_ASSOC,
    H_MGR,
    H_PAY,
    HA_ADMIN,
    HB_ADMIN,
    TENANT_A,
    client,
)


def test_associate_decide_is_403():
    r = client.post(
        "/api/v1/workflows/expense_claim/102/decide",
        headers=H_ASSOC,
        json={"action": "approve", "comment": "self approve"},
    )
    assert r.status_code == 403, r.text


def test_payrollviewer_decide_is_403():
    r = client.post(
        "/api/v1/workflows/expense_claim/103/decide",
        headers=H_PAY,
        json={"action": "approve", "comment": "x"},
    )
    assert r.status_code == 403, r.text


def test_manager_final_approve_is_403():
    r = client.post(
        "/api/v1/workflows/expense_claim/104/decide",
        headers=H_MGR,
        json={"action": "approve", "comment": "l1"},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/api/v1/workflows/expense_claim/104/decide",
        headers=H_MGR,
        json={"action": "approve", "comment": "final by manager"},
    )
    assert r.status_code == 403, r.text


def test_manager_reject_is_allowed():
    r = client.post(
        "/api/v1/workflows/expense_claim/105/decide",
        headers=H_MGR,
        json={"action": "reject", "comment": "not eligible"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "REJECTED"


def test_unknown_entity_type_is_404():
    r = client.post(
        "/api/v1/workflows/time_off/106/decide",
        headers=H_ADMIN,
        json={"action": "approve", "comment": "x"},
    )
    assert r.status_code == 404, r.text


def test_history_without_trail_is_404():
    r = client.get("/api/v1/workflows/asset/99991/history", headers=H_ADMIN)
    assert r.status_code == 404, r.text


def test_cross_tenant_history_is_404():
    r = client.post(
        "/api/v1/workflows/document/501/decide",
        headers=HA_ADMIN,
        json={"action": "approve", "comment": "tenant a l1"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["tenant_id"] == TENANT_A
    r = client.get("/api/v1/workflows/document/501/history", headers=HB_ADMIN)
    assert r.status_code == 404, r.text
    r = client.get("/api/v1/workflows/document/501/history", headers=HA_ADMIN)
    assert r.status_code == 200 and len(r.json()) == 2, r.text
