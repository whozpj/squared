"""Bills: create a bill with line items + shares, read it back with computed shares."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_member
from app.core.db import get_db
from app.models import Bill, BillShare, Group, GroupMember, ItemShare, LineItem, User
from app.schemas.entities import BillCreate, BillOut, LineItemOut, ShareOut
from app.services.allocation import AllocationError
from app.services.bills import recompute_bill_shares

router = APIRouter(tags=["bills"])


def _member_ids(db: Session, group_id: int) -> set[int]:
    return set(
        db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == group_id)).all()
    )


def _serialize_bill(db: Session, bill: Bill) -> BillOut:
    line_items = db.scalars(select(LineItem).where(LineItem.bill_id == bill.id)).all()
    li_out = []
    for li in line_items:
        shares = db.scalars(select(ItemShare).where(ItemShare.line_item_id == li.id)).all()
        li_out.append(
            LineItemOut(
                id=li.id,
                name=li.name,
                price=li.price,
                quantity=li.quantity,
                shares={s.user_id: s.weight for s in shares},
            )
        )
    bill_shares = db.scalars(select(BillShare).where(BillShare.bill_id == bill.id)).all()
    return BillOut(
        id=bill.id,
        title=bill.title,
        payer_id=bill.payer_id,
        subtotal=bill.subtotal,
        tax=bill.tax,
        tip=bill.tip,
        total=bill.total,
        currency=bill.currency,
        version=bill.version,
        line_items=li_out,
        shares=[ShareOut(user_id=s.user_id, amount=s.amount) for s in bill_shares],
    )


@router.post("/groups/{group_id}/bills", response_model=BillOut)
def create_bill(
    group_id: int,
    req: BillCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BillOut:
    require_member(db, group_id, user.id)
    members = _member_ids(db, group_id)

    if req.payer_id not in members:
        raise HTTPException(status_code=422, detail="payer must be a group member")
    for item in req.items:
        if not item.shares:
            raise HTTPException(status_code=422, detail=f"item '{item.name}' is unassigned")
        for uid in item.shares:
            if uid not in members:
                raise HTTPException(status_code=422, detail=f"user {uid} is not a group member")

    group = db.get(Group, group_id)
    bill = Bill(
        group_id=group_id,
        payer_id=req.payer_id,
        title=req.title,
        tax=req.tax,
        tip=req.tip,
        currency=group.currency,  # one currency per group (C4)
    )
    db.add(bill)
    db.flush()

    for item in req.items:
        li = LineItem(bill_id=bill.id, name=item.name, price=item.price, quantity=item.quantity)
        db.add(li)
        db.flush()
        for uid, weight in item.shares.items():
            db.add(ItemShare(line_item_id=li.id, user_id=uid, weight=weight))
    db.flush()

    try:
        recompute_bill_shares(db, bill.id)
    except AllocationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(bill)
    return _serialize_bill(db, bill)


@router.get("/bills/{bill_id}", response_model=BillOut)
def get_bill(
    bill_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> BillOut:
    bill = db.get(Bill, bill_id)
    if bill is None or bill.deleted_at is not None:
        raise HTTPException(status_code=404, detail="bill not found")
    require_member(db, bill.group_id, user.id)
    return _serialize_bill(db, bill)
