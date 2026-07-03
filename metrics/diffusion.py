"""Seeded-fact diffusion: periodic fact probes over frozen snapshots ->
holder curve. The curve is THE v1 deliverable (success criterion #1).

Snapshots are reconstructed post-hoc: memory streams are append-only with a
tick per record, so 'state at tick t' = records with tick <= t. One pass
over the run yields the whole curve at any cadence.
"""
from __future__ import annotations

from cognition.embedding import Embedder
from metrics.probes import ProbeRunner
from metrics.store import FrozenStream


def diffusion_curve(memories: dict[str, list[dict]], fact: str, inject_tick: int,
                    end_tick: int, cadence: int, run_id: str,
                    embedder: Embedder, seeds: dict[str, dict]) -> dict:
    """Fact-check every agent at every cadence point; returns curve + probes."""
    runner = ProbeRunner(run_id, seeds, gateway=None, embedder=embedder)  # fact checks are model-free
    points: list[dict] = []
    probes: list[dict] = []
    ticks = list(range(inject_tick, end_tick + 1, cadence))
    if ticks[-1] != end_tick:
        ticks.append(end_tick)
    for tick in ticks:
        holders = []
        for aid in sorted(memories):
            stream = FrozenStream(memories[aid], tick, _NoEmbed())
            probe = runner.fact_check(aid, stream, fact, tick)
            probes.append(probe)
            if probe["scores"]["knows_fact"]:
                holders.append(aid)
        points.append({"tick": tick, "holders": len(holders), "agent_ids": holders})
    return {"fact": fact, "inject_tick": inject_tick, "cadence": cadence,
            "points": points, "probes": probes}


class _NoEmbed:
    """Fact checks are keyword-based; skip embedding work entirely."""
    dim = 0

    def embed(self, texts):
        return [[] for _ in texts]


def plot_diffusion(curve: dict, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ticks = [p["tick"] for p in curve["points"]]
    holders = [p["holders"] for p in curve["points"]]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.step(ticks, holders, where="post")
    ax.axvline(curve["inject_tick"], linestyle="--", linewidth=1)
    ax.set_xlabel("tick (10 sim-seconds each)")
    ax.set_ylabel("agents holding the fact")
    ax.set_title(f"Seeded-fact diffusion: \"{curve['fact'][:60]}\"")
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
