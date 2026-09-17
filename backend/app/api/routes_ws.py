"""WebSocket endpoint for real-time balance sync (DESIGN.md §7).

Protocol (client -> server):
  {"type": "auth", "token": "<jwt>"}          # required first message
  {"type": "subscribe", "group_id": <int>}    # after auth; must be a member
  {"type": "ping"}
Server -> client:
  {"type": "auth_ok", "user_id"}, {"type": "subscribed", "group_id"},
  {"type": "balances.updated", "group_id"}, {"type": "error", "detail"}, {"type": "pong"}

Auth is via the first message (never a query param) so tokens don't land in logs.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app.core.db import get_db
from app.core.security import decode_token
from app.models import GroupMember, User
from app.services.ws_manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)) -> None:
    await websocket.accept()
    manager.set_loop(asyncio.get_running_loop())

    # First message must authenticate.
    try:
        first = await websocket.receive_json()
    except WebSocketDisconnect:
        return
    if first.get("type") != "auth":
        await websocket.close(code=1008)
        return
    try:
        payload = decode_token(first.get("token", ""))
        user = db.get(User, int(payload["sub"]))
    except Exception:
        user = None
    if user is None:
        await websocket.close(code=1008)
        return
    await websocket.send_json({"type": "auth_ok", "user_id": user.id})

    try:
        while True:
            msg = await websocket.receive_json()
            kind = msg.get("type")
            if kind == "subscribe":
                group_id = int(msg["group_id"])
                member = db.scalar(
                    select(GroupMember).where(
                        GroupMember.group_id == group_id, GroupMember.user_id == user.id
                    )
                )
                if member is None:
                    await websocket.send_json({"type": "error", "detail": "not a member"})
                    continue
                manager.subscribe(group_id, websocket)
                await websocket.send_json({"type": "subscribed", "group_id": group_id})
            elif kind == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
