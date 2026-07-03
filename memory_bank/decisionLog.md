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

Reason: Tick work is trivial at ≤25 agents; the bottleneck is LLM latency. One language for sim + cognition + metrics + TheseusInsight tooling. Rust/wgpu ambitions stay with Vivarium.

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
