# POLIS — MASTER PLAN

**Current phase:** P0 closed; **P2 gate met LIVE 2026-07-03**; pre-soak fixes complete (dynamic schema enums, crossing-request race, full DB wiring) · next: **P5 soak** (20 agents, sim-week, overnight) · **Last updated:** 2026-07-03

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
- [x] Model gateway, from scratch: validation wall + structured outputs + one repair re-prompt + named hardware profiles + **per-model/per-role sampling config** (glasshouse pattern reimplemented, zero code import) — `services/gateway/`, unit-tested against a mocked endpoint. **Smoked live 2026-07-03** from Theseus against metis+athena (plain, structured, embeddings); thinking-model hardening added (request_extras, reasoning_content salvage, empty-content failure — see decisionLog).
- [x] Schemas v0: `ledger_event`, `agent_intent`, `memory_record`, `experiment_config`, `probe_result` + `town_spec`/`agent_seed`/`relationships` formalized from content. Pydantic mirrors generated (`scripts/gen_models.sh`).
- [x] Postgres schema (pgvector enabled; any Postgres host): DDL (`services/db/schema.sql`: runs, agents, memory_records, plans, ledger_events, completions, probes, metrics; embedding dim 768) **applied 2026-07-03** to local Postgres 14 + pgvector 0.8.0 on Theseus (`polis` + `polis_test`); pg integration tests run live, no skips.
- [x] Serving profiles — **re-scoped 2026-07-03**: the Mnemosyne vLLM plan is superseded by reality — metis + athena (LM Studio-class OpenAI-compatible endpoints, :1240 over Tailscale), qwen3.6-35b-a3b-mtp (thinking model, MTP) for BOTH tiers (user call: speed + ease), nomic-embed-text-v1.5 (768-dim) for embeddings. `services/serving/profiles.yaml` carries both profiles; `services/serving/mnemosyne/` remains as historical record.

## P1 — World core (gate: byte-equal ledger fixture across two headless runs, no LLM)

- [x] Town spec: **DONE at inception** — generated once via `scripts/generate_content.py`, frozen as static `content/town.json` (Harrowmere, 16 locations, 48×48). Objects-with-states populated 2026-07-03: 35 objects, deterministic verb→state interactions, `use_object` transitions them (validator + schema extended; part of Christian's pending rejection pass).
- [x] Tick loop: deterministic world step (`sim/world.py`), seeded PRNG streams per subsystem (`sim/rng.py`, plumbed; scripted mode draws nothing yet — pinned by test), A* pathfinding with fixed tie-breaks (`sim/grid.py`), co-location.
- [x] Intent grammar + validator: move_to, use_object, converse_with(request/accept/decline), idle, sleep — schema wall + world-semantic checks; rejects land in the ledger as `intent_rejected`.
- [x] Perception, from scratch to P11 semantics: sight cone ∧ occlusion ∨ hearing radius (`sim/perception.py`); all parameters config (`experiment_config.perception`).
- [x] Scripted-agent mode (FSM stand-ins, anchor-driven) — a full sim-day: 20 agents wake, commute, work, return, sleep; zero rejections.
- [x] Ledger stream: canonical JSONL writer + WebSocket sidecar (`sim/stream.py`, zero authority); **byte-equal replay fixture established** (`tests/fixtures/ledger_scripted_seed42_3000.jsonl` — the permanent wall). Postgres sink (`services/db/ledger_sink.py`, `--pg-dsn` on the runner) integration-tested against a throwaway container Postgres; tests skip cleanly where no DB is reachable. Homelab run still on Christian's batch list.

## P2 — Cognition (gate: 5 agents live a coherent unscripted day; every completion logged and replayable)

**Gate met 2026-07-03 on the deterministic fake model** (`tests/test_cognition_day.py`), **and re-met LIVE the same day** (`runs/p2_gate_live_metis_seed42`, local only): 5 agents, full unscripted day on metis — 1221 completions, 0 gateway failures, 132 object uses, 26 conversations, coherent contextual dialogue, **replay byte-equal from the completion log** (determinism holds with real sampled inference), HTTPEmbedder live. ~25 min wall (~1.15 s/call), 264k prompt / 79k completion tokens. Findings for pre-soak fixes: 27 intent rejections from two grounding gaps (decompositions missing `move_to` before `use_object`; hallucinated locations in agendas — fix: dynamic schema enums from town spec / location objects); real-model importance runs hot vs fake tiers (reflection trigger fires often — threshold calibration is experiment config); one era anachronism in dialogue (folds into the content rejection pass); conversation_started (26) vs conversation_ended (18) imbalance to check (sleep wind-down event emission).

- [x] Memory stream: write path with importance scoring (fast tier) + embedding at write (`cognition/memory.py`; deterministic uuid5 ids). **Real embedder wired 2026-07-03:** `HTTPEmbedder` (nomic-embed-text-v1.5, 768-dim, asymmetric doc/query prefixes) via the profile `embedding:` block; HashEmbedder remains the offline stand-in (non-conforming by construction).
- [x] Retrieval: R×I×R scorer, α/β/γ/decay/top_k in config (`cognition/retrieval.py`; min-max normalized per paper; creation-time recency decay — access-time decay noted as possible ablation). pgvector storage parity integration-tested (`tests/test_pg_memory.py`).
- [x] Cognition runtime: plan-cache execution (cached steps = zero calls), importance-gated interrupts, react calls, gateway-down fallback per subsystem (`cognition/runtime.py`). Scheduling is deterministic (sorted-agent await order) — wall-clock overlap is a serving-time optimization that must never change sim-time semantics.
- [x] Planning: daily agenda → lazy per-block decomposition → grounded action steps; plans stored as memory records; deterministic anchor-driven fallbacks (`cognition/planning.py`).
- [x] Dialogue: turn loop with per-turn retrieval about the interlocutor; per-POV summaries written back as memories; hearers (including eavesdroppers, via hearing radius) get observation memories — the diffusion channel (`cognition/runtime.py`).
- [x] Reflection: importance-sum trigger → questions → retrieve → insight records with citation edges (`cognition/runtime.py`).
- [x] Logged-completion replay mode; replay reproduces the ledger byte-equal, run_started included (`cognition/completions.py`; failures are logged and replayed too).
- [x] Cost telemetry per agent per sim-hour per tier (`cognition/telemetry.py`). **Re-scoped 2026-07-03** (tp-split question is moot without Mnemosyne): measure metis (grammar path, ~35 tok/structured call) vs athena (full reasoning, ~300–1000 tok/call) on the same run shape, record in decisionLog.

## P3 — Measurement plane (gate: metrics run against a P2 ledger and produce plots without touching sim state)

**Gate met 2026-07-03** (`tests/test_metrics_probes.py::test_probe_and_metrics_contamination`): every metric + the full probe battery runs against a treated P2 run's artifacts and leaves sim state and artifacts byte-identical; plots land in the bundle.

- [x] Probe runner: frozen-state interviews + fact checks (`metrics/probes.py`; FrozenStream tick-bounded copies, probes get their own CompletionLog); contamination test is the gate test. Fact checks are deterministic keyword checks in v1 (objective, model-free); judge-scored fact checks join with real models. **DB wiring done 2026-07-03:** `services/db/run_sink.py` — cognition runs stream ledger + completions + memory records (embeddings included) into Postgres (`cognition.runner --pg-dsn`), probes insert via `metrics.assemble --pg-dsn`; all inserts idempotent (deterministic keys, ON CONFLICT DO NOTHING).
- [x] Diffusion pipeline: treatment injection wired into the runner (ledger `treatment_injected` + target memory at controlled importance), periodic post-hoc fact probes over reconstructed snapshots, curve + plot (`metrics/diffusion.py`). **First measured curve: fact injected at the tavernkeeper reaches the co-located household (1→3 of 5) and never reaches the never-co-present bakery pair — information asymmetry measurable end-to-end (fake-model, non-conforming).**
- [x] Relationship graph builder: per-sim-hour interaction-weighted snapshots from ledger utterances; density / mean clustering / components / window-stability series + plot (`metrics/graph.py`).
- [x] Coordination-event detector: sustained ≥k-agent co-location spans reconstructed purely from the ledger (`metrics/coordination.py`).
- [x] Believability probe battery: Park's five interview categories over frozen state (`metrics/believability.py`); judge is a pluggable interface — DeterministicJudge stub offline. **Pending: real LLM-as-judge with a rubric (judge tier, hardware time).**
- [x] Experiment record assembly: `python -m metrics.assemble` → self-contained bundle (artifacts, config + hash, metrics.json, probes.jsonl, plots, sha256 manifest). **Pending: rsync bundle to Aletheia (hardware).**

## P4 — Observer (parallel after P1; gate: live view + replay scrub of a real run)

**Built 2026-07-03** (`observer/`, pnpm + vitest, 14 tests incl. the real P1 byte-equal fixture and probes.py fact-check parity): Ajv validation against the shared schemas, pure replay fold (world-at-tick = fold of event prefix).

- [x] Vite/React/R3F app reading the WebSocket ledger stream (`?ws=`) and exported ledgers + memories (drag-and-drop JSONL, routed by record shape).
- [x] Town render (simple geometry from town.json, occluders included), day/night lighting as a pure function of sim time, agents with status colors + smoothed movement, click → inspector with the agent's **memory stream at the cursor** (kind/importance/text).
- [x] Diffusion overlay (fact from `treatment_injected`; holders haloed via the probes.py-parity keyword check, live while scrubbing) and relationship-thread view (pair lines weighted by accumulated conversation; talking pairs glow). Demo data: `runs/demo_treated_fake/`.
- [x] Replay scrubber (tick slider + play; live mode follows the stream head).

Gate check (live view + scrub of a real run, human eyes on it) still open — needs a session with the sidecar up.

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
