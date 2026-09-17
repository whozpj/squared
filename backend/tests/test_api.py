"""Smoke tests: the app boots and the compute endpoints return correct results."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_allocate_endpoint():
    payload = {
        "items": [
            {"price": 3000, "shares": {"1": 1}},
            {"price": 1000, "shares": {"2": 1}},
        ],
        "tax": 400,
        "tip": 800,
        "participants": [1, 2],
    }
    r = client.post("/compute/allocate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["shares"] == {"1": 3900, "2": 1300}
    assert body["total"] == 5200


def test_allocate_rejects_unassigned_item():
    payload = {"items": [{"price": 1000, "shares": {}}], "participants": [1]}
    r = client.post("/compute/allocate", json=payload)
    assert r.status_code == 422


def test_settle_endpoint():
    payload = {
        "obligations": [
            {"debtor": 1, "creditor": 2, "amount": 1000},
            {"debtor": 2, "creditor": 3, "amount": 1000},
        ]
    }
    r = client.post("/compute/settle", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["transfers"] == [{"debtor": 1, "creditor": 3, "amount": 1000}]
