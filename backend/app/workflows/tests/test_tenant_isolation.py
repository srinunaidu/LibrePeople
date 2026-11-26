"""Tenant-isolation probe: tenant B sees none of tenant A's trails."""
from .conftest import HA_ADMIN, HA_MGR, HB_ADMIN, H_ADMIN, client


def test_tenant_b_cannot_read_tenant_a_trail():
    r = client.post(
        "/api/v1/workflows/expense_claim/801/decide",
        headers=HA_MGR,
        json={"action": "approve", "comment": "a l1"},
    )
    assert r.status_code == 200, r.text
    r = client.get("/api/v1/workflows/expense_claim/801/history", headers=HB_ADMIN)
    assert r.status_code == 404, r.text


def test_tenant_b_decide_creates_separate_trail():
    r = client.post(
        "/api/v1/workflows/expense_claim/801/decide",
        headers=HB_ADMIN,
        json={"action": "approve", "comment": "b l1"},
    )
    assert r.status_code == 200, r.text
    r = client.get("/api/v1/workflows/expense_claim/801/history", headers=HB_ADMIN)
    assert r.status_code == 200, r.text
    assert len(r.json()) == 2
    assert all(row["tenant_id"] != "tenant-wf-a" for row in r.json())


def test_default_tenant_cannot_read_named_tenant_trail():
    r = client.get("/api/v1/workflows/expense_claim/801/history", headers=H_ADMIN)
    assert r.status_code == 404, r.text
