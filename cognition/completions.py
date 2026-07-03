"""Logged-completion replay: the determinism mechanism.

Every cognition call's final outcome (success or failure) is logged keyed by
(agent_id, call_site, sequence). Replay mode serves outcomes from the log
instead of the model, making any sampled run byte-reproducible after the
fact. Failures are logged too — a run that degraded to fallback must replay
as exactly that run.

CognitionGateway is the only surface cognition code calls; it owns the
sequence counters, the logging, and the live/replay switch.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import BinaryIO

from services.gateway import GatewayCompletion, GatewayFailure, GatewayResult, ModelGateway


def canonical(obj: dict) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()


class CompletionLog:
    """Ordered, keyed log of call outcomes. JSONL is the wall; the Postgres
    completions table is the queryable copy (services/db)."""

    def __init__(self, run_id: str, sink: BinaryIO | None = None,
                 on_record=None):
        self.run_id = run_id
        self.records: list[dict] = []
        self._by_key: dict[tuple[str, str, int], dict] = {}
        self._sink = sink
        self._on_record = on_record  # e.g. PostgresRunSink.on_completion

    def record(self, agent_id: str, call_site: str, sequence: int, role: str,
               request_messages: list[dict], result: GatewayResult, tick: int) -> dict:
        entry = {
            "run_id": self.run_id,
            "agent_id": agent_id,
            "call_site": call_site,
            "sequence": sequence,
            "tick": tick,
            "role": role,
            "request": {"messages": request_messages},
            "outcome": ("completion" if isinstance(result, GatewayCompletion) else "failure"),
            "result": asdict(result),
        }
        self.records.append(entry)
        self._by_key[(agent_id, call_site, sequence)] = entry
        if self._sink is not None:
            self._sink.write(canonical(entry))
        if self._on_record is not None:
            self._on_record(entry)
        return entry

    def lookup(self, agent_id: str, call_site: str, sequence: int) -> dict | None:
        return self._by_key.get((agent_id, call_site, sequence))

    @classmethod
    def load(cls, lines: list[str] | list[bytes], run_id: str) -> "CompletionLog":
        log = cls(run_id)
        for line in lines:
            entry = json.loads(line)
            log.records.append(entry)
            log._by_key[(entry["agent_id"], entry["call_site"], entry["sequence"])] = entry
        return log


class CognitionGateway:
    """Sequence-counted, logged, replayable front on the model gateway."""

    def __init__(self, gateway: ModelGateway | None, log: CompletionLog,
                 replay_from: CompletionLog | None = None):
        if gateway is None and replay_from is None:
            raise ValueError("need a live gateway or a replay log")
        self._gateway = gateway
        self.log = log
        self._replay = replay_from
        self._counters: dict[tuple[str, str], int] = {}

    @property
    def replay_mode(self) -> bool:
        return self._replay is not None

    async def complete(self, agent_id: str, call_site: str, role: str,
                       messages: list[dict], response_schema: dict | None = None,
                       tick: int = 0) -> GatewayResult:
        key = (agent_id, call_site)
        sequence = self._counters.get(key, 0)
        self._counters[key] = sequence + 1

        if self._replay is not None:
            entry = self._replay.lookup(agent_id, call_site, sequence)
            if entry is None:
                result: GatewayResult = GatewayFailure(
                    kind="replay_miss", role=role,
                    errors=[f"no logged completion for ({agent_id}, {call_site}, {sequence})"],
                )
            elif entry["outcome"] == "completion":
                result = GatewayCompletion(**entry["result"])
            else:
                result = GatewayFailure(**entry["result"])
        else:
            result = await self._gateway.complete(role, messages, response_schema=response_schema,
                                                  call_site=call_site)
        self.log.record(agent_id, call_site, sequence, role, messages, result, tick)
        return result

    def total_calls(self) -> int:
        return sum(self._counters.values())
