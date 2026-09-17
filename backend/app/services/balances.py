"""Derived group balances + simplified settlement (DESIGN.md §3, §6).

Balances are never stored: we rebuild the raw ledger of obligations from bills and
confirmed payments, then net + simplify. The reduction metric and the transfers
come from the SAME ledger, so they are always consistent.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bill, BillShare, Payment, PaymentStatus
from app.services.settlement import (
    Obligation,
    net_balances,
    net_pairwise_count,
    simplify_debts,
)


def group_ledger(db: Session, group_id: int) -> list[Obligation]:
    """Every raw IOU in the group: each non-payer owes the payer their share,
    and each confirmed payment cancels debt the other way."""
    obligations: list[Obligation] = []

    bills = db.scalars(
        select(Bill).where(Bill.group_id == group_id, Bill.deleted_at.is_(None))
    ).all()
    for bill in bills:
        shares = db.scalars(select(BillShare).where(BillShare.bill_id == bill.id)).all()
        for s in shares:
            if s.user_id == bill.payer_id or s.amount == 0:
                continue
            if s.amount > 0:
                obligations.append(Obligation(debtor=s.user_id, creditor=bill.payer_id, amount=s.amount))
            else:  # a negative share (net discount) flips direction
                obligations.append(Obligation(debtor=bill.payer_id, creditor=s.user_id, amount=-s.amount))

    payments = db.scalars(
        select(Payment).where(
            Payment.group_id == group_id, Payment.status == PaymentStatus.confirmed
        )
    ).all()
    for p in payments:
        # from_user paid to_user, so it discharges from_user's debt to to_user.
        obligations.append(Obligation(debtor=p.to_user, creditor=p.from_user, amount=p.amount))

    return obligations


def compute_balances(db: Session, group_id: int) -> dict:
    obligations = group_ledger(db, group_id)
    balances = net_balances(obligations)  # positive = owed money
    transfers = simplify_debts(balances)
    baseline = net_pairwise_count(obligations)
    simplified = len(transfers)
    pct = 0.0 if baseline == 0 else round((baseline - simplified) / baseline * 100, 1)
    return {
        "balances": balances,
        "transfers": transfers,
        "baseline": baseline,
        "simplified": simplified,
        "reduction_pct": pct,
    }
