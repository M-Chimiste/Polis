"""Thin FastAPI sidecar: the live ledger stream over WebSocket.

Read-only and zero-authority — it relays what the LedgerWriter emits and can
never write back into the sim. The observer (P4) is its only intended
consumer; headless runs work identically without it.
"""
from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


class LedgerBroadcaster:
    """Fan-out from the (synchronous) sim loop to async WebSocket subscribers.

    Keeps the full event history so a viewer connecting mid-run gets the
    backlog first (agent_initialized and all), then live-tails. seq is
    monotonic, so the handler dedupes the register/snapshot race by seq.
    """

    def __init__(self) -> None:
        self._subscribers: dict[int, tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = {}
        self._next_key = 0
        self._history: list[dict] = []

    def publish(self, event: dict) -> None:
        """Thread-safe; callable from the sim thread as LedgerWriter.on_event."""
        self._history.append(event)  # list.append is atomic under the GIL
        for loop, queue in list(self._subscribers.values()):
            loop.call_soon_threadsafe(queue.put_nowait, event)

    def _subscribe(self) -> tuple[int, asyncio.Queue, list[dict]]:
        key = self._next_key
        self._next_key += 1
        queue: asyncio.Queue = asyncio.Queue()
        # register BEFORE snapshotting: an event landing in between appears
        # in both queue and backlog and is deduped by seq in the handler
        self._subscribers[key] = (asyncio.get_running_loop(), queue)
        backlog = list(self._history)
        return key, queue, backlog

    def _unsubscribe(self, key: int) -> None:
        self._subscribers.pop(key, None)


def create_app(broadcaster: LedgerBroadcaster) -> FastAPI:
    app = FastAPI(title="polis ledger stream", docs_url=None)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    @app.websocket("/ws/ledger")
    async def ledger_stream(ws: WebSocket) -> None:
        key, queue, backlog = broadcaster._subscribe()
        await ws.accept()
        try:
            last_seq = -1
            for event in backlog:
                await ws.send_json(event)
                last_seq = event.get("seq", last_seq)
            while True:
                event = await queue.get()
                if event.get("seq", last_seq + 1) <= last_seq:
                    continue  # already sent in the backlog
                await ws.send_json(event)
        except WebSocketDisconnect:
            pass
        finally:
            broadcaster._unsubscribe(key)

    return app
