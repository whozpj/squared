"""Test harness: an in-memory SQLite DB wired into the app via dependency override.

Lets the full MVP flow be tested end-to-end without Docker or Postgres.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.main import app
from app.models import Base


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, email: str, name: str) -> tuple[str, int]:
    r = client.post("/auth/dev-login", json={"email": email, "name": name})
    assert r.status_code == 200, r.text
    body = r.json()
    return body["access_token"], body["user_id"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
