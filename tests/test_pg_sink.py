"""Postgres ledger sink integration tests.

Run against POLIS_TEST_DSN if set, else a local Postgres; skipped cleanly
when neither is reachable (the standing remote constraint: never require
real infrastructure).
"""
import io
import json
import os

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.environ.get("POLIS_TEST_DSN", "postgresql:///polis_test")


def db_available() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


pytestmark = pytest.mark.skipif(not db_available(), reason=f"no test database at {DSN}")


@pytest.fixture()
def clean_db():
    from services.db.ledger_sink import apply_schema
    apply_schema(DSN)
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("TRUNCATE runs CASCADE")
    yield DSN


def test_schema_applies_idempotently(clean_db):
    from services.db.ledger_sink import apply_schema
    apply_schema(clean_db)  # second application must be a no-op
    with psycopg.connect(clean_db) as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
    assert {"runs", "agents", "ledger_events", "memory_records",
            "plans", "completions", "probes", "metrics"} <= tables


def test_full_run_persists_and_round_trips(clean_db):
    from services.db.ledger_sink import PostgresLedgerSink
    from sim.runner import run

    sink = PostgresLedgerSink(clean_db, batch_size=50)
    jsonl = io.BytesIO()
    writer = run(600, seed=7, sink=jsonl, on_event=sink)
    sink.close()

    with psycopg.connect(clean_db) as conn:
        count = conn.execute(
            "SELECT count(*) FROM ledger_events WHERE run_id = %s", (writer.run_id,)
        ).fetchone()[0]
        status, seed = conn.execute(
            "SELECT status, seed FROM runs WHERE run_id = %s", (writer.run_id,)
        ).fetchone()
        rows = conn.execute(
            "SELECT seq, tick, kind, agent_id, data FROM ledger_events "
            "WHERE run_id = %s ORDER BY seq", (writer.run_id,)
        ).fetchall()

    assert count == writer.seq
    assert status == "finished"
    assert seed == 7
    # byte-level parity with the JSONL wall
    jsonl_events = [json.loads(line) for line in jsonl.getvalue().splitlines()]
    assert len(jsonl_events) == count
    for row, expected in zip(rows, jsonl_events):
        assert row[0] == expected["seq"]
        assert row[1] == expected["tick"]
        assert row[2] == expected["kind"]
        assert row[3] == expected["agent_id"]
        assert row[4] == expected["data"]


def test_duplicate_seq_rejected_by_primary_key(clean_db):
    from services.db.ledger_sink import PostgresLedgerSink
    sink = PostgresLedgerSink(clean_db)
    event = {"run_id": "9e1a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b", "seq": 0, "tick": 0,
             "kind": "run_started", "agent_id": None, "data": {"seed": 1}}
    sink(event)
    sink.flush()
    sink(event)
    with pytest.raises(psycopg.errors.UniqueViolation):
        sink.flush()
    sink._conn.close()
