"""Believability probe battery (Park interview categories) + judge scoring.

Interviews run through the probe runner against frozen state. Scoring is a
pluggable async judge; DeterministicJudge is the offline stand-in (runs
scored with it are non-conforming). The TheseusInsight rubric judge plugs in
here when hardware/infra is available — same interface, judge tier, offline.
"""
from __future__ import annotations

import hashlib
from typing import Awaitable, Callable, Protocol

from metrics.probes import ProbeRunner
from metrics.store import FrozenStream

# (category, question template) — Park's interview categories
BATTERY: list[tuple[str, str]] = [
    ("self_knowledge", "Give a short introduction of yourself."),
    ("self_knowledge", "What is your typical day like?"),
    ("memory", "Who is {other}? What do you make of them?"),
    ("memory", "What have you talked about with people recently?"),
    ("plans", "What are you planning to do for the rest of the day?"),
    ("reactions", "If the mill flooded tomorrow, what would you do first?"),
    ("reflections", "What has been on your mind lately?"),
]


class Judge(Protocol):
    async def score(self, category: str, question: str, response: str,
                    seed: dict) -> dict: ...


class DeterministicJudge:
    """Offline stand-in: stable pseudo-scores. Non-conforming by construction."""

    async def score(self, category: str, question: str, response: str, seed: dict) -> dict:
        digest = hashlib.sha256(f"{category}:{question}:{response}".encode()).digest()
        return {"believability": (digest[0] % 6) + 4}  # 4..9, deterministic


def closest_partner(agent_id: str, relationships: list[dict]) -> str | None:
    edges = [e for e in relationships if agent_id in (e["a"], e["b"])]
    if not edges:
        return None
    best = max(edges, key=lambda e: (e["closeness"], e["a"], e["b"]))
    return best["b"] if best["a"] == agent_id else best["a"]


async def run_battery(runner: ProbeRunner, streams: dict[str, FrozenStream],
                      relationships: list[dict], tick: int,
                      judge: Judge) -> list[dict]:
    results: list[dict] = []
    for aid in sorted(streams):
        other = closest_partner(aid, relationships) or "your neighbour"
        for category, template in BATTERY:
            question = template.format(other=other)
            probe = await runner.interview(aid, streams[aid], question, tick,
                                           category=category)
            probe["scores"] = await judge.score(category, question,
                                                probe["response"], runner.seeds[aid])
            results.append(probe)
    return results


def summarize(results: list[dict]) -> dict:
    by_category: dict[str, list[int]] = {}
    for probe in results:
        by_category.setdefault(probe["category"], []).append(
            probe["scores"]["believability"])
    return {
        "per_category": {c: sum(v) / len(v) for c, v in sorted(by_category.items())},
        "overall": (sum(s for v in by_category.values() for s in v)
                    / sum(len(v) for v in by_category.values())) if by_category else None,
        "probes": len(results),
    }
