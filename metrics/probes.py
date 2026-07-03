"""Probe runner: interviews and fact checks against FROZEN agent state.

Probe traffic is invisible to the sim: probes operate on FrozenStream
copies, use their own CompletionLog, and write only probe_result records
(the probes table / probes.jsonl). The contamination test in the suite
asserts a probe run leaves zero diff in sim artifacts.

Fact checks are deterministic keyword checks in v1 (objective, model-free —
right for the fake-model era where utterances quote memories verbatim).
Judge-scored fact checks join with real models.
"""
from __future__ import annotations

import re
import uuid

import schemas
from cognition import prompts
from cognition.completions import CognitionGateway
from cognition.retrieval import RetrievalParams, retrieve
from metrics.store import FrozenStream
from services.gateway import GatewayCompletion

PROBE_NS = uuid.UUID("6ba7b813-9dad-11d1-80b4-00c04fd430c8")  # uuid.NAMESPACE_X500

STOPWORDS = {"a", "an", "the", "is", "are", "was", "at", "on", "in", "of", "to",
             "and", "or", "there", "be", "will", "for", "with", "about"}


def significant_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", text.lower()) if t not in STOPWORDS}


def knows_fact(stream: FrozenStream, fact: str, threshold: float = 0.6) -> bool:
    """True if any single memory record carries enough of the fact's content."""
    fact_tokens = significant_tokens(fact)
    if not fact_tokens:
        return False
    return any(
        len(fact_tokens & significant_tokens(r["text"])) / len(fact_tokens) >= threshold
        for r in stream.records
    )


def probe_prompt(seed: dict, question: str, retrieved: list[str]) -> list[dict]:
    return prompts.with_context(
        "Answer the interviewer's question in first person, as this villager, "
        "grounded only in the provided memories.",
        {"role": "probe", "agent": seed["id"], "bio": seed["bio"],
         "traits": seed["traits"], "question": question, "memories": retrieved},
    )


class ProbeRunner:
    def __init__(self, run_id: str, seeds: dict[str, dict], gateway: CognitionGateway,
                 embedder, retrieval: RetrievalParams | None = None):
        self.run_id = run_id
        self.seeds = seeds
        self.gateway = gateway  # its own CompletionLog — never the sim's
        self.embedder = embedder
        self.retrieval = retrieval or RetrievalParams()

    def _result(self, agent_id: str, kind: str, tick: int, question: str,
                response: str, scores: dict | None = None,
                category: str | None = None) -> dict:
        result = {
            "probe_id": str(uuid.uuid5(PROBE_NS, f"{self.run_id}:{agent_id}:{kind}:{tick}:{question}")),
            "run_id": self.run_id,
            "agent_id": agent_id,
            "kind": kind,
            "tick": tick,
            "question": question,
            "response": response,
        }
        if scores is not None:
            result["scores"] = scores
        if category is not None:
            result["category"] = category
        problems = schemas.errors("probe_result", result)
        if problems:
            raise ValueError(f"internal bug: invalid probe result: {problems[0]}")
        return result

    def fact_check(self, agent_id: str, stream: FrozenStream, fact: str, tick: int) -> dict:
        """Deterministic, model-free: zero traffic anywhere."""
        return self._result(
            agent_id, "fact_check", tick,
            question=f"Have you heard anything about this: {fact}?",
            response="", scores={"knows_fact": knows_fact(stream, fact)})

    async def interview(self, agent_id: str, stream: FrozenStream, question: str,
                        tick: int, category: str | None = None) -> dict:
        retrieved = [r["text"] for r in retrieve(stream, self.embedder, question,
                                                 tick, self.retrieval)]
        result = await self.gateway.complete(
            agent_id, f"probe:{category or 'interview'}", "probe",
            probe_prompt(self.seeds[agent_id], question, retrieved), tick=tick)
        response = result.content if isinstance(result, GatewayCompletion) else ""
        return self._result(agent_id, "interview", tick, question, response,
                            category=category)
