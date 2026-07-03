"""Probe runner: keyword fact checks, frozen state, and THE P3 GATE —
probes and metrics leave zero footprint in sim artifacts."""
import copy
import json

import pytest

import schemas
from cognition.completions import CognitionGateway, CompletionLog
from cognition.embedding import HashEmbedder
from cognition.runner import fake_gateway
from metrics.believability import DeterministicJudge, run_battery
from metrics.coordination import detect_gatherings
from metrics.diffusion import diffusion_curve
from metrics.graph import graph_metrics
from metrics.probes import ProbeRunner, knows_fact
from metrics.store import FrozenStream, freeze, load_ledger, load_memories
from sim.content import load_agents, load_relationships

FACT = "there is a gathering at the tavern on day three"


def stream_of(texts_ticks):
    records = [{"id": f"r{i}", "tick": t, "text": x, "importance": 5,
                "agent_id": "a", "run_id": "r", "kind": "observation"}
               for i, (x, t) in enumerate(texts_ticks)]
    return FrozenStream(records, upto_tick=10**9, embedder=HashEmbedder())


def test_knows_fact_verbatim_and_paraphrase():
    assert knows_fact(stream_of([(f"maren said to me: {FACT}", 5)]), FACT)
    assert knows_fact(stream_of([("heard there is a gathering at the tavern day three", 5)]), FACT)
    assert not knows_fact(stream_of([("the ale is two barrels short", 5)]), FACT)
    # scattered tokens across records don't count — one record must carry it
    assert not knows_fact(stream_of([("a gathering of geese", 1), ("the tavern roof", 2),
                                     ("three loaves", 3)]), FACT)


def test_frozen_stream_is_tick_bounded():
    records = [{"id": f"r{i}", "tick": t, "text": f"x{i}", "importance": 5,
                "agent_id": "a", "run_id": "r", "kind": "observation"}
               for i, t in enumerate([10, 20, 30])]
    frozen = FrozenStream(records, upto_tick=20, embedder=HashEmbedder())
    assert [r["tick"] for r in frozen.records] == [10, 20]


async def test_interview_probe_is_schema_valid_and_isolated():
    seeds = load_agents()
    log = CompletionLog("6f1a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b")
    runner = ProbeRunner("6f1a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b", seeds,
                         CognitionGateway(fake_gateway(), log), HashEmbedder())
    frozen = stream_of([("the autumn ale is two barrels short", 3)])
    probe = await runner.interview("maren_alder", frozen, "How is business?", 100,
                                   category="self_knowledge")
    assert schemas.errors("probe_result", probe) == []
    assert probe["category"] == "self_knowledge"
    assert probe["response"]
    assert len(log.records) == 1  # probe traffic in the probe log, nowhere else


def test_probe_and_metrics_contamination(treated_run):
    """THE GATE: run every metric + probe against the run; sim artifacts and
    live sim state must be byte-identical afterwards."""
    runtime = treated_run["runtime"]
    ledger_before = (treated_run["dir"] / "ledger.jsonl").read_bytes()
    completions_before = (treated_run["dir"] / "completions.jsonl").read_bytes()
    sim_log_before = len(treated_run["gateway"].log.records)
    streams_before = {aid: copy.deepcopy(m.stream.records)
                      for aid, m in runtime.minds.items()}
    objects_before = json.dumps(runtime.world.objects, sort_keys=True)
    tick_before = runtime.world.tick

    ledger = load_ledger(ledger_before.splitlines())
    memories = load_memories((treated_run["dir"] / "memories.jsonl").read_bytes().splitlines())
    seeds = {a: s for a, s in load_agents().items() if a in treated_run["agents"]}

    curve = diffusion_curve(memories, FACT, 2400, 8640, 720,
                            treated_run["writer"].run_id, HashEmbedder(), seeds)
    graph_metrics(ledger, treated_run["agents"])
    detect_gatherings(ledger)
    frozen = freeze(memories, 8640, HashEmbedder())
    probe_log = CompletionLog(treated_run["writer"].run_id + "-probes")
    runner = ProbeRunner(treated_run["writer"].run_id, seeds,
                         CognitionGateway(fake_gateway(), probe_log), HashEmbedder())
    import asyncio
    battery = asyncio.run(run_battery(runner, frozen, load_relationships(), 8640,
                                      DeterministicJudge()))
    assert battery and curve["points"]

    # zero footprint
    assert (treated_run["dir"] / "ledger.jsonl").read_bytes() == ledger_before
    assert (treated_run["dir"] / "completions.jsonl").read_bytes() == completions_before
    assert len(treated_run["gateway"].log.records) == sim_log_before
    for aid, before in streams_before.items():
        assert runtime.minds[aid].stream.records == before, aid
    assert json.dumps(runtime.world.objects, sort_keys=True) == objects_before
    assert runtime.world.tick == tick_before
    for probe in battery:
        assert schemas.errors("probe_result", probe) == []
