"""Embedder interface. Production: HTTPEmbedder against an OpenAI-compatible
/v1/embeddings endpoint (nomic-embed-text-v1.5 on metis/athena: 768-dim,
matching vector(768) in schema.sql).

HashEmbedder is the deterministic dev/test stand-in: unit-norm vectors from
sha256, so retrieval machinery is exercisable and byte-reproducible offline.
Its 'relevance' is arbitrary (no real semantics) — runs using it are
non-conforming by definition and it must never appear in an experiment.

embed() is for memory records (documents); embed_query() for retrieval
queries — nomic v1.5 is asymmetric and wants distinct task prefixes.
HashEmbedder aliases them (no prefix) so pre-existing fixtures hold.
"""
from __future__ import annotations

import hashlib
import math
import struct
from typing import Protocol

import httpx

EMBEDDING_DIM = 768


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def embed_query(self, texts: list[str]) -> list[list[float]]:
        return self.embed(texts)  # no prefix: keeps pre-prefix fixtures byte-equal

    def _one(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self.dim:
            digest = hashlib.sha256(f"{counter}:{text}".encode()).digest()
            for i in range(0, 32, 4):
                (u,) = struct.unpack_from(">I", digest, i)
                values.append(u / 2**31 - 1.0)  # [-1, 1)
            counter += 1
        values = values[: self.dim]
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


class HTTPEmbedder:
    """OpenAI-compatible /v1/embeddings client — the production embedder.

    Synchronous by design: memory writes embed inline and cognition
    scheduling is deterministic sorted-await anyway (wall-clock overlap is a
    serving-time optimization, never a semantics change). Raises on transport
    error or dimension mismatch — an embedderless run must fail loudly, not
    silently degrade to non-semantic vectors.
    """

    DOC_PREFIX = "search_document: "     # nomic v1.5 asymmetric task prefixes
    QUERY_PREFIX = "search_query: "

    def __init__(self, base_url: str, model: str, dim: int = EMBEDDING_DIM,
                 http_client: httpx.Client | None = None, timeout: float = 60.0):
        self.dim = dim
        self.model = model
        self._client = http_client or httpx.Client(base_url=base_url, timeout=timeout)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._post([self.DOC_PREFIX + t for t in texts])

    def embed_query(self, texts: list[str]) -> list[list[float]]:
        return self._post([self.QUERY_PREFIX + t for t in texts])

    def _post(self, inputs: list[str]) -> list[list[float]]:
        resp = self._client.post("/embeddings", json={"model": self.model, "input": inputs})
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda d: d["index"])
        vectors = [d["embedding"] for d in data]
        for v in vectors:
            if len(v) != self.dim:
                raise ValueError(f"embedder returned dim {len(v)}, expected {self.dim}")
        return vectors


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
