# AGENTS.md

Guidance for AI coding agents working in this repository.

## Read First

Before changing code, read:

- `CLAUDE.md`
- `MASTER_PLAN.md`
- `memory_bank/activeContext.md`
- `memory_bank/decisionLog.md`
- `memory_bank/progress.md`

The memory bank is the state of record. `decisionLog.md` contains ratified decisions; do not relitigate them unless the user explicitly asks. `MASTER_PLAN.md` tracks phase gates and dashboard state.

## Project Snapshot

POLIS is a research instrument for studying emergent social behavior in LLM-backed generative agents. It is a headless-first town simulation with cognition, replay, metrics, and later a zero-authority observer.

POLIS is not a game, not a broadcast product, and not a narrative system. The prime directive is no narrative injection: no director, no scenarios, no viewer commands, no set pieces. Exogenous inputs are limited to initial content, the clock, and explicitly logged experimental treatments.

Current state as of 2026-07-03: P3 measurement plane is complete on fake-model stand-ins. P4 observer, P5 experiment prep, and hardware-backed serving/database tasks remain.

## Operating Rules

- Preserve the no-narrative-injection boundary.
- Do not import or port glasshouse code. POLIS may reimplement proven patterns from specs only.
- Remote-session development is the standing constraint: do not attempt live LLM connectivity or real database access unless Christian explicitly asks. Use mocks, fixtures, fake model paths, and tests that skip cleanly without services.
- Keep sim authority strict. World state mutates only through schema-validated intents, never freeform action strings.
- Preserve determinism. Stable sorted ordering, seeded PRNG streams, canonical JSONL, and logged-completion replay are part of the instrument.
- Metrics and probes are a separate plane. They post-process run artifacts or frozen state and must not feed back into sim memory or world state.
- Gateway failures are typed results, not exceptions callers rely on catching. Callers branch on `GatewayCompletion | GatewayFailure`.

## Common Commands

```bash
uv sync
uv run pytest
uv run pytest tests/test_gateway.py -k repair
python3 scripts/validate_content.py
./scripts/gen_models.sh
```

Scripted headless run:

```bash
python -m sim.runner --ticks 3000 --seed 42 --out ledger.jsonl
```

Cognition fake-model run:

```bash
python -m cognition.runner --ticks 8640 --seed 42 --agents maren_alder,piet_alder --out-dir run_out
```

Replay a cognition run from logged completions:

```bash
python -m cognition.runner --ticks 8640 --seed 42 --agents maren_alder,piet_alder --out-dir replay_out --replay-dir run_out
```

Assemble an experiment bundle:

```bash
python -m metrics.assemble --run-dir run_out --config experiment.json --out bundle
```

## Files And Boundaries

- `sim/`: authoritative world core, content loading, deterministic runner, ledger writer, perception, scripted stand-ins.
- `cognition/`: Park-style cognition stack, memory, retrieval, planning, dialogue, reflection, completions, telemetry, fake-model dev path.
- `metrics/`: post-hoc measurement plane: probes, diffusion, graph, coordination, believability, bundle assembly.
- `schemas/json/`: source of truth for cross-boundary contracts.
- `schemas/models/`: generated pydantic mirrors. Never hand-edit this directory.
- `content/`: frozen static town, agents, and relationships. Hand-edit JSON directly, then validate.
- `services/gateway/`: model gateway, serving profiles, validation wall.
- `services/db/`: Postgres/pgvector DDL and sinks.
- `observer/`: P4 placeholder for Vite/React/R3F observer. It must remain zero-authority over the sim.

## Generated Or Guarded Files

- Do not rerun `scripts/generate_content.py`. It is historical record and can clobber the frozen town.
- After editing `content/`, run `python3 scripts/validate_content.py`.
- After editing `schemas/json/`, run `./scripts/gen_models.sh` and commit the generated `schemas/models/` changes.
- Do not hand-edit `schemas/models/`.
- Treat `tests/fixtures/ledger_scripted_seed42_3000.jsonl` as a permanent-wall fixture. Regenerate only when an intentional content or sim semantics change requires it, and explain why.

## Testing Guidance

Run the narrowest useful tests while iterating, then broaden based on risk. Use `uv run pytest` before handoff for code changes when feasible. Postgres integration tests are expected to skip when no database is reachable. Hardware-backed LLM or database smoke tests are Christian's home-network tasks unless explicitly requested.

For docs-only changes, tests may be unnecessary; say so in the handoff.

## State Updates

For meaningful implementation work, update the relevant project state before handoff:

- `MASTER_PLAN.md` for phase boxes, dashboard, and phase log changes.
- `memory_bank/activeContext.md` for current focus and open forks.
- `memory_bank/progress.md` for completed work.
- `memory_bank/decisionLog.md` only for new ratified decisions.

Do not add state churn for trivial docs or formatting-only changes.

## Engineering Style

Prefer small, contract-preserving changes. Reuse existing patterns before introducing abstractions. Keep JSON canonical where ledgers, completions, manifests, or fixtures depend on byte equality. Preserve async cognition boundaries without changing sim-time semantics. When adding observer code later, keep the app read-only: ledger stream in, no sim mutation out.
