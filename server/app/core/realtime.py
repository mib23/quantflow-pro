import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            for subscribers in self._channels.values():
                subscribers.discard(websocket)

    async def subscribe(self, websocket: WebSocket, channel: str) -> None:
        async with self._lock:
            self._channels[channel].add(websocket)

    async def publish(self, channel: str, event: str, payload: dict) -> None:
        message = json.dumps({"channel": channel, "event": event, "payload": payload})
        async with self._lock:
            subscribers = list(self._channels.get(channel, set()))

        stale_connections: list[WebSocket] = []
        for websocket in subscribers:
            try:
                await websocket.send_text(message)
            except Exception:
                stale_connections.append(websocket)

        if stale_connections:
            async with self._lock:
                for websocket in stale_connections:
                    self._channels[channel].discard(websocket)


realtime_hub = RealtimeHub()
