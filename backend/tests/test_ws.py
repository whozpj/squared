"""Real-time sync: subscribers get balances.updated on mutations."""

from tests.conftest import auth, login


def _setup(client):
    alice_tok, alice = login(client, "alice@example.com", "Alice")
    bob_tok, bob = login(client, "bob@example.com", "Bob")
    gid = client.post("/groups", json={"name": "G"}, headers=auth(alice_tok)).json()["id"]
    tok = client.post(f"/groups/{gid}/invites", json={}, headers=auth(alice_tok)).json()["token"]
    client.post(f"/invites/{tok}/accept", headers=auth(bob_tok))
    return (alice_tok, alice), (bob_tok, bob), gid


def test_subscriber_receives_balances_update_on_new_bill(client):
    (alice_tok, alice), (bob_tok, bob), gid = _setup(client)

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": bob_tok})
        assert ws.receive_json()["type"] == "auth_ok"
        ws.send_json({"type": "subscribe", "group_id": gid})
        assert ws.receive_json() == {"type": "subscribed", "group_id": gid}

        # Alice posts a bill -> Bob's socket should get an invalidate event.
        client.post(
            f"/groups/{gid}/bills",
            json={
                "title": "Dinner",
                "payer_id": alice,
                "items": [{"name": "x", "price": 1000, "shares": {bob: 1}}],
            },
            headers=auth(alice_tok),
        )
        evt = ws.receive_json()
        assert evt == {"type": "balances.updated", "group_id": gid}


def test_ws_rejects_bad_token(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": "garbage"})
        # server closes the connection on bad auth
        try:
            ws.receive_json()
            assert False, "expected disconnect"
        except Exception:
            pass


def test_ws_non_member_cannot_subscribe(client):
    (alice_tok, alice), (bob_tok, bob), gid = _setup(client)
    eve_tok, _ = login(client, "eve@example.com", "Eve")
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": eve_tok})
        assert ws.receive_json()["type"] == "auth_ok"
        ws.send_json({"type": "subscribe", "group_id": gid})
        assert ws.receive_json() == {"type": "error", "detail": "not a member"}
