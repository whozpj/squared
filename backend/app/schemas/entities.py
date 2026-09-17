"""Request/response schemas for the DB-backed MVP endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- auth (dev seam) ---
class DevLoginRequest(BaseModel):
    email: str
    name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int


class UserOut(BaseModel):
    id: int
    email: str
    name: str


# --- groups ---
class GroupCreate(BaseModel):
    name: str
    currency: str = "USD"


class GroupOut(BaseModel):
    id: int
    name: str
    currency: str
    role: str | None = None


class MemberOut(BaseModel):
    user_id: int
    name: str
    email: str
    role: str


class InviteCreate(BaseModel):
    email: str | None = None


class InviteOut(BaseModel):
    id: int
    token: str
    status: str


# --- bills ---
class ItemIn(BaseModel):
    name: str
    price: int = Field(description="Line total in signed cents (discount = negative)")
    quantity: int = 1
    shares: dict[int, int] = Field(description="user_id -> integer weight (>= 1)")


class BillCreate(BaseModel):
    title: str
    payer_id: int
    tax: int = 0
    tip: int = 0
    items: list[ItemIn]


class LineItemOut(BaseModel):
    id: int
    name: str
    price: int
    quantity: int
    shares: dict[int, int]


class ShareOut(BaseModel):
    user_id: int
    amount: int


class BillOut(BaseModel):
    id: int
    title: str
    payer_id: int
    subtotal: int
    tax: int
    tip: int
    total: int
    currency: str
    version: int
    line_items: list[LineItemOut]
    shares: list[ShareOut]


# --- payments ---
class PaymentCreate(BaseModel):
    to_user: int
    amount: int = Field(gt=0)
    method: str | None = None


class PaymentOut(BaseModel):
    id: int
    from_user: int
    to_user: int
    amount: int
    method: str | None
    status: str


# --- balances ---
class TransferOut(BaseModel):
    debtor: int
    creditor: int
    amount: int


class BalancesOut(BaseModel):
    balances: dict[int, int]  # user_id -> net cents (positive = owed money)
    transfers: list[TransferOut]
    baseline: int
    simplified: int
    reduction_pct: float
