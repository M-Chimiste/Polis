"""Unified Postgres sink for cognition runs: ledger events, completions, and
memory records (with embeddings) stream into their tables over one
connection; probes insert post-hoc from the measurement plane.

JSONL files remain the byte-equal wall; Postgres is the queryable copy.
Every insert is ON CONFLICT DO NOTHING: ids and sequence keys are
deterministic (uuid5 / keyed counters), so re-running or replaying the same
run is a no-op instead of a violation.

Works against any Postgres with pgvector. Apply services/db/schema.sql first
(ledger_sink.apply_schema does it idempotently).
"""
from __future__ import annotations

import hashlib
import json

import psycopg
from psycopg.types.json import Jsonb

INSERT_EVENT = (
    "INSERT INTO ledger_events (run_id, seq, tick, kind, agent_id, data) "
    "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"
)
INSERT_COMPLETION = (
    "INSERT INTO completions (run_id, agent_id, call_site, sequence, role, "
    "model, request, response) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
    "ON CONFLICT DO NOTHING"
)
INSERT_MEMORY = (
    "INSERT INTO memory_records (id, run_id, agent_id, kind, tick, text, "
    "importance, citations, embedding) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::uuid[], %s::vector) "
    "ON CONFLICT DO NOTHING"
)
INSERT_PROBE = (
    "INSERT INTO probes (probe_id, run_id, agent_id, kind, tick, question, "
    "response, category, scores, frozen_state_ref) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"
)


def vector_literal(v: list[float]) -> str:
    return "[" + ",".join(repr(x) for x in v) + "]"


class PostgresRunSink:
    """Wire begin_run() before the runtime exists (FK ordering), then the
    three hooks; run_finished in the ledger stream marks the run finished."""

    def __init__(self, dsn: str, batch_size: int = 200):
        self._conn = psycopg.connect(dsn)
        self._batch_size = batch_size
        self._events: list[tuple] = []
        self._completions: list[tuple] = []
        self._memories: list[tuple] = []

    def begin_run(self, run_id: str, config: dict) -> None:
        config_hash = hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self._conn.execute(
            "INSERT INTO runs (run_id, experiment_id, config, config_hash, seed) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (run_id) DO NOTHING",
            (run_id, config.get("mode", "unspecified"), Jsonb(config),
             config_hash, config.get("seed", 0)),
        )
        self._conn.commit()

    # ------------------------------------------------------------- hooks --
    def on_ledger_event(self, event: dict) -> None:
        """LedgerWriter on_event."""
        self._events.append((
            event["run_id"], event["seq"], event["tick"],
            event["kind"], event["agent_id"], Jsonb(event["data"]),
        ))
        self._maybe_flush()
        if event["kind"] == "run_finished":
            self._finish_run(event["run_id"])

    def on_completion(self, entry: dict) -> None:
        """CompletionLog on_record."""
        result = entry["result"]
        self._completions.append((
            entry["run_id"], entry["agent_id"], entry["call_site"],
            entry["sequence"], entry["role"], result.get("model") or "unknown",
            Jsonb(entry["request"]),
            Jsonb({"outcome": entry["outcome"], "result": result}),
        ))
        self._maybe_flush()

    def on_memory(self, record: dict, embedding: list[float]) -> None:
        """MemoryStream on_record."""
        self._memories.append((
            record["id"], record["run_id"], record["agent_id"], record["kind"],
            record["tick"], record["text"], record["importance"],
            record.get("citations", []), vector_literal(embedding),
        ))
        self._maybe_flush()

    # ---------------------------------------------------------- plumbing --
    def _maybe_flush(self) -> None:
        if (len(self._events) + len(self._completions) + len(self._memories)
                >= self._batch_size):
            self.flush()

    def flush(self) -> None:
        with self._conn.cursor() as cur:
            if self._events:
                cur.executemany(INSERT_EVENT, self._events)
            if self._completions:
                cur.executemany(INSERT_COMPLETION, self._completions)
            if self._memories:
                cur.executemany(INSERT_MEMORY, self._memories)
        self._conn.commit()
        self._events, self._completions, self._memories = [], [], []

    def _finish_run(self, run_id: str) -> None:
        self.flush()
        self._conn.execute(
            "UPDATE runs SET status = 'finished', finished_at = now() WHERE run_id = %s",
            (run_id,),
        )
        self._conn.commit()

    def close(self) -> None:
        self.flush()
        self._conn.close()


def insert_probes(dsn: str, results: list[dict]) -> int:
    """Measurement plane, post-hoc: probe_result documents into the probes
    table. probe_ids are deterministic, so re-inserting a bundle is a no-op."""
    rows = [(r["probe_id"], r["run_id"], r["agent_id"], r["kind"], r["tick"],
             r["question"], r["response"], r.get("category"),
             Jsonb(r["scores"]) if r.get("scores") is not None else None,
             r.get("frozen_state_ref"))
            for r in results]
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_PROBE, rows)
        conn.commit()
    return len(rows)
