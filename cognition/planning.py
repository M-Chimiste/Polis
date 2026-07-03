"""Hierarchical planning: daily agenda -> lazy per-block decomposition ->
action steps executed from the plan cache (the cost gate: cached steps cost
zero model calls).

Plans are memory records (kind "plan") and therefore retrievable. When the
gateway is down, fallback_agenda() builds a deterministic anchor-driven day
so the sim slows narratively instead of crashing (service-optionality).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sim.clock import parse_hhmm


@dataclass
class Step:
    minutes: int
    kind: str  # move_to | use_object | idle | sleep
    destination: str | None = None
    object_id: str | None = None
    interaction: str | None = None
    ticks_left: int = 0
    started: bool = False


@dataclass
class PlanCache:
    day: int = -1
    agenda: list[dict] = field(default_factory=list)
    from_fallback: bool = False
    block_index: int = -1
    steps: list[Step] = field(default_factory=list)

    def current_block(self, minute: int) -> tuple[int, dict] | None:
        for i, block in enumerate(self.agenda):
            start, end = parse_hhmm(block["start"]), parse_hhmm(block["end"])
            if (start <= minute < end) or (start > end and (minute >= start or minute < end)):
                return i, block
        return None


def fallback_agenda(agent: dict) -> list[dict]:
    """Deterministic anchor-driven agenda used when planning calls fail."""
    a = agent["daily_anchors"]
    return [
        {"start": a["wake"], "end": a["work_start"],
         "activity": "morning routine at home", "location": agent["home"]},
        {"start": a["work_start"], "end": a["work_end"],
         "activity": f"work as {agent['occupation']}", "location": agent["workplace"]},
        {"start": a["work_end"], "end": a["sleep"],
         "activity": "evening at home", "location": agent["home"]},
        {"start": a["sleep"], "end": a["wake"],
         "activity": "sleep", "location": agent["home"]},
    ]


def fallback_steps(block: dict) -> list[dict]:
    """Deterministic decomposition used when the decompose call fails."""
    if block["activity"] == "sleep":
        return [{"minutes": 24 * 60, "kind": "sleep"}]
    return [
        {"minutes": 1, "kind": "move_to", "destination": block["location"]},
        {"minutes": 24 * 60, "kind": "idle"},
    ]


def steps_from_payload(payload: dict, block: dict, world_objects: dict) -> list[Step]:
    """Ground model-proposed steps; ungroundable steps degrade to idle rather
    than reaching the world (the intent wall would reject them anyway —
    grounding here keeps the plan cache clean)."""
    steps: list[Step] = []
    for raw in payload["steps"]:
        step = Step(minutes=raw["minutes"], kind=raw["kind"],
                    destination=raw.get("destination"),
                    object_id=raw.get("object_id"),
                    interaction=raw.get("interaction"))
        if step.kind == "move_to" and step.destination is None:
            step = Step(minutes=raw["minutes"], kind="idle")
        if step.kind == "use_object":
            obj = world_objects.get(step.object_id or "")
            grounded = (
                obj is not None
                and obj["location"] == block["location"]
                and step.interaction in obj["interactions"]
            )
            if not grounded:
                step = Step(minutes=raw["minutes"], kind="idle")
        steps.append(step)
    return steps


def agenda_text(agenda: list[dict]) -> str:
    return "; ".join(f"{b['start']}-{b['end']} {b['activity']} @ {b['location']}" for b in agenda)
