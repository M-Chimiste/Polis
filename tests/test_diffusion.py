"""Diffusion pipeline: curve correctness + the real spread in a treated day."""
import schemas
from cognition.embedding import HashEmbedder
from metrics.diffusion import diffusion_curve, plot_diffusion
from metrics.store import load_memories
from sim.content import load_agents

FACT = "there is a gathering at the tavern on day three"


RUN = "6f1a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b"


def rec(aid, tick, text, i=0):
    import uuid
    return {"id": str(uuid.uuid5(uuid.NAMESPACE_OID, f"{aid}-{tick}-{i}")),
            "run_id": RUN, "agent_id": aid,
            "kind": "observation", "tick": tick, "text": text, "importance": 5}


def test_synthetic_curve_counts_holders_from_memory():
    memories = {
        "maren_alder": [rec("maren_alder", 100, FACT)],
        "piet_alder": [rec("piet_alder", 500, f"maren said to me: {FACT}")],
        "sela_crane": [rec("sela_crane", 300, "the oven needs raking")],
    }
    seeds = {a: s for a, s in load_agents().items() if a in memories}
    curve = diffusion_curve(memories, FACT, 100, 900, 200, RUN, HashEmbedder(), seeds)
    holders = [(p["tick"], p["holders"]) for p in curve["points"]]
    assert holders == [(100, 1), (300, 1), (500, 2), (700, 2), (900, 2)]
    assert curve["points"][2]["agent_ids"] == ["maren_alder", "piet_alder"]
    for probe in curve["probes"]:
        assert schemas.errors("probe_result", probe) == []


def test_curve_is_non_decreasing_by_construction(treated_run):
    memories = load_memories((treated_run["dir"] / "memories.jsonl").read_bytes().splitlines())
    seeds = {a: s for a, s in load_agents().items() if a in treated_run["agents"]}
    curve = diffusion_curve(memories, FACT, 2400, 8640, 360,
                            treated_run["writer"].run_id, HashEmbedder(), seeds)
    counts = [p["holders"] for p in curve["points"]]
    assert counts == sorted(counts)


def test_fact_diffused_through_the_household(treated_run):
    """The pinned end-to-end result: inject at the tavernkeeper, and by end
    of day the co-located household holds it while the bakery pair (never
    co-present) does not — information asymmetry made measurable."""
    memories = load_memories((treated_run["dir"] / "memories.jsonl").read_bytes().splitlines())
    seeds = {a: s for a, s in load_agents().items() if a in treated_run["agents"]}
    curve = diffusion_curve(memories, FACT, 2400, 8640, 720,
                            treated_run["writer"].run_id, HashEmbedder(), seeds)
    first, last = curve["points"][0], curve["points"][-1]
    assert first["agent_ids"] == ["maren_alder"]
    assert set(last["agent_ids"]) >= {"maren_alder", "ilse_alder", "piet_alder"}
    assert "sela_crane" not in last["agent_ids"]
    assert "tobias_crane" not in last["agent_ids"]


def test_plot_written(treated_run, tmp_path):
    memories = load_memories((treated_run["dir"] / "memories.jsonl").read_bytes().splitlines())
    seeds = {a: s for a, s in load_agents().items() if a in treated_run["agents"]}
    curve = diffusion_curve(memories, FACT, 2400, 8640, 1440,
                            treated_run["writer"].run_id, HashEmbedder(), seeds)
    out = tmp_path / "diffusion.png"
    plot_diffusion(curve, out)
    assert out.stat().st_size > 5000
