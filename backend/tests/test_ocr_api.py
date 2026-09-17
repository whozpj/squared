"""OCR API: upload -> job runs -> parsed proposal -> apply reviewed items -> balances.

Uses a fake OCR provider so no Tesseract binary is needed.
"""

from app.workers import ocr_runner
from tests.conftest import auth, login

FAKE_RECEIPT = "BURGER 12.00\nFRIES 4.50\nSUBTOTAL 16.50\nTAX 1.00\nTOTAL 17.50\n"


class FakeProvider:
    def __init__(self, text: str):
        self.text = text

    def extract_text(self, image: bytes) -> str:  # noqa: ARG002
        return self.text


def _group_with_empty_bill(client):
    alice_tok, alice = login(client, "alice@example.com", "Alice")
    bob_tok, bob = login(client, "bob@example.com", "Bob")
    gid = client.post("/groups", json={"name": "G"}, headers=auth(alice_tok)).json()["id"]
    tok = client.post(f"/groups/{gid}/invites", json={}, headers=auth(alice_tok)).json()["token"]
    client.post(f"/invites/{tok}/accept", headers=auth(bob_tok))
    bill = client.post(
        f"/groups/{gid}/bills",
        json={"title": "Dinner", "payer_id": alice, "items": []},
        headers=auth(alice_tok),
    ).json()
    return (alice_tok, alice), (bob_tok, bob), gid, bill["id"]


def test_upload_parses_and_review_applies(client):
    (alice_tok, alice), (bob_tok, bob), gid, bill_id = _group_with_empty_bill(client)
    ocr_runner.provider = FakeProvider(FAKE_RECEIPT)

    r = client.post(
        f"/bills/{bill_id}/ocr",
        files={"file": ("receipt.png", b"not-a-real-image", "image/png")},
        headers=auth(alice_tok),
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]

    # Job ran inline -> done, with a reconciled proposal.
    job = client.get(f"/ocr/{job_id}", headers=auth(alice_tok)).json()
    assert job["status"] == "done", job
    parsed = job["parsed"]
    assert parsed["reconciled"] is True
    assert parsed["total"] == 1750
    assert [i["price"] for i in parsed["items"]] == [1200, 450]

    # User reviews: assigns the burger to Alice, fries to Bob; applies.
    apply = {
        "tax": parsed["tax"],
        "tip": 0,
        "items": [
            {"name": "Burger", "price": 1200, "shares": {alice: 1}},
            {"name": "Fries", "price": 450, "shares": {bob: 1}},
        ],
    }
    r = client.put(f"/bills/{bill_id}/items", json=apply, headers=auth(alice_tok))
    assert r.status_code == 200, r.text
    shares = {s["user_id"]: s["amount"] for s in r.json()["shares"]}
    assert sum(shares.values()) == r.json()["total"]  # conservation

    # Balances now reflect the applied bill.
    bal = client.get(f"/groups/{gid}/balances", headers=auth(alice_tok)).json()
    assert bal["balances"].get(str(bob), 0) < 0  # Bob owes


def test_ocr_status_pushed_over_websocket(client):
    (alice_tok, alice), (bob_tok, bob), gid, bill_id = _group_with_empty_bill(client)
    ocr_runner.provider = FakeProvider(FAKE_RECEIPT)

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": bob_tok})
        assert ws.receive_json()["type"] == "auth_ok"
        ws.send_json({"type": "subscribe", "group_id": gid})
        assert ws.receive_json()["type"] == "subscribed"

        client.post(
            f"/bills/{bill_id}/ocr",
            files={"file": ("r.png", b"x", "image/png")},
            headers=auth(alice_tok),
        )
        statuses = [ws.receive_json() for _ in range(2)]
        kinds = [(s["type"], s["status"]) for s in statuses]
        assert ("ocr.status", "processing") in kinds
        assert ("ocr.status", "done") in kinds


def test_apply_version_conflict(client):
    (alice_tok, alice), _bob, gid, bill_id = _group_with_empty_bill(client)
    apply = {
        "tax": 0,
        "tip": 0,
        "version": 999,  # stale
        "items": [{"name": "X", "price": 100, "shares": {alice: 1}}],
    }
    r = client.put(f"/bills/{bill_id}/items", json=apply, headers=auth(alice_tok))
    assert r.status_code == 409


def test_ocr_upload_requires_membership(client):
    (alice_tok, alice), _bob, gid, bill_id = _group_with_empty_bill(client)
    eve_tok, _ = login(client, "eve@example.com", "Eve")
    r = client.post(
        f"/bills/{bill_id}/ocr",
        files={"file": ("r.png", b"x", "image/png")},
        headers=auth(eve_tok),
    )
    assert r.status_code == 403
