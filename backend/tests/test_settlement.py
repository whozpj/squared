import random

from app.services.settlement import (
    Obligation,
    Transfer,
    net_balances,
    net_pairwise_count,
    reduction,
    simplify_debts,
)

import pytest


def test_simple_chain_collapses():
    # A owes B $10, B owes C $10  ->  A pays C $10 (one transfer instead of two).
    obligations = [
        Obligation(debtor=1, creditor=2, amount=1000),
        Obligation(debtor=2, creditor=3, amount=1000),
    ]
    transfers = simplify_debts(net_balances(obligations))
    assert transfers == [Transfer(debtor=1, creditor=3, amount=1000)]


def test_balances_must_sum_to_zero():
    with pytest.raises(ValueError):
        simplify_debts({1: 100, 2: 50})


def test_transfers_conserve_money_and_clear_balances():
    balances = {1: -700, 2: -300, 3: 500, 4: 500}
    transfers = simplify_debts(balances)
    # Every debtor's outflow and creditor's inflow matches their balance.
    net = {u: 0 for u in balances}
    for t in transfers:
        net[t.debtor] -= t.amount
        net[t.creditor] += t.amount
    assert net == balances
    # At most n-1 transfers.
    assert len(transfers) <= len(balances) - 1


def test_reduction_metric_is_honest():
    # 4 people each owe the payer (user 4) on one bill, and separately user 4
    # owes user 1. Net-pairwise has several edges; simplified has fewer.
    obligations = [
        Obligation(debtor=1, creditor=4, amount=1000),
        Obligation(debtor=2, creditor=4, amount=1000),
        Obligation(debtor=3, creditor=4, amount=1000),
        Obligation(debtor=4, creditor=1, amount=600),
    ]
    r = reduction(obligations)
    assert r["baseline"] == net_pairwise_count(obligations)
    assert r["simplified"] <= r["baseline"]
    assert 0 <= r["reduction_pct"] <= 100


def test_no_transfers_when_settled():
    assert simplify_debts({}) == []
    assert simplify_debts({1: 0, 2: 0}) == []


def test_property_conserves_and_bounded():
    rng = random.Random(7)
    for _ in range(500):
        n = rng.randint(2, 8)
        users = list(range(1, n + 1))
        # Build random obligations, then settle the net.
        obligations = []
        for _ in range(rng.randint(1, 12)):
            a, b = rng.sample(users, 2)
            obligations.append(Obligation(debtor=a, creditor=b, amount=rng.randint(1, 5000)))
        balances = net_balances(obligations)
        transfers = simplify_debts(balances)

        net = {u: 0 for u in balances}
        for t in transfers:
            net[t.debtor] -= t.amount
            net[t.creditor] += t.amount
        assert net == balances
        # The only hard guarantee: at most n-1 transfers among nonzero balances.
        # (Greedy is NOT provably optimal, and for an already-sparse pairwise
        # graph it can even exceed the pairwise count -- the ~40% reduction is an
        # average over realistic dense groups, not a per-input bound. See §6.)
        assert len(transfers) <= max(0, len(balances) - 1)
