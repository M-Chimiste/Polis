"""Relationship graph builder + coordination detector."""
from metrics.coordination import detect_gatherings
from metrics.graph import (
    components, density, graph_metrics, hourly_graphs, mean_clustering,
)
from metrics.store import load_ledger


def utterance(tick, a, b):
    return {"run_id": "r", "seq": 0, "tick": tick, "kind": "utterance",
            "agent_id": a, "data": {"partner": b, "turn": 0, "text": "..."}}


def test_hourly_windows_and_weights():
    ledger = [utterance(10, "a", "b"), utterance(20, "b", "a"),
              utterance(400, "a", "c")]
    graphs = hourly_graphs(ledger, ["a", "b", "c"])
    assert graphs[0]["edges"] == {"a|b": 2}
    assert graphs[1]["edges"] == {"a|c": 1}


def test_density_and_clustering_math():
    triangle = {"a|b": 1, "b|c": 1, "a|c": 1}
    assert density(triangle, 3) == 1.0
    assert mean_clustering(triangle) == 1.0
    chain = {"a|b": 1, "b|c": 1}
    assert mean_clustering(chain) == 0.0
    assert len(components(chain)) == 1
    assert len(components({"a|b": 1, "c|d": 1})) == 2


def test_graph_metrics_on_real_run(treated_run):
    ledger = load_ledger((treated_run["dir"] / "ledger.jsonl").read_bytes().splitlines())
    metrics = graph_metrics(ledger, treated_run["agents"])
    total_interactions = sum(s["interactions"] for s in metrics["hourly"])
    assert total_interactions > 0
    for snapshot in metrics["hourly"]:
        assert 0.0 <= snapshot["density"] <= 1.0
    # stability defined from the second window on
    assert metrics["hourly"][0]["stability_vs_prev"] is None
    assert all(s["stability_vs_prev"] is not None for s in metrics["hourly"][1:])


def test_gathering_detected_at_the_tavern(treated_run):
    """Three residents live at the gilded_perch — the detector must find a
    sustained >=3-agent span there, purely from the ledger."""
    ledger = load_ledger((treated_run["dir"] / "ledger.jsonl").read_bytes().splitlines())
    gatherings = detect_gatherings(ledger, min_agents=3, min_ticks=30)
    assert gatherings
    perch = [g for g in gatherings if g["location"] == "gilded_perch"]
    assert perch
    assert {"ilse_alder", "maren_alder", "piet_alder"} <= set(perch[0]["agents"])


def test_detector_is_deterministic(treated_run):
    ledger = load_ledger((treated_run["dir"] / "ledger.jsonl").read_bytes().splitlines())
    assert detect_gatherings(ledger) == detect_gatherings(ledger)
