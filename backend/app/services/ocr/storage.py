"""Local receipt-image storage (DESIGN.md §11).

Dev stores images on disk under a gitignored dir; prod would swap for S3. `UPLOAD_DIR`
can be overridden (tests point it at a temp dir).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import get_settings

UPLOAD_DIR: str | None = None


def _dir() -> Path:
    base = Path(UPLOAD_DIR or get_settings().upload_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_image(data: bytes, ext: str = "png") -> str:
    key = f"{uuid.uuid4().hex}.{ext}"
    (_dir() / key).write_bytes(data)
    return key


def load_image(key: str) -> bytes:
    return (_dir() / key).read_bytes()
