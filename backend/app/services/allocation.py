"""Exact tax & tip allocation.

Given a bill's line items (each split among participants by integer weight),
plus tax and tip, compute how many cents each participant owes.

Guarantees (see DESIGN.md §5):
- All math is exact (Fraction) until a single largest-remainder rounding pass.
- The returned per-person amounts sum EXACTLY to the bill total
  (subtotal + tax + tip), in integer cents. No lost or phantom pennies.
- Deterministic: ties in the rounding pass break by ascending user id.

This module is pure (no I/O, no DB) so it is trivially unit-testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction


@dataclass(frozen=True)
class LineItem:
    """A single line on the receipt.

    price:  signed cents (a discount is a negative price).
    shares: user_id -> integer weight (>= 1). The item's price is split
            among these users in proportion to their weights.
    """

    price: int
    shares: dict[int, int] = field(default_factory=dict)


class AllocationError(ValueError):
    """Raised when the input cannot be allocated (e.g. an unassigned item)."""


def allocate_bill(
    items: list[LineItem],
    tax: int,
    tip: int,
    participants: list[int],
) -> dict[int, int]:
    """Return {user_id: cents_owed}, summing exactly to subtotal + tax + tip.

    participants is the full set of people the bill is split among (the payer
    included). Every user in an item's shares must be a participant, and every
    item must be assigned to at least one participant (DESIGN.md §5 precondition).
    """
    if not participants:
        raise AllocationError("a bill needs at least one participant")
    part_set = set(participants)

    # Exact per-user item subtotal, accumulated as Fractions of a cent.
    item_subtotal: dict[int, Fraction] = {u: Fraction(0) for u in participants}
    for idx, item in enumerate(items):
        if not item.shares:
            raise AllocationError(f"line item {idx} is not assigned to anyone")
        total_weight = 0
        for uid, weight in item.shares.items():
            if uid not in part_set:
                raise AllocationError(f"item {idx} assigned to non-participant {uid}")
            if weight < 1:
                raise AllocationError(f"item {idx} has a non-positive weight for {uid}")
            total_weight += weight
        for uid, weight in item.shares.items():
            item_subtotal[uid] += Fraction(item.price * weight, total_weight)

    items_subtotal = sum(item_subtotal.values())  # == subtotal, exactly
    n = len(participants)

    # Exact amount owed per user, before rounding.
    owed_exact: dict[int, Fraction] = {}
    if items_subtotal == 0:
        # No proportional base (no items, or discounts cancel the subtotal):
        # split tax+tip equally, on top of each user's item subtotal (§5 fallback).
        per_head = Fraction(tax + tip, n)
        for uid in participants:
            owed_exact[uid] = item_subtotal[uid] + per_head
    else:
        # Tax and tip proportional to each user's share of the item subtotal.
        factor = Fraction(tax + tip, 1) / items_subtotal
        for uid in participants:
            owed_exact[uid] = item_subtotal[uid] * (1 + factor)

    total = int(items_subtotal) + tax + tip  # items_subtotal is a whole number here
    return _largest_remainder_round(owed_exact, total)


def _largest_remainder_round(owed_exact: dict[int, Fraction], total: int) -> dict[int, int]:
    """Round exact amounts to integer cents so they sum to `total` exactly.

    Uses the largest-remainder (Hamilton) method: floor everything, then hand
    the leftover cents to the largest fractional remainders, ties broken by
    ascending user id for determinism.
    """
    floors: dict[int, int] = {}
    remainders: list[tuple[Fraction, int]] = []
    for uid, amount in owed_exact.items():
        f = math.floor(amount)  # toward -inf, correct for negatives too
        floors[uid] = f
        remainders.append((amount - f, uid))  # remainder in [0, 1)

    leftover = total - sum(floors.values())  # whole number of cents to distribute
    # Largest remainder first; tie-break ascending user id.
    remainders.sort(key=lambda r: (-r[0], r[1]))
    for i in range(leftover):
        floors[remainders[i][1]] += 1
    return floors
