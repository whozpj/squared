"""Payment handles on the profile + the email/nudge remind flow."""

from app.services.email import send_email
from tests.conftest import auth, login


def test_email_noop_without_key():
    # No RESEND_API_KEY in tests -> gracefully skipped, returns False.
    assert send_email("someone@example.com", "hi", "<p>hi</p>") is False


def test_update_and_read_payment_handles(client):
    tok, _ = login(client, "alice@example.com", "Alice")
    r = client.patch(
        "/auth/me",
        json={"venmo_handle": "@alice-v", "paypal_handle": "alicep", "cashapp_cashtag": "$alicec"},
        headers=auth(tok),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Leading @ / $ are stripped.
    assert body["venmo_handle"] == "alice-v"
    assert body["paypal_handle"] == "alicep"
    assert body["cashapp_cashtag"] == "alicec"
    # Persisted on /me.
    assert client.get("/auth/me", headers=auth(tok)).json()["venmo_handle"] == "alice-v"


def test_members_include_handles(client):
    alice_tok, alice = login(client, "alice@example.com", "Alice")
    client.patch("/auth/me", json={"venmo_handle": "alice-v"}, headers=auth(alice_tok))
    gid = client.post("/groups", json={"name": "G"}, headers=auth(alice_tok)).json()["id"]
    members = client.get(f"/groups/{gid}/members", headers=auth(alice_tok)).json()
    assert members[0]["venmo_handle"] == "alice-v"


def _group_two(client):
    alice_tok, alice = login(client, "alice@example.com", "Alice")
    bob_tok, bob = login(client, "bob@example.com", "Bob")
    gid = client.post("/groups", json={"name": "G"}, headers=auth(alice_tok)).json()["id"]
    tok = client.post(f"/groups/{gid}/invites", json={}, headers=auth(alice_tok)).json()["token"]
    client.post(f"/invites/{tok}/accept", headers=auth(bob_tok))
    return (alice_tok, alice), (bob_tok, bob), gid


def test_remind_creates_notification(client):
    (alice_tok, alice), (bob_tok, bob), gid = _group_two(client)
    r = client.post(
        f"/groups/{gid}/settle/remind", json={"to_user": bob, "amount": 1500}, headers=auth(alice_tok)
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["notified"] is True
    assert body["emailed"] is False  # no email key configured in tests

    # Bob got the nudge notification.
    notes = client.get("/notifications", headers=auth(bob_tok)).json()
    assert any(n["payload"] and n["payload"].get("owed_cents") == 1500 for n in notes)


def test_remind_rejects_non_member(client):
    (alice_tok, alice), _bob, gid = _group_two(client)
    r = client.post(
        f"/groups/{gid}/settle/remind", json={"to_user": 9999, "amount": 100}, headers=auth(alice_tok)
    )
    assert r.status_code == 422
