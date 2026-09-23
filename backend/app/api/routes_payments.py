"""Payments: a debtor claims they paid a creditor; the creditor confirms.

Only confirmed payments affect balances (DESIGN.md §3). Confirming broadcasts a
balances.updated event to the group.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_member
from app.core.db import get_db
from app.models import Group, GroupMember, Notification, Payment, PaymentStatus, User
from app.schemas.entities import PaymentCreate, PaymentOut, RemindRequest, RemindResult
from app.services.email import send_email, settle_reminder_html
from app.services.ws_manager import balances_updated, manager

router = APIRouter(tags=["payments"])


def _out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id,
        from_user=p.from_user,
        to_user=p.to_user,
        amount=p.amount,
        method=p.method,
        status=p.status.value,
    )


@router.post("/groups/{group_id}/payments", response_model=PaymentOut)
def claim_payment(
    group_id: int,
    req: PaymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaymentOut:
    require_member(db, group_id, user.id)
    recipient = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.user_id == req.to_user
        )
    )
    if recipient is None:
        raise HTTPException(status_code=422, detail="recipient must be a group member")
    if req.to_user == user.id:
        raise HTTPException(status_code=422, detail="cannot pay yourself")

    payment = Payment(
        group_id=group_id,
        from_user=user.id,
        to_user=req.to_user,
        amount=req.amount,
        method=req.method,
        status=PaymentStatus.claimed,
        claimed_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return _out(payment)


@router.post("/payments/{payment_id}/confirm", response_model=PaymentOut)
def confirm_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaymentOut:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")
    if payment.to_user != user.id:
        raise HTTPException(status_code=403, detail="only the recipient can confirm")
    if payment.status != PaymentStatus.confirmed:
        payment.status = PaymentStatus.confirmed
        payment.confirmed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(payment)
        manager.broadcast(payment.group_id, balances_updated(payment.group_id))
    return _out(payment)


@router.post("/groups/{group_id}/settle/remind", response_model=RemindResult)
def remind(
    group_id: int,
    req: RemindRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RemindResult:
    """Nudge a debtor: an in-app notification + (if configured) an email."""
    require_member(db, group_id, user.id)
    debtor_member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.user_id == req.to_user
        )
    )
    if debtor_member is None:
        raise HTTPException(status_code=422, detail="that person isn't in this group")
    debtor = db.get(User, req.to_user)
    group = db.get(Group, group_id)

    payload = {"group_id": group_id, "owed_cents": req.amount, "from_user": user.id}
    note = Notification(
        user_id=req.to_user,
        type="nudge",
        payload_json=json.dumps(payload),
        dedup_key=f"nudge:{group_id}:{req.to_user}:{user.id}:{datetime.now(timezone.utc).timestamp()}",
    )
    db.add(note)
    db.commit()
    manager.broadcast(
        group_id, {"type": "notification.new", "group_id": group_id, "user_id": req.to_user}
    )

    emailed = send_email(
        debtor.email,
        f"You owe {user.name} ${req.amount / 100:.2f} on Squared",
        settle_reminder_html(user.name, req.amount, group.name),
    )
    return RemindResult(emailed=emailed, notified=True)


@router.get("/groups/{group_id}/payments", response_model=list[PaymentOut])
def list_payments(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PaymentOut]:
    require_member(db, group_id, user.id)
    rows = db.scalars(select(Payment).where(Payment.group_id == group_id)).all()
    return [_out(p) for p in rows]
