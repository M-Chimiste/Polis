"""Headless run loop — the primary mode.

python -m sim.runner --ticks 3000 --seed 42 --out ledger.jsonl

Deterministic end to end: seeded world, scripted agents, canonical ledger.
Two runs with the same (seed, ticks) produce byte-equal JSONL — the P1 gate.
run_id defaults to a uuid5 of (seed, ticks) so even the id is reproducible;
real experiments pass an explicit run_id.
"""
from __future__ import annotations

import argparse
import pathlib
import uuid
from typing import BinaryIO, Callable

from sim.clock import minute_of_day
from sim.content import content_hash, load_agents, load_town
from sim.ledger import LedgerWriter
from sim.scripted import ScriptedAgent
from sim.world import World

RUN_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")  # uuid.NAMESPACE_URL


def default_run_id(seed: int, ticks: int) -> str:
    return str(uuid.uuid5(RUN_NS, f"polis:scripted:{seed}:{ticks}"))


def run(
    ticks: int,
    seed: int,
    run_id: str | None = None,
    sink: BinaryIO | None = None,
    on_event: Callable[[dict], None] | None = None,
) -> LedgerWriter:
    town = load_town()
    seeds = load_agents()
    world = World(town, seeds, master_seed=seed)
    controllers = {aid: ScriptedAgent(s) for aid, s in seeds.items()}
    writer = LedgerWriter(run_id or default_run_id(seed, ticks), sink=sink, on_event=on_event)

    writer.append(0, "run_started", None, {
        "seed": seed, "ticks": ticks, "content_hash": content_hash(), "mode": "scripted",
    })
    for aid in sorted(world.agents):
        agent = world.agents[aid]
        writer.append(0, "agent_initialized", aid, {
            "pos": list(agent.pos), "location": world.location_of(aid), "status": agent.status,
        })

    for _ in range(ticks):
        minute = minute_of_day(world.tick)
        tick = world.tick
        intents = {}
        for aid in sorted(controllers):
            intent = controllers[aid].intent(world, minute)
            if intent is not None:
                intents[aid] = intent
        for kind, agent_id, data in world.step(intents):
            writer.append(tick, kind, agent_id, data)

    writer.append(world.tick, "run_finished", None, {"events": writer.seq + 1})
    return writer


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless scripted-mode run")
    parser.add_argument("--ticks", type=int, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--pg-dsn", default=None,
                        help="also persist the ledger to Postgres (schema must be applied)")
    args = parser.parse_args()
    pg_sink = None
    if args.pg_dsn:
        from services.db.ledger_sink import PostgresLedgerSink
        pg_sink = PostgresLedgerSink(args.pg_dsn)
    try:
        with open(args.out, "wb") as sink:
            writer = run(args.ticks, args.seed, run_id=args.run_id, sink=sink, on_event=pg_sink)
    finally:
        if pg_sink is not None:
            pg_sink.close()
    print(f"{writer.seq} events -> {args.out}" + (" + postgres" if pg_sink else ""))


if __name__ == "__main__":
    main()
