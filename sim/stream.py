"""Thin FastAPI sidecar: the live ledger stream over WebSocket.

Read-only and zero-authority — it relays what the LedgerWriter emits and can
never write back into the sim. The observer (P4) is its only intended
consumer; headless runs work identically without it.
"""
from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


class LedgerBroadcaster:
    """Fan-out from the (synchronous) sim loop to async WebSocket subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[int, tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = {}
        self._next_key = 0

    def publish(self, event: dict) -> None:
        """Thread-safe; callable from the sim thread as LedgerWriter.on_event."""
        for loop, queue in list(self._subscribers.values()):
            loop.call_soon_threadsafe(queue.put_nowait, event)

    def _subscribe(self) -> tuple[int, asyncio.Queue]:
        key = self._next_key
        self._next_key += 1
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[key] = (asyncio.get_running_loop(), queue)
        return key, queue

    def _unsubscribe(self, key: int) -> None:
        self._subscribers.pop(key, None)


def create_app(broadcaster: LedgerBroadcaster) -> FastAPI:
    app = FastAPI(title="polis ledger stream", docs_url=None)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    @app.websocket("/ws/ledger")
    async def ledger_stream(ws: WebSocket) -> None:
        key, queue = broadcaster._subscribe()
        await ws.accept()
        try:
            while True:
                await ws.send_json(await queue.get())
        except WebSocketDisconnect:
            pass
        finally:
            broadcaster._unsubscribe(key)

    return app
