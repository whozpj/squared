"""Squared API entrypoint.

Boots with no external dependencies: the health check and the /compute endpoints
(the verified allocation + settlement core) work immediately. Database-backed
routes (groups, bills, auth, …) are layered on in later build steps per DESIGN.md §13.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_bills import router as bills_router
from app.api.routes_compute import router as compute_router
from app.api.routes_groups import invites_router
from app.api.routes_groups import router as groups_router
from app.api.routes_payments import router as payments_router
from app.api.routes_ws import router as ws_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


app.include_router(compute_router)
app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(invites_router)
app.include_router(bills_router)
app.include_router(payments_router)
app.include_router(ws_router)
