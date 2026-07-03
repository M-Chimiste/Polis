# Active Context

Updated: 2026-07-03

## Current state

P0 in progress. The software half of the bootstrap exists and `pytest` is green (48 tests): uv project scaffold (`sim/`, `cognition/`, `metrics/`, `observer/`, `schemas/`, `services/`), schemas v0 with generated pydantic mirrors, model gateway implemented and unit-tested against a mocked OpenAI-compatible endpoint, Postgres DDL and vLLM serving profiles recorded in-repo. The hardware half remains: apply `services/db/schema.sql` on Nyx, launch the serving profiles on Mnemosyne, smoke the gateway from the sim host.

## Current focus

Founding decisions ratified 2026-07-03: logged-completion replay with per-model/per-role sampling config; Python sim; **from scratch — zero glasshouse code import** (patterns reimplemented from spec); Mnemosyne = inference server, sim runs on a Mac; metrics-before-agents confirmed.

Town fork closed 2026-07-03: **generate once, freeze as static content.** v1 content exists and validates — Harrowmere (16 locations, 48×48 grid, 2 occluders) + 20 agent seeds + 32-edge relationship list, all in `content/`, guarded by `scripts/validate_content.py`. Awaiting Christian's rejection pass on the content itself (names, tone, tension seeds).

Open fork still awaiting a call:

1. **tp split on Mnemosyne:** two single-GPU models (fast+slow) vs. tp=2 one larger model. Measure in P2; default to the split.

## Immediate next action

Still pending from before: content rejection pass (Christian — names, tone, tension seeds).

P0 hardware tasks (need Tailscale access to the boxes; can't run from a cloud session):

1. Nyx: create the `polis` database, enable pgvector, apply `services/db/schema.sql`. Confirm the embedder choice first — the DDL carries a `vector(384)` placeholder (MiniLM-class) and changing it later is a migration.
2. Mnemosyne: launch fast/slow tiers per `services/serving/mnemosyne/*.yaml` through the vLLM manager, reconcile those records with the manager's real config format, confirm the proxy base_url in `services/serving/profiles.yaml`.
3. Sim host (Mac): run a gateway smoke test against the live proxy (structured output + repair path against a real model). That closes P0.

Then P1: tick loop, intent validator wired to `agent_intent.schema.json`, perception, scripted-agent mode, ledger stream.
