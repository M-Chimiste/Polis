"""Headless cognition run: the P2 counterpart of sim.runner.

python -m cognition.runner --ticks 8640 --seed 42 --agents maren_alder,piet_alder \
    --out-dir run_out            # fake model (dev; non-conforming by construction)
python -m cognition.runner ... --replay-dir run_out   # replay from logged completions

Writes ledger.jsonl + completions.jsonl (canonical JSONL). Real-model runs
use --profile against live serving — a hardware-session task.
"""
from __future__ import annotations

import argparse
import asyncio
import pathlib
import uuid

import httpx

from cognition.completions import CognitionGateway, CompletionLog
from cognition.embedding import HashEmbedder
from cognition.fake_model import fake_model_transport
from cognition.runtime import CognitionRuntime, Settings
from services.gateway import ModelGateway, ServingProfile, load_profiles
from sim.content import content_hash, load_agents, load_town
from sim.ledger import LedgerWriter
from sim.world import World

RUN_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

FAKE_PROFILE = ServingProfile(
    name="fake",
    base_url="http://fake.local/v1",
    tiers={"fast": {"model": "fake-fast"}, "slow": {"model": "fake-slow"}},
    roles={
        "importance": {"tier": "fast", "sampling": {"temperature": 0.0, "max_tokens": 16}},
        "action_selection": {"tier": "fast", "sampling": {"temperature": 0.7, "max_tokens": 128}},
        "dialogue": {"tier": "fast", "sampling": {"temperature": 0.9, "max_tokens": 256}},
        "daily_planning": {"tier": "slow", "sampling": {"temperature": 0.8, "max_tokens": 1024}},
        "decomposition": {"tier": "slow", "sampling": {"temperature": 0.6, "max_tokens": 768}},
        "reflection": {"tier": "slow", "sampling": {"temperature": 0.8, "max_tokens": 1024}},
    },
)


def fake_gateway() -> ModelGateway:
    client = httpx.AsyncClient(transport=fake_model_transport(), base_url=FAKE_PROFILE.base_url)
    return ModelGateway(FAKE_PROFILE, http_client=client)


async def run_cognition(
    ticks: int,
    seed: int,
    agent_ids: list[str] | None = None,
    run_id: str | None = None,
    settings: Settings | None = None,
    gateway: ModelGateway | None = None,
    replay_log: CompletionLog | None = None,
    ledger_sink=None,
    completions_sink=None,
) -> tuple[LedgerWriter, CognitionGateway, CognitionRuntime]:
    town = load_town()
    seeds = load_agents()
    if agent_ids:
        seeds = {aid: seeds[aid] for aid in agent_ids}
    run_id = run_id or str(uuid.uuid5(RUN_NS, f"polis:cognition:{seed}:{ticks}:{sorted(seeds)}"))
    settings = settings or Settings()

    world = World(town, seeds, master_seed=seed)
    log = CompletionLog(run_id, sink=completions_sink)
    cog_gateway = CognitionGateway(gateway if replay_log is None else None,
                                   log, replay_from=replay_log)
    runtime = CognitionRuntime(world, seeds, cog_gateway, HashEmbedder(), settings, run_id)
    writer = LedgerWriter(run_id, sink=ledger_sink)

    # NOTE: replay must reproduce the ledger byte-equal, so nothing here may
    # depend on live-vs-replay; provenance lives in the experiment record
    # (experiment_config.replay_of_run_id), not the ledger.
    writer.append(0, "run_started", None, {
        "seed": seed, "ticks": ticks, "content_hash": content_hash(),
        "mode": "cognition", "agents": sorted(seeds),
    })
    for aid in sorted(world.agents):
        agent = world.agents[aid]
        writer.append(0, "agent_initialized", aid, {
            "pos": list(agent.pos), "location": world.location_of(aid), "status": agent.status,
        })

    events: list = []
    for _ in range(ticks):
        tick = world.tick
        intents, cognition_events = await runtime.tick(events)
        for kind, agent_id, data in cognition_events:
            writer.append(tick, kind, agent_id, data)
        events = world.step(intents)
        for kind, agent_id, data in events:
            writer.append(tick, kind, agent_id, data)

    writer.append(world.tick, "run_finished", None, {
        "events": writer.seq + 1,
        "completions": cog_gateway.total_calls(),
        "gateway_failures": runtime.total_gateway_failures(),
    })
    return writer, cog_gateway, runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless cognition run (fake model or replay)")
    parser.add_argument("--ticks", type=int, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--agents", default=None, help="comma-separated agent ids (default: all)")
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--replay-dir", type=pathlib.Path, default=None,
                        help="replay completions from a previous --out-dir")
    parser.add_argument("--profile", default=None,
                        help="serving profile name for a real-model run (hardware sessions only)")
    args = parser.parse_args()

    agent_ids = args.agents.split(",") if args.agents else None
    replay_log = None
    run_id = None
    if args.replay_dir is not None:
        lines = (args.replay_dir / "completions.jsonl").read_bytes().splitlines()
        import json as _json
        run_id = _json.loads(lines[0])["run_id"]
        replay_log = CompletionLog.load(lines, run_id)
        gateway = None
    elif args.profile:
        gateway = ModelGateway(load_profiles()[args.profile])
    else:
        gateway = fake_gateway()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with open(args.out_dir / "ledger.jsonl", "wb") as ledger_sink, \
         open(args.out_dir / "completions.jsonl", "wb") as completions_sink:
        writer, cog_gateway, runtime = asyncio.run(run_cognition(
            args.ticks, args.seed, agent_ids=agent_ids, run_id=run_id,
            gateway=gateway, replay_log=replay_log,
            ledger_sink=ledger_sink, completions_sink=completions_sink,
        ))
    print(f"{writer.seq} ledger events, {cog_gateway.total_calls()} completions, "
          f"{runtime.total_gateway_failures()} gateway failures -> {args.out_dir}")


if __name__ == "__main__":
    main()
