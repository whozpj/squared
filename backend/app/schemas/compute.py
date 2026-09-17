"""Request/response schemas for the pure compute endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LineItemIn(BaseModel):
    price: int = Field(description="Signed cents; a discount is negative")
    shares: dict[int, int] = Field(description="user_id -> integer weight (>= 1)")


class AllocateRequest(BaseModel):
    items: list[LineItemIn]
    tax: int = 0
    tip: int = 0
    participants: list[int]


class AllocateResponse(BaseModel):
    shares: dict[int, int]
    total: int


class ObligationIn(BaseModel):
    debtor: int
    creditor: int
    amount: int = Field(gt=0)


class SettleRequest(BaseModel):
    obligations: list[ObligationIn]


class TransferOut(BaseModel):
    debtor: int
    creditor: int
    amount: int


class SettleResponse(BaseModel):
    transfers: list[TransferOut]
    baseline: int
    simplified: int
    reduction_pct: float
