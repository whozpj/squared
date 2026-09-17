"""Bill share recomputation — the SOLE writer of BillShare (DESIGN.md §5, C1/C2).

Every bill mutation funnels through recompute_bill_shares, which recomputes the
exact per-person amounts, rewrites BillShare rows in the same transaction, and
asserts the money-conservation invariant before returning.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Bill, BillShare, ItemShare, LineItem
from app.services.allocation import LineItem as AllocItem
from app.services.allocation import allocate_bill


def recompute_bill_shares(db: Session, bill_id: int) -> None:
    """Recompute and persist BillShare rows for a bill. Caller commits."""
    bill = db.get(Bill, bill_id)
    if bill is None:
        raise ValueError(f"bill {bill_id} not found")

    # Row lock on Postgres; SQLAlchemy no-ops it on SQLite (tests).
    db.execute(select(Bill.id).where(Bill.id == bill_id).with_for_update())

    line_items = db.scalars(select(LineItem).where(LineItem.bill_id == bill_id)).all()

    alloc_items: list[AllocItem] = []
    participants: set[int] = {bill.payer_id}
    for li in line_items:
        shares = db.scalars(select(ItemShare).where(ItemShare.line_item_id == li.id)).all()
        weights = {s.user_id: s.weight for s in shares}
        participants.update(weights)
        alloc_items.append(AllocItem(price=li.price, shares=weights))

    amounts = allocate_bill(
        alloc_items, tax=bill.tax, tip=bill.tip, participants=sorted(participants)
    )

    subtotal = sum(li.price for li in line_items)
    total = subtotal + bill.tax + bill.tip
    assert sum(amounts.values()) == total, "allocation must sum to bill total (C1)"

    bill.subtotal = subtotal
    bill.total = total
    bill.version += 1

    db.execute(delete(BillShare).where(BillShare.bill_id == bill_id))
    db.add_all([BillShare(bill_id=bill_id, user_id=uid, amount=amt) for uid, amt in amounts.items()])
    db.flush()
