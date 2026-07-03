"""Experiment record assembly: one command -> a self-contained run bundle.

python -m metrics.assemble --run-dir out/ --config experiment.json --out bundle/

Bundle contents: the raw artifacts (ledger/completions/memories), the
experiment config + its hash, metrics.json (diffusion curve, graph series,
coordination events, optional believability), plots/, probes.jsonl, and a
manifest with sha256 of every file. Archiving the bundle to Aletheia is a
one-line rsync — a hardware-session step; assembly itself is fully local.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import pathlib
import shutil

import schemas
from cognition.completions import CognitionGateway, CompletionLog
from cognition.embedding import HashEmbedder
from cognition.retrieval import RetrievalParams
from metrics.believability import DeterministicJudge, run_battery, summarize
from metrics.coordination import detect_gatherings
from metrics.diffusion import diffusion_curve, plot_diffusion
from metrics.graph import graph_metrics, plot_graph_series
from metrics.probes import ProbeRunner
from metrics.store import freeze, load_ledger, load_memories
from sim.content import load_agents, load_relationships


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble(run_dir: pathlib.Path, config: dict, out_dir: pathlib.Path,
             with_believability: bool = False, probe_gateway=None) -> dict:
    schemas.validate("experiment_config", config)
    out_dir.mkdir(parents=True, exist_ok=True)
    plots = out_dir / "plots"
    plots.mkdir(exist_ok=True)

    ledger = load_ledger((run_dir / "ledger.jsonl").read_bytes().splitlines())
    memories = load_memories((run_dir / "memories.jsonl").read_bytes().splitlines())
    run_meta = ledger[0]["data"]
    run_id = ledger[0]["run_id"]
    end_tick = ledger[-1]["tick"]
    agents = run_meta["agents"]
    seeds = {aid: s for aid, s in load_agents().items() if aid in agents}

    metrics_out: dict = {"run_id": run_id, "agents": agents, "end_tick": end_tick}
    probes: list[dict] = []

    for i, treatment in enumerate(config.get("treatments", [])):
        curve = diffusion_curve(
            memories, treatment["fact"], treatment["inject_tick"], end_tick,
            cadence=360, run_id=run_id, embedder=HashEmbedder(), seeds=seeds)
        probes.extend(curve.pop("probes"))
        metrics_out.setdefault("diffusion", []).append(curve)
        plot_diffusion(curve, plots / f"diffusion_{i}.png")

    graphs = graph_metrics(ledger, agents)
    metrics_out["graph"] = {"hourly": graphs["hourly"]}
    plot_graph_series(graphs, plots / "graph.png")

    metrics_out["coordination_events"] = detect_gatherings(ledger)

    if with_believability:
        embedder = HashEmbedder()
        streams = freeze(memories, end_tick, embedder)
        log = CompletionLog(run_id + "-probes")
        runner = ProbeRunner(run_id, seeds,
                             CognitionGateway(probe_gateway, log), embedder,
                             retrieval=RetrievalParams())
        results = asyncio.run(run_battery(runner, streams, load_relationships(),
                                          end_tick, DeterministicJudge()))
        probes.extend(results)
        metrics_out["believability"] = summarize(results)
        metrics_out["believability"]["judge"] = "deterministic_stub_non_conforming"

    for name in ("ledger.jsonl", "completions.jsonl", "memories.jsonl"):
        shutil.copyfile(run_dir / name, out_dir / name)
    (out_dir / "probes.jsonl").write_bytes(
        b"".join(canonical(p).encode() + b"\n" for p in probes))
    (out_dir / "config.json").write_text(canonical(config) + "\n")
    (out_dir / "metrics.json").write_text(canonical(metrics_out) + "\n")

    manifest = {
        "run_id": run_id,
        "experiment_id": config["experiment_id"],
        "config_hash": hashlib.sha256(canonical(config).encode()).hexdigest(),
        "files": {p.relative_to(out_dir).as_posix(): sha256_file(p)
                  for p in sorted(out_dir.rglob("*")) if p.is_file()},
    }
    (out_dir / "manifest.json").write_text(canonical(manifest) + "\n")
    return metrics_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble an experiment record bundle")
    parser.add_argument("--run-dir", type=pathlib.Path, required=True)
    parser.add_argument("--config", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--with-believability", action="store_true",
                        help="run the interview battery with the offline stub judge")
    parser.add_argument("--pg-dsn", default=None,
                        help="also insert the bundle's probe results into Postgres")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    gateway = None
    if args.with_believability:
        from cognition.runner import fake_gateway
        gateway = fake_gateway()
    result = assemble(args.run_dir, config, args.out,
                      with_believability=args.with_believability,
                      probe_gateway=gateway)
    inserted = ""
    if args.pg_dsn:
        from services.db.run_sink import insert_probes
        probes = [json.loads(line)
                  for line in (args.out / "probes.jsonl").read_bytes().splitlines()]
        inserted = f", {insert_probes(args.pg_dsn, probes)} probes -> postgres"
    print(f"bundle -> {args.out} ({len(result.get('coordination_events', []))} gatherings, "
          f"{len(result.get('diffusion', []))} diffusion curves{inserted})")


if __name__ == "__main__":
    main()
