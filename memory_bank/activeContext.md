# Active Context

Updated: 2026-07-03

## Current state

P3 measurement plane complete, gate met: all metrics + the probe battery post-process run artifacts with provably zero sim footprint (contamination test), and **the first measured diffusion curve exists** — a fact seeded at the tavernkeeper reaches her co-located household (1→3 of 5) through dialogue + eavesdropping while the never-co-present bakery pair stays dark. Fake-model, so non-conforming — but the entire instrument path (inject → memory → retrieval → utterance → hearing → probe → curve → plot → bundle) demonstrably works.

Built today, in order: P0 software half → P1 world core (byte-equal wall, 90 affordance-tagged objects, Postgres ledger sink) → P2 cognition (Park stack, logged-completion replay, cost telemetry) → P3 (probes, diffusion, graph, coordination, believability battery, bundle assembly). `pytest` green — 130 tests (incl. live local-Postgres integration).

Cognition dynamics calibrated while chasing diffusion (see decisionLog): dialogue context carries salience and always includes the speaker's top salient recent memories (the gossip channel); hourly re-observation of co-present agents (cohabitants otherwise get one react chance per day); recency decay per sim-hour (Park's calibration); fake importance is content-tiered. Zombie-conversation bug fixed (conversations no longer attach to sleeping agents).

Known stand-ins pending hardware: HashEmbedder (non-semantic), fake model, DeterministicJudge. Runs using any of them are non-conforming by construction.

**Standing constraint (user, 2026-07-03): development happens from remote sessions — do not attempt live LLM connectivity or real database access; everything is built and tested against mocks/fixtures.** Hardware tasks (Postgres apply, Mnemosyne profile launch, gateway smoke, Postgres ledger sink) are batched for Christian to run from the home network later.

## Current focus

Founding decisions ratified 2026-07-03: logged-completion replay with per-model/per-role sampling config; Python sim; **from scratch — zero glasshouse code import** (patterns reimplemented from spec); Mnemosyne = inference server, sim runs on a Mac; metrics-before-agents confirmed.

Town fork closed 2026-07-03: **generate once, freeze as static content.** v1 content exists and validates — Harrowmere (16 locations, 48×48 grid, 2 occluders) + 20 agent seeds + 32-edge relationship list, all in `content/`, guarded by `scripts/validate_content.py`. Awaiting Christian's rejection pass on the content itself (names, tone, tension seeds).

Open fork still awaiting a call:

1. **tp split on Mnemosyne:** two single-GPU models (fast+slow) vs. tp=2 one larger model. Measure in P2; default to the split.

## Immediate next action

P1 is complete (2026-07-03): objects-with-states authored (35 objects, deterministic verb→state transitions wired through `use_object`), and the Postgres ledger sink built + integration-tested against a throwaway Postgres inside the dev container (tests auto-skip without a DB; `POLIS_TEST_DSN` overrides).

Buildable from remote next:

- P4 observer (Vite/React/R3F over exported ledger JSONL + the WebSocket sidecar; zero authority).
- P5 prep: soak runs (multi-day fake-model headless), seed-sweep harness over the diffusion pipeline.
- DB wiring completion: probes + memory_records + completions Postgres inserts alongside the ledger sink.

Batched for Christian (home network):

1. Content rejection pass (names, tone, tension seeds, 90 objects + affordances) — still pending.
2. Postgres with pgvector anywhere: apply `services/db/schema.sql` and run one sim with `--pg-dsn` at it.
3. Mnemosyne: launch fast/slow vLLM tiers per `services/serving/mnemosyne/*.yaml`; confirm proxy base_url in `profiles.yaml`; gateway smoke from the sim host (closes P0).
4. Stand up the 768-dim embedder service; swap HashEmbedder out.
5. Re-run the P2 gate harness (`cognition.runner --profile mnemosyne`) against live serving — the real "coherent day" check — and measure tp split vs tp=2 (cost telemetry is ready).
