"""Scripted-agent mode: deterministic FSM stand-ins driven by daily anchors.

Exercises the full loop — intents, pathfinding, ledger — with zero model
calls (the P1 gate is explicitly no-LLM). Replaced by the cognition layer
per-agent in P2; the world cannot tell the difference, which is the point.
"""
from __future__ import annotations

from sim.clock import in_window, parse_hhmm
from sim.world import World


class ScriptedAgent:
    def __init__(self, seed: dict):
        self.id = seed["id"]
        self.home = seed["home"]
        self.workplace = seed["workplace"]
        anchors = seed["daily_anchors"]
        self.wake = parse_hhmm(anchors["wake"])
        self.work_start = parse_hhmm(anchors["work_start"])
        self.work_end = parse_hhmm(anchors["work_end"])
        self.sleep = parse_hhmm(anchors["sleep"])

    def desired(self, minute: int) -> tuple[str, str]:
        """(mode, target location) for this sim-minute."""
        if in_window(minute, self.sleep, self.wake):
            return "sleep", self.home
        if in_window(minute, self.work_start, self.work_end):
            return "work", self.workplace
        return "rest", self.home

    def intent(self, world: World, minute: int) -> dict | None:
        """Next intent, or None when already doing the right thing."""
        mode, target = self.desired(minute)
        agent = world.agents[self.id]
        at_target = world.location_of(self.id) == target
        if not at_target:
            if agent.dest == target:
                return None  # already en route
            return {"agent_id": self.id, "tick": world.tick, "kind": "move_to", "destination": target}
        if mode == "sleep" and agent.status != "sleeping":
            return {"agent_id": self.id, "tick": world.tick, "kind": "sleep"}
        if mode != "sleep" and agent.status == "sleeping":
            return {"agent_id": self.id, "tick": world.tick, "kind": "idle"}
        return None
