"""Believability battery over frozen state with the stub judge."""
import asyncio

import schemas
from cognition.completions import CognitionGateway, CompletionLog
from cognition.embedding import HashEmbedder
from cognition.runner import fake_gateway
from metrics.believability import (
    BATTERY, DeterministicJudge, closest_partner, run_battery, summarize,
)
from metrics.probes import ProbeRunner
from metrics.store import freeze, load_memories
from sim.content import load_agents, load_relationships


def test_battery_covers_park_categories():
    assert {c for c, _ in BATTERY} == {"self_knowledge", "memory", "plans",
                                       "reactions", "reflections"}


def test_closest_partner_uses_closeness():
    rels = load_relationships()
    partner = closest_partner("maren_alder", rels)
    assert partner == "piet_alder"  # spouses, closeness 0.9


def test_battery_runs_and_summarizes(treated_run):
    memories = load_memories((treated_run["dir"] / "memories.jsonl").read_bytes().splitlines())
    seeds = {a: s for a, s in load_agents().items() if a in treated_run["agents"]}
    frozen = freeze(memories, 8640, HashEmbedder())
    log = CompletionLog(treated_run["writer"].run_id + "-probes")
    runner = ProbeRunner(treated_run["writer"].run_id, seeds,
                         CognitionGateway(fake_gateway(), log), HashEmbedder())
    results = asyncio.run(run_battery(runner, frozen, load_relationships(), 8640,
                                      DeterministicJudge()))
    assert len(results) == len(BATTERY) * len(seeds)
    for probe in results:
        assert schemas.errors("probe_result", probe) == []
        assert 4 <= probe["scores"]["believability"] <= 9
    summary = summarize(results)
    assert set(summary["per_category"]) == {c for c, _ in BATTERY}
    assert summary["overall"] is not None
    assert summary["probes"] == len(results)
