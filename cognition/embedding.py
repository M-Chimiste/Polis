"""Embedder interface. Production: a 768-dim BERT-class service (decision
2026-07-03), reached over HTTP — lands with hardware access.

HashEmbedder is the deterministic dev/test stand-in: unit-norm vectors from
sha256, so retrieval machinery is exercisable and byte-reproducible offline.
Its 'relevance' is arbitrary (no real semantics) — runs using it are
non-conforming by definition and it must never appear in an experiment.
"""
from __future__ import annotations

import hashlib
import math
import struct
from typing import Protocol

EMBEDDING_DIM = 768


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

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


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
