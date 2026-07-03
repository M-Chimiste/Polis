"""THE P2 GATE: agents live a coherent unscripted day on the cognition stack;
every completion is logged; replay reproduces the ledger byte-equal.

Runs on the deterministic fake model through the real gateway path — the
same harness reruns against live serving when hardware is available.
"""
import io
import json

import httpx
import pytest

from cognition.completions import CompletionLog
from cognition.runner import FAKE_PROFILE, fake_gateway, run_cognition
from cognition.runtime import Settings
from services.gateway import ModelGateway
from sim.clock import TICKS_PER_DAY

FIVE = ["ilse_alder", "maren_alder", "piet_alder", "sela_crane", "tobias_crane"]
SETTINGS = Settings(reflection_importance_sum_threshold=40.0)


async def day_run(replay_log=None, gateway=None):
    ledger = io.BytesIO()
    completions = io.BytesIO()
    writer, cog_gateway, runtime = await run_cognition(
        TICKS_PER_DAY, seed=42, agent_ids=FIVE, settings=SETTINGS,
        gateway=gateway or (None if replay_log else fake_gateway()),
        replay_log=replay_log, ledger_sink=ledger, completions_sink=completions,
    )
    return ledger.getvalue(), completions.getvalue(), writer, cog_gateway, runtime


@pytest.fixture(scope="module")
def day():
    import asyncio
    return asyncio.run(day_run())


def events_of(ledger_bytes, kind=None):
    events = [json.loads(l) for l in ledger_bytes.splitlines()]
    return [e for e in events if kind is None or e["kind"] == kind]


def test_no_grammar_rejections(day):
    ledger, *_ = day
    grammar = [e for e in events_of(ledger, "intent_rejected")
               if e["data"]["reason"].startswith("grammar")]
    assert grammar == []


def test_agents_plan_and_live_the_day(day):
    ledger, _, _, _, runtime = day
    for aid in FIVE:
        mind = runtime.minds[aid]
        kinds = {r["kind"] for r in mind.stream.records}
        assert "plan" in kinds, aid
        assert not mind.plan.from_fallback, aid
    # commuters actually went to work
    arrivals = events_of(ledger, "agent_arrived")
    assert any(e["agent_id"] == "sela_crane" and e["data"]["location"] == "market_square"
               for e in arrivals)
    # objects got used in the course of the day
    assert len(events_of(ledger, "object_state_changed")) >= 5


def test_everyone_asleep_at_end_of_day(day):
    _, _, _, _, runtime = day
    for aid in FIVE:
        assert runtime.world.agents[aid].status == "sleeping", aid


def test_conversations_happened_and_diffused(day):
    ledger, _, _, _, runtime = day
    assert len(events_of(ledger, "conversation_started")) >= 1
    utterances = events_of(ledger, "utterance")
    assert len(utterances) >= 2
    assert len(events_of(ledger, "conversation_ended")) >= 1
    # both participants wrote summaries back into memory
    ended = events_of(ledger, "conversation_ended")[0]
    for aid in (ended["agent_id"], ended["data"]["partner"]):
        kinds = [r["kind"] for r in runtime.minds[aid].stream.records]
        assert "conversation_summary" in kinds, aid
    # hearing produced observations in someone's memory
    heard = [r for m in runtime.minds.values() for r in m.stream.records
             if "said to me" in r["text"] or "overheard" in r["text"]]
    assert heard


def test_reflection_synthesized_with_citations(day):
    _, _, _, _, runtime = day
    reflections = [r for m in runtime.minds.values() for r in m.stream.records
                   if r["kind"] == "reflection"]
    assert reflections, "no agent crossed the reflection threshold"
    for r in reflections:
        assert r["citations"], r
        owner = runtime.minds[r["agent_id"]].stream
        known = {rec["id"] for rec in owner.records}
        assert set(r["citations"]) <= known


def test_every_completion_logged(day):
    _, completions, _, cog_gateway, runtime = day
    lines = completions.splitlines()
    assert len(lines) == cog_gateway.total_calls() == len(cog_gateway.log.records)
    assert cog_gateway.total_calls() > 50  # a real day of cognition, not a stub
    assert runtime.total_gateway_failures() == 0


async def test_live_rerun_is_byte_equal():
    a_ledger, a_completions, *_ = await day_run()
    b_ledger, b_completions, *_ = await day_run()
    assert a_ledger == b_ledger
    assert a_completions == b_completions


async def test_replay_reproduces_ledger_byte_equal():
    a_ledger, a_completions, writer, *_ = await day_run()
    replay_log = CompletionLog.load(a_completions.splitlines(), writer.run_id)
    b_ledger, _, _, replay_gateway, _ = await day_run(replay_log=replay_log)
    # replay serves every call from the log...
    assert replay_gateway.replay_mode
    misses = [r for r in replay_gateway.log.records
              if r["outcome"] == "failure" and r["result"]["kind"] == "replay_miss"]
    assert misses == []
    # ...and the whole ledger is byte-equal, run_started included
    assert a_ledger == b_ledger


async def test_gateway_down_degrades_never_crashes():
    def dead(request):
        raise httpx.ConnectError("gateway down")

    client = httpx.AsyncClient(transport=httpx.MockTransport(dead),
                               base_url=FAKE_PROFILE.base_url)
    gateway = ModelGateway(FAKE_PROFILE, http_client=client)
    ledger = io.BytesIO()
    writer, cog_gateway, runtime = await run_cognition(
        TICKS_PER_DAY // 2, seed=42, agent_ids=FIVE, settings=SETTINGS,
        gateway=gateway, ledger_sink=ledger,
    )
    assert runtime.total_gateway_failures() > 0
    for aid in FIVE:
        assert runtime.minds[aid].plan.from_fallback, aid
    # fallback agenda still commutes people to work
    arrivals = [json.loads(l) for l in ledger.getvalue().splitlines()
                if json.loads(l)["kind"] == "agent_arrived"]
    assert any(e["agent_id"] == "sela_crane" and e["data"]["location"] == "market_square"
               for e in arrivals)
