"""Runs OCR jobs off the request path (DESIGN.md §4 execution model).

Tesseract + OpenCV are CPU-heavy and synchronous, so jobs run in a capped thread
pool, never on the event loop. Each job uses its own DB session and pushes
`ocr.status` events over the WebSocket.

Test hooks: set `run_inline = True` to execute synchronously, `session_factory` to a
test sessionmaker, and `provider` to a fake OCR provider (no Tesseract needed).
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from app.core import db as db_mod
from app.core.config import get_settings
from app.models import Bill, OcrJob, OcrStatus
from app.services.ocr.pipeline import run_pipeline
from app.services.ocr.provider import TesseractProvider
from app.services.ocr.storage import load_image
from app.services.ws_manager import manager

_executor = ThreadPoolExecutor(max_workers=get_settings().ocr_max_workers)

# Test overrides.
run_inline = False
session_factory = None  # a sessionmaker; defaults to the app engine's
provider = None  # an OcrProvider; defaults to Tesseract


def _new_session():
    if session_factory is not None:
        return session_factory()
    return db_mod.get_sessionmaker()()


def _ocr_event(bill_id: int, status: str) -> dict:
    return {"type": "ocr.status", "bill_id": bill_id, "status": status}


def submit(job_id: int) -> None:
    if run_inline:
        _run(job_id)
    else:
        _executor.submit(_run, job_id)


def _run(job_id: int) -> None:
    db = _new_session()
    try:
        job = db.get(OcrJob, job_id)
        if job is None:
            return
        bill = db.get(Bill, job.bill_id)
        group_id = bill.group_id if bill else None

        job.status = OcrStatus.processing
        job.attempts += 1
        db.commit()
        if group_id is not None:
            manager.broadcast(group_id, _ocr_event(job.bill_id, "processing"))

        try:
            image = load_image(bill.receipt_image_key)
            result = run_pipeline(image, provider=provider or TesseractProvider())
            job.parsed_json = json.dumps(result.to_dict())
            job.confidence = int(round(result.confidence * 100))
            job.raw_text = (result.raw_text or "")[:5000]
            job.status = OcrStatus.done
            final = "done"
        except Exception as exc:  # noqa: BLE001 - record failure, don't crash the pool
            job.status = OcrStatus.failed
            job.error = str(exc)[:500]
            final = "failed"
        db.commit()
        if group_id is not None:
            manager.broadcast(group_id, _ocr_event(job.bill_id, final))
    finally:
        db.close()
