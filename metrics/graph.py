"""Relationship graph builder: interaction-weighted snapshots per sim-hour
from ledger utterances, plus density / clustering / component-stability
series. Pure ledger post-processing."""
from __future__ import annotations

from collections import defaultdict

from cognition.telemetry import TICKS_PER_HOUR


def hourly_graphs(ledger: list[dict], agents: list[str]) -> list[dict]:
    """One weighted undirected graph per sim-hour window (utterance = 1)."""
    windows: dict[int, dict[tuple[str, str], int]] = defaultdict(lambda: defaultdict(int))
    last_hour = 0
    for event in ledger:
        hour = event["tick"] // TICKS_PER_HOUR
        last_hour = max(last_hour, hour)
        if event["kind"] == "utterance":
            pair = tuple(sorted((event["agent_id"], event["data"]["partner"])))
            windows[hour][pair] += 1
    return [
        {"hour": hour, "edges": {"|".join(pair): w for pair, w in sorted(windows[hour].items())}}
        for hour in range(last_hour + 1)
    ]


def _adjacency(edges: dict[str, int]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for key in edges:
        a, b = key.split("|")
        adj[a].add(b)
        adj[b].add(a)
    return adj


def density(edges: dict[str, int], n_agents: int) -> float:
    possible = n_agents * (n_agents - 1) / 2
    return len(edges) / possible if possible else 0.0


def mean_clustering(edges: dict[str, int]) -> float:
    adj = _adjacency(edges)
    coefficients = []
    for node, neighbours in adj.items():
        k = len(neighbours)
        if k < 2:
            coefficients.append(0.0)
            continue
        links = sum(1 for x in neighbours for y in neighbours
                    if x < y and y in adj[x])
        coefficients.append(2 * links / (k * (k - 1)))
    return sum(coefficients) / len(coefficients) if coefficients else 0.0


def components(edges: dict[str, int]) -> list[frozenset]:
    adj = _adjacency(edges)
    seen: set[str] = set()
    result = []
    for node in sorted(adj):
        if node in seen:
            continue
        stack, group = [node], set()
        while stack:
            current = stack.pop()
            if current in group:
                continue
            group.add(current)
            stack.extend(adj[current] - group)
        seen |= group
        result.append(frozenset(group))
    return result


def component_stability(prev_edges: dict[str, int], edges: dict[str, int]) -> float:
    """Jaccard similarity of the edge sets of consecutive windows."""
    a, b = set(prev_edges), set(edges)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def graph_metrics(ledger: list[dict], agents: list[str]) -> dict:
    graphs = hourly_graphs(ledger, agents)
    series = []
    for i, snapshot in enumerate(graphs):
        edges = snapshot["edges"]
        series.append({
            "hour": snapshot["hour"],
            "edges": len(edges),
            "interactions": sum(edges.values()),
            "density": density(edges, len(agents)),
            "mean_clustering": mean_clustering(edges),
            "components": len(components(edges)),
            "stability_vs_prev": (component_stability(graphs[i - 1]["edges"], edges)
                                  if i > 0 else None),
        })
    return {"agents": sorted(agents), "hourly": series, "graphs": graphs}


def plot_graph_series(metrics: dict, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    hours = [s["hour"] for s in metrics["hourly"]]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(hours, [s["density"] for s in metrics["hourly"]], label="density")
    ax.plot(hours, [s["mean_clustering"] for s in metrics["hourly"]], label="mean clustering")
    ax.set_xlabel("sim-hour")
    ax.set_ylabel("value")
    ax.set_title("Interaction graph per sim-hour")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
