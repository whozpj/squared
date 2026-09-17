"""JWT issue/verify. Auth-provider-agnostic: dev-login and (later) Google OAuth
both mint the same app token, so everything downstream is unaffected by the swap.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import get_settings


def create_access_token(subject: str, extra: dict | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    # algorithms is pinned (never accept alg=none).
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


__all__ = ["create_access_token", "decode_token", "JWTError"]
