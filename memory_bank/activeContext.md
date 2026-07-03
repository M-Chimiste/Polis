# Active Context

Updated: 2026-07-03

## Current state

P2 cognition software complete, gate met on the deterministic fake model: 5 agents (and all 20 via CLI) live a coherent unscripted day on the full Park stack — daily agenda → lazy decomposition → plan-cache execution, importance-scored observations, importance-gated react interrupts, retrieval-grounded dialogue with per-POV summaries and eavesdropper diffusion, reflection with citation edges — every completion logged keyed (agent, call_site, sequence), replay byte-equal including run_started, gateway-down degrading to anchor fallbacks without a crash. `pytest` green — 112 tests.

P1 complete earlier same day (world core, byte-equal fixture wall, 90 affordance-tagged objects, Postgres ledger sink). P0 software half done.

Known stand-ins pending hardware: HashEmbedder (deterministic, non-semantic — runs with it are non-conforming) until the 768-dim BERT-class embedder service exists; fake model until Mnemosyne serving is up.

**Standing constraint (user, 2026-07-03): development happens from remote sessions — do not attempt live LLM connectivity or real database access; everything is built and tested against mocks/fixtures.** Hardware tasks (Postgres apply, Mnemosyne profile launch, gateway smoke, Postgres ledger sink) are batched for Christian to run from the home network later.

## Current focus

Founding decisions ratified 2026-07-03: logged-completion replay with per-model/per-role sampling config; Python sim; **from scratch — zero glasshouse code import** (patterns reimplemented from spec); Mnemosyne = inference server, sim runs on a Mac; metrics-before-agents confirmed.

Town fork closed 2026-07-03: **generate once, freeze as static content.** v1 content exists and validates — Harrowmere (16 locations, 48×48 grid, 2 occluders) + 20 agent seeds + 32-edge relationship list, all in `content/`, guarded by `scripts/validate_content.py`. Awaiting Christian's rejection pass on the content itself (names, tone, tension seeds).

Open fork still awaiting a call:

1. **tp split on Mnemosyne:** two single-GPU models (fast+slow) vs. tp=2 one larger model. Measure in P2; default to the split.

## Immediate next action

P1 is complete (2026-07-03): objects-with-states authored (35 objects, deterministic verb→state transitions wired through `use_object`), and the Postgres ledger sink built + integration-tested against a throwaway Postgres inside the dev container (tests auto-skip without a DB; `POLIS_TEST_DSN` overrides).

Buildable from remote next:

- P3 measurement plane: probe runner against frozen state, seeded-fact diffusion pipeline (treatment injection is already just a ledger event + target-agent memory), relationship graph builder, coordination detector — all post-processing cognition-run ledgers/memories, generatable offline with the fake model.
- P4 observer against exported ledger JSONL.

Batched for Christian (home network):

1. Content rejection pass (names, tone, tension seeds, 90 objects + affordances) — still pending.
2. Postgres with pgvector anywhere: apply `services/db/schema.sql` and run one sim with `--pg-dsn` at it.
3. Mnemosyne: launch fast/slow vLLM tiers per `services/serving/mnemosyne/*.yaml`; confirm proxy base_url in `profiles.yaml`; gateway smoke from the sim host (closes P0).
4. Stand up the 768-dim embedder service; swap HashEmbedder out.
5. Re-run the P2 gate harness (`cognition.runner --profile mnemosyne`) against live serving — the real "coherent day" check — and measure tp split vs tp=2 (cost telemetry is ready).
