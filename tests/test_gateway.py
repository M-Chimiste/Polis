"""Gateway wall: structured outputs, one repair re-prompt, typed errors,
per-role sampling resolution. Model side is a mocked OpenAI-compatible
endpoint (the real smoke test against Mnemosyne is a P0 hardware task)."""
import json

import httpx
import pytest

from services.gateway import (
    GatewayCompletion,
    GatewayFailure,
    ModelGateway,
    ServingProfile,
    load_profiles,
)

RESPONSE_SCHEMA = {
    "title": "importance",
    "type": "object",
    "required": ["score"],
    "additionalProperties": False,
    "properties": {"score": {"type": "integer", "minimum": 1, "maximum": 10}},
}

PROFILE = ServingProfile(
    name="test",
    base_url="http://gateway.test/v1",
    tiers={"fast": {"model": "test-8b"}, "slow": {"model": "test-32b"}},
    roles={
        "importance": {"tier": "fast", "sampling": {"temperature": 0.2, "max_tokens": 16}},
        "reflection": {"tier": "slow", "sampling": {"temperature": 0.8, "top_k": 40, "min_p": 0.05}},
    },
)


def make_gateway(responder, on_completion=None):
    transport = httpx.MockTransport(responder)
    client = httpx.AsyncClient(transport=transport, base_url=PROFILE.base_url)
    return ModelGateway(PROFILE, http_client=client, on_completion=on_completion)


def chat_response(content: str) -> httpx.Response:
    return httpx.Response(200, json={
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    })


async def test_structured_output_success():
    seen = {}

    def responder(request):
        seen["body"] = json.loads(request.content)
        return chat_response('{"score": 7}')

    gw = make_gateway(responder)
    result = await gw.complete("importance", [{"role": "user", "content": "score this"}],
                               response_schema=RESPONSE_SCHEMA)
    assert isinstance(result, GatewayCompletion)
    assert result.parsed == {"score": 7}
    assert result.attempts == 1
    assert result.model == "test-8b"
    # sampling resolved per role
    assert seen["body"]["temperature"] == 0.2
    assert seen["body"]["max_tokens"] == 16
    # structured output requested
    assert seen["body"]["response_format"]["json_schema"]["schema"] == RESPONSE_SCHEMA


async def test_repair_reprompt_recovers():
    calls = []

    def responder(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return chat_response('{"score": "very important"}')  # violates schema
        return chat_response('{"score": 9}')

    gw = make_gateway(responder)
    result = await gw.complete("importance", [{"role": "user", "content": "score"}],
                               response_schema=RESPONSE_SCHEMA)
    assert isinstance(result, GatewayCompletion)
    assert result.parsed == {"score": 9}
    assert result.attempts == 2
    # repair turn carries the failed output and the validation error
    repair_messages = calls[1]["messages"]
    assert repair_messages[-2]["role"] == "assistant"
    assert "not valid" in repair_messages[-1]["content"]


async def test_double_validation_failure_returns_typed_error():
    def responder(request):
        return chat_response("i cannot answer in json, sorry")

    gw = make_gateway(responder)
    result = await gw.complete("importance", [{"role": "user", "content": "score"}],
                               response_schema=RESPONSE_SCHEMA)
    assert isinstance(result, GatewayFailure)
    assert result.kind == "validation"
    assert result.attempts == 2
    assert result.raw_content == "i cannot answer in json, sorry"


async def test_transport_failure_is_typed_not_raised():
    def responder(request):
        raise httpx.ConnectError("gateway down")

    gw = make_gateway(responder)
    result = await gw.complete("importance", [{"role": "user", "content": "hi"}])
    assert isinstance(result, GatewayFailure)
    assert result.kind == "transport"


async def test_http_error_status_is_typed():
    def responder(request):
        return httpx.Response(503, text="overloaded")

    gw = make_gateway(responder)
    result = await gw.complete("reflection", [{"role": "user", "content": "reflect"}])
    assert isinstance(result, GatewayFailure)
    assert result.kind == "transport"
    assert "503" in result.errors[0]


async def test_freeform_completion_and_vllm_sampling_extensions():
    seen = {}

    def responder(request):
        seen["body"] = json.loads(request.content)
        return chat_response("a quiet day at the mill")

    gw = make_gateway(responder)
    result = await gw.complete("reflection", [{"role": "user", "content": "reflect"}])
    assert isinstance(result, GatewayCompletion)
    assert result.parsed is None
    assert seen["body"]["model"] == "test-32b"
    # vLLM extensions ride as top-level body fields
    assert seen["body"]["top_k"] == 40
    assert seen["body"]["min_p"] == 0.05


async def test_completion_log_hook_fires_per_roundtrip():
    logged = []

    async def on_completion(record):
        logged.append(record)

    def responder(request):
        return chat_response("not json either")

    gw = make_gateway(responder, on_completion=on_completion)
    await gw.complete("importance", [{"role": "user", "content": "x"}],
                      response_schema=RESPONSE_SCHEMA, call_site="importance_score")
    assert len(logged) == 2  # initial + repair, both replayable
    assert all(r["call_site"] == "importance_score" for r in logged)
    assert logged[0]["request"]["messages"][0]["content"] == "x"


async def test_unknown_role_raises_keyerror():
    gw = make_gateway(lambda request: chat_response("ok"))
    with pytest.raises(KeyError):
        await gw.complete("dramaturgy", [{"role": "user", "content": "no"}])


def test_shipped_profiles_load_and_resolve():
    profiles = load_profiles()
    mnemosyne = profiles["mnemosyne"]
    model, sampling = mnemosyne.resolve("dialogue")
    assert model == "Qwen/Qwen3-8B"
    assert sampling.temperature is not None
    model, _ = mnemosyne.resolve("reflection")
    assert model == "Qwen/Qwen3-32B"
    # every role references a real tier (validated at load)
    assert set(c.tier for c in mnemosyne.roles.values()) <= set(mnemosyne.tiers)


def test_role_with_unknown_tier_rejected():
    with pytest.raises(ValueError):
        ServingProfile(
            name="bad", base_url="http://x/v1",
            tiers={"fast": {"model": "m"}},
            roles={"dialogue": {"tier": "warp", "sampling": {}}},
        )
