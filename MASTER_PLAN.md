# POLIS — MASTER PLAN

**Current phase:** P0 in progress — software half done, hardware half (Nyx/Mnemosyne) pending · **Last updated:** 2026-07-03

Plan-of-record. `memory_bank/` is the state-of-record for narrative and decisions. Same operating protocol as glasshouse: read MEMORY_BANK context before any task; after any task update phase boxes, phase log, dashboard, activeContext/progress/decisionLog; run tests; one commit per coherent work item.

**Design north star:** shortest path to a real diffusion curve (P5), with the ablation harness (P6) immediately behind it. Everything not on that path is deferred.

---

## Phase map

```text
P0 ──► P1 ──► P2 ──► P3 ──► P5 ──► P6
boot   world  minds  measure│first  ablate
                            │exp.
              P4 observer ──┘ (parallel; depends only on P1 ledger stream)
```

---

## P0 — Bootstrap (gate: `pytest` green on a walking skeleton)

- [x] Repo scaffold: uv project, `sim/`, `cognition/`, `metrics/`, `observer/`, `schemas/`, `services/`.
- [x] Model gateway, from scratch: validation wall + structured outputs + one repair re-prompt + named hardware profiles + **per-model/per-role sampling config** (glasshouse pattern reimplemented, zero code import) — `services/gateway/`, unit-tested against a mocked endpoint. **Pending: smoke against Mnemosyne vLLM proxy profile from the sim host (Mac).**
- [x] Schemas v0: `ledger_event`, `agent_intent`, `memory_record`, `experiment_config`, `probe_result` + `town_spec`/`agent_seed`/`relationships` formalized from content. Pydantic mirrors generated (`scripts/gen_models.sh`).
- [ ] Postgres schema (pgvector enabled; any Postgres host — Nyx is the default, not a dependency): DDL authored in-repo (`services/db/schema.sql`: runs, agents, memory_records, plans, ledger_events, completions, probes, metrics; embedding dim 768, BERT-class). **Pending: apply to a real database.**
- [ ] vLLM serving profiles on Mnemosyne: fast tier (8B, GPU0) + slow tier (32–70B, GPU1), reasoning capped at launch; profile configs recorded in-repo (`services/serving/`). **Pending: launch + reconcile with the vLLM manager's config format.**

## P1 — World core (gate: byte-equal ledger fixture across two headless runs, no LLM)

- [x] Town spec: **DONE at inception** — generated once via `scripts/generate_content.py`, frozen as static `content/town.json` (Harrowmere, 16 locations, 48×48). Objects-with-states still to populate.
- [ ] Tick loop: pure world step, seeded PRNG streams per subsystem, A*/grid pathfinding, co-location cells.
- [ ] Intent grammar + validator: move_to, use_object, converse_with(request/accept/decline), idle, sleep.
- [ ] Perception, from scratch to P11 semantics: sight cone ∧ occlusion ∨ hearing radius; all parameters in config.
- [ ] Scripted-agent mode (FSM stand-ins) to exercise the loop without models.
- [ ] Ledger stream: Postgres persistence + WebSocket sidecar; legacy-replay fixture established (the permanent wall).

## P2 — Cognition (gate: 5 agents live a coherent unscripted day; every completion logged and replayable)

- [ ] Memory stream: write path with importance scoring (fast tier) + embedding at write.
- [ ] Retrieval: R×I×R scorer over pgvector; α/β/γ in config.
- [ ] Async cognition runtime: plan-cache execution, importance-gated interrupts, react calls; gateway-down fallback.
- [ ] Planning: daily plan → lazy hourly → action-step decomposition; plans stored as memory records.
- [ ] Dialogue: turn loop with per-turn retrieval about interlocutor; conversation summary written back as observations.
- [ ] Reflection: importance-sum trigger → questions → retrieve → insight records with citation edges.
- [ ] Logged-completion replay mode; replay of a sampled run reproduces the ledger byte-equal.
- [ ] Cost telemetry per agent per sim-hour per tier; measure tp split vs. tp=2 on Mnemosyne, record in decisionLog.

## P3 — Measurement plane (gate: metrics run against a P2 ledger and produce plots without touching sim state)

- [ ] Probe runner: frozen-state agent interviews + fact checks; probes table; contamination test (probe run ⇒ zero memory/ledger diff).
- [ ] Diffusion pipeline: seeded-fact treatment injection (logged), periodic fact probes, curve output.
- [ ] Relationship graph builder: interaction-weighted snapshots per sim-hour; density/clustering/community stability.
- [ ] Coordination-event detector over the ledger.
- [ ] Believability probe battery (Park interview categories) + LLM-as-judge scoring via TheseusInsight rubric infra.
- [ ] Experiment record assembly: one command → archived run bundle on Aletheia.

## P4 — Observer (parallel after P1; gate: live view + replay scrub of a real run)

- [ ] Vite/React/R3F app reading the WebSocket ledger stream and exported ledgers.
- [ ] Town render (simple geometry, no art pipeline), agents with action labels, click → memory/plan inspector.
- [ ] Diffusion overlay (seeded-fact holders colored) and relationship-thread view.
- [ ] Replay scrubber.

## P5 — First experiment (gate: a diffusion curve from ≥8 seeds, 20 agents, ≥3 sim-days, unattended)

- [x] 20 agent seeds: **DONE at inception** — `content/agents/*.json` + `content/relationships.json` (32 edges), validator-guarded. Rejection pass pending.
- [ ] Soak: full sim-week headless run; fix what breaks.
- [ ] Run the seeded-fact diffusion experiment across ≥8 seeds; produce curves + believability scores + cost report.
- [ ] Writeup pass: does the instrument work? Record verdict + gaps in progress.md.

## P6 — Ablation harness (gate: same experiment, ≥2 conditions, statistically compared)

- [ ] Condition runner: config-matrix execution across retrieval variants (full R×I×R / recency-only / salience+tag), reflection on/off, interrupt-threshold sweep.
- [ ] Comparison reports: per-condition diffusion curves, graph metrics, believability, cost, with seed-level variance.
- [ ] Decide the first writeup target (blog / whitepaper / TheseusInsight pipeline) from the data.

---

## Deferred register (not before P6)

Town re-generation / variants · perception-parameter ablations · population scaling >25 · Twitch replay broadcasting (observer-only) · multi-day persistent society (season-style continuity) · cross-model/cross-backend comparisons (e.g. MLX serving profiles) · belief-divergence formal analysis over reflection citation edges.
