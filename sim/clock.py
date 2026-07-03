"""Sim time: 1 tick = 10 sim-seconds (default; config in experiment_config)."""
from __future__ import annotations

TICK_SIM_SECONDS = 10
TICKS_PER_DAY = 24 * 3600 // TICK_SIM_SECONDS  # 8640


def minute_of_day(tick: int, tick_sim_seconds: int = TICK_SIM_SECONDS) -> int:
    return (tick * tick_sim_seconds // 60) % (24 * 60)


def hhmm(tick: int, tick_sim_seconds: int = TICK_SIM_SECONDS) -> str:
    m = minute_of_day(tick, tick_sim_seconds)
    return f"{m // 60:02d}:{m % 60:02d}"


def parse_hhmm(value: str) -> int:
    h, m = value.split(":")
    return int(h) * 60 + int(m)


def in_window(minute: int, start: int, end: int) -> bool:
    """True if minute falls in [start, end), wrap-aware (e.g. 23:30 -> 06:00)."""
    if start <= end:
        return start <= minute < end
    return minute >= start or minute < end
