"""End-to-end MVP flow: login -> group -> invite/join -> bill -> balances."""

from tests.conftest import auth, login


def test_full_flow(client):
    alice_tok, alice = login(client, "alice@example.com", "Alice")
    bob_tok, bob = login(client, "bob@example.com", "Bob")

    # Alice creates a group.
    r = client.post("/groups", json={"name": "Trip"}, headers=auth(alice_tok))
    assert r.status_code == 200, r.text
    group_id = r.json()["id"]

    # Alice invites; Bob accepts.
    r = client.post(f"/groups/{group_id}/invites", json={}, headers=auth(alice_tok))
    token = r.json()["token"]
    r = client.post(f"/invites/{token}/accept", headers=auth(bob_tok))
    assert r.status_code == 200, r.text

    members = client.get(f"/groups/{group_id}/members", headers=auth(alice_tok)).json()
    assert {m["user_id"] for m in members} == {alice, bob}

    # Alice pays a $44 bill: her $30 item, Bob's $10 item, $4 tax + $8 tip (cents).
    bill = {
        "title": "Dinner",
        "payer_id": alice,
        "tax": 400,
        "tip": 800,
        "items": [
            {"name": "Steak", "price": 3000, "shares": {alice: 1}},
            {"name": "Salad", "price": 1000, "shares": {bob: 1}},
        ],
    }
    r = client.post(f"/groups/{group_id}/bills", json=bill, headers=auth(alice_tok))
    assert r.status_code == 200, r.text
    body = r.json()
    shares = {s["user_id"]: s["amount"] for s in body["shares"]}
    assert shares == {alice: 3900, bob: 1300}
    assert body["total"] == 5200
    assert sum(shares.values()) == body["total"]  # conservation (C1)

    # Balances: Bob owes Alice $13.00; one transfer.
    r = client.get(f"/groups/{group_id}/balances", headers=auth(bob_tok))
    assert r.status_code == 200, r.text
    bal = r.json()
    assert bal["balances"] == {str(alice): 1300, str(bob): -1300}
    assert bal["transfers"] == [{"debtor": bob, "creditor": alice, "amount": 1300}]


def test_non_member_cannot_view_balances(client):
    alice_tok, _ = login(client, "alice@example.com", "Alice")
    intruder_tok, _ = login(client, "eve@example.com", "Eve")
    group_id = client.post("/groups", json={"name": "Private"}, headers=auth(alice_tok)).json()["id"]

    r = client.get(f"/groups/{group_id}/balances", headers=auth(intruder_tok))
    assert r.status_code == 403


def test_bill_rejects_non_member_payer(client):
    alice_tok, alice = login(client, "alice@example.com", "Alice")
    group_id = client.post("/groups", json={"name": "Solo"}, headers=auth(alice_tok)).json()["id"]

    bill = {
        "title": "x",
        "payer_id": 999,  # not a member
        "items": [{"name": "a", "price": 100, "shares": {alice: 1}}],
    }
    r = client.post(f"/groups/{group_id}/bills", json=bill, headers=auth(alice_tok))
    assert r.status_code == 422


def test_requires_auth(client):
    assert client.get("/groups").status_code == 401


def test_reduction_metric_on_chain(client):
    # A pays for B and C; separately B pays a bill for C. Simplify should net these.
    a_tok, a = login(client, "a@x.com", "A")
    b_tok, b = login(client, "b@x.com", "B")
    c_tok, c = login(client, "c@x.com", "C")
    gid = client.post("/groups", json={"name": "G"}, headers=auth(a_tok)).json()["id"]
    for tok in (b_tok, c_tok):
        t = client.post(f"/groups/{gid}/invites", json={}, headers=auth(a_tok)).json()["token"]
        client.post(f"/invites/{t}/accept", headers=auth(tok))

    # A fronts $30 split among B and C.
    client.post(
        f"/groups/{gid}/bills",
        json={
            "title": "A pays",
            "payer_id": a,
            "items": [{"name": "shared", "price": 3000, "shares": {b: 1, c: 1}}],
        },
        headers=auth(a_tok),
    )
    # B fronts $10 for C.
    client.post(
        f"/groups/{gid}/bills",
        json={
            "title": "B pays",
            "payer_id": b,
            "items": [{"name": "c item", "price": 1000, "shares": {c: 1}}],
        },
        headers=auth(b_tok),
    )

    bal = client.get(f"/groups/{gid}/balances", headers=auth(a_tok)).json()
    # Everyone nets out through the transfers.
    net = {a: 0, b: 0, c: 0}
    for t in bal["transfers"]:
        net[t["debtor"]] -= t["amount"]
        net[t["creditor"]] += t["amount"]
    assert net == {int(k): v for k, v in bal["balances"].items()} | {
        u: 0 for u in (a, b, c) if str(u) not in bal["balances"]
    }
    assert bal["simplified"] <= bal["baseline"]
