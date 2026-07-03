# Decision Log

## 2026-07-03 — POLIS is a sibling repo, not a glasshouse mode

Decision: New repo. Glasshouse's director/scenario/broadcast stack contaminates emergence claims; a "research mode" flag would leave injection pathways in the codebase and in doubt. The dividing rule must be structural.

## 2026-07-03 — From scratch: zero glasshouse code import

Decision: No glasshouse code is imported or ported. Proven patterns (gateway validation wall, P11 perception semantics, contract discipline, byte-equal replay fixtures) are reimplemented clean from their specs.

Reason: User call — building from scratch ensures nothing show-shaped survives by accident. Supersedes the inception-draft salvage manifest.

## 2026-07-03 — Sampling parameters configurable per model, per role

Decision: Temperature/top_p/top_k/min_p/max_tokens/reasoning budget are set per model per role in config; no global policy and never a temperature-0 requirement. Sampling params are part of the experiment config hash.

Reason: Different models need different sampling to behave; determinism comes from logged-completion replay, not from constraining sampling. Config-hash inclusion keeps conditions honest.

## 2026-07-03 — Mnemosyne serves, Macs simulate

Decision: Mnemosyne is the inference server, exclusively. The sim process (plus probes and metrics) runs on a Mac (Athena/Metis primary) and must be host-portable to any Tailscale node; hard dependencies limited to gateway HTTP + Postgres.

Reason: User call. Keeps the GPUs dedicated to the throughput workload and the sim independently movable/restartable.

## 2026-07-03 — No narrative injection, ever

Decision: No director, scenarios, viewer input, or set pieces. Exogenous inputs limited to initial content, clock, and logged experimental treatments.

Reason: Any injected pressure destroys the ability to attribute observed behavior to the agent architecture. The null hypothesis must be boring.

## 2026-07-03 — Python sim core (not Rust/Bevy, not FastAPI-as-sim)

Decision: Single authoritative Python process for the sim; thin FastAPI sidecar for ledger streaming/control only. Runs on a Mac (see "Mnemosyne serves, Macs simulate").

Reason: Tick work is trivial at ≤25 agents; the bottleneck is LLM latency. One language for sim + cognition + metrics tooling. Rust/wgpu ambitions stay with Vivarium.

## 2026-07-03 — Park-faithful cognition, corners un-cut

Decision: Full recency×importance×relevance retrieval with embeddings, reflection synthesis with citation edges, hierarchical lazy planning. Glasshouse's salience+tag memory is not carried over.

Reason: Retrieval architecture is research question #4 (the publishable knob). Fidelity first, then ablate; can't ablate what was never built.

## 2026-07-03 — Determinism via logged-completion replay, not temperature 0

Decision: Sampling allowed live; every completion persisted keyed by (run, agent, call_site, seq); replay serves from the log. Sim randomness from seeded per-subsystem PRNG streams.

Reason: Temperature 0 sacrifices behavioral diversity, which is the phenomenon under study. Logged replay gives byte-reproducibility without that cost. Statistical claims come from ≥8 seeds per condition regardless.

## 2026-07-03 — Metrics decided before agents exist

Decision: Diffusion curve, relationship graph evolution, coordination-event detection, believability probes, and cost telemetry are specified in productContext.md before any agent code is written. Probes run against frozen state and never feed back.

Reason: Post-hoc metric selection on emergent systems is how you fool yourself. Measurement contamination (probes altering memory) would invalidate diffusion results.

## 2026-07-03 — Serving on Mnemosyne, reasoning capped server-side

Decision: vLLM on Mnemosyne via the existing manager proxy; fast tier + slow tier split across the two Blackwells (tp=2 single-model as a measured alternative). Reasoning budgets set at server launch.

Reason: Glasshouse measured that request-level enable_thinking can be ignored; the cap must live server-side. Per-model overrides remain possible where a server honors request-level params.

## 2026-07-03 — Town: generated once, frozen as static content

Decision: The town is produced by a one-shot generator script (`scripts/generate_content.py`) whose output is committed as static, hand-editable JSON in `content/`. The sim only reads `content/`; it never generates. After ratification, edits go directly to the JSON (guarded by `scripts/validate_content.py`); the generator becomes historical record.

Reason: User call — generate-and-freeze. Closes the hand-authored-vs-procedural fork with both properties: cheap to produce, static across all experiments (content is a controlled variable, not a noise source).

## 2026-07-03 — Agent seeds as per-agent files + single relationship edge list

Decision: One JSON file per agent (`content/agents/{id}.json`: bio, traits, daily anchors, initial memories) and one shared `content/relationships.json` edge list (pair + closeness + per-direction views). `validate_content.py` enforces referential integrity, no orphans, no duplicate pairs, grid consistency.

Reason: Update ergonomics — editing one agent touches one file; editing a relationship touches one edge in one place (no symmetric duplication to keep in sync). Validator makes hand edits safe.

## 2026-07-03 — Working name: POLIS

Decision: POLIS, pending rejection.

Reason: Fits the naming universe; it is literally the object of study (a small self-governing community). Alternatives considered: Agora (too market-specific), Demos (collides with "demo").
## 2026-07-03 — Pydantic mirrors are generated, not hand-written

Decision: `schemas/json/` (JSON Schema 2020-12) is the source of truth; `schemas/models/` is generated by datamodel-code-generator via `scripts/gen_models.sh` and never hand-edited. Runtime validation walls use the JSON Schema directly (jsonschema); the mirrors exist for typed ergonomics in Python code.

Reason: One artifact to review per contract change; drift between schema and mirror becomes impossible rather than merely tested-against. Matches the schema/contract discipline (Ajv will consume the same files on the TS side in P4).

## 2026-07-03 — Gateway returns typed results, never raises

Decision: `ModelGateway.complete()` returns `GatewayCompletion | GatewayFailure` for every outcome — validation failure after the one repair re-prompt AND transport/HTTP failures. Callers branch, they don't catch.

Reason: Service-optionality pattern made structural: gateway-down must degrade to plan-cache execution, so the sim's cognition dispatch should never need a try/except to survive it.
## 2026-07-03 — Embeddings: 768-dim BERT-class; Postgres host-agnostic

Decision: memory_records.embedding is vector(768) — a modern BERT-class embedder. And the DDL/tooling assume "any Postgres with pgvector", not Nyx specifically; Nyx remains the default home but is not a dependency of the schema or the code.

Reason: User call. 768 fixes the migration-sensitive choice now instead of carrying a placeholder into P2; decoupling from Nyx keeps the sim host-portable (the only hard dependencies stay HTTP reach to the gateway and a Postgres URL).

## 2026-07-03 — Objects are generic affordance-tagged fixtures; needs get grounded in content

Decision: Objects are generic fixtures of a location ("Bed", "Hearth", "Strongbox"), never personalized to an agent (validator rejects possessive names). Every object carries `affordances` ⊆ {sleep, food, hygiene, leisure, social, work} — the grounding layer for a future agent-needs system. Coverage is validator-enforced: every agent's home must afford sleep and food; every workplace must afford work.

Reason: User call. Generic fixtures keep ownership/meaning emergent (an agent's attachment to a bed should come from memories, not labels), daily-life + leisure + utility coverage lets P2 plan decomposition ground morning/evening/leisure steps in real `use_object` targets, and affordance tags give the needs system a contract instead of string-matching object names later.

## 2026-07-03 — Deterministic cognition scheduling; replay ledgers carry no provenance

Decision: The cognition runtime awaits every model call inline, in sorted agent-id order — call order is a pure function of sim state. Wall-clock overlap of slow-tier calls is a serving-time optimization that must never change sim-time semantics, else logged-completion replay breaks. And a replayed run's ledger is byte-equal to the original including run_started: replay provenance lives in the experiment record (experiment_config.replay_of_run_id), never in the ledger.

Reason: Replay is the reproducibility mechanism; it only works if the Nth call per (agent, call_site) is the same call every run. Any "faster because parallel" scheme has to preserve that keying. Ledger-identical replay keeps the permanent-wall property simple: one ledger, one hash, no diff-except-line-0 caveats.

## 2026-07-03 — Dev stand-ins are non-conforming by construction

Decision: The deterministic fake model (cognition/fake_model.py) and HashEmbedder (cognition/embedding.py) exist so the whole stack runs offline under the remote constraint, driving the real gateway/validation/logging path. Any run using either is non-conforming and can never be an experiment; the P2 gate is re-checked against live serving when hardware is available.

Reason: Keeps development unblocked without corrupting the instrument: the machinery (schemas, walls, replay, telemetry) is fully exercised, while semantic behavior (real dialogue, real relevance) is explicitly out of scope for stand-in runs.

## 2026-07-03 — Dialogue context carries salience and always includes top salient news

Decision: Dialogue-turn context is retrieval about the interlocutor PLUS the speaker's 1–2 most salient recent memories regardless of topic, and each memory travels with its importance score. Prompts instruct speakers to prefer salient material.

Reason: Chasing the first diffusion curve exposed it: query-by-partner alone means a salient fact that isn't about the partner never enters any conversation, so seeded facts cannot spread (Park's party invite spread precisely because salient news rides along). This is the gossip channel — with real models it means the model always sees what's on the agent's mind.

## 2026-07-03 — Conversation ecology calibrations

Decision: (1) Hourly re-observation of still-co-present agents — cohabitants who never move would otherwise get exactly one sighting (and hence one react chance) per day. (2) Recency decay is per sim-HOUR (Park's calibration), not per minute. (3) The fake importance scorer is content-tiered (heard speech 4–7 > sightings/co-presence 2–5 > routine), and the default interrupt threshold is 4 — explicitly a fake-era calibration; real-model runs set thresholds in experiment config. (4) Conversations never attach to sleeping agents, and a conversation whose partner detaches/sleeps is wound down (zombie fix).

Reason: All four surfaced while making diffusion measurable end-to-end. Without them: tavern cohabitants never conversed all day (one spark chance, hash said no), per-minute decay buried day-old salient facts under fresh routine, uniform hash importance let "spent time with X" outrank a seeded rumor, and one zombie conversation kept an agent awake past midnight.

## 2026-07-03 — Fact checks are keyword-based in v1

Decision: Diffusion fact probes are deterministic token-overlap checks against single memory records (model-free, zero probe traffic). Judge-scored fact checks (interview + LLM judgment) become an additional method when real models arrive; the curve methodology stays comparable across both.

Reason: Objective and reproducible, correct for the fake-model era (utterances quote memories verbatim), and it keeps the v1 curve free of judge noise. Real-model paraphrase will need the judge path — tracked, not forgotten.

## 2026-07-03 — Correction: "TheseusInsight" was drafting leakage, not a dependency

Decision: All references to "TheseusInsight" are removed from the plan, memory bank, code comments, and serving notes. The believability judge is a generic LLM-as-judge with a rubric — model and rubric chosen at hardware time — behind the existing pluggable Judge interface. No external project's infrastructure is assumed for scoring or publication.

Reason: User call. The name leaked into the drafted planning documents from unrelated older projects; nothing about POLIS depends on it and nothing project-specific was ever meant. The judge-tier design (offline, never on the hot path, pluggable) is unchanged.

## 2026-07-03 — Serving topology is metis + athena; Theseus simulates; Postgres is local

Decision: Supersedes "Mnemosyne serves, Macs simulate" and "Serving on Mnemosyne" in topology (their principles — sim host-portable, reasoning capped away from the request — stand). Inference is metis + athena: LM Studio-class OpenAI-compatible endpoints on :1240 over Tailscale (endpoints recorded in the untracked `.env`; profiles carry them explicitly). The sim runs on Theseus. Postgres 14 + pgvector 0.8.0 is local on Theseus (`polis` for runs, `polis_test` for the suite) — the host-agnostic DDL held: applying it elsewhere is a DSN change.

Reason: This is the hardware that exists. The remote-only standing constraint is lifted: live LLM connectivity and a real database are available from the dev machine.

## 2026-07-03 — Model assignment: qwen3.6-35b-a3b-mtp for both tiers; structured outputs on every call

Decision: User call — qwen3.6-35b-a3b-mtp (thinking model, MTP decode) serves BOTH fast and slow tiers on both servers, for speed and ease of use. Corollary (also user call): every model call carries a response_schema — the last freeform calls (dialogue turns, probe interviews) got schemas (`{"utterance"}`, `{"answer"}`). The fast/slow tier split survives in the role mapping so a future model split is a profile edit, not a code change. Judge model remains an open fork (pick a different family — minimax-m3 / deepseek-v4-flash / gemma-4-26b are on the shelf — at believability time).

Reason: One model everywhere removes cross-tier behavioral confounds and halves serving ops; schemas-everywhere is what makes thinking-model output reliable (and, via the metis grammar path, cheap).

## 2026-07-03 — Thinking-model serving facts (measured) and the gateway's response

Decision: Measured from Theseus against both servers: (1) request-level thinking kill switches (`enable_thinking`, `chat_template_kwargs`, `reasoning`, `reasoning_budget`, `/no_think`) are ALL ignored — the glasshouse lesson holds beyond vLLM; `request_extras: {enable_thinking: false}` is still sent best-effort. (2) Reasoning arrives in a separate `reasoning_content` field; `content` stays clean. (3) metis shunts grammar-constrained (json_schema) output entirely into `reasoning_content` with empty `content` — the grammar forbids the think block and the reasoning parser misfiles the answer; net effect: structured calls on metis skip thinking (~35 tokens/call vs athena's ~300–1000). The gateway therefore: salvages `reasoning_content` for structured calls when `content` is empty (schema-gated — the wall still decides), treats empty freeform content as a typed failure (truncation mid-reasoning is not an answer), and role budgets are ≥1024 tokens (caps sized for reasoning + answer, not spend targets).

Reason: The instrument must be honest about what serving actually does. Salvage is acceptable because validation still gates every accepted payload; a server update that changes the shunt shows up as test-visible behavior, not silent corruption.

## 2026-07-03 — Embedder: nomic-embed-text-v1.5 over HTTP, asymmetric prefixes

Decision: `HTTPEmbedder` against the OpenAI-compatible `/v1/embeddings` on either server, model text-embedding-nomic-embed-text-v1.5, 768-dim (matches vector(768) — no migration). Documents embed with `search_document:`, retrieval queries with `search_query:` (`embed_query()` added to the Embedder protocol). HashEmbedder aliases embed_query→embed (no prefix) so pre-prefix fixtures stay byte-equal. Embedder failures raise loudly — a conforming run must never silently degrade to hash vectors.

Reason: nomic v1.5 is asymmetric by design; skipping prefixes measurably degrades retrieval, and retrieval quality is research question #4's substrate. 768 was fixed in the DDL precisely so this day would be a config change.
