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
