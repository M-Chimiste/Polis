"""Coordination-event detector: spans where >= k agents share a location,
reconstructed purely from the ledger (positions replay deterministically
from agent_initialized + agent_moved)."""
from __future__ import annotations

from sim.content import load_town
from sim.grid import locate


def detect_gatherings(ledger: list[dict], min_agents: int = 3,
                      min_ticks: int = 30) -> list[dict]:
    town = load_town()
    positions: dict[str, tuple] = {}
    locations: dict[str, str | None] = {}
    open_spans: dict[str, dict] = {}
    finished: list[dict] = []
    current_tick = 0

    def occupancy() -> dict[str, list[str]]:
        occ: dict[str, list[str]] = {}
        for aid, loc in sorted(locations.items()):
            if loc is not None:
                occ.setdefault(loc, []).append(aid)
        return occ

    def close_span(loc: str, span: dict, tick: int) -> None:
        span["end_tick"] = tick
        if tick - span["start_tick"] >= min_ticks:
            finished.append(span)

    def refresh(tick: int) -> None:
        occ = occupancy()
        for loc, agents in occ.items():
            if len(agents) >= min_agents and loc not in open_spans:
                open_spans[loc] = {"location": loc, "start_tick": tick,
                                   "agents": sorted(agents), "peak": len(agents)}
            elif loc in open_spans:
                span = open_spans[loc]
                span["peak"] = max(span["peak"], len(agents))
                span["agents"] = sorted(set(span["agents"]) | set(agents))
        for loc in list(open_spans):
            if len(occ.get(loc, [])) < min_agents:
                close_span(loc, open_spans.pop(loc), tick)

    for event in ledger:
        current_tick = event["tick"]
        if event["kind"] == "agent_initialized":
            positions[event["agent_id"]] = tuple(event["data"]["pos"])
            locations[event["agent_id"]] = event["data"]["location"]
        elif event["kind"] == "agent_moved":
            positions[event["agent_id"]] = tuple(event["data"]["to"])
            locations[event["agent_id"]] = locate(town, positions[event["agent_id"]])
        else:
            continue
        refresh(current_tick)

    for loc in list(open_spans):
        close_span(loc, open_spans.pop(loc), current_tick)
    finished.sort(key=lambda s: (s["start_tick"], s["location"]))
    return finished
