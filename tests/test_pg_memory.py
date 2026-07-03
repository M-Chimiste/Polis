"""Memory records + embeddings in Postgres/pgvector: storage parity with the
in-memory scorer's cosine ranking. Skips cleanly without a database."""
import os

import pytest

psycopg = pytest.importorskip("psycopg")

from cognition.embedding import HashEmbedder, cosine  # noqa: E402
from cognition.memory import MemoryStream  # noqa: E402

DSN = os.environ.get("POLIS_TEST_DSN", "postgresql:///polis_test")
RUN = "6f1a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b"


def db_available() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


pytestmark = pytest.mark.skipif(not db_available(), reason=f"no test database at {DSN}")


def vector_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.9f}" for x in v) + "]"


def test_pgvector_cosine_ranking_matches_in_memory():
    from services.db.ledger_sink import apply_schema
    apply_schema(DSN)
    embedder = HashEmbedder()
    stream = MemoryStream(RUN, "maren_alder", embedder)
    for i in range(25):
        stream.write("observation", f"village happening number {i}", i, (i % 10) + 1)

    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("TRUNCATE runs CASCADE")
        conn.execute(
            "INSERT INTO runs (run_id, experiment_id, config, config_hash, seed) "
            "VALUES (%s, 'test', '{}', 'x', 0)", (RUN,))
        for r in stream.records:
            conn.execute(
                "INSERT INTO memory_records (id, run_id, agent_id, kind, tick, text, "
                "importance, embedding) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (r["id"], RUN, r["agent_id"], r["kind"], r["tick"], r["text"],
                 r["importance"], vector_literal(stream.embeddings[r["id"]])))

        query = embedder.embed(["what has been happening in the village?"])[0]
        rows = conn.execute(
            "SELECT id FROM memory_records WHERE run_id = %s AND agent_id = %s "
            "ORDER BY embedding <=> %s::vector, id LIMIT 5",
            (RUN, "maren_alder", vector_literal(query))).fetchall()

    pg_top = [str(row[0]) for row in rows]
    ranked = sorted(stream.records,
                    key=lambda r: (-cosine(query, stream.embeddings[r["id"]]), r["id"]))
    local_top = [r["id"] for r in ranked[:5]]
    assert pg_top == local_top
