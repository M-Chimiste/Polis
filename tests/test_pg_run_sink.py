"""PostgresRunSink integration: a cognition run streams ledger events,
completions, and memory records (with embeddings) into Postgres; probe
results insert post-hoc. Deterministic keys make every insert idempotent —
re-running the same run is a no-op, never a violation.

Runs against POLIS_TEST_DSN (default local polis_test); skips cleanly
without a database.
"""
import asyncio
import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

from cognition.runner import fake_gateway, run_cognition  # noqa: E402
from cognition.runtime import Settings  # noqa: E402

DSN = os.environ.get("POLIS_TEST_DSN", "postgresql:///polis_test")
PAIR = ["maren_alder", "piet_alder"]
TICKS = 2400  # through both wakes: plans, decompositions, object use


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


def run_with_sink(dsn):
    from services.db.run_sink import PostgresRunSink
    sink = PostgresRunSink(dsn, batch_size=50)
    try:
        writer, gateway, runtime = asyncio.run(run_cognition(
            TICKS, seed=42, agent_ids=PAIR, settings=Settings(),
            gateway=fake_gateway(), pg_sink=sink))
    finally:
        sink.close()
    return writer, gateway, runtime


def counts(dsn, run_id):
    with psycopg.connect(dsn) as conn:
        def one(sql):
            return conn.execute(sql, (run_id,)).fetchone()[0]
        return {
            "events": one("SELECT count(*) FROM ledger_events WHERE run_id = %s"),
            "completions": one("SELECT count(*) FROM completions WHERE run_id = %s"),
            "memories": one("SELECT count(*) FROM memory_records WHERE run_id = %s"),
            "status": one("SELECT status FROM runs WHERE run_id = %s"),
        }


def test_run_streams_all_three_tables_and_finishes(clean_db):
    writer, gateway, runtime = run_with_sink(clean_db)
    got = counts(clean_db, writer.run_id)
    assert got["status"] == "finished"
    assert got["events"] == writer.seq  # seq post-increments: it IS the count
    assert got["completions"] == gateway.total_calls()
    assert got["memories"] == sum(len(m.stream.records) for m in runtime.minds.values())
    # embeddings round-trip at the schema dimension
    with psycopg.connect(clean_db) as conn:
        dims = conn.execute(
            "SELECT DISTINCT vector_dims(embedding) FROM memory_records "
            "WHERE run_id = %s", (writer.run_id,)).fetchall()
    assert dims == [(768,)]


def test_rerun_is_idempotent_not_a_violation(clean_db):
    writer, gateway, runtime = run_with_sink(clean_db)
    before = counts(clean_db, writer.run_id)
    run_with_sink(clean_db)  # same seed/agents/ticks -> same run_id, same keys
    assert counts(clean_db, writer.run_id) == before


def test_insert_probes_idempotent(clean_db):
    writer, *_ = run_with_sink(clean_db)
    from services.db.run_sink import insert_probes
    probe = {
        "probe_id": str(uuid.uuid5(uuid.NAMESPACE_OID, "probe-test-0")),
        "run_id": writer.run_id,
        "agent_id": "maren_alder",
        "kind": "fact_check",
        "tick": 1200,
        "question": "Have you heard anything about the gathering?",
        "response": "",
        "scores": {"knows_fact": False},
    }
    assert insert_probes(clean_db, [probe]) == 1
    insert_probes(clean_db, [probe])  # deterministic probe_id -> no-op
    with psycopg.connect(clean_db) as conn:
        n = conn.execute("SELECT count(*) FROM probes WHERE run_id = %s",
                         (writer.run_id,)).fetchone()[0]
    assert n == 1
