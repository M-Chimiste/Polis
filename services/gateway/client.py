"""The gateway wall: structured outputs validated against JSON Schema, one
repair re-prompt on failure, then a typed error object. Callers never see an
exception from `complete()` — transport and validation failures both come
back as GatewayFailure so the sim can fall back to plan-cache execution.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Union

import httpx
import jsonschema

from services.gateway.config import ServingProfile

REPAIR_PROMPT = (
    "Your previous response was not valid against the required JSON schema. "
    "Validation error: {error}\n"
    "Respond again with ONLY the corrected JSON object, no prose."
)

# Called after every model round-trip with a replayable record; the P2
# logged-completion replay mode is built on this hook.
CompletionLogger = Callable[[dict], Awaitable[None]]


@dataclass
class GatewayCompletion:
    role: str
    model: str
    content: str
    parsed: Any | None = None  # set when a response_schema was requested
    attempts: int = 1
    usage: dict = field(default_factory=dict)


@dataclass
class GatewayFailure:
    kind: str  # "transport" | "validation"
    role: str
    model: str | None = None
    errors: list[str] = field(default_factory=list)
    attempts: int = 0
    raw_content: str | None = None


GatewayResult = Union[GatewayCompletion, GatewayFailure]


class ModelGateway:
    def __init__(
        self,
        profile: ServingProfile,
        http_client: httpx.AsyncClient | None = None,
        on_completion: CompletionLogger | None = None,
        timeout: float = 120.0,
    ):
        self.profile = profile
        self._client = http_client or httpx.AsyncClient(base_url=profile.base_url, timeout=timeout)
        self._on_completion = on_completion

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        role: str,
        messages: list[dict],
        response_schema: dict | None = None,
        call_site: str | None = None,
    ) -> GatewayResult:
        """One cognition call. At most two model round-trips (initial + one repair)."""
        model, sampling = self.profile.resolve(role)
        convo = list(messages)
        last_error = ""
        last_content = None

        max_attempts = 2 if response_schema is not None else 1
        for attempt in range(1, max_attempts + 1):
            body: dict = {"model": model, "messages": convo, **sampling.as_request_params()}
            if response_schema is not None:
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_schema.get("title", "response"),
                        "schema": response_schema,
                    },
                }

            try:
                resp = await self._client.post("/chat/completions", json=body)
            except httpx.HTTPError as exc:
                return GatewayFailure(
                    kind="transport", role=role, model=model,
                    errors=[f"{type(exc).__name__}: {exc}"], attempts=attempt,
                )
            if resp.status_code != 200:
                return GatewayFailure(
                    kind="transport", role=role, model=model,
                    errors=[f"HTTP {resp.status_code}: {resp.text[:500]}"], attempts=attempt,
                )

            payload = resp.json()
            content = payload["choices"][0]["message"]["content"]
            last_content = content
            usage = payload.get("usage") or {}
            await self._log(role=role, call_site=call_site, attempt=attempt, request=body, response=payload)

            if response_schema is None:
                return GatewayCompletion(role=role, model=model, content=content, attempts=attempt, usage=usage)

            try:
                parsed = json.loads(content)
                jsonschema.validate(parsed, response_schema)
                return GatewayCompletion(
                    role=role, model=model, content=content, parsed=parsed, attempts=attempt, usage=usage,
                )
            except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
                last_error = str(exc).splitlines()[0]
                convo = convo + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": REPAIR_PROMPT.format(error=last_error)},
                ]

        return GatewayFailure(
            kind="validation", role=role, model=model,
            errors=[last_error], attempts=max_attempts, raw_content=last_content,
        )

    async def _log(self, **record) -> None:
        if self._on_completion is not None:
            await self._on_completion(record)
