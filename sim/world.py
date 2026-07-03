"""Authoritative tick-stepped world state.

The only way anything mutates is `World.step(intents)`: intents are validated
against the action grammar (schema wall) then against world semantics; what
fails is rejected into the ledger, never applied. The step is deterministic —
agents are processed in sorted id order and pathfinding tie-breaks are fixed —
which is what the byte-equal ledger fixture guards.

Events are returned as (kind, agent_id, data) tuples; the runner owns the
ledger (run_id/seq/tick envelope).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import schemas
from sim.grid import Cell, astar, build_blocked, locate

Event = tuple[str, str | None, dict]


@dataclass
class AgentState:
    id: str
    pos: Cell
    facing: Cell = (0, 1)
    status: str = "sleeping"  # sleeping | idle | moving
    dest: str | None = None
    path: list[Cell] = field(default_factory=list)


class World:
    def __init__(self, town: dict, seeds: dict[str, dict], master_seed: int):
        self.town = town
        self.width = town["grid"]["width"]
        self.height = town["grid"]["height"]
        self.blocked = build_blocked(town)
        self.doors: dict[str, Cell] = {l["id"]: tuple(l["door"]) for l in town["locations"]}
        self.objects: dict[str, dict] = {
            o["id"]: {
                "location": l["id"],
                "name": o["name"],
                "state": o["state"],
                "interactions": o["interactions"],
                "affordances": o["affordances"],
            }
            for l in town["locations"]
            for o in l["objects"]
        }
        self.master_seed = master_seed
        self.tick = 0
        self.agents: dict[str, AgentState] = {
            aid: AgentState(id=aid, pos=self.doors[seed["home"]])
            for aid, seed in sorted(seeds.items())
        }
        self.pending_conversations: set[tuple[str, str]] = set()  # (requester, target)

    def location_of(self, agent_id: str) -> str | None:
        return locate(self.town, self.agents[agent_id].pos)

    def co_located(self, a: str, b: str) -> bool:
        pa, pb = self.agents[a].pos, self.agents[b].pos
        adjacent = max(abs(pa[0] - pb[0]), abs(pa[1] - pb[1])) <= 1
        loc_a = self.location_of(a)
        return adjacent or (loc_a is not None and loc_a == self.location_of(b))

    def step(self, intents: dict[str, dict]) -> list[Event]:
        events: list[Event] = []
        for agent_id in sorted(intents):
            events.extend(self._apply_intent(agent_id, intents[agent_id]))
        for agent_id in sorted(self.agents):
            events.extend(self._advance(self.agents[agent_id]))
        self.tick += 1
        return events

    def _reject(self, agent_id: str, intent: dict, reason: str) -> list[Event]:
        return [("intent_rejected", agent_id, {"intent": intent, "reason": reason})]

    def _apply_intent(self, agent_id: str, intent: dict) -> list[Event]:
        if agent_id not in self.agents:
            return self._reject(agent_id, intent, f"unknown agent '{agent_id}'")
        schema_errors = schemas.errors("agent_intent", intent)
        if schema_errors:
            return self._reject(agent_id, intent, f"grammar: {schema_errors[0]}")
        if intent["agent_id"] != agent_id:
            return self._reject(agent_id, intent, "agent_id mismatch")
        agent = self.agents[agent_id]
        kind = intent["kind"]

        if kind == "move_to":
            dest = intent["destination"]
            if dest not in self.doors:
                return self._reject(agent_id, intent, f"unknown location '{dest}'")
            path = astar(self.blocked, self.width, self.height, agent.pos, self.doors[dest])
            if path is None:
                return self._reject(agent_id, intent, f"no path to '{dest}'")
            events: list[Event] = []
            if agent.status == "sleeping":
                events.append(("agent_status_changed", agent_id, {"status": "idle"}))
            if path:
                agent.dest, agent.path, agent.status = dest, path, "moving"
            else:  # already standing at the destination door
                agent.dest, agent.path, agent.status = None, [], "idle"
            return events

        if kind == "idle":
            agent.path, agent.dest = [], None
            if agent.status == "sleeping":
                agent.status = "idle"
                return [("agent_status_changed", agent_id, {"status": "idle"})]
            agent.status = "idle"
            return []

        if kind == "sleep":
            agent.path, agent.dest = [], None
            if agent.status != "sleeping":
                agent.status = "sleeping"
                return [("agent_status_changed", agent_id, {"status": "sleeping"})]
            return []

        if kind == "use_object":
            obj_id, interaction = intent["object_id"], intent["interaction"]
            obj = self.objects.get(obj_id)
            if obj is None:
                return self._reject(agent_id, intent, f"unknown object '{obj_id}'")
            if self.location_of(agent_id) != obj["location"]:
                return self._reject(agent_id, intent, f"not at '{obj['location']}' where '{obj_id}' is")
            new_state = obj["interactions"].get(interaction)
            if new_state is None:
                return self._reject(agent_id, intent, f"'{interaction}' not allowed on '{obj_id}'")
            old_state, obj["state"] = obj["state"], new_state
            return [("object_state_changed", agent_id, {
                "object_id": obj_id, "interaction": interaction, "from": old_state, "to": new_state,
            })]

        if kind == "converse_with":
            partner, mode = intent["partner_id"], intent["mode"]
            if partner not in self.agents:
                return self._reject(agent_id, intent, f"unknown agent '{partner}'")
            if not self.co_located(agent_id, partner):
                return self._reject(agent_id, intent, f"not co-located with '{partner}'")
            if mode == "request":
                self.pending_conversations.add((agent_id, partner))
                return [("conversation_requested", agent_id, {"partner": partner})]
            if (partner, agent_id) not in self.pending_conversations:
                return self._reject(agent_id, intent, f"no pending request from '{partner}'")
            self.pending_conversations.discard((partner, agent_id))
            if mode == "accept":
                return [("conversation_started", agent_id, {"partner": partner})]
            return [("conversation_declined", agent_id, {"partner": partner})]

        raise AssertionError(f"unreachable intent kind {kind}")  # grammar wall guarantees

    def _advance(self, agent: AgentState) -> list[Event]:
        if agent.status != "moving" or not agent.path:
            return []
        nxt = agent.path.pop(0)
        prev = agent.pos
        agent.facing = (nxt[0] - prev[0], nxt[1] - prev[1])
        agent.pos = nxt
        events: list[Event] = [("agent_moved", agent.id, {"from": list(prev), "to": list(nxt)})]
        if not agent.path:
            agent.status = "idle"
            events.append(("agent_arrived", agent.id, {"location": agent.dest}))
            agent.dest = None
        return events
