# POLIS — MASTER PLAN

**Current phase:** P3 software complete — gate met (metrics + probes over run artifacts, zero sim footprint, plots produced); first measured diffusion curve exists (fake-model, non-conforming) · next: P4 observer, or hardware tasks · **Last updated:** 2026-07-03

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

- [x] Town spec: **DONE at inception** — generated once via `scripts/generate_content.py`, frozen as static `content/town.json` (Harrowmere, 16 locations, 48×48). Objects-with-states populated 2026-07-03: 35 objects, deterministic verb→state interactions, `use_object` transitions them (validator + schema extended; part of Christian's pending rejection pass).
- [x] Tick loop: deterministic world step (`sim/world.py`), seeded PRNG streams per subsystem (`sim/rng.py`, plumbed; scripted mode draws nothing yet — pinned by test), A* pathfinding with fixed tie-breaks (`sim/grid.py`), co-location.
- [x] Intent grammar + validator: move_to, use_object, converse_with(request/accept/decline), idle, sleep — schema wall + world-semantic checks; rejects land in the ledger as `intent_rejected`.
- [x] Perception, from scratch to P11 semantics: sight cone ∧ occlusion ∨ hearing radius (`sim/perception.py`); all parameters config (`experiment_config.perception`).
- [x] Scripted-agent mode (FSM stand-ins, anchor-driven) — a full sim-day: 20 agents wake, commute, work, return, sleep; zero rejections.
- [x] Ledger stream: canonical JSONL writer + WebSocket sidecar (`sim/stream.py`, zero authority); **byte-equal replay fixture established** (`tests/fixtures/ledger_scripted_seed42_3000.jsonl` — the permanent wall). Postgres sink (`services/db/ledger_sink.py`, `--pg-dsn` on the runner) integration-tested against a throwaway container Postgres; tests skip cleanly where no DB is reachable. Homelab run still on Christian's batch list.

## P2 — Cognition (gate: 5 agents live a coherent unscripted day; every completion logged and replayable)

**Gate met 2026-07-03 on the deterministic fake model** (`tests/test_cognition_day.py`): 5 agents live a full unscripted day — plan, commute, use objects, converse, reflect, sleep — every completion logged, replay byte-equal, gateway-down degrades without crashing. The same harness must re-run against live serving when hardware is available (that re-run is the final gate check).

- [x] Memory stream: write path with importance scoring (fast tier) + embedding at write (`cognition/memory.py`; deterministic uuid5 ids). **Embedder is the HashEmbedder stand-in — real 768-dim BERT-class service pending hardware; HashEmbedder runs are non-conforming by construction.**
- [x] Retrieval: R×I×R scorer, α/β/γ/decay/top_k in config (`cognition/retrieval.py`; min-max normalized per paper; creation-time recency decay — access-time decay noted as possible ablation). pgvector storage parity integration-tested (`tests/test_pg_memory.py`).
- [x] Cognition runtime: plan-cache execution (cached steps = zero calls), importance-gated interrupts, react calls, gateway-down fallback per subsystem (`cognition/runtime.py`). Scheduling is deterministic (sorted-agent await order) — wall-clock overlap is a serving-time optimization that must never change sim-time semantics.
- [x] Planning: daily agenda → lazy per-block decomposition → grounded action steps; plans stored as memory records; deterministic anchor-driven fallbacks (`cognition/planning.py`).
- [x] Dialogue: turn loop with per-turn retrieval about the interlocutor; per-POV summaries written back as memories; hearers (including eavesdroppers, via hearing radius) get observation memories — the diffusion channel (`cognition/runtime.py`).
- [x] Reflection: importance-sum trigger → questions → retrieve → insight records with citation edges (`cognition/runtime.py`).
- [x] Logged-completion replay mode; replay reproduces the ledger byte-equal, run_started included (`cognition/completions.py`; failures are logged and replayed too).
- [x] Cost telemetry per agent per sim-hour per tier (`cognition/telemetry.py`). **Pending hardware: measure tp split vs. tp=2 on Mnemosyne, record in decisionLog.**

## P3 — Measurement plane (gate: metrics run against a P2 ledger and produce plots without touching sim state)

**Gate met 2026-07-03** (`tests/test_metrics_probes.py::test_probe_and_metrics_contamination`): every metric + the full probe battery runs against a treated P2 run's artifacts and leaves sim state and artifacts byte-identical; plots land in the bundle.

- [x] Probe runner: frozen-state interviews + fact checks (`metrics/probes.py`; FrozenStream tick-bounded copies, probes get their own CompletionLog); contamination test is the gate test. Fact checks are deterministic keyword checks in v1 (objective, model-free); judge-scored fact checks join with real models. **Pending: probes → Postgres probes table insert (with the other DB wiring).**
- [x] Diffusion pipeline: treatment injection wired into the runner (ledger `treatment_injected` + target memory at controlled importance), periodic post-hoc fact probes over reconstructed snapshots, curve + plot (`metrics/diffusion.py`). **First measured curve: fact injected at the tavernkeeper reaches the co-located household (1→3 of 5) and never reaches the never-co-present bakery pair — information asymmetry measurable end-to-end (fake-model, non-conforming).**
- [x] Relationship graph builder: per-sim-hour interaction-weighted snapshots from ledger utterances; density / mean clustering / components / window-stability series + plot (`metrics/graph.py`).
- [x] Coordination-event detector: sustained ≥k-agent co-location spans reconstructed purely from the ledger (`metrics/coordination.py`).
- [x] Believability probe battery: Park's five interview categories over frozen state (`metrics/believability.py`); judge is a pluggable interface — DeterministicJudge stub offline. **Pending: real LLM-as-judge with a rubric (judge tier, hardware time).**
- [x] Experiment record assembly: `python -m metrics.assemble` → self-contained bundle (artifacts, config + hash, metrics.json, probes.jsonl, plots, sha256 manifest). **Pending: rsync bundle to Aletheia (hardware).**

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
- [ ] Decide the first writeup target (blog / whitepaper) from the data.

---

## Deferred register (not before P6)

Town re-generation / variants · perception-parameter ablations · population scaling >25 · Twitch replay broadcasting (observer-only) · multi-day persistent society (season-style continuity) · cross-model/cross-backend comparisons (e.g. MLX serving profiles) · belief-divergence formal analysis over reflection citation edges.
