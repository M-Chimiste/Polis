"""Memory stream + R*I*R retrieval."""
import schemas
from cognition.embedding import HashEmbedder, cosine
from cognition.memory import MemoryStream
from cognition.retrieval import RetrievalParams, retrieve

RUN = "6f1a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b"


def make_stream():
    return MemoryStream(RUN, "maren_alder", HashEmbedder())


def test_records_schema_valid_and_ids_deterministic():
    s1, s2 = make_stream(), make_stream()
    r1 = s1.write("observation", "the ale is short", 10, 4)
    r2 = s2.write("observation", "the ale is short", 10, 4)
    assert schemas.errors("memory_record", r1) == []
    assert r1["id"] == r2["id"]  # uuid5, not uuid4 — replay depends on this
    assert s1.embeddings[r1["id"]] == s2.embeddings[r2["id"]]
    assert len(s1.embeddings[r1["id"]]) == 768


def test_citations_survive():
    s = make_stream()
    base = s.write("observation", "piet was quiet", 5, 6)
    refl = s.write("reflection", "something weighs on piet", 100, 8, citations=[base["id"]])
    assert refl["citations"] == [base["id"]]
    assert schemas.errors("memory_record", refl) == []


def test_relevance_dominates_when_weighted():
    s = make_stream()
    e = HashEmbedder()
    s.write("observation", "alpha topic", 0, 5)
    s.write("observation", "beta topic", 0, 5)
    params = RetrievalParams(alpha=0, beta=0, gamma=1, top_k=1)
    got = retrieve(s, e, "alpha topic", 10, params)
    assert got[0]["text"] == "alpha topic"  # exact text = identical embedding


def test_importance_dominates_when_weighted():
    s = make_stream()
    s.write("observation", "mundane thing", 0, 1)
    s.write("observation", "huge thing", 0, 10)
    got = retrieve(s, HashEmbedder(), "unrelated query", 10,
                   RetrievalParams(alpha=0, beta=1, gamma=0, top_k=1))
    assert got[0]["text"] == "huge thing"


def test_recency_dominates_when_weighted():
    s = make_stream()
    s.write("observation", "old news", 0, 5)
    s.write("observation", "fresh news", 5000, 5)
    got = retrieve(s, HashEmbedder(), "anything", 5100,
                   RetrievalParams(alpha=1, beta=0, gamma=0, top_k=1))
    assert got[0]["text"] == "fresh news"


def test_top_k_and_determinism():
    s = make_stream()
    for i in range(20):
        s.write("observation", f"event number {i}", i, (i % 10) + 1)
    params = RetrievalParams(top_k=5)
    a = retrieve(s, HashEmbedder(), "event", 100, params)
    b = retrieve(s, HashEmbedder(), "event", 100, params)
    assert len(a) == 5
    assert [r["id"] for r in a] == [r["id"] for r in b]


def test_cosine_sanity():
    e = HashEmbedder()
    v1, v2 = e.embed(["same text", "same text"])
    assert abs(cosine(v1, v2) - 1.0) < 1e-9
