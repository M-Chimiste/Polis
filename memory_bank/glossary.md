# Glossary

- **Ledger** — append-only, schema-valid record of everything that happened in a run (world events, intents, dialogue). The single source of truth for all metrics and the observer.
- **Completion log** — verbatim persisted model requests/responses keyed by (run, agent, call_site, seq); enables byte-reproducible replay of sampled runs.
- **Memory record** — one entry in an agent's memory stream: observation, plan, or reflection, with importance score, embedding, and (for reflections) citation edges.
- **Retrieval scoring** — recency × importance × relevance ranking over memory records; the primary ablation knob.
- **Reflection** — periodic synthesis of higher-level insights from accumulated memories, triggered by an importance-sum threshold.
- **Probe** — an experimenter query (interview, fact check) run against a frozen copy of agent state; logged, never visible to the sim.
- **Seeded fact** — an experimental treatment: information planted in exactly one agent's memory at a logged time, whose diffusion is then measured.
- **Diffusion curve** — % of population holding a seeded fact vs. sim-time, established via probes.
- **Coordination event** — ≥3 agents co-located with convergent stated intent within a time window, detected by ledger post-processing.
- **Fast tier / slow tier** — model serving split: small model for high-frequency calls (importance scoring, dialogue, action selection); larger model for reflection and planning.
- **Plan cache** — the agent's current decomposed plan steps, executed without model calls until interrupted or exhausted.
- **Interrupt threshold** — importance score above which an observation triggers replanning instead of plan-cache continuation.
- **Run / experiment record** — config hash + seed + model manifest + completion log + ledger + metric outputs; the unit of comparison.
- **Non-conforming run** — a run flagged for degraded conditions (embedder down, gateway outage) and excluded from headline results.
- **Observer** — the three.js/R3F frontend; renders ledger streams or exports; has zero write authority.
