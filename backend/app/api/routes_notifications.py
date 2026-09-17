"""Notification center: list + mark read, plus a dev-only manual reminder trigger."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.models import Notification, User
from app.schemas.entities import NotificationOut
from app.workers.reminders import run_reminders

router = APIRouter(tags=["notifications"])


def _out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        type=n.type,
        payload=json.loads(n.payload_json) if n.payload_json else None,
        read=n.read_at is not None,
    )


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[NotificationOut]:
    rows = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.id.desc())
        .limit(min(limit, 200))
    ).all()
    return [_out(n) for n in rows]


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationOut:
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="notification not found")
    if note.read_at is None:
        note.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(note)
    return _out(note)


@router.post("/dev/run-reminders")
def dev_run_reminders(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    """DEV ONLY: run the reminder job now (the scheduler runs it periodically in prod)."""
    if get_settings().environment == "production":
        raise HTTPException(status_code=404, detail="not found")
    return {"created": run_reminders(db)}
