# Progress

Updated: 2026-07-03

## Inception (2026-07-03)

- Memory Bank drafted (brief, product, tech, patterns, decisions, glossary).
- MASTER_PLAN.md drafted: P0 bootstrap → P1 world core → P2 cognition → P3 measurement → P4 observer → P5 first experiment → P6 ablation harness.
- Founding decisions ratified same day (from-scratch build, per-model sampling config, Mnemosyne-serves/Macs-simulate); see decisionLog.md.
- Nothing built. Remaining forks recorded in activeContext.md.

## v1 content authored (2026-07-03)

- Town fork closed: generate-once-freeze. `scripts/generate_content.py` (one-shot, clobbers on rerun — historical after ratification) emitted Harrowmere: 16 locations on a 48×48 grid (tavern, bakery, smithy, mill, chapel, farm, store, herbalist, well, square, orchard, 5 homes), 2 occluders, per-location privacy.
- 20 agent seeds in `content/agents/` (one file each: bio, traits, HH:MM daily anchors, 2 initial memories) + `content/relationships.json` (32 edges, closeness prior + per-direction views). Seeds carry latent tensions, no scripted events: succession (Ilse), leaving-shaped son (Corin), unpaid debt (reeve↔smith), commercial feud (Sela↔Petra), hidden illness (Nan), millstone secret (Josta), drainage-vs-mill-path conflict (Bram↔reeve).
- `scripts/validate_content.py`: location refs, grid fit, rect overlap, door placement, anchor format, edge integrity, orphan detection. Caught one rect overlap on first run (fixed). Current: OK — 16/20/32.

## P0 software half built (2026-07-03)

- uv project (Python 3.12, pydantic/httpx/jsonschema/pyyaml; pytest + datamodel-code-generator dev). Scaffold: `sim/`, `cognition/`, `metrics/`, `observer/` (stub), `schemas/`, `services/`, `tests/`.
- Schemas v0 in `schemas/json/` (JSON Schema 2020-12, source of truth): ledger_event, agent_intent (oneOf action grammar, strict), memory_record, experiment_config (config-hash-covered sampling, treatments, replay_of_run_id), probe_result, plus town_spec/agent_seed/relationships formalized from the frozen content. Pydantic mirrors generated into `schemas/models/` via `scripts/gen_models.sh`.
- Model gateway (`services/gateway/`): named hardware profiles + per-model/per-role sampling from `services/serving/profiles.yaml`; structured outputs via response_format json_schema; validation wall with one repair re-prompt then typed GatewayFailure (never raises — transport failures typed too); on_completion hook as the seam for P2 logged-completion replay.
- Postgres DDL `services/db/schema.sql` (runs/agents/ledger_events/memory_records/plans/completions/probes/metrics, pgvector; embedding vector(768), BERT-class, host-agnostic). Mnemosyne serving profile records in `services/serving/mnemosyne/`.
- `sim/content.py`: schema-validating content loaders + content_hash() (sha256 over content/) for experiment_config.
- Gate progress: `uv run pytest` green — 48 tests (content wall, intent grammar accept/reject, contract fixtures, gateway success/repair/double-fail/transport/logging, mirror parity). Full P0 gate still needs the Nyx/Mnemosyne hardware tasks.

## P1 world core built, gate met (2026-07-03)

- Standing constraint recorded: remote-session development only — no live LLM or database connectivity; mocks/fixtures everywhere. Hardware tasks batched for Christian.
- `sim/`: deterministic tick loop (`world.py` — intents are the only mutation path, sorted-order processing), A* with fixed tie-breaks + door-priority `locate()` (`grid.py`), seeded per-subsystem PRNG streams (`rng.py`), P11 perception (`perception.py` — cone ∧ occlusion ∨ hearing, occlusion-exempt hearing, all params config), anchor-driven scripted FSM agents (`scripted.py`), canonical JSONL ledger writer (`ledger.py`), headless runner CLI (`runner.py`), zero-authority WebSocket sidecar (`stream.py`, FastAPI).
- **P1 gate met:** two headless runs byte-equal; fixture committed (`tests/fixtures/ledger_scripted_seed42_3000.jsonl`, 127 events, seed 42, 3000 ticks). A full sim-day: 20 agents wake/commute/work/return/sleep, 5 commuters, zero intent rejections.
- Bug caught by the gate work: door cells can lie on a neighbouring rect's edge; `locate()` now resolves doors first and treats rect membership as strictly interior (perimeter = walls, nobody's floor).
- Remaining P1: objects-with-states in town.json; Postgres ledger sink (hardware-batched).
- Suite: 79 tests green.

## P1 completed: objects + Postgres sink (2026-07-03)

- Objects-with-states: 35 objects authored across all 16 locations (content edit, folded into the pending rejection pass). Deterministic interaction model: each object carries `interactions: {verb: resulting_state}`; `use_object` requires co-location and an allowed verb, transitions state, and emits `object_state_changed`. Schema + validator extended (object ids globally unique, interactions non-empty); mirrors regenerated. Fixture regenerated (content_hash lives in run_started, so content edits move the wall — deliberate).
- Postgres ledger sink (`services/db/ledger_sink.py`): LedgerWriter on_event hook; registers the run on run_started, batches inserts, marks runs finished on run_finished; `apply_schema()` applies the DDL idempotently. Runner gained `--pg-dsn`. Integration-tested against a throwaway Postgres 16 + pgvector installed in the dev container; tests skip cleanly when no DB is reachable (POLIS_TEST_DSN overrides the default local DSN). JSONL remains the byte-equal wall; Postgres is the queryable copy for the measurement plane.
- Suite: 83 tests green (3 of them live-DB integration).

## Object inventory rebuilt: generic + affordance-tagged (2026-07-03)

- Compared against Park et al.'s Smallville (46 object types / 19 sectors / 63 arenas / 25 agents): POLIS was proportionally consistent but thin on domestic coverage (no beds, little food-prep). User called it: generic fixtures, full daily-life coverage, leisure + utility both, grounded for future needs.
- Inventory now 90 objects across all 16 locations. Every object: generic name, deterministic verb→state interactions, `affordances` tags (schema-enforced enum). Coverage: work 32, food 27, social 25, hygiene 15, sleep 14, leisure 13.
- Guarantees (validator + tests): every agent's home affords sleep+food; every workplace affords work; possessive/agent-owned object names rejected; all six affordance domains present in town.
- Fixture regenerated (content_hash). Suite: 85 tests green.

## P2 cognition built, gate met on fake model (2026-07-03)

- Full Park stack in cognition/: memory stream (uuid5 ids, embed-at-write), R×I×R retrieval (min-max normalized, α/β/γ/decay/top_k config, pgvector storage parity test), hierarchical planning (daily agenda → lazy block decomposition → grounded steps; plans are memory records; anchor-driven fallbacks), dialogue (per-turn retrieval, per-POV summaries, hearer/eavesdropper observations = the diffusion channel), reflection (importance-sum trigger → questions → retrieve → insights with citation edges), importance-gated react interrupts, plan-cache cost gate (sleeping/cached = zero calls).
- Logged-completion replay: CognitionGateway keys every outcome (agent, call_site, sequence), logs failures too; replay reproduces the ledger byte-equal including run_started. Cost telemetry per agent/sim-hour/tier from the log.
- Deterministic fake model + prompts with machine-readable CONTEXT_JSON blocks drive the real gateway path offline. Gate test: 5 agents, full day — plans, commutes, 164 object uses (20-agent CLI run), 11 conversations, reflections with citations, 0 failures, byte-equal live rerun AND replay; gateway-down run completes on fallbacks.
- 20-agent full-day CLI run: 734 ledger events, 431 completions (importance 185, decompose 120, dialogue 60, react 28, planning 20, reflection 18) — call profile matches the paper's shape.
- Suite: 112 tests green. Pending hardware: real embedder, real-model gate re-run, tp-split measurement.
