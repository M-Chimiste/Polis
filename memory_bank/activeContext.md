# Active Context

Updated: 2026-07-03

## Current state

P1 world core built and its gate met: byte-equal ledger fixture across headless runs, no LLM (`tests/fixtures/ledger_scripted_seed42_3000.jsonl` is the permanent wall). `pytest` green — 79 tests. Working: deterministic tick loop, A* pathfinding, intent grammar wall with semantic rejection, P11 perception (cone ∧ occlusion ∨ hearing, all config), scripted FSM agents living coherent anchor-driven days, canonical JSONL ledger + zero-authority WebSocket sidecar.

P0's software half is also done (scaffold, schemas v0 + mirrors, gateway vs mocked endpoint, DDL, serving profile records).

**Standing constraint (user, 2026-07-03): development happens from remote sessions — do not attempt live LLM connectivity or real database access; everything is built and tested against mocks/fixtures.** Hardware tasks (Postgres apply, Mnemosyne profile launch, gateway smoke, Postgres ledger sink) are batched for Christian to run from the home network later.

## Current focus

Founding decisions ratified 2026-07-03: logged-completion replay with per-model/per-role sampling config; Python sim; **from scratch — zero glasshouse code import** (patterns reimplemented from spec); Mnemosyne = inference server, sim runs on a Mac; metrics-before-agents confirmed.

Town fork closed 2026-07-03: **generate once, freeze as static content.** v1 content exists and validates — Harrowmere (16 locations, 48×48 grid, 2 occluders) + 20 agent seeds + 32-edge relationship list, all in `content/`, guarded by `scripts/validate_content.py`. Awaiting Christian's rejection pass on the content itself (names, tone, tension seeds).

Open fork still awaiting a call:

1. **tp split on Mnemosyne:** two single-GPU models (fast+slow) vs. tp=2 one larger model. Measure in P2; default to the split.

## Immediate next action

P1 is complete (2026-07-03): objects-with-states authored (35 objects, deterministic verb→state transitions wired through `use_object`), and the Postgres ledger sink built + integration-tested against a throwaway Postgres inside the dev container (tests auto-skip without a DB; `POLIS_TEST_DSN` overrides).

Buildable from remote next:

- P2 cognition against the mocked gateway: memory stream write path, R×I×R retrieval scorer (pgvector-backed in prod, in-memory for tests), plan-cache runtime, logged-completion replay mode — replay is by construction testable without a model.
- P3 metrics over the committed ledger fixture; P4 observer against exported ledger JSONL.

Batched for Christian (home network):

1. Content rejection pass (names, tone, tension seeds, now also the 35 objects) — still pending.
2. Postgres with pgvector anywhere: apply `services/db/schema.sql` (768-dim, decided) and run one sim with `--pg-dsn` at it.
3. Mnemosyne: launch fast/slow vLLM tiers per `services/serving/mnemosyne/*.yaml`; confirm proxy base_url in `profiles.yaml`.
4. Gateway smoke from the sim host against the live proxy. Closes P0.
