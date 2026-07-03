"""Perception with information asymmetry (glasshouse P11 semantics, reimplemented).

See = same location (or both outdoors) AND within the sight cone AND the
segment is unoccluded. Hear = within hearing radius, occlusion-exempt.
Agents can miss things — that asymmetry is what makes diffusion and rumor
measurable. Every parameter is config (experiment_config.perception), never
a constant baked into code.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from sim.world import World


@dataclass(frozen=True)
class PerceptionParams:
    sight_cone_half_angle_deg: float = 65.0
    sight_range: float = 8.0
    hearing_radius: float = 3.0


def _segment_hits_circle(a: tuple, b: tuple, center: tuple, radius: float) -> bool:
    ax, ay = a
    bx, by = b
    cx, cy = center
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.dist(a, center) < radius
    t = max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / length_sq))
    return math.dist((ax + t * dx, ay + t * dy), center) < radius


def _occluded(town: dict, a: tuple, b: tuple) -> bool:
    return any(
        _segment_hits_circle(a, b, tuple(o["at"]), o["radius"])
        for o in town["occluders"]
    )


def _in_cone(facing: tuple, origin: tuple, target: tuple, half_angle_deg: float) -> bool:
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    if dx == 0 and dy == 0:
        return True
    dist = math.hypot(dx, dy)
    fx, fy = facing
    fnorm = math.hypot(fx, fy) or 1.0
    cos_angle = (fx * dx + fy * dy) / (fnorm * dist)
    return cos_angle >= math.cos(math.radians(half_angle_deg))


def perceive(world: World, params: PerceptionParams, observer_id: str) -> dict:
    """What one agent perceives this tick: {'seen': [...], 'heard': [...]}.

    Pure read — perception never mutates world state. Output feeds the
    cognition layer (P2) as observations; it is NOT a ledger event.
    """
    me = world.agents[observer_id]
    my_loc = world.location_of(observer_id)
    seen: list[str] = []
    heard: list[str] = []
    for other_id in sorted(world.agents):
        if other_id == observer_id:
            continue
        other = world.agents[other_id]
        dist = math.dist(me.pos, other.pos)
        if dist <= params.hearing_radius:
            heard.append(other_id)
        if (
            dist <= params.sight_range
            and my_loc == world.location_of(other_id)
            and _in_cone(me.facing, me.pos, other.pos, params.sight_cone_half_angle_deg)
            and not _occluded(world.town, me.pos, other.pos)
        ):
            seen.append(other_id)
    return {"seen": seen, "heard": heard}
