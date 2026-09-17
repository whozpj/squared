"""In-process WebSocket connection manager (DESIGN.md §7).

Maps group_id -> connected sockets and fans out "invalidate + refetch" events.
Sync route handlers (which FastAPI runs in a threadpool) call `broadcast`, which
hops onto the event loop thread-safely. Interface kept small so a Redis pub/sub
implementation can replace it later without touching callers.
"""

from __future__ import annotations

import asyncio
from typing import Any

from starlette.websockets import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._by_group: dict[int, set[WebSocket]] = {}
        self._groups_of: dict[WebSocket, set[int]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, group_id: int, ws: WebSocket) -> None:
        self._by_group.setdefault(group_id, set()).add(ws)
        self._groups_of.setdefault(ws, set()).add(group_id)

    def disconnect(self, ws: WebSocket) -> None:
        for group_id in self._groups_of.pop(ws, set()):
            self._by_group.get(group_id, set()).discard(ws)

    def broadcast(self, group_id: int, message: dict[str, Any]) -> None:
        """Thread-safe: safe to call from sync request handlers."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(self._fanout, group_id, dict(message))
        except RuntimeError:
            # Loop shut down between the check and the call; nothing to deliver.
            pass

    def reset(self) -> None:
        self._by_group.clear()
        self._groups_of.clear()
        self._loop = None

    def _fanout(self, group_id: int, message: dict[str, Any]) -> None:
        for ws in list(self._by_group.get(group_id, ())):
            asyncio.create_task(self._safe_send(ws, message))

    async def _safe_send(self, ws: WebSocket, message: dict[str, Any]) -> None:
        try:
            await ws.send_json(message)
        except Exception:
            self.disconnect(ws)


manager = ConnectionManager()


def balances_updated(group_id: int) -> dict[str, Any]:
    return {"type": "balances.updated", "group_id": group_id}
