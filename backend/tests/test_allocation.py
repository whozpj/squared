import random

from app.services.allocation import AllocationError, LineItem, allocate_bill

import pytest


def total_of(items, tax, tip):
    return sum(i.price for i in items) + tax + tip


def test_even_split_no_tax_tip():
    items = [LineItem(price=1000, shares={1: 1, 2: 1})]
    result = allocate_bill(items, tax=0, tip=0, participants=[1, 2])
    assert result == {1: 500, 2: 500}


def test_tax_and_tip_are_proportional():
    # Alice eats $30, Bob eats $10. Tax $4 + tip $8 = $12 split 3:1.
    items = [
        LineItem(price=3000, shares={1: 1}),
        LineItem(price=1000, shares={2: 1}),
    ]
    result = allocate_bill(items, tax=400, tip=800, participants=[1, 2])
    assert result == {1: 3000 + 900, 2: 1000 + 300}
    assert sum(result.values()) == total_of(items, 400, 800)


def test_penny_is_never_lost():
    # $10.00 split 3 ways cannot divide evenly; must still sum to exactly 1000.
    items = [LineItem(price=1000, shares={1: 1, 2: 1, 3: 1})]
    result = allocate_bill(items, tax=0, tip=0, participants=[1, 2, 3])
    assert sum(result.values()) == 1000
    assert sorted(result.values()) == [333, 333, 334]
    # Deterministic tie-break: the extra cent goes to the lowest user id.
    assert result[1] == 334


def test_weighted_shares():
    # One item split so user 1 pays twice user 2's share.
    items = [LineItem(price=900, shares={1: 2, 2: 1})]
    result = allocate_bill(items, tax=0, tip=0, participants=[1, 2])
    assert result == {1: 600, 2: 300}


def test_participant_with_no_items_owes_nothing():
    items = [LineItem(price=1000, shares={1: 1})]
    result = allocate_bill(items, tax=200, tip=0, participants=[1, 2])
    assert result[2] == 0
    assert sum(result.values()) == 1200


def test_zero_subtotal_splits_tax_tip_equally():
    # A fully comped bill ($0 items) with a $9 tip splits 3 ways.
    items = [LineItem(price=0, shares={1: 1, 2: 1, 3: 1})]
    result = allocate_bill(items, tax=0, tip=900, participants=[1, 2, 3])
    assert result == {1: 300, 2: 300, 3: 300}


def test_discount_line_item():
    # $20 item for user 1, minus a $5 discount for user 1, plus $3 tip split by subtotal.
    items = [
        LineItem(price=2000, shares={1: 1}),
        LineItem(price=-500, shares={1: 1}),
        LineItem(price=1000, shares={2: 1}),
    ]
    result = allocate_bill(items, tax=0, tip=300, participants=[1, 2])
    assert sum(result.values()) == total_of(items, 0, 300)  # 2500
    # user1 net items = 1500, user2 = 1000; tip 300 split 15:10 -> 180/120
    assert result == {1: 1680, 2: 1120}


def test_unassigned_item_is_rejected():
    items = [LineItem(price=1000, shares={})]
    with pytest.raises(AllocationError):
        allocate_bill(items, tax=0, tip=0, participants=[1])


def test_property_always_sums_to_total():
    rng = random.Random(42)
    for _ in range(500):
        n = rng.randint(1, 6)
        participants = list(range(1, n + 1))
        items = []
        for _ in range(rng.randint(1, 8)):
            k = rng.randint(1, n)
            sharers = rng.sample(participants, k)
            shares = {u: rng.randint(1, 4) for u in sharers}
            items.append(LineItem(price=rng.randint(-500, 5000), shares=shares))
        tax = rng.randint(0, 800)
        tip = rng.randint(0, 800)
        result = allocate_bill(items, tax, tip, participants)
        assert sum(result.values()) == total_of(items, tax, tip)
        assert set(result) == set(participants)
