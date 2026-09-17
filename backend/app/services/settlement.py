"""Greedy debt simplification (see DESIGN.md §6).

Turns a group's net balances into a minimal-ish set of transfers, and measures
the reduction vs. a fair "net pairwise" baseline.

The exact minimum-transaction problem is NP-hard (subset-sum partition); this
greedy match-largest-creditor-with-largest-debtor approach is the standard
practical method (the same idea as Splitwise's "simplify debts"). It always
terminates, conserves money, and produces at most n-1 transfers.

Pure module (no I/O, no DB).
"""

from __future__ import annotations

import heapq
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Obligation:
    """A raw IOU: `debtor` owes `creditor` `amount` cents (amount > 0)."""

    debtor: int
    creditor: int
    amount: int


@dataclass(frozen=True)
class Transfer:
    """A settlement instruction: `debtor` pays `creditor` `amount` cents."""

    debtor: int
    creditor: int
    amount: int


def net_balances(obligations: list[Obligation]) -> dict[int, int]:
    """Collapse raw IOUs into a net balance per user (creditor positive)."""
    bal: dict[int, int] = defaultdict(int)
    for o in obligations:
        bal[o.creditor] += o.amount
        bal[o.debtor] -= o.amount
    return {u: b for u, b in bal.items() if b != 0}


def simplify_debts(balances: dict[int, int]) -> list[Transfer]:
    """Greedily settle net balances into transfers (at most n-1 of them).

    balances maps user_id -> net cents; positive = owed money (creditor),
    negative = owes money (debtor). Must sum to zero.
    """
    if sum(balances.values()) != 0:
        raise ValueError("balances must sum to zero to be settleable")

    # Max-heaps via negated magnitude; user id in the tuple makes ties deterministic.
    creditors = [(-amt, uid) for uid, amt in balances.items() if amt > 0]
    debtors = [(amt, uid) for uid, amt in balances.items() if amt < 0]  # amt<0 => most-negative first
    heapq.heapify(creditors)
    heapq.heapify(debtors)

    transfers: list[Transfer] = []
    while creditors and debtors:
        neg_credit, cu = heapq.heappop(creditors)
        neg_debit, du = heapq.heappop(debtors)
        credit = -neg_credit
        debit = -neg_debit
        pay = min(credit, debit)
        transfers.append(Transfer(debtor=du, creditor=cu, amount=pay))

        if credit - pay > 0:
            heapq.heappush(creditors, (-(credit - pay), cu))
        if debit - pay > 0:
            heapq.heappush(debtors, (-(debit - pay), du))
    return transfers


def net_pairwise_count(obligations: list[Obligation]) -> int:
    """Baseline: number of transfers if we only net each unordered pair.

    This is the honest baseline for the reduction metric (DESIGN.md §6, N3):
    each A<->B pair collapses to a single directed edge, but debts are NOT
    simplified across the whole graph.
    """
    pair: dict[tuple[int, int], int] = defaultdict(int)
    for o in obligations:
        a, b = o.debtor, o.creditor
        key = (a, b) if a < b else (b, a)
        sign = 1 if a < b else -1
        pair[key] += sign * o.amount
    return sum(1 for v in pair.values() if v != 0)


def reduction(obligations: list[Obligation]) -> dict[str, float]:
    """Compare the net-pairwise baseline to the simplified transfer count."""
    baseline = net_pairwise_count(obligations)
    simplified = len(simplify_debts(net_balances(obligations)))
    pct = 0.0 if baseline == 0 else round((baseline - simplified) / baseline * 100, 1)
    return {"baseline": baseline, "simplified": simplified, "reduction_pct": pct}
