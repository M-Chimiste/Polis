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

## P3 measurement plane built, gate met — first diffusion curve (2026-07-03)

- metrics/: probe runner (frozen tick-bounded state, own completion log, keyword fact checks + model interviews), diffusion pipeline (treatment injection in the runner: ledger event + controlled-importance target memory; post-hoc periodic fact probes over reconstructed snapshots; curve + matplotlib plot), relationship graph builder (hourly interaction snapshots, density/clustering/components/stability), coordination detector (≥k-agent co-location spans from the ledger alone), believability battery (Park's 5 interview categories, pluggable judge — DeterministicJudge stub), experiment record assembly (one command → bundle with artifacts, config hash, metrics.json, probes.jsonl, plots, sha256 manifest; Aletheia rsync pending hardware).
- Gate met: contamination test — every metric + full battery against a treated run; sim artifacts and live state byte-identical after.
- **First measured diffusion curve**: seeded fact at maren_alder (tavern) → ilse + piet by evening (direct hearing + eavesdrop), bakery pair never reached (never co-present). 1→3 of 5, non-decreasing, pinned in tests. Fake-model = non-conforming, but the whole instrument path works.
- Getting there surfaced real cognition fixes (salient-news dialogue channel, hourly re-observation, per-hour recency, tiered fake importance, zombie-conversation bug) — see decisionLog.
- cognition runner: --config (validated experiment config, treatments read from it), memories.jsonl export; probe role added to profiles.
- Suite: 130 tests green (4 live-Postgres). matplotlib added.

## P0 hardware half closed — live serving bring-up on Theseus (2026-07-03)

- Moved to Theseus (real computer); remote-only constraint lifted. `.env` (untracked) carries LLM endpoints; local Postgres available.
- DB: created `polis` + `polis_test` on local Postgres 14 + pgvector 0.8.0, applied `schema.sql`; pg integration tests run live — first no-skip suite run.
- Serving reality (probed): metis + athena, LM Studio-class OpenAI-compatible on :1240, NOT Mnemosyne/vLLM. User call: qwen3.6-35b-a3b-mtp (thinking, MTP) for both tiers; nomic-embed-text-v1.5 (768-dim — matches vector(768) exactly) for embeddings.
- Measured thinking-model behavior (decisionLog): request-level kill switches all ignored; reasoning separated into `reasoning_content`; metis shunts grammar-constrained JSON into `reasoning_content` (empty content, ~35 tok/call — de facto no-think); athena reasons fully (~300–1000 tok) then emits valid JSON; tiny max_tokens truncate mid-reasoning to empty content.
- Gateway hardened: profile `request_extras` (carries best-effort `enable_thinking: false`), schema-gated reasoning_content salvage, empty freeform content → typed validation failure; budgets ≥1024 across roles. Profiles rewritten: `metis` + `athena`.
- Structured outputs everywhere (user directive): UTTERANCE_SCHEMA on dialogue turns, PROBE_ANSWER_SCHEMA on probe interviews — zero freeform calls left; fake model updated to match.
- HTTPEmbedder (`cognition/embedding.py`): OpenAI-compatible /v1/embeddings, asymmetric nomic prefixes (`embed_query` added to the protocol; HashEmbedder aliases it prefix-free — fixtures hold), hard dim check, raises loudly. Runner wires it from the profile `embedding:` block.
- **First live cognition run** (2 Alder agents, ticks to ~07:13, `--profile metis`): 29 completions, 0 gateway failures, real daily plans, 12 object uses, real 4-turn conversation at the Gilded Perch, salvage path exercised in production (2130/2159 completion tokens via reasoning_content).
- Suite: 140 tests green (10 new: extras/salvage/empty-content, shipped-profile invariants, HTTPEmbedder). Remaining P2 check: full 5-agent live day.

## P2 gate re-met on live serving (2026-07-03)

- Full 5-agent unscripted day (`--profile metis`, seed 42, 8640 ticks, same five as the offline gate): **1221 completions, 0 gateway failures, replay byte-equal** — determinism holds with real sampled inference. 132 object uses, 26 conversations, 71 utterances; dialogue coherent and memory-grounded across the day. ~25 min wall (~1.15 s/call); 264k prompt / 79k completion tokens; salvage path carried essentially every structured call.
- Live-only findings recorded in activeContext (pre-soak list): two grounding gaps behind 27 intent rejections (missing move_to before use_object; hallucinated agenda locations → fix = dynamic schema enums), hot importance scores (reflection 168 calls — threshold calibration to experiment config during soak), one era anachronism (content pass), conversation_ended undercount to check.
- Soak sizing datum: 20-agent sim-week ≈ 34k calls ≈ ~11 h overnight.
- User decisions: metis/athena are identical servers (shunt difference is version drift — treat as interchangeable); proceed to P5 (north star), P4 stays deferred.

## Pre-soak fix list landed (2026-07-03)

- **Dynamic grounding schemas** (efb4889): agenda_schema/steps_schema/reaction_schema are per-call builders — town-location enums, block-location object/verb enums, co-located candidate enums. Grammar makes bad grounding unrepresentable; a location with no objects doesn't offer use_object; no candidates forces "continue". 5 new schema tests.
- **Crossing-request race fixed** (2dd914b): Mind.incoming_requests is a deduped FIFO answered one per tick (accept if free, else explicit decline); a conversation_started the runtime can't attach (busy/asleep party) immediately emits conversation_ended (turns=0). Regression test reproduces the exact live-day 3-way crossing. Pre-fix completion logs no longer replay byte-equal on new code (replay holds within a code version — expected).
- **DB wiring complete**: PostgresRunSink (services/db/run_sink.py) streams ledger events + completions + memory records with embeddings over one connection via hooks (LedgerWriter on_event, CompletionLog on_record, MemoryStream on_record); insert_probes for the measurement plane. All inserts ON CONFLICT DO NOTHING against deterministic keys — reruns/replays are no-ops. CLI: cognition.runner --pg-dsn, metrics.assemble --pg-dsn. 3 live-Postgres integration tests.
- Suite: 150 tests green. Next: the sim-week soak.
