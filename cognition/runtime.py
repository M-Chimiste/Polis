"""The cognition runtime: per-tick orchestration of the Park stack.

Scheduling is deterministic — agents are processed in sorted id order and
every model call is awaited in that order. Wall-clock overlap of slow calls
is a serving-time optimization that must never change sim-time semantics:
determinism comes from logged-completion replay, and replay only works if
call order is a function of sim state.

Cost gate: sleeping agents and cached plan steps consume zero model calls.
Gateway failures degrade per subsystem (fallback agenda/steps, conversation
ends, reflection skipped) and are counted — the sim never crashes on a dead
gateway.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from cognition import prompts
from cognition.completions import CognitionGateway
from cognition.memory import MemoryStream
from cognition.planning import (
    PlanCache, Step, agenda_text, fallback_agenda, fallback_steps, steps_from_payload,
)
from cognition.retrieval import RetrievalParams, retrieve
from services.gateway import GatewayCompletion
from sim.clock import TICKS_PER_DAY, in_window, minute_of_day, parse_hhmm
from sim.perception import PerceptionParams, perceive
from sim.world import World

Event = tuple[str, str | None, dict]
DEFAULT_IMPORTANCE = 5  # used when the importance call fails (gateway down)


@dataclass
class Settings:
    retrieval: RetrievalParams = field(default_factory=RetrievalParams)
    perception: PerceptionParams = field(default_factory=PerceptionParams)
    interrupt_importance_threshold: int = 6
    reflection_importance_sum_threshold: float = 60.0
    max_conversation_turns: int = 4

    @classmethod
    def from_experiment_config(cls, config: dict) -> "Settings":
        r, p = config["retrieval"], config["perception"]
        return cls(
            retrieval=RetrievalParams(
                alpha=r["alpha"], beta=r["beta"], gamma=r["gamma"],
                recency_decay=r.get("recency_decay", 0.995), top_k=r.get("top_k", 5),
            ),
            perception=PerceptionParams(
                sight_cone_half_angle_deg=p["sight_cone_half_angle_deg"],
                sight_range=p["sight_range"], hearing_radius=p["hearing_radius"],
            ),
            interrupt_importance_threshold=config.get("interrupt_importance_threshold", 6),
            reflection_importance_sum_threshold=config.get("reflection_importance_sum_threshold", 60.0),
            max_conversation_turns=config.get("max_conversation_turns", 4),
        )


@dataclass
class Conversation:
    initiator: str
    partner: str
    speaker: str
    turn: int = 0
    history: list[str] = field(default_factory=list)

    def other(self, agent_id: str) -> str:
        return self.partner if agent_id == self.initiator else self.initiator


@dataclass
class Mind:
    seed: dict
    stream: MemoryStream
    plan: PlanCache = field(default_factory=PlanCache)
    last_seen: frozenset = frozenset()
    conversation: Conversation | None = None
    incoming_request: str | None = None
    reflection_marker: int = 0
    gateway_failures: int = 0


class CognitionRuntime:
    def __init__(self, world: World, seeds: dict[str, dict], gateway: CognitionGateway,
                 embedder, settings: Settings, run_id: str):
        self.world = world
        self.gateway = gateway
        self.embedder = embedder
        self.settings = settings
        self.minds = {
            aid: Mind(seed=seed, stream=MemoryStream(run_id, aid, embedder))
            for aid, seed in sorted(seeds.items())
        }

    # ------------------------------------------------------------ helpers --
    async def _call(self, agent_id, call_site, role, messages, schema=None):
        return await self.gateway.complete(agent_id, call_site, role, messages,
                                           response_schema=schema, tick=self.world.tick)

    async def _score_importance(self, mind: Mind, text: str) -> int:
        result = await self._call(
            mind.seed["id"], "importance", "importance",
            prompts.importance_prompt(mind.seed, text), prompts.IMPORTANCE_SCHEMA)
        if isinstance(result, GatewayCompletion):
            return result.parsed["score"]
        mind.gateway_failures += 1
        return DEFAULT_IMPORTANCE

    async def _observe(self, mind: Mind, text: str, kind: str = "observation") -> dict:
        importance = await self._score_importance(mind, text)
        return mind.stream.write(kind, text, self.world.tick, importance)

    def _location_objects(self, location: str) -> list[dict]:
        return [
            {"id": oid, "name": o["name"], "interactions": sorted(o["interactions"]),
             "affordances": o["affordances"]}
            for oid, o in sorted(self.world.objects.items()) if o["location"] == location
        ]

    def _hearers(self, speaker: str) -> list[str]:
        pos = self.world.agents[speaker].pos
        radius = self.settings.perception.hearing_radius
        return [aid for aid in sorted(self.world.agents)
                if aid != speaker and math.dist(self.world.agents[aid].pos, pos) <= radius]

    def _retrieved_texts(self, mind: Mind, query: str) -> list[str]:
        records = retrieve(mind.stream, self.embedder, query,
                           self.world.tick, self.settings.retrieval)
        return [r["text"] for r in records]

    # ------------------------------------------------------------ planning --
    async def _ensure_plan(self, mind: Mind, day: int) -> None:
        if mind.plan.day == day:
            return
        aid = mind.seed["id"]
        recap = [r["text"] for r in mind.stream.records
                 if r["kind"] in ("reflection", "conversation_summary")][-3:]
        result = await self._call(
            aid, "daily_plan", "daily_planning",
            prompts.daily_plan_prompt(mind.seed, day, recap), prompts.AGENDA_SCHEMA)
        if isinstance(result, GatewayCompletion):
            agenda, from_fallback = result.parsed["agenda"], False
        else:
            mind.gateway_failures += 1
            agenda, from_fallback = fallback_agenda(mind.seed), True
        mind.plan = PlanCache(day=day, agenda=agenda, from_fallback=from_fallback)
        importance = DEFAULT_IMPORTANCE if from_fallback else \
            await self._score_importance(mind, agenda_text(agenda))
        mind.stream.write("plan", f"plan for day {day}: {agenda_text(agenda)}",
                          self.world.tick, importance)

    async def _ensure_steps(self, mind: Mind, minute: int) -> None:
        located = mind.plan.current_block(minute)
        if located is None:
            if not mind.plan.steps:
                mind.plan.steps = [Step(minutes=5, kind="idle")]
            return
        index, block = located
        if index == mind.plan.block_index and mind.plan.steps:
            return
        mind.plan.block_index = index
        aid = mind.seed["id"]
        if mind.plan.from_fallback:
            payload = {"steps": fallback_steps(block)}
        else:
            result = await self._call(
                aid, "decompose", "decomposition",
                prompts.decompose_prompt(mind.seed, block,
                                         self._location_objects(block["location"])),
                prompts.STEPS_SCHEMA)
            if isinstance(result, GatewayCompletion):
                payload = result.parsed
            else:
                mind.gateway_failures += 1
                payload = {"steps": fallback_steps(block)}
        mind.plan.steps = steps_from_payload(payload, block, self.world.objects)

    def _step_intent(self, mind: Mind) -> dict | None:
        """Advance the plan cache; returns an intent or None. Zero model calls."""
        aid = mind.seed["id"]
        agent = self.world.agents[aid]
        while mind.plan.steps:
            step = mind.plan.steps[0]
            if not step.started:
                step.started = True
                step.ticks_left = step.minutes * 60 // 10
                if step.kind == "move_to":
                    if self.world.location_of(aid) == step.destination:
                        mind.plan.steps.pop(0)
                        continue
                    return {"agent_id": aid, "tick": self.world.tick,
                            "kind": "move_to", "destination": step.destination}
                if step.kind == "use_object":
                    return {"agent_id": aid, "tick": self.world.tick, "kind": "use_object",
                            "object_id": step.object_id, "interaction": step.interaction}
                if step.kind == "sleep":
                    return {"agent_id": aid, "tick": self.world.tick, "kind": "sleep"}
                return None  # idle: the world's default is already idle
            # step in progress
            if step.kind == "move_to":
                if agent.dest is None and agent.status != "moving":
                    mind.plan.steps.pop(0)
                    continue
                return None
            step.ticks_left -= 1
            if step.ticks_left <= 0:
                mind.plan.steps.pop(0)
                continue
            return None
        return None

    # ------------------------------------------------------------ dialogue --
    async def _dialogue_turn(self, conv: Conversation) -> list[Event]:
        speaker_mind = self.minds[conv.speaker]
        listener = conv.other(conv.speaker)
        events: list[Event] = []
        result = await self._call(
            conv.speaker, "dialogue_turn", "dialogue",
            prompts.dialogue_turn_prompt(speaker_mind.seed, listener, conv.turn,
                                         self._retrieved_texts(speaker_mind, listener),
                                         conv.history))
        if isinstance(result, GatewayCompletion):
            text = result.content
        else:
            speaker_mind.gateway_failures += 1
            text = "[DONE]"
        conv.history.append(f"{conv.speaker}: {text}")
        events.append(("utterance", conv.speaker,
                       {"partner": listener, "turn": conv.turn, "text": text}))
        for hearer in self._hearers(conv.speaker):
            prefix = (f"{conv.speaker} said to me" if hearer == listener
                      else f"overheard {conv.speaker} tell {listener}")
            await self._observe(self.minds[hearer], f"{prefix}: {text}")
        conv.turn += 1
        done = "[DONE]" in text or conv.turn >= self.settings.max_conversation_turns
        if done:
            events.extend(await self._end_conversation(conv))
        else:
            conv.speaker = listener
        return events

    async def _end_conversation(self, conv: Conversation) -> list[Event]:
        for aid in (conv.initiator, conv.partner):
            mind = self.minds[aid]
            result = await self._call(
                aid, "dialogue_summary", "dialogue",
                prompts.summary_prompt(mind.seed, conv.other(aid), conv.history),
                prompts.SUMMARY_SCHEMA)
            if isinstance(result, GatewayCompletion):
                summary = result.parsed["summary"]
            else:
                mind.gateway_failures += 1
                summary = f"spoke with {conv.other(aid)}"
            importance = await self._score_importance(mind, summary)
            mind.stream.write("conversation_summary", summary, self.world.tick, importance)
            mind.conversation = None
        return [("conversation_ended", conv.initiator,
                 {"partner": conv.partner, "turns": conv.turn})]

    # ---------------------------------------------------------- reflection --
    async def _maybe_reflect(self, mind: Mind) -> None:
        if mind.stream.importance_sum_since(mind.reflection_marker) < \
                self.settings.reflection_importance_sum_threshold:
            return
        aid = mind.seed["id"]
        recent = [r["text"] for r in mind.stream.records[mind.reflection_marker:]]
        mind.reflection_marker = len(mind.stream.records)
        result = await self._call(
            aid, "reflection_questions", "reflection",
            prompts.questions_prompt(mind.seed, recent[-10:]), prompts.QUESTIONS_SCHEMA)
        if not isinstance(result, GatewayCompletion):
            mind.gateway_failures += 1
            return
        for question in result.parsed["questions"][:2]:
            evidence = retrieve(mind.stream, self.embedder, question,
                                self.world.tick, self.settings.retrieval)
            if not evidence:
                continue
            insight_result = await self._call(
                aid, "reflection_insights", "reflection",
                prompts.insights_prompt(mind.seed, question, [r["text"] for r in evidence]),
                prompts.INSIGHTS_SCHEMA)
            if not isinstance(insight_result, GatewayCompletion):
                mind.gateway_failures += 1
                continue
            for insight in insight_result.parsed["insights"]:
                citations = [evidence[i]["id"] for i in insight["evidence"] if i < len(evidence)]
                if not citations:
                    continue
                importance = await self._score_importance(mind, insight["text"])
                mind.stream.write("reflection", insight["text"], self.world.tick,
                                  importance, citations=citations)

    # ------------------------------------------------------------- the tick --
    async def tick(self, prev_events: list[Event]) -> tuple[dict[str, dict], list[Event]]:
        world = self.world
        minute = minute_of_day(world.tick)
        day = world.tick // TICKS_PER_DAY
        intents: dict[str, dict] = {}
        cognition_events: list[Event] = []

        for kind, agent_id, data in prev_events:
            if kind == "conversation_requested":
                self.minds[data["partner"]].incoming_request = agent_id
            elif kind == "conversation_started":
                initiator = data["partner"]
                conv = Conversation(initiator=initiator, partner=agent_id, speaker=initiator)
                if self.minds[initiator].conversation is None and \
                        self.minds[agent_id].conversation is None:
                    self.minds[initiator].conversation = conv
                    self.minds[agent_id].conversation = conv

        handled_conversations: set[int] = set()
        for aid in sorted(self.minds):
            mind = self.minds[aid]
            agent = world.agents[aid]
            anchors = mind.seed["daily_anchors"]
            asleep_window = in_window(minute, parse_hhmm(anchors["sleep"]),
                                      parse_hhmm(anchors["wake"]))

            if agent.status == "sleeping":
                if asleep_window:
                    continue  # cost gate: zero calls while asleep
                intents[aid] = {"agent_id": aid, "tick": world.tick, "kind": "idle"}
                continue  # wake this tick, think next tick

            # -- perception -> observations (importance-scored)
            percept = perceive(world, self.settings.perception, aid)
            seen = frozenset(percept["seen"])
            salient: list[dict] = []
            for other in sorted(seen - mind.last_seen):
                where = world.location_of(aid) or "the lanes"
                record = await self._observe(mind, f"saw {other} at {where}")
                salient.append(record)
            mind.last_seen = seen

            # -- incoming conversation request: accept unless busy
            if mind.incoming_request is not None:
                requester = mind.incoming_request
                mind.incoming_request = None
                mode = "accept" if mind.conversation is None else "decline"
                intents[aid] = {"agent_id": aid, "tick": world.tick,
                                "kind": "converse_with", "partner_id": requester, "mode": mode}
                continue

            # -- active conversation: one utterance per tick, speaker's pass
            if mind.conversation is not None:
                conv = mind.conversation
                if id(conv) not in handled_conversations and conv.speaker == aid:
                    handled_conversations.add(id(conv))
                    cognition_events.extend(await self._dialogue_turn(conv))
                continue  # conversing agents hold position (no plan intents)

            # -- importance-gated interrupt -> react call
            reacted = False
            threshold = self.settings.interrupt_importance_threshold
            for record in salient:
                if record["importance"] < threshold:
                    continue
                candidates = [x for x in sorted(seen) if world.co_located(aid, x)
                              and self.minds[x].conversation is None]
                result = await self._call(
                    aid, "react", "action_selection",
                    prompts.reaction_prompt(mind.seed, record["text"], candidates),
                    prompts.REACTION_SCHEMA)
                if not isinstance(result, GatewayCompletion):
                    mind.gateway_failures += 1
                    continue
                partner = result.parsed.get("partner")
                if result.parsed["action"] == "start_conversation" and partner in candidates:
                    intents[aid] = {"agent_id": aid, "tick": world.tick,
                                    "kind": "converse_with", "partner_id": partner,
                                    "mode": "request"}
                    reacted = True
                    break
            if reacted:
                continue

            # -- plan cache execution (the cheap path)
            await self._ensure_plan(mind, day)
            await self._ensure_steps(mind, minute)
            intent = self._step_intent(mind)
            if intent is not None:
                intents[aid] = intent

            # -- reflection trigger
            await self._maybe_reflect(mind)

        return intents, cognition_events

    def total_gateway_failures(self) -> int:
        return sum(m.gateway_failures for m in self.minds.values())
