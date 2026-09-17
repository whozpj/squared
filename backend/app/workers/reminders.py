"""Idempotent debt reminders (DESIGN.md §8).

Once per period (ISO week), every debtor in a group gets ONE notification summarizing
what they owe (based on the simplified transfers). Idempotency is enforced by a unique
`dedup_key = reminder:{group}:{debtor}:{iso_week}`: a double-fire, retry, or restart
within the same week never creates a duplicate.

`run_reminders` is pure w.r.t. its session so it can be unit-tested directly and also
driven by the APScheduler job.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Group, Notification
from app.services.balances import compute_balances
from app.services.ws_manager import manager


def iso_week(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def run_reminders(db: Session, now: datetime | None = None) -> int:
    """Create per-debtor reminders for all groups. Returns how many were newly created."""
    week = iso_week(now)
    created = 0

    for group in db.scalars(select(Group)).all():
        transfers = compute_balances(db, group.id)["transfers"]
        by_debtor: dict[int, list] = defaultdict(list)
        for t in transfers:
            by_debtor[t.debtor].append(t)

        for debtor, ts in by_debtor.items():
            owed = sum(t.amount for t in ts)
            payload = {
                "group_id": group.id,
                "owed_cents": owed,
                "week": week,
                "transfers": [{"creditor": t.creditor, "amount": t.amount} for t in ts],
            }
            note = Notification(
                user_id=debtor,
                type="debt_reminder",
                payload_json=json.dumps(payload),
                dedup_key=f"reminder:{group.id}:{debtor}:{week}",
            )
            try:
                with db.begin_nested():
                    db.add(note)
                    db.flush()
            except IntegrityError:
                continue  # already reminded this week — idempotent
            created += 1
            manager.broadcast(
                group.id, {"type": "notification.new", "group_id": group.id, "user_id": debtor}
            )

    db.commit()
    return created
