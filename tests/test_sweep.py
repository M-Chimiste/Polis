"""P5 sweep harness: N seeds fan out as cognition.runner subprocesses,
bundle + cost per seed, cross-seed summary + overlay plot, and a killed
sweep resumes (complete seeds are skipped). Fake model — harness plumbing
only; such runs are non-conforming by construction."""
import asyncio
import json

from experiments.sweep import derive_config, sweep

PAIR = "maren_alder,piet_alder"

BASE_CONFIG = {
    "experiment_id": "sweep-harness-test",
    "seed": 42,
    "duration_ticks": 2400,
    "content_hash": "a" * 64,  # placeholder; derive_config fills the real one
    "gateway_profile": "fake",
    "roles": {
        "dialogue": {"tier": "fast", "sampling": {"temperature": 0.9, "max_tokens": 256}},
        "importance": {"tier": "fast", "sampling": {"temperature": 0.0, "max_tokens": 16}},
        "daily_planning": {"tier": "slow", "sampling": {"temperature": 0.8, "max_tokens": 1024}},
        "decomposition": {"tier": "slow", "sampling": {"temperature": 0.6, "max_tokens": 768}},
        "action_selection": {"tier": "fast", "sampling": {"temperature": 0.7, "max_tokens": 128}},
        "reflection": {"tier": "slow", "sampling": {"temperature": 0.8, "max_tokens": 1024}},
        "probe": {"tier": "fast", "sampling": {"temperature": 0.3, "max_tokens": 256}},
    },
    "retrieval": {"alpha": 1.0, "beta": 1.0, "gamma": 1.0},
    "perception": {"sight_cone_half_angle_deg": 65, "sight_range": 8, "hearing_radius": 3},
    "treatments": [
        {"kind": "seeded_fact", "fact": "there is a gathering at the tavern",
         "target_agent": "maren_alder", "inject_tick": 2250, "importance": 9}
    ],
}


def test_derive_config_stamps_seed_and_real_content_hash():
    derived = derive_config(BASE_CONFIG, 77, None)
    assert derived["seed"] == 77
    assert derived["content_hash"] != BASE_CONFIG["content_hash"]
    # real-profile derivation records the assigned profile + its roles
    derived = derive_config(BASE_CONFIG, 78, "metis")
    assert derived["gateway_profile"] == "metis"
    assert derived["roles"]["dialogue"]["tier"] == "fast"
    assert derived["roles"]["dialogue"]["sampling"]["max_tokens"] >= 1024


def test_sweep_runs_bundles_aggregates_and_resumes(tmp_path):
    out = tmp_path / "sweep"
    summary = asyncio.run(sweep(BASE_CONFIG, [42, 43], out, profiles=None,
                                agents=PAIR))
    assert summary["statuses"] == {42: "ran", 43: "ran"}

    for seed in (42, 43):
        seed_dir = out / f"seed_{seed}"
        assert (seed_dir / "experiment.json").exists()      # provenance first
        assert (seed_dir / "bundle" / "metrics.json").exists()
        assert (seed_dir / "bundle" / "manifest.json").exists()
        assert (seed_dir / "cost.json").exists()
    assert (out / "diffusion_overlay.png").exists()

    written = json.loads((out / "summary.json").read_text())
    assert set(written["per_seed"]) == {"42", "43"}
    assert all(row["curves"] for row in written["per_seed"].values())
    assert written["aggregate_cost"]["calls"] > 0

    # resume: everything complete -> nothing re-runs
    summary2 = asyncio.run(sweep(BASE_CONFIG, [42, 43], out, profiles=None,
                                 agents=PAIR))
    assert summary2["statuses"] == {42: "resumed", 43: "resumed"}
