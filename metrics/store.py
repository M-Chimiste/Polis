"""Artifact loaders: the measurement plane reads run artifacts (ledger.jsonl,
memories.jsonl) — never live sim objects. FrozenStream is the probe-facing
copy of an agent's memory: filtered to a tick, detached from the sim, and
duck-typed for the retrieval scorer (records + embeddings)."""
from __future__ import annotations

import json
from collections import defaultdict

from cognition.embedding import Embedder


def load_ledger(lines: list[bytes] | list[str]) -> list[dict]:
    return [json.loads(line) for line in lines]


def load_memories(lines: list[bytes] | list[str]) -> dict[str, list[dict]]:
    by_agent: dict[str, list[dict]] = defaultdict(list)
    for line in lines:
        record = json.loads(line)
        by_agent[record["agent_id"]].append(record)
    for records in by_agent.values():
        records.sort(key=lambda r: (r["tick"], r["id"]))
    return dict(by_agent)


class FrozenStream:
    """A frozen, tick-bounded view of one agent's memory for probing.

    Embeddings are re-derived from text via the run's embedder (for real
    runs the canonical copy lives in pgvector; re-embedding the same text
    with the same model is equivalent for probe retrieval)."""

    def __init__(self, records: list[dict], upto_tick: int, embedder: Embedder):
        self.records = [dict(r) for r in records if r["tick"] <= upto_tick]
        texts = [r["text"] for r in self.records]
        vectors = embedder.embed(texts) if texts else []
        self.embeddings = {r["id"]: v for r, v in zip(self.records, vectors)}


def freeze(memories: dict[str, list[dict]], upto_tick: int,
           embedder: Embedder) -> dict[str, FrozenStream]:
    return {aid: FrozenStream(records, upto_tick, embedder)
            for aid, records in sorted(memories.items())}
