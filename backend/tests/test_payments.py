"""Payments: claim -> confirm, and its effect on balances."""

from tests.conftest import auth, login


def _group_with_bill(client):
    alice_tok, alice = login(client, "alice@example.com", "Alice")
    bob_tok, bob = login(client, "bob@example.com", "Bob")
    gid = client.post("/groups", json={"name": "G"}, headers=auth(alice_tok)).json()["id"]
    tok = client.post(f"/groups/{gid}/invites", json={}, headers=auth(alice_tok)).json()["token"]
    client.post(f"/invites/{tok}/accept", headers=auth(bob_tok))
    # Alice fronts $20 that Bob owes entirely.
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


def test_confirmed_payment_clears_balance(client):
    (alice_tok, alice), (bob_tok, bob), gid = _group_with_bill(client)

    # Before: Bob owes Alice $20.
    bal = client.get(f"/groups/{gid}/balances", headers=auth(alice_tok)).json()
    assert bal["balances"] == {str(alice): 2000, str(bob): -2000}

    # Bob claims he paid Alice $20.
    r = client.post(
        f"/groups/{gid}/payments", json={"to_user": alice, "amount": 2000}, headers=auth(bob_tok)
    )
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    assert r.json()["status"] == "claimed"

    # Claim alone does not change balances.
    bal = client.get(f"/groups/{gid}/balances", headers=auth(alice_tok)).json()
    assert bal["balances"] == {str(alice): 2000, str(bob): -2000}

    # Alice (recipient) confirms -> balances clear.
    r = client.post(f"/payments/{pid}/confirm", headers=auth(alice_tok))
    assert r.status_code == 200 and r.json()["status"] == "confirmed"
    bal = client.get(f"/groups/{gid}/balances", headers=auth(alice_tok)).json()
    assert bal["balances"] == {}


def test_only_recipient_can_confirm(client):
    (alice_tok, alice), (bob_tok, bob), gid = _group_with_bill(client)
    pid = client.post(
        f"/groups/{gid}/payments", json={"to_user": alice, "amount": 2000}, headers=auth(bob_tok)
    ).json()["id"]
    # Bob (the payer) cannot confirm his own payment.
    r = client.post(f"/payments/{pid}/confirm", headers=auth(bob_tok))
    assert r.status_code == 403


def test_cannot_pay_yourself(client):
    (alice_tok, alice), (bob_tok, bob), gid = _group_with_bill(client)
    r = client.post(
        f"/groups/{gid}/payments", json={"to_user": bob, "amount": 100}, headers=auth(bob_tok)
    )
    assert r.status_code == 422
