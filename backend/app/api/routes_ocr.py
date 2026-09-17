"""OCR endpoints: upload a receipt, poll the job, and apply reviewed items.

Upload creates an OcrJob and hands it to the capped worker pool; progress arrives
over the WebSocket as `ocr.status`. The parsed result is a PROPOSAL — the user
reviews/edits, then applies it, which is the only thing that writes line items.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_member
from app.core.db import get_db
from app.models import Bill, GroupMember, ItemShare, LineItem, OcrJob, OcrStatus, User
from app.schemas.entities import BillItemsReplace, BillOut, OcrJobOut
from app.services.allocation import AllocationError
from app.services.bills import recompute_bill_shares
from app.services.ocr.storage import save_image
from app.services.ws_manager import balances_updated, manager
from app.workers import ocr_runner

router = APIRouter(tags=["ocr"])


def _job_out(job: OcrJob) -> OcrJobOut:
    return OcrJobOut(
        id=job.id,
        bill_id=job.bill_id,
        status=job.status.value,
        confidence=job.confidence,
        error=job.error,
        parsed=json.loads(job.parsed_json) if job.parsed_json else None,
    )


def _require_bill_member(db: Session, bill_id: int, user: User) -> Bill:
    bill = db.get(Bill, bill_id)
    if bill is None or bill.deleted_at is not None:
        raise HTTPException(status_code=404, detail="bill not found")
    require_member(db, bill.group_id, user.id)
    return bill


@router.post("/bills/{bill_id}/ocr", response_model=OcrJobOut)
async def upload_receipt(
    bill_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OcrJobOut:
    bill = _require_bill_member(db, bill_id, user)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty upload")

    ext = (file.filename or "img.png").rsplit(".", 1)[-1].lower()
    bill.receipt_image_key = save_image(data, ext=ext if ext in {"png", "jpg", "jpeg"} else "png")

    job = db.scalar(select(OcrJob).where(OcrJob.bill_id == bill_id))
    if job is None:
        job = OcrJob(bill_id=bill_id, status=OcrStatus.pending)
        db.add(job)
    else:  # re-upload: reset the existing job
        job.status = OcrStatus.pending
        job.parsed_json = None
        job.error = None
        job.confidence = None
    db.commit()
    db.refresh(job)

    ocr_runner.submit(job.id)
    return _job_out(job)


@router.get("/ocr/{job_id}", response_model=OcrJobOut)
def get_job(
    job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> OcrJobOut:
    job = db.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    _require_bill_member(db, job.bill_id, user)
    return _job_out(job)


@router.put("/bills/{bill_id}/items", response_model=BillOut)
def replace_items(
    bill_id: int,
    req: BillItemsReplace,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BillOut:
    """Replace a bill's line items with the user-reviewed set, then recompute."""
    bill = _require_bill_member(db, bill_id, user)
    if req.version is not None and req.version != bill.version:
        raise HTTPException(status_code=409, detail="bill was modified; refetch and retry")

    members = set(
        db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == bill.group_id)).all()
    )
    for item in req.items:
        if not item.shares:
            raise HTTPException(status_code=422, detail=f"item '{item.name}' is unassigned")
        for uid in item.shares:
            if uid not in members:
                raise HTTPException(status_code=422, detail=f"user {uid} is not a group member")

    # Replace line items + their shares.
    old_ids = db.scalars(select(LineItem.id).where(LineItem.bill_id == bill_id)).all()
    if old_ids:
        db.execute(delete(ItemShare).where(ItemShare.line_item_id.in_(old_ids)))
        db.execute(delete(LineItem).where(LineItem.bill_id == bill_id))
    bill.tax = req.tax
    bill.tip = req.tip
    db.flush()
    for item in req.items:
        li = LineItem(bill_id=bill_id, name=item.name, price=item.price, quantity=item.quantity)
        db.add(li)
        db.flush()
        for uid, weight in item.shares.items():
            db.add(ItemShare(line_item_id=li.id, user_id=uid, weight=weight))
    db.flush()

    try:
        recompute_bill_shares(db, bill_id)
    except AllocationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(bill)
    manager.broadcast(bill.group_id, balances_updated(bill.group_id))

    # Serialize (reuse the bills serializer).
    from app.api.routes_bills import _serialize_bill

    return _serialize_bill(db, bill)
