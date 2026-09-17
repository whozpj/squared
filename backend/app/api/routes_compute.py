"""Stateless compute endpoints exposing the verified core algorithms.

These need no database, so the app is demonstrably functional the moment it boots.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.compute import (
    AllocateRequest,
    AllocateResponse,
    SettleRequest,
    SettleResponse,
    TransferOut,
)
from app.services.allocation import AllocationError, LineItem, allocate_bill
from app.services.settlement import Obligation, net_balances, net_pairwise_count, simplify_debts

router = APIRouter(prefix="/compute", tags=["compute"])


@router.post("/allocate", response_model=AllocateResponse)
def allocate(req: AllocateRequest) -> AllocateResponse:
    items = [LineItem(price=i.price, shares=i.shares) for i in req.items]
    try:
        shares = allocate_bill(items, req.tax, req.tip, req.participants)
    except AllocationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AllocateResponse(shares=shares, total=sum(shares.values()))


@router.post("/settle", response_model=SettleResponse)
def settle(req: SettleRequest) -> SettleResponse:
    obligations = [Obligation(o.debtor, o.creditor, o.amount) for o in req.obligations]
    transfers = simplify_debts(net_balances(obligations))
    baseline = net_pairwise_count(obligations)
    simplified = len(transfers)
    pct = 0.0 if baseline == 0 else round((baseline - simplified) / baseline * 100, 1)
    return SettleResponse(
        transfers=[TransferOut(debtor=t.debtor, creditor=t.creditor, amount=t.amount) for t in transfers],
        baseline=baseline,
        simplified=simplified,
        reduction_pct=pct,
    )
