"""Seed sweep: the P5 experiment harness.

python -m experiments.sweep --config experiment.json --seeds 8 \
    --profiles metis,athena --out-dir runs/sweep_v1

One base experiment_config fans out over N seeds; runs distribute
round-robin across serving profiles and execute as cognition.runner
subprocesses (crash-contained, resumable). Each completed run is assembled
into a bundle; the sweep root gets summary.json + a cross-seed diffusion
overlay plot. Everything a run needs for provenance lands in its own
directory: the derived per-seed config is written before launch, with
gateway_profile, roles (auto-filled from the assigned profile), and the
actual content_hash.

Resume: a seed whose memories.jsonl exists is complete (the runner writes it
after the tick loop) and is skipped — re-invoking a killed sweep finishes
only what's missing.

Fake mode (--fake) runs the deterministic fake model: harness plumbing is
fully testable offline; such runs are non-conforming by construction.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
import pathlib
import sys

import schemas
from cognition.telemetry import cost_report
from services.gateway import load_profiles
from sim.content import content_hash

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def derive_config(base: dict, seed: int, profile: str | None) -> dict:
    """Per-seed config: the experiment's provenance record for that run."""
    config = copy.deepcopy(base)
    config["seed"] = seed
    config["content_hash"] = content_hash()
    if profile is not None:
        config["gateway_profile"] = profile
        profile_cfg = load_profiles()[profile]
        config["roles"] = {
            role: {"tier": cfg.tier,
                   "sampling": cfg.sampling.as_request_params()}
            for role, cfg in profile_cfg.roles.items()
        }
    schemas.validate("experiment_config", config)
    return config


def seed_complete(seed_dir: pathlib.Path) -> bool:
    return (seed_dir / "memories.jsonl").exists()


async def run_seed(seed: int, seed_dir: pathlib.Path, config: dict,
                   profile: str | None, agents: str | None,
                   pg_dsn: str | None, semaphore: asyncio.Semaphore) -> str:
    if seed_complete(seed_dir):
        return "resumed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    config_path = seed_dir / "experiment.json"
    config_path.write_text(json.dumps(config, sort_keys=True, indent=1) + "\n")

    cmd = [sys.executable, "-m", "cognition.runner",
           "--ticks", str(config["duration_ticks"]),
           "--seed", str(seed),
           "--out-dir", str(seed_dir),
           "--config", str(config_path)]
    if profile is not None:
        cmd += ["--profile", profile]
    if agents:
        cmd += ["--agents", agents]
    if pg_dsn:
        cmd += ["--pg-dsn", pg_dsn]

    async with semaphore:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=REPO_ROOT,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        output, _ = await proc.communicate()
    (seed_dir / "runner.log").write_bytes(output)
    if proc.returncode != 0:
        return "failed"
    return "ran"


def post_process(seed_dir: pathlib.Path, config: dict,
                 with_believability: bool) -> dict:
    """Bundle + cost report for one completed seed. Returns summary row."""
    from metrics.assemble import assemble  # heavy import, deferred
    gateway = None
    if with_believability:
        from cognition.runner import fake_gateway
        gateway = fake_gateway()
    metrics_out = assemble(seed_dir, config, seed_dir / "bundle",
                           with_believability=with_believability,
                           probe_gateway=gateway)

    records = [json.loads(line) for line in
               (seed_dir / "completions.jsonl").read_bytes().splitlines()]
    role_tiers = {role: cfg["tier"] for role, cfg in config["roles"].items()}
    cost = cost_report(records, role_tiers)
    (seed_dir / "cost.json").write_text(
        json.dumps(cost, sort_keys=True, indent=1) + "\n")

    curves = metrics_out.get("diffusion", [])
    return {
        "run_id": metrics_out["run_id"],
        "curves": [{"fact": c["fact"], "inject_tick": c["inject_tick"],
                    "points": c["points"]} for c in curves],
        "cost": cost.get("totals", cost),
        "gateway_profile": config["gateway_profile"],
    }


def plot_overlay(per_seed: dict[int, dict], path: pathlib.Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    inject_ticks = set()
    for seed, row in sorted(per_seed.items()):
        for curve in row.get("curves", []):
            ticks = [p["tick"] for p in curve["points"]]
            holders = [p["holders"] for p in curve["points"]]
            ax.plot(ticks, holders, marker="o", markersize=3, alpha=0.7,
                    label=f"seed {seed}")
            inject_ticks.add(curve["inject_tick"])
    for tick in sorted(inject_ticks):
        ax.axvline(tick, linestyle="--", linewidth=1, color="grey")
    ax.set_xlabel("tick")
    ax.set_ylabel("fact holders")
    ax.set_title("Seeded-fact diffusion across seeds")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


async def sweep(base_config: dict, seeds: list[int], out_dir: pathlib.Path,
                profiles: list[str] | None, agents: str | None = None,
                pg_dsn: str | None = None, parallel_per_profile: int = 1,
                with_believability: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    buckets = profiles or [None]  # fake mode: one unnamed bucket
    semaphores = {p: asyncio.Semaphore(parallel_per_profile) for p in buckets}

    jobs = []
    assignments: dict[int, str | None] = {}
    for i, seed in enumerate(seeds):
        profile = buckets[i % len(buckets)]
        assignments[seed] = profile
        config = derive_config(base_config, seed, profile)
        jobs.append(run_seed(seed, out_dir / f"seed_{seed}", config, profile,
                             agents, pg_dsn, semaphores[profile]))
    statuses = dict(zip(seeds, await asyncio.gather(*jobs)))

    per_seed: dict[int, dict] = {}
    for seed in seeds:
        if statuses[seed] == "failed":
            continue
        config = derive_config(base_config, seed, assignments[seed])
        per_seed[seed] = post_process(out_dir / f"seed_{seed}", config,
                                      with_believability)

    summary = {
        "experiment_id": base_config["experiment_id"],
        "seeds": seeds,
        "statuses": statuses,
        "per_seed": {str(s): row for s, row in per_seed.items()},
        "aggregate_cost": {
            "calls": sum(r["cost"].get("calls", 0) for r in per_seed.values()),
            "prompt_tokens": sum(r["cost"].get("prompt_tokens", 0)
                                 for r in per_seed.values()),
            "completion_tokens": sum(r["cost"].get("completion_tokens", 0)
                                     for r in per_seed.values()),
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=1) + "\n")
    if any(row.get("curves") for row in per_seed.values()):
        plot_overlay(per_seed, out_dir / "diffusion_overlay.png")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed-sweep experiment harness")
    parser.add_argument("--config", type=pathlib.Path, required=True,
                        help="base experiment_config JSON")
    parser.add_argument("--seeds", type=int, default=8,
                        help="number of seeds (base config seed + 0..N-1)")
    parser.add_argument("--seed-list", default=None,
                        help="explicit comma-separated seeds (overrides --seeds)")
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--profiles", default=None,
                        help="comma-separated serving profiles to distribute over")
    parser.add_argument("--parallel-per-profile", type=int, default=1)
    parser.add_argument("--agents", default=None,
                        help="agent subset passthrough (default: all 20)")
    parser.add_argument("--pg-dsn", default=None)
    parser.add_argument("--with-believability", action="store_true")
    parser.add_argument("--fake", action="store_true",
                        help="fake model (harness dev; non-conforming)")
    args = parser.parse_args()

    base = json.loads(args.config.read_text())
    schemas.validate("experiment_config", base)
    if args.seed_list:
        seeds = [int(s) for s in args.seed_list.split(",")]
    else:
        seeds = [base["seed"] + i for i in range(args.seeds)]
    profiles = None if args.fake else \
        (args.profiles.split(",") if args.profiles else None)
    if not args.fake and not profiles:
        parser.error("--profiles is required unless --fake")

    summary = asyncio.run(sweep(
        base, seeds, args.out_dir, profiles, agents=args.agents,
        pg_dsn=args.pg_dsn, parallel_per_profile=args.parallel_per_profile,
        with_believability=args.with_believability))
    failed = [s for s, st in summary["statuses"].items() if st == "failed"]
    print(f"sweep {summary['experiment_id']}: "
          f"{len(summary['per_seed'])}/{len(seeds)} seeds complete, "
          f"{summary['aggregate_cost']['calls']} total calls -> {args.out_dir}")
    if failed:
        raise SystemExit(f"failed seeds: {failed}")


if __name__ == "__main__":
    main()
