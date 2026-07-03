# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

POLIS is a research instrument for studying emergent social behavior in LLM-backed generative agents (a faithful implementation of Park et al. 2023's Generative Agents, running on local models, instrumented for measurement). It is glasshouse's sibling, not its sequel: glasshouse is a show, POLIS is an experiment, and **zero glasshouse code is imported** — proven patterns are reimplemented from spec only.

**Current state: P0 fully closed; P1–P3 software complete, all gates met (140 tests green).** The world core (P1), the Park cognition stack (P2), and the measurement plane (P3) all exist and run headless end-to-end; the first measured diffusion curve exists (fake-model) and the first live-model cognition run succeeded (2 agents, `--profile metis`, zero failures). P4 (observer) is a stub; P5 (first experiment) and P6 (ablation) are not started. `MASTER_PLAN.md` tracks phase state; `memory_bank/` is the state-of-record.

**Environment:** development happens on Theseus with **live serving and a local database available**: metis + athena (OpenAI-compatible LLM endpoints over Tailscale, profiles in `services/serving/profiles.yaml`; raw endpoints in untracked `.env`) and local Postgres 14 + pgvector (`polis` for runs, `polis_test` for the suite). The `fake_model`, `HashEmbedder`, and `DeterministicJudge` stand-ins remain the default for tests and offline dev; any run using a stand-in is **non-conforming by construction** (not a real measurement). The serving models are thinking models — see the thinking-model decisionLog entry before touching gateway or profile code.

## Operating protocol (required)

- **Before any task:** read `memory_bank/` — especially `activeContext.md` (current focus, open forks, batched hardware tasks) and `decisionLog.md` (ratified decisions; do not relitigate them).
- **After any task:** update `MASTER_PLAN.md` phase boxes/dashboard and the relevant memory bank files (`activeContext.md`, `progress.md`, `decisionLog.md` for new decisions). Run tests. One commit per coherent work item.

## Commands

```bash
uv sync                                          # install deps (Python 3.12, uv-managed)
uv run pytest                                    # full suite (130 tests)
uv run pytest tests/test_gateway.py -k repair    # single test by file + keyword
python3 scripts/validate_content.py              # run after ANY hand edit to content/; exits nonzero on failure
./scripts/gen_models.sh                          # regenerate pydantic mirrors after ANY edit to schemas/json/

# Headless runs (the primary mode; all deterministic given seed):
python -m sim.runner --ticks 3000 --seed 42 --out ledger.jsonl              # P1 scripted world, no LLM
python -m cognition.runner --ticks 8640 --seed 42 --agents maren_alder,piet_alder --out-dir run_out   # P2, fake model
python -m cognition.runner --ticks 8640 --seed 42 --agents ... --profile metis --out-dir run_out      # live models (metis|athena); --pg-dsn postgresql:///polis also streams to Postgres
python -m cognition.runner --ticks 8640 --seed 42 --agents ... --replay-dir run_out --out-dir run2    # replay from logged completions
python -m metrics.assemble --run-dir run_out --config experiment.json --out bundle/   # P3 experiment record bundle
```

Postgres-backed tests (`test_pg_*.py`) run against the local `polis_test` DB (skip cleanly if it's unreachable; `POLIS_TEST_DSN=postgresql://…` overrides). `TICKS_PER_DAY = 8640` (1 tick = 10 sim-seconds).

Do **not** re-run `scripts/generate_content.py`: it regenerates from scratch and clobbers hand edits. The town was generated once and frozen (decision 2026-07-03); the generator is historical record. Edit `content/*.json` directly and validate.

Do **not** hand-edit `schemas/models/` — it is generated. Edit the JSON Schema in `schemas/json/` (the source of truth) and run `./scripts/gen_models.sh`.

The observer (P4, not started) will use `vitest`.

## The prime directive: no narrative injection

Nothing in POLIS proposes, nudges, or schedules drama. The only exogenous inputs are initial world content, the clock, and explicitly-logged experimental treatments (e.g. a seeded fact). If a subsystem's purpose is "make it interesting," it does not belong here. No director, no scenarios, no viewer commands, no TTS/broadcast features.

## Architecture (built — see memory_bank for full detail)

Layering with strict authority boundaries:

- **World state** (`sim/world.py`) is authoritative and tick-stepped (pure-function `step()`, seeded PRNG per subsystem via `sim/rng.py`, A* pathfinding with fixed tie-breaks in `sim/grid.py`). Agents act only through **intents** validated against an action grammar — freeform strings never mutate world state; rejected intents land in the ledger as `intent_rejected`.
- **Cognition** (`cognition/`, the Park stack: memory stream → R×I×R retrieval → reflection → hierarchical planning → dialogue) is fully async; the world never blocks on a model (`cognition/runtime.py` awaits agents in deterministic sorted order). Observations are importance-scored; below threshold, agents run from plan cache (cached steps = zero model calls) — that gate is what makes 20+ agents affordable.
- **Perception** (`sim/perception.py`) carries information asymmetry (sight cone ∧ occlusion ∨ hearing radius): agents can miss things, which is what makes diffusion and rumor measurable. Parameters are config (`experiment_config.perception`), not constants. Eavesdropping via hearing radius is the diffusion channel.
- **Measurement is a separate plane** (`metrics/`): metrics post-process the exported ledger + memory store, never read sim internals live. Probes (`metrics/probes.py`) run against `FrozenStream` tick-bounded state copies with their own `CompletionLog` and must leave zero footprint in sim data — the contamination test (`tests/test_metrics_probes.py`) is the P3 gate.
- **Observer** (`observer/`, P4 stub) will be Vite/React/R3F reading the ledger stream with zero authority; headless is the primary mode.

Determinism: sampling with temperature > 0 is allowed; reproducibility comes from **logged-completion replay** (`cognition/completions.py`) — every completion (successes *and* failures) is persisted keyed by (run_id, agent_id, call_site, sequence) and replay serves from the log, reproducing the ledger byte-equal. Byte-equal ledger fixtures guard the sim core (`tests/fixtures/ledger_scripted_seed42_3000.jsonl`, checked by `tests/test_replay_fixture.py`).

Contracts: JSON Schema (`schemas/json/`) is the source of truth for all cross-boundary data (jsonschema Draft 2020-12 validation via `schemas.validate(name, instance)`; pydantic mirrors in `schemas/models/` are generated for typed access). Never invent shapes a schema already defines.

Layout: `sim/` (world core, content loaders, ledger, stream), `cognition/` (P2 minds + fake_model + replay), `metrics/` (P3 probes/diffusion/graph/coordination/believability/assemble), `observer/` (P4 stub), `schemas/` (`json/` source of truth + generated `models/`), `services/` (`gateway/` model gateway, `serving/` vLLM profiles, `db/` DDL + ledger sink), `tests/`. The gateway (`services/gateway/client.py`) returns typed `GatewayCompletion | GatewayFailure` results and never raises — callers branch, they don't catch — and applies a validation wall + one repair re-prompt around structured outputs.

## Infrastructure

The sim runs on Theseus. metis + athena serve inference (LM Studio-class OpenAI-compatible endpoints on :1240 over Tailscale): qwen3.6-35b-a3b-mtp — a **thinking model** — for both the fast and slow tiers (the tier split survives in the role mapping so a model split stays a profile edit), plus nomic-embed-text-v1.5 (768-dim) for embeddings. Postgres + pgvector is local on Theseus (host-agnostic DDL — moving it is a DSN change). Aletheia archives run bundles (pending). Judge (offline believability scoring) is an open fork — pick a different model family at judge time.

Thinking-model facts (measured 2026-07-03, see decisionLog): request-level thinking kill switches are ignored (`request_extras: {enable_thinking: false}` is sent best-effort anyway); reasoning arrives in `reasoning_content`; metis shunts grammar-constrained JSON into `reasoning_content` with empty content — the gateway salvages it schema-gated (structured calls on metis effectively skip thinking, ~35 tok/call; athena reasons fully, ~300–1000 tok). Role `max_tokens` are caps sized for reasoning + answer — never set them small. Every model call carries a `response_schema` (user directive); empty freeform content is a typed failure. Sampling params are per-model per-role config, covered by the experiment config hash.

## Content (`content/`)

Static, hand-editable world data: `town.json` (Harrowmere: 16 locations, 48×48 grid), `agents/*.json` (20 seeds: bio, traits, HH:MM daily anchors, initial memories), `relationships.json` (32 edges with per-direction views). One file per agent; relationships live only in the shared edge list (no symmetric duplication). The seeds carry latent tensions but no scripted events. Always run the validator after edits.
