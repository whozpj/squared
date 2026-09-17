"""Shared FastAPI dependencies: current user + group membership checks."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import JWTError, decode_token
from app.models import GroupMember, User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


def require_member(db: Session, group_id: int, user_id: int) -> GroupMember:
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.user_id == user_id
        )
    )
    if member is None:
        raise HTTPException(status_code=403, detail="not a member of this group")
    return member
