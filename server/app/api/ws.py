from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.realtime import realtime_hub

ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await realtime_hub.connect(websocket)
    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action") or message.get("type")
            if action == "subscribe":
                channels = message.get("channels", [])
                for channel in channels:
                    await realtime_hub.subscribe(websocket, channel)
                    if isinstance(channel, str) and channel.startswith("market.quote."):
                        symbol = channel.rsplit(".", 1)[-1].upper()
                        await websocket.send_json(
                            {
                                "channel": channel,
                                "event": "quote.updated",
                                "payload": {
                                    "symbol": symbol,
                                    "bid": 245.2,
                                    "ask": 245.25,
                                    "last": 245.23,
                                    "timestamp": datetime.now(UTC).isoformat(),
                                },
                            }
                        )
    except WebSocketDisconnect:
        await realtime_hub.disconnect(websocket)
