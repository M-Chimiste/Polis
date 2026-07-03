# Decision Log

## 2026-07-03 — POLIS is a sibling repo, not a glasshouse mode

Decision: New repo. Glasshouse parts are imported/ported explicitly (agent_model_service, memory_service persistence, P11 perception, contract discipline); nothing else crosses over.

Reason: Glasshouse's director/scenario/broadcast stack contaminates emergence claims. A "research mode" flag would leave injection pathways in the codebase and in doubt. The dividing rule must be structural.

## 2026-07-03 — No narrative injection, ever

Decision: No director, scenarios, viewer input, or set pieces. Exogenous inputs limited to initial content, clock, and logged experimental treatments.

Reason: Any injected pressure destroys the ability to attribute observed behavior to the agent architecture. The null hypothesis must be boring.

## 2026-07-03 — Python sim core (not Rust/Bevy, not FastAPI-as-sim)

Decision: Single authoritative Python process for the sim; thin FastAPI sidecar for ledger streaming/control only.

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

Reason: Glasshouse measured that request-level enable_thinking can be ignored; the cap must live server-side. Two Blackwells idle while an 8B on metis carries cognition is the wrong allocation for a throughput workload.

## 2026-07-03 — Working name: POLIS

Decision: POLIS, pending rejection.

Reason: Fits the naming universe; it is literally the object of study (a small self-governing community). Alternatives considered: Agora (too market-specific), Demos (collides with "demo").
