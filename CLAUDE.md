# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

POLIS is a research instrument for studying emergent social behavior in LLM-backed generative agents (a faithful implementation of Park et al. 2023's Generative Agents, running on local models, instrumented for measurement). It is glasshouse's sibling, not its sequel: glasshouse is a show, POLIS is an experiment, and **zero glasshouse code is imported** — proven patterns are reimplemented from spec only.

**Current state: P0 in progress.** The uv project scaffold, schemas v0, and the model gateway exist and are tested; the sim itself (P1+) does not exist yet. `MASTER_PLAN.md` tracks phase state; `memory_bank/` is the state-of-record.

## Operating protocol (required)

- **Before any task:** read `memory_bank/` — especially `activeContext.md` (current focus and open forks) and `decisionLog.md` (ratified decisions; do not relitigate them).
- **After any task:** update `MASTER_PLAN.md` phase boxes/dashboard and the relevant memory bank files (`activeContext.md`, `progress.md`, `decisionLog.md` for new decisions). Run tests. One commit per coherent work item.

## Commands

```bash
uv sync                               # install deps (Python 3.12, uv-managed)
uv run pytest                         # full suite; single test: uv run pytest tests/test_gateway.py -k repair
python3 scripts/validate_content.py   # run after ANY hand edit to content/; exits nonzero on failure
./scripts/gen_models.sh               # regenerate pydantic mirrors after ANY edit to schemas/json/
```

Do **not** re-run `scripts/generate_content.py`: it regenerates from scratch and clobbers hand edits. The town was generated once and frozen (decision 2026-07-03); the generator is historical record. Edit `content/*.json` directly and validate.

Do **not** hand-edit `schemas/models/` — it is generated. Edit the JSON Schema in `schemas/json/` (the source of truth) and run `./scripts/gen_models.sh`.

The observer (P4, not started) will use `vitest`.

## The prime directive: no narrative injection

Nothing in POLIS proposes, nudges, or schedules drama. The only exogenous inputs are initial world content, the clock, and explicitly-logged experimental treatments (e.g. a seeded fact). If a subsystem's purpose is "make it interesting," it does not belong here. No director, no scenarios, no viewer commands, no TTS/broadcast features.

## Architecture (planned, decided — see memory_bank for full detail)

Layering with strict authority boundaries:

- **World state** is authoritative and tick-stepped (1 tick = 10 sim-seconds, pure-function step, seeded PRNG per subsystem). Agents act only through **intents** validated against an action grammar — freeform strings never mutate world state.
- **Cognition** (Park stack: memory stream → R×I×R retrieval → reflection → hierarchical planning → dialogue) is fully async; the world never blocks on a model. Observations are importance-scored; below threshold, agents run from plan cache — that gate is what makes 20+ agents affordable.
- **Perception** carries information asymmetry (sight cone ∧ occlusion ∨ hearing radius): agents can miss things, which is what makes diffusion and rumor measurable. Perception parameters are config, not constants.
- **Measurement is a separate plane:** metrics post-process the ledger and memory store, never read sim internals live. Probes run against frozen state copies and must leave zero footprint in sim data.
- **Observer** (Vite/React/R3F) reads the ledger stream with zero authority; headless is the primary mode.

Determinism: sampling with temperature > 0 is allowed; reproducibility comes from **logged-completion replay** — every completion is persisted keyed by (run_id, agent_id, call_site, sequence) and replay serves from the log. Byte-equal ledger fixtures guard the sim core.

Contracts: JSON Schema is the source of truth for all cross-boundary data (Ajv on the TS side, pydantic mirrors on the Python side). Never invent shapes a schema already defines.

Layout: `sim/` (world core, content loaders), `cognition/` (P2), `metrics/` (P3), `observer/` (P4 stub), `schemas/` (`json/` source of truth + generated `models/`), `services/` (`gateway/` model gateway, `serving/` profiles, `db/` DDL), `tests/`. The gateway returns typed `GatewayCompletion | GatewayFailure` results and never raises — callers branch, they don't catch.

## Infrastructure

The sim runs on a Mac (Athena/Metis); Mnemosyne (2× GPU) is the vLLM inference server exclusively; Nyx hosts Postgres + pgvector and the embedder; Aletheia archives run bundles. All over Tailscale. Model tiers: fast (8B — dialogue, importance scoring), slow (32–70B — reflection, planning), judge (offline believability scoring). Sampling params are per-model per-role config, covered by the experiment config hash.

## Content (`content/`)

Static, hand-editable world data: `town.json` (Harrowmere: 16 locations, 48×48 grid), `agents/*.json` (20 seeds: bio, traits, HH:MM daily anchors, initial memories), `relationships.json` (32 edges with per-direction views). One file per agent; relationships live only in the shared edge list (no symmetric duplication). The seeds carry latent tensions but no scripted events. Always run the validator after edits.
