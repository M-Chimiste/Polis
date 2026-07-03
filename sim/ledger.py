"""Append-only ledger writer — the permanent wall.

Every event is schema-validated on write and serialized canonically
(sorted keys, compact separators) so equal runs produce byte-equal JSONL.
Sinks: any binary file object (headless JSONL, the primary mode). The
Postgres sink lands with hardware access; the WebSocket sidecar subscribes
via on_event.
"""
from __future__ import annotations

import json
from typing import BinaryIO, Callable

import schemas


class LedgerWriter:
    def __init__(
        self,
        run_id: str,
        sink: BinaryIO | None = None,
        on_event: Callable[[dict], None] | None = None,
    ):
        self.run_id = run_id
        self.seq = 0
        self._sink = sink
        self._on_event = on_event

    def append(self, tick: int, kind: str, agent_id: str | None, data: dict) -> dict:
        event = {
            "run_id": self.run_id,
            "seq": self.seq,
            "tick": tick,
            "kind": kind,
            "agent_id": agent_id,
            "data": data,
        }
        problems = schemas.errors("ledger_event", event)
        if problems:
            raise ValueError(f"internal bug: invalid ledger event {kind}: {problems[0]}")
        self.seq += 1
        if self._sink is not None:
            self._sink.write(canonical_line(event))
        if self._on_event is not None:
            self._on_event(event)
        return event


def canonical_line(event: dict) -> bytes:
    return (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()
