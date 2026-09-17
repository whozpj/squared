"""Auth routes.

For the MVP this exposes a DEV-ONLY login that mints the app JWT directly from an
email+name, so we can build and test everything before wiring Google OAuth. The
real Google OAuth flow (DESIGN.md §9) is added at the end and issues the same token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import create_access_token
from app.models import User
from app.schemas.entities import DevLoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-login", response_model=TokenResponse)
def dev_login(req: DevLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if get_settings().environment == "production":
        raise HTTPException(status_code=404, detail="not found")
    user = db.scalar(select(User).where(User.email == req.email))
    if user is None:
        user = User(google_sub=f"dev:{req.email}", email=req.email, name=req.name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return TokenResponse(access_token=create_access_token(str(user.id)), user_id=user.id)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name)
