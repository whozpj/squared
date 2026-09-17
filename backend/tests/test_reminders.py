"""Idempotent debt reminders: one per debtor per week, no duplicates on re-run."""

from tests.conftest import auth, login


def _group_with_debt(client):
    alice_tok, alice = login(client, "alice@example.com", "Alice")
    bob_tok, bob = login(client, "bob@example.com", "Bob")
    gid = client.post("/groups", json={"name": "G"}, headers=auth(alice_tok)).json()["id"]
    tok = client.post(f"/groups/{gid}/invites", json={}, headers=auth(alice_tok)).json()["token"]
    client.post(f"/invites/{tok}/accept", headers=auth(bob_tok))
    # Alice fronts $20 that Bob owes -> Bob is a debtor.
    client.post(
        f"/groups/{gid}/bills",
        json={
            "title": "Bob's meal",
            "payer_id": alice,
            "items": [{"name": "meal", "price": 2000, "shares": {bob: 1}}],
        },
        headers=auth(alice_tok),
    )
    return (alice_tok, alice), (bob_tok, bob), gid


def test_reminder_created_for_debtor(client):
    (alice_tok, alice), (bob_tok, bob), gid = _group_with_debt(client)

    r = client.post("/dev/run-reminders", headers=auth(alice_tok))
    assert r.status_code == 200
    assert r.json()["created"] == 1  # only Bob (the debtor) gets one

    # Bob sees it; Alice (creditor) does not.
    bob_notes = client.get("/notifications", headers=auth(bob_tok)).json()
    assert len(bob_notes) == 1
    note = bob_notes[0]
    assert note["type"] == "debt_reminder"
    assert note["payload"]["owed_cents"] == 2000
    assert note["read"] is False

    alice_notes = client.get("/notifications", headers=auth(alice_tok)).json()
    assert alice_notes == []


def test_reminders_are_idempotent_within_week(client):
    (alice_tok, alice), (bob_tok, bob), gid = _group_with_debt(client)

    first = client.post("/dev/run-reminders", headers=auth(alice_tok)).json()["created"]
    second = client.post("/dev/run-reminders", headers=auth(alice_tok)).json()["created"]
    assert first == 1
    assert second == 0  # dedup_key prevents a duplicate

    bob_notes = client.get("/notifications", headers=auth(bob_tok)).json()
    assert len(bob_notes) == 1  # still exactly one


def test_mark_notification_read(client):
    (alice_tok, alice), (bob_tok, bob), gid = _group_with_debt(client)
    client.post("/dev/run-reminders", headers=auth(alice_tok))
    nid = client.get("/notifications", headers=auth(bob_tok)).json()[0]["id"]

    r = client.post(f"/notifications/{nid}/read", headers=auth(bob_tok))
    assert r.status_code == 200 and r.json()["read"] is True

    # Another user can't read/modify it.
    r = client.post(f"/notifications/{nid}/read", headers=auth(alice_tok))
    assert r.status_code == 404


def test_notification_pushed_over_websocket(client):
    (alice_tok, alice), (bob_tok, bob), gid = _group_with_debt(client)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": bob_tok})
        assert ws.receive_json()["type"] == "auth_ok"
        ws.send_json({"type": "subscribe", "group_id": gid})
        assert ws.receive_json()["type"] == "subscribed"

        client.post("/dev/run-reminders", headers=auth(alice_tok))
        evt = ws.receive_json()
        assert evt["type"] == "notification.new"
        assert evt["user_id"] == bob
