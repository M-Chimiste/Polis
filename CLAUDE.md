# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

POLIS is a research instrument for studying emergent social behavior in LLM-backed generative agents (a faithful implementation of Park et al. 2023's Generative Agents, running on local models, instrumented for measurement). It is glasshouse's sibling, not its sequel: glasshouse is a show, POLIS is an experiment, and **zero glasshouse code is imported** — proven patterns are reimplemented from spec only.

**Current state: pre-code.** The repo contains the plan (`MASTER_PLAN.md`), the state-of-record docs (`memory_bank/`), the frozen v1 world content (`content/`), and content tooling (`scripts/`). The Python sim scaffold (P0) does not exist yet.

## Operating protocol (required)

- **Before any task:** read `memory_bank/` — especially `activeContext.md` (current focus and open forks) and `decisionLog.md` (ratified decisions; do not relitigate them).
- **After any task:** update `MASTER_PLAN.md` phase boxes/dashboard and the relevant memory bank files (`activeContext.md`, `progress.md`, `decisionLog.md` for new decisions). Run tests. One commit per coherent work item.

## Commands

```bash
python3 scripts/validate_content.py   # run after ANY hand edit to content/; exits nonzero on failure
```

Do **not** re-run `scripts/generate_content.py`: it regenerates from scratch and clobbers hand edits. The town was generated once and frozen (decision 2026-07-03); the generator is historical record. Edit `content/*.json` directly and validate.

Once P0 lands: uv-managed Python 3.12, `pytest` for sim/cognition/metrics, `vitest` for the observer.

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

Planned scaffold: `sim/`, `cognition/`, `metrics/`, `observer/`, `schemas/`, `services/`.

## Infrastructure

The sim runs on a Mac (Athena/Metis); Mnemosyne (2× GPU) is the vLLM inference server exclusively; Nyx hosts Postgres + pgvector and the embedder; Aletheia archives run bundles. All over Tailscale. Model tiers: fast (8B — dialogue, importance scoring), slow (32–70B — reflection, planning), judge (offline believability scoring). Sampling params are per-model per-role config, covered by the experiment config hash.

## Content (`content/`)

Static, hand-editable world data: `town.json` (Harrowmere: 16 locations, 48×48 grid), `agents/*.json` (20 seeds: bio, traits, HH:MM daily anchors, initial memories), `relationships.json` (32 edges with per-direction views). One file per agent; relationships live only in the shared edge list (no symmetric duplication). The seeds carry latent tensions but no scripted events. Always run the validator after edits.
