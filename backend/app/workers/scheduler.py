"""APScheduler setup for periodic debt reminders (DESIGN.md §8).

Single-process only (see the workers=1 constraint in DESIGN §2). Started from the
app lifespan when `enable_reminders` is set.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.workers.reminders import run_reminders


def _job() -> None:
    db = get_sessionmaker()()
    try:
        run_reminders(db)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _job,
        "interval",
        hours=get_settings().reminder_interval_hours,
        id="debt_reminders",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
