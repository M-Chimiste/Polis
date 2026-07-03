"""Completion log: sequence keys, failure logging, replay round-trip."""
import io
import json

import httpx
import pytest

from cognition.completions import CognitionGateway, CompletionLog
from cognition.fake_model import fake_model_transport
from cognition.prompts import IMPORTANCE_SCHEMA, importance_prompt
from cognition.runner import FAKE_PROFILE
from services.gateway import GatewayCompletion, GatewayFailure, ModelGateway

RUN = "6f1a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b"
AGENT = {"id": "maren_alder"}


def live_gateway(transport=None):
    client = httpx.AsyncClient(transport=transport or fake_model_transport(),
                               base_url=FAKE_PROFILE.base_url)
    return ModelGateway(FAKE_PROFILE, http_client=client)


async def test_sequences_and_log_keys():
    sink = io.BytesIO()
    log = CompletionLog(RUN, sink=sink)
    gw = CognitionGateway(live_gateway(), log)
    for _ in range(3):
        result = await gw.complete("maren_alder", "importance", "importance",
                                   importance_prompt(AGENT, "saw piet"), IMPORTANCE_SCHEMA, tick=7)
        assert isinstance(result, GatewayCompletion)
    await gw.complete("piet_alder", "importance", "importance",
                      importance_prompt({"id": "piet_alder"}, "saw maren"), IMPORTANCE_SCHEMA)
    assert gw.total_calls() == 4
    assert [r["sequence"] for r in log.records if r["agent_id"] == "maren_alder"] == [0, 1, 2]
    assert log.lookup("piet_alder", "importance", 0) is not None
    lines = sink.getvalue().splitlines()
    assert len(lines) == 4
    assert json.loads(lines[0])["tick"] == 7


async def test_replay_serves_from_log_including_failures():
    def flaky(request):
        raise httpx.ConnectError("down")

    # a live run where one call fails
    log = CompletionLog(RUN)
    gw = CognitionGateway(live_gateway(), log)
    ok = await gw.complete("a", "importance", "importance",
                           importance_prompt({"id": "a"}, "x"), IMPORTANCE_SCHEMA)
    gw_down = CognitionGateway(live_gateway(httpx.MockTransport(flaky)), log)
    gw_down._counters = gw._counters  # continue the same sequence space
    failed = await gw_down.complete("a", "importance", "importance",
                                    importance_prompt({"id": "a"}, "y"), IMPORTANCE_SCHEMA)
    assert isinstance(ok, GatewayCompletion) and isinstance(failed, GatewayFailure)

    # replay: identical outcomes, no model
    replay = CognitionGateway(None, CompletionLog(RUN), replay_from=log)
    r1 = await replay.complete("a", "importance", "importance",
                               importance_prompt({"id": "a"}, "x"), IMPORTANCE_SCHEMA)
    r2 = await replay.complete("a", "importance", "importance",
                               importance_prompt({"id": "a"}, "y"), IMPORTANCE_SCHEMA)
    assert isinstance(r1, GatewayCompletion) and r1.parsed == ok.parsed
    assert isinstance(r2, GatewayFailure) and r2.kind == failed.kind


async def test_replay_miss_is_typed():
    log = CompletionLog(RUN)
    replay = CognitionGateway(None, CompletionLog(RUN), replay_from=log)
    result = await replay.complete("a", "importance", "importance",
                                   importance_prompt({"id": "a"}, "x"), IMPORTANCE_SCHEMA)
    assert isinstance(result, GatewayFailure)
    assert result.kind == "replay_miss"


def test_log_round_trips_through_jsonl():
    sink = io.BytesIO()
    log = CompletionLog(RUN, sink=sink)
    log.record("a", "s", 0, "importance", [{"role": "user", "content": "p"}],
               GatewayCompletion(role="importance", model="m", content="{}"), tick=3)
    loaded = CompletionLog.load(sink.getvalue().splitlines(), RUN)
    assert loaded.lookup("a", "s", 0)["result"]["model"] == "m"


def test_needs_gateway_or_replay():
    with pytest.raises(ValueError):
        CognitionGateway(None, CompletionLog(RUN))
