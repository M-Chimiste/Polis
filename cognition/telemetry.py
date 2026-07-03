"""Cost telemetry: per agent, per sim-hour, per tier, from the completion log.

Post-processes the log only (measurement-plane discipline). The tp-split vs
tp=2 comparison on Mnemosyne consumes this report once hardware runs happen.
"""
from __future__ import annotations

from collections import defaultdict

from sim.clock import TICK_SIM_SECONDS

TICKS_PER_HOUR = 3600 // TICK_SIM_SECONDS


def cost_report(completion_records: list[dict], role_tiers: dict[str, str]) -> dict:
    """Aggregate calls/tokens by (agent, sim_hour, tier) from CompletionLog
    records (each carries the sim tick it was issued at)."""
    cells: dict[tuple[str, int, str], dict] = defaultdict(
        lambda: {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "failures": 0})
    for record in completion_records:
        tick = record.get("tick", 0)
        tier = role_tiers.get(record["role"], "unknown")
        cell = cells[(record["agent_id"], tick // TICKS_PER_HOUR, tier)]
        cell["calls"] += 1
        if record["outcome"] == "completion":
            usage = record["result"].get("usage") or {}
            cell["prompt_tokens"] += usage.get("prompt_tokens", 0)
            cell["completion_tokens"] += usage.get("completion_tokens", 0)
        else:
            cell["failures"] += 1
    return {
        "cells": [
            {"agent_id": agent, "sim_hour": hour, "tier": tier, **stats}
            for (agent, hour, tier), stats in sorted(cells.items())
        ],
        "totals": {
            "calls": sum(c["calls"] for c in cells.values()),
            "prompt_tokens": sum(c["prompt_tokens"] for c in cells.values()),
            "completion_tokens": sum(c["completion_tokens"] for c in cells.values()),
            "failures": sum(c["failures"] for c in cells.values()),
        },
    }
