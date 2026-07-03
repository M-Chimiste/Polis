"""Recency x Importance x Relevance retrieval (Park scoring).

score = alpha*recency + beta*importance + gamma*relevance, each component
min-max normalized over the candidate set (per the paper), weights and decay
from experiment_config.retrieval — all three are ablation knobs.

Recency decays exponentially on sim-time since creation. (Park decays since
last access; creation-time decay keeps retrieval a pure read. Revisit as an
ablation if access-decay matters.)

Production stores embeddings in pgvector (services/db/schema.sql); the
scorer itself is storage-agnostic and takes the stream directly.
"""
from __future__ import annotations

from dataclasses import dataclass

from cognition.embedding import Embedder, cosine
from cognition.memory import MemoryStream
from sim.clock import TICK_SIM_SECONDS


@dataclass(frozen=True)
class RetrievalParams:
    alpha: float = 1.0
    beta: float = 1.0
    gamma: float = 1.0
    recency_decay: float = 0.995  # per sim-HOUR (Park's calibration)
    top_k: int = 5


def _normalize(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def retrieve(stream: MemoryStream, embedder: Embedder, query: str,
             now_tick: int, params: RetrievalParams) -> list[dict]:
    if not stream.records:
        return []
    query_emb = embedder.embed_query([query])[0]
    recency, importance, relevance = [], [], []
    for r in stream.records:
        age_hours = max(0, now_tick - r["tick"]) * TICK_SIM_SECONDS / 3600
        recency.append(params.recency_decay ** age_hours)
        importance.append(float(r["importance"]))
        relevance.append(cosine(query_emb, stream.embeddings[r["id"]]))
    rec_n, imp_n, rel_n = _normalize(recency), _normalize(importance), _normalize(relevance)
    scored = [
        (params.alpha * rec_n[i] + params.beta * imp_n[i] + params.gamma * rel_n[i], i)
        for i in range(len(stream.records))
    ]
    # deterministic tie-break: newer record (higher index) wins ties
    scored.sort(key=lambda s: (-s[0], -s[1]))
    return [stream.records[i] for _, i in scored[: params.top_k]]
