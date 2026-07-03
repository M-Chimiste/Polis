"""Deterministic fake model: a role-aware OpenAI-compatible mock transport.

Dev/test stand-in only — it lets the entire cognition stack run offline and
byte-reproducibly (the standing remote constraint), driving the REAL gateway
code path (structured outputs, validation wall, repair, logging). It must
never appear in an experiment; runs made with it are non-conforming by
construction.

Behavior is a pure function of the prompt's CONTEXT_JSON, so live runs are
deterministic and replay comparisons are meaningful.
"""
from __future__ import annotations

import hashlib
import json

import httpx

from cognition.prompts import parse_context
from sim.clock import parse_hhmm


def _h(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def _minutes_to_hhmm(minute: int) -> str:
    minute %= 24 * 60
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _agenda(ctx: dict) -> dict:
    anchors = ctx["anchors"]
    wake, ws = anchors["wake"], anchors["work_start"]
    midday, we, sleep = anchors["midday_meal"], anchors["work_end"], anchors["sleep"]
    meal_end = _minutes_to_hhmm(parse_hhmm(midday) + 60)
    return {"agenda": [
        {"start": wake, "end": ws, "activity": "morning routine", "location": ctx["home"]},
        {"start": ws, "end": midday, "activity": f"morning work as {ctx['occupation']}",
         "location": ctx["workplace"]},
        {"start": midday, "end": meal_end, "activity": "midday meal", "location": ctx["home"]},
        {"start": meal_end, "end": we, "activity": f"afternoon work as {ctx['occupation']}",
         "location": ctx["workplace"]},
        {"start": we, "end": sleep, "activity": "evening leisure", "location": ctx["home"]},
        {"start": sleep, "end": wake, "activity": "sleep", "location": ctx["home"]},
    ]}


def _pick_objects(ctx: dict, affordance: str) -> list[dict]:
    return [o for o in ctx["objects"] if affordance in o["affordances"]]


def _steps(ctx: dict) -> dict:
    block = ctx["block"]
    activity = block["activity"]
    steps: list[dict] = [{"minutes": 1, "kind": "move_to", "destination": block["location"]}]
    if activity == "sleep":
        steps.append({"minutes": 24 * 60, "kind": "sleep"})
        return {"steps": steps}
    if "work" in activity:
        wanted = "work"
    elif "meal" in activity or "morning" in activity:
        wanted = "food"
    else:
        wanted = "leisure"
    usable = _pick_objects(ctx, wanted) or _pick_objects(ctx, "social")
    for obj in usable[:2]:
        verb = sorted(obj["interactions"])[_h(ctx["agent"] + obj["id"]) % len(obj["interactions"])]
        steps.append({"minutes": 30, "kind": "use_object",
                      "object_id": obj["id"], "interaction": verb})
    steps.append({"minutes": 24 * 60, "kind": "idle"})
    return {"steps": steps}


def _respond(ctx: dict) -> str:
    role = ctx["role"]
    if role == "importance":
        # tiered like a real fast-tier scorer would: routine co-presence is
        # mundane, speech heard is memorable, sightings sit between
        text = ctx["observation"]
        if "said to me" in text or "overheard" in text:
            score = 4 + _h(text) % 4          # 4-7: speech heard is memorable
        elif "spent time with" in text or text.startswith("saw "):
            score = 2 + _h(text) % 4          # 2-5: co-presence and sightings
        else:
            score = 3 + _h(text) % 5          # 3-7: plans, summaries, insights
        return json.dumps({"score": score})
    if role == "daily_planning":
        return json.dumps(_agenda(ctx))
    if role == "decomposition":
        return json.dumps(_steps(ctx))
    if role == "action_selection":
        nearby = ctx["nearby"]
        if nearby and _h(ctx["agent"] + ctx["observation"]) % 3 == 0:
            return json.dumps({"action": "start_conversation", "partner": sorted(nearby)[0]})
        return json.dumps({"action": "continue"})
    if role == "dialogue":
        if "turn" in ctx:  # a turn: most salient memory not already said
            history_text = "\n".join(ctx["history"])
            fresh = [m for m in ctx["memories"] if m["text"][:60] not in history_text]
            if fresh:
                best = max(fresh, key=lambda m: (m["importance"], _h(m["text"])))
                memory = best["text"]
            else:
                memory = "the day's small business"
            line = f"{ctx['agent']} to {ctx['partner']}: thinking on '{memory[:60]}'"
            if ctx["turn"] >= 3:
                line += " [DONE]"
            return line
        return json.dumps({"summary": (
            f"{ctx['agent']} spoke with {ctx['partner']}: "
            + (ctx["history"][0][:80] if ctx["history"] else "small talk")
        )})
    if role == "probe":
        memory = ctx["memories"][0] if ctx["memories"] else "nothing in particular"
        return f"Well, since you ask — {memory[:100]}"
    if role == "reflection":
        if "question" in ctx:
            n = len(ctx["memories"])
            return json.dumps({"insights": [{
                "text": f"{ctx['agent']} keeps returning to: {ctx['question'][:70]}",
                "evidence": sorted({_h(ctx["question"]) % n, (_h(ctx["question"]) // 7) % n}),
            }]})
        seed_text = ctx["memories"][0] if ctx["memories"] else "the day"
        return json.dumps({"questions": [f"What does '{seed_text[:50]}' mean for {ctx['agent']}?"]})
    raise AssertionError(f"fake model: unknown role '{role}'")


def fake_model_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        prompt = body["messages"][-1]["content"]
        # repair re-prompts append a correction turn; the original context
        # prompt is the last message that carries the marker
        for message in reversed(body["messages"]):
            if "CONTEXT_JSON:" in message["content"]:
                prompt = message["content"]
                break
        content = _respond(parse_context(prompt))
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": len(prompt) // 4,
                      "completion_tokens": len(content) // 4},
        })

    return httpx.MockTransport(handler)
