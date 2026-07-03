"""The memory stream: append-only records, embedded at write time.

Record ids are deterministic (uuid5 over run/agent/counter) — uuid4 would
break logged-completion replay. Importance is scored by the caller (the
runtime owns the gateway call); the stream owns storage and embedding.
"""
from __future__ import annotations

import uuid

import schemas
from cognition.embedding import Embedder

MEM_NS = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")  # uuid.NAMESPACE_OID


class MemoryStream:
    def __init__(self, run_id: str, agent_id: str, embedder: Embedder):
        self.run_id = run_id
        self.agent_id = agent_id
        self._embedder = embedder
        self.records: list[dict] = []
        self.embeddings: dict[str, list[float]] = {}
        self._counter = 0

    def write(self, kind: str, text: str, tick: int, importance: int,
              citations: list[str] | None = None) -> dict:
        record = {
            "id": str(uuid.uuid5(MEM_NS, f"{self.run_id}:{self.agent_id}:mem:{self._counter}")),
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "kind": kind,
            "tick": tick,
            "text": text,
            "importance": importance,
        }
        if citations is not None:
            record["citations"] = citations
        problems = schemas.errors("memory_record", record)
        if problems:
            raise ValueError(f"internal bug: invalid memory record: {problems[0]}")
        self._counter += 1
        self.records.append(record)
        self.embeddings[record["id"]] = self._embedder.embed([text])[0]
        return record

    def importance_sum_since(self, record_count: int) -> float:
        return float(sum(r["importance"] for r in self.records[record_count:]))

    def __len__(self) -> int:
        return len(self.records)
