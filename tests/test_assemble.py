"""Experiment record assembly: one call -> a complete verified bundle."""
import hashlib
import json

from cognition.runner import fake_gateway
from metrics.assemble import assemble
from sim.content import content_hash
from tests.conftest import TREATMENT


def make_config():
    return {
        "experiment_id": "diffusion-fake-v0",
        "description": "fake-model machinery check",
        "seed": 42,
        "duration_ticks": 8640,
        "content_hash": content_hash(),
        "gateway_profile": "fake",
        "roles": {"dialogue": {"tier": "fast", "sampling": {"temperature": 0.9}}},
        "retrieval": {"alpha": 1.0, "beta": 1.0, "gamma": 1.0, "top_k": 5},
        "perception": {"sight_cone_half_angle_deg": 65, "sight_range": 8, "hearing_radius": 3},
        "treatments": [TREATMENT],
    }


def test_bundle_is_complete_and_verified(treated_run, tmp_path):
    out = tmp_path / "bundle"
    metrics = assemble(treated_run["dir"], make_config(), out,
                       with_believability=True, probe_gateway=fake_gateway())

    for name in ("ledger.jsonl", "completions.jsonl", "memories.jsonl",
                 "probes.jsonl", "config.json", "metrics.json", "manifest.json",
                 "plots/diffusion_0.png", "plots/graph.png"):
        assert (out / name).exists(), name

    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["experiment_id"] == "diffusion-fake-v0"
    for rel, digest in manifest["files"].items():
        if rel == "manifest.json":
            continue
        assert hashlib.sha256((out / rel).read_bytes()).hexdigest() == digest, rel

    # the assembled metrics carry the pinned diffusion result
    curve = metrics["diffusion"][0]
    assert curve["points"][-1]["holders"] >= 3
    assert metrics["believability"]["judge"] == "deterministic_stub_non_conforming"
    assert metrics["coordination_events"]


def test_metrics_json_is_deterministic(treated_run, tmp_path):
    a = assemble(treated_run["dir"], make_config(), tmp_path / "b1")
    b = assemble(treated_run["dir"], make_config(), tmp_path / "b2")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert (tmp_path / "b1" / "metrics.json").read_bytes() == \
           (tmp_path / "b2" / "metrics.json").read_bytes()
