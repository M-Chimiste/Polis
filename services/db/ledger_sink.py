"""Postgres ledger sink.

Wire it as `LedgerWriter(on_event=sink)`: it registers the run when it sees
`run_started`, buffers events, and marks the run finished on `run_finished`.
The JSONL file stays the byte-equal wall; Postgres is the queryable copy the
measurement plane reads (metrics post-process the ledger, never the sim).

Works against any Postgres with pgvector (host-agnostic, decision
2026-07-03). Apply services/db/schema.sql first — apply_schema() does it
idempotently.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import psycopg
from psycopg.types.json import Jsonb

SCHEMA_SQL = pathlib.Path(__file__).resolve().parent / "schema.sql"

INSERT_EVENT = (
    "INSERT INTO ledger_events (run_id, seq, tick, kind, agent_id, data) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)


def apply_schema(dsn: str) -> None:
    # drop whole-line comments first (they may contain semicolons), then split
    sql = "\n".join(
        line for line in SCHEMA_SQL.read_text().splitlines()
        if not line.strip().startswith("--")
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        for statement in sql.split(";"):
            if statement.strip():
                conn.execute(statement)


class PostgresLedgerSink:
    def __init__(self, dsn: str, batch_size: int = 200):
        self._conn = psycopg.connect(dsn)
        self._batch_size = batch_size
        self._buffer: list[tuple] = []

    def __call__(self, event: dict) -> None:
        """LedgerWriter on_event hook."""
        if event["kind"] == "run_started":
            self._begin_run(event["run_id"], event["data"])
        self._buffer.append((
            event["run_id"], event["seq"], event["tick"],
            event["kind"], event["agent_id"], Jsonb(event["data"]),
        ))
        if len(self._buffer) >= self._batch_size:
            self.flush()
        if event["kind"] == "run_finished":
            self._finish_run(event["run_id"])

    def _begin_run(self, run_id: str, config: dict) -> None:
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

    def _finish_run(self, run_id: str) -> None:
        self.flush()
        self._conn.execute(
            "UPDATE runs SET status = 'finished', finished_at = now() WHERE run_id = %s",
            (run_id,),
        )
        self._conn.commit()

    def flush(self) -> None:
        if self._buffer:
            with self._conn.cursor() as cur:
                cur.executemany(INSERT_EVENT, self._buffer)
            self._conn.commit()
            self._buffer = []

    def close(self) -> None:
        self.flush()
        self._conn.close()
