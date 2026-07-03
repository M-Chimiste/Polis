"""HTTPEmbedder: OpenAI-compatible /v1/embeddings client with nomic v1.5
asymmetric task prefixes and a hard dimension check. Endpoint is mocked;
smoked live against metis/athena (768-dim) 2026-07-03."""
import json

import httpx
import pytest

from cognition.embedding import EMBEDDING_DIM, HashEmbedder, HTTPEmbedder


def make_embedder(responder, dim=4):
    transport = httpx.MockTransport(responder)
    client = httpx.Client(transport=transport, base_url="http://embed.test/v1")
    return HTTPEmbedder("http://embed.test/v1", "test-embed", dim=dim, http_client=client)


def embeddings_response(inputs: list[str], dim: int) -> httpx.Response:
    # deliberately out of order: the client must sort by index
    data = [{"index": i, "embedding": [float(i)] * dim}
            for i in reversed(range(len(inputs)))]
    return httpx.Response(200, json={"data": data})


def test_document_and_query_prefixes():
    seen = []

    def responder(request):
        body = json.loads(request.content)
        seen.append(body["input"])
        return embeddings_response(body["input"], 4)

    emb = make_embedder(responder)
    emb.embed(["the tavern is busy"])
    emb.embed_query(["who runs the tavern?"])
    assert seen[0] == ["search_document: the tavern is busy"]
    assert seen[1] == ["search_query: who runs the tavern?"]


def test_batch_order_restored_by_index():
    def responder(request):
        body = json.loads(request.content)
        return embeddings_response(body["input"], 4)

    emb = make_embedder(responder)
    vectors = emb.embed(["a", "b", "c"])
    assert [v[0] for v in vectors] == [0.0, 1.0, 2.0]


def test_dimension_mismatch_raises():
    def responder(request):
        body = json.loads(request.content)
        return embeddings_response(body["input"], 5)  # wrong dim

    emb = make_embedder(responder, dim=4)
    with pytest.raises(ValueError, match="dim 5"):
        emb.embed(["x"])


def test_transport_error_raises_loudly():
    def responder(request):
        return httpx.Response(503, text="loading model")

    emb = make_embedder(responder)
    with pytest.raises(httpx.HTTPStatusError):
        emb.embed(["x"])


def test_hash_embedder_query_alias_preserves_fixtures():
    # embed_query must equal embed (no prefix), or every pre-prefix
    # byte-equal fixture would silently break
    h = HashEmbedder()
    assert h.embed_query(["gossip"]) == h.embed(["gossip"])
    assert h.dim == EMBEDDING_DIM
