"""Gateway wall: structured outputs, one repair re-prompt, typed errors,
per-role sampling resolution, thinking-model hardening (request_extras,
reasoning_content salvage, empty-content failure). Model side is a mocked
OpenAI-compatible endpoint; smoked live against metis/athena 2026-07-03."""
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
    for name in ("metis", "athena"):
        profile = profiles[name]
        model, sampling = profile.resolve("dialogue")
        assert model == "qwen3.6-35b-a3b-mtp"
        assert sampling.temperature is not None
        # thinking model: every role budgets for reasoning + answer
        for role in profile.roles:
            _, s = profile.resolve(role)
            assert s.max_tokens >= 1024, f"{name}:{role} cannot fit reasoning"
        # best-effort thinking kill switch rides on every request
        assert profile.request_extras == {"enable_thinking": False}
        # embedder endpoint matches the pgvector column dimension
        assert profile.embedding is not None and profile.embedding.dim == 768
        # every role references a real tier (validated at load)
        assert set(c.tier for c in profile.roles.values()) <= set(profile.tiers)


def test_role_with_unknown_tier_rejected():
    with pytest.raises(ValueError):
        ServingProfile(
            name="bad", base_url="http://x/v1",
            tiers={"fast": {"model": "m"}},
            roles={"dialogue": {"tier": "warp", "sampling": {}}},
        )


# --- thinking-model hardening (metis/athena measurements, 2026-07-03) ---

EXTRAS_PROFILE = ServingProfile(
    name="extras",
    base_url="http://gateway.test/v1",
    request_extras={"enable_thinking": False},
    tiers={"fast": {"model": "test-8b"}},
    roles={"importance": {"tier": "fast", "sampling": {"temperature": 0.2, "max_tokens": 1024}}},
)


def reasoning_response(content: str, reasoning: str, finish: str = "stop") -> httpx.Response:
    return httpx.Response(200, json={
        "choices": [{"finish_reason": finish,
                     "message": {"role": "assistant", "content": content,
                                 "reasoning_content": reasoning}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    })


async def test_request_extras_ride_every_body_and_sampling_wins():
    seen = {}

    def responder(request):
        seen["body"] = json.loads(request.content)
        return chat_response('{"score": 7}')

    client = httpx.AsyncClient(transport=httpx.MockTransport(responder),
                               base_url=EXTRAS_PROFILE.base_url)
    gw = ModelGateway(EXTRAS_PROFILE, http_client=client)
    result = await gw.complete("importance", [{"role": "user", "content": "score"}],
                               response_schema=RESPONSE_SCHEMA)
    assert isinstance(result, GatewayCompletion)
    assert seen["body"]["enable_thinking"] is False
    assert seen["body"]["temperature"] == 0.2  # sampling still applied


async def test_structured_salvage_from_reasoning_content():
    # metis shunt: grammar-constrained JSON lands in reasoning_content,
    # content is empty. The wall still validates before accepting.
    def responder(request):
        return reasoning_response("", '{"score": 6}')

    gw = make_gateway(responder)
    result = await gw.complete("importance", [{"role": "user", "content": "score"}],
                               response_schema=RESPONSE_SCHEMA)
    assert isinstance(result, GatewayCompletion)
    assert result.parsed == {"score": 6}
    assert result.attempts == 1


async def test_salvage_still_schema_gated():
    # invalid JSON in reasoning_content must NOT be salvaged
    def responder(request):
        return reasoning_response("", "let me think about the score...")

    gw = make_gateway(responder)
    result = await gw.complete("importance", [{"role": "user", "content": "score"}],
                               response_schema=RESPONSE_SCHEMA)
    assert isinstance(result, GatewayFailure)
    assert result.kind == "validation"


async def test_reasoning_never_salvaged_when_content_present():
    # athena shape: thinking in reasoning_content, real answer in content
    def responder(request):
        return reasoning_response('{"score": 3}', "hmm, maybe {\"score\": 9}?")

    gw = make_gateway(responder)
    result = await gw.complete("importance", [{"role": "user", "content": "score"}],
                               response_schema=RESPONSE_SCHEMA)
    assert isinstance(result, GatewayCompletion)
    assert result.parsed == {"score": 3}


async def test_empty_freeform_content_is_failure_not_answer():
    # truncation mid-reasoning: finish_reason=length, empty content
    def responder(request):
        return reasoning_response("", "I was still thinking when", finish="length")

    gw = make_gateway(responder)
    result = await gw.complete("reflection", [{"role": "user", "content": "reflect"}])
    assert isinstance(result, GatewayFailure)
    assert result.kind == "validation"
    assert "length" in result.errors[0]
