"""Groups, membership, invites, and derived balances."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_member
from app.core.db import get_db
from app.models import (
    Group,
    GroupInvite,
    GroupMember,
    InviteStatus,
    MemberRole,
    User,
)
from app.schemas.entities import (
    BalancesOut,
    GroupCreate,
    GroupOut,
    InviteCreate,
    InviteOut,
    MemberOut,
    TransferOut,
)
from app.services.balances import compute_balances

router = APIRouter(prefix="/groups", tags=["groups"])
invites_router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("", response_model=GroupOut)
def create_group(
    req: GroupCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GroupOut:
    group = Group(name=req.name, currency=req.currency, created_by=user.id)
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=user.id, role=MemberRole.admin))
    db.commit()
    return GroupOut(id=group.id, name=group.name, currency=group.currency, role="admin")


@router.get("", response_model=list[GroupOut])
def list_groups(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[GroupOut]:
    rows = db.execute(
        select(Group, GroupMember.role)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user.id)
    ).all()
    return [GroupOut(id=g.id, name=g.name, currency=g.currency, role=role.value) for g, role in rows]


@router.get("/{group_id}/members", response_model=list[MemberOut])
def list_members(
    group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[MemberOut]:
    require_member(db, group_id, user.id)
    rows = db.execute(
        select(GroupMember, User)
        .join(User, User.id == GroupMember.user_id)
        .where(GroupMember.group_id == group_id)
    ).all()
    return [
        MemberOut(user_id=u.id, name=u.name, email=u.email, role=m.role.value) for m, u in rows
    ]


@router.post("/{group_id}/invites", response_model=InviteOut)
def create_invite(
    group_id: int,
    req: InviteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InviteOut:
    require_member(db, group_id, user.id)
    invite = GroupInvite(
        group_id=group_id,
        email=req.email,
        token=secrets.token_urlsafe(24),
        status=InviteStatus.pending,
        invited_by=user.id,
    )
    db.add(invite)
    db.commit()
    return InviteOut(id=invite.id, token=invite.token, status=invite.status.value)


@invites_router.post("/{token}/accept", response_model=GroupOut)
def accept_invite(
    token: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> GroupOut:
    invite = db.scalar(select(GroupInvite).where(GroupInvite.token == token))
    if invite is None or invite.status != InviteStatus.pending:
        raise HTTPException(status_code=404, detail="invite not found or already used")

    existing = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == invite.group_id, GroupMember.user_id == user.id
        )
    )
    if existing is None:
        db.add(GroupMember(group_id=invite.group_id, user_id=user.id, role=MemberRole.member))
    invite.status = InviteStatus.accepted
    db.commit()

    group = db.get(Group, invite.group_id)
    return GroupOut(id=group.id, name=group.name, currency=group.currency, role="member")


@router.get("/{group_id}/balances", response_model=BalancesOut)
def group_balances(
    group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> BalancesOut:
    require_member(db, group_id, user.id)
    result = compute_balances(db, group_id)
    return BalancesOut(
        balances=result["balances"],
        transfers=[
            TransferOut(debtor=t.debtor, creditor=t.creditor, amount=t.amount)
            for t in result["transfers"]
        ],
        baseline=result["baseline"],
        simplified=result["simplified"],
        reduction_pct=result["reduction_pct"],
    )
