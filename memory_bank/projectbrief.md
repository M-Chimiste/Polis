# Project Brief

POLIS is a research instrument for studying emergent social behavior in LLM-backed generative agents in a town/village setting. It is a faithful-and-beyond implementation of the Generative Agents architecture (Park et al. 2023, arXiv:2304.03442) running live on local models, instrumented for measurement rather than staged for entertainment.

POLIS is glasshouse's sibling, not its sequel. Glasshouse is a show; POLIS is an experiment. The dividing rule: **nothing in POLIS injects narrative.** No director, no scenarios, no viewer interventions, no set pieces. Agents, environment, clock, and measurement — the null hypothesis must be boring.

## What POLIS is

- A headless-first, deterministically-replayable town simulation of 15–25 named agents.
- Full Park cognition stack: memory stream, recency × importance × relevance retrieval, reflection synthesis, hierarchical planning with lazy decomposition, plan interruption on salient observations.
- Perception with information asymmetry (directional witnessing + occlusion, adapted from glasshouse P11) — agents can miss things, so rumor, belief divergence, and information diffusion are possible.
- A measurement harness that produces diffusion curves, relationship-graph evolution, coordination-event counts, and ablation comparisons as first-class artifacts.
- A three.js/R3F observer that renders a live or replayed ledger with zero authority over the simulation.

## What POLIS is not

- Not a broadcast product. No TTS, no captions-as-drama, no episode structure. (A stream mode may exist later as a pure observer.)
- Not a game. No win states, no viewer commands.
- Not glasshouse with the director turned off — it is a from-scratch build that reimplements a few proven glasshouse patterns.

## Success criteria (v1)

1. A seeded fact ("there is a gathering at the tavern on day 3") diffuses through the population measurably, producing a diffusion curve from ledger data alone.
2. Same experiment run with retrieval scoring ablated (salience-only) shows a measurable difference — the publishable knob.
3. A full sim-week of 20 agents runs unattended on local hardware with logged-completion replay.

## Glasshouse relationship: reference-only, zero code import

POLIS is built from scratch (decision 2026-07-03): no glasshouse code crosses over, ensuring nothing show-shaped survives by accident. Glasshouse remains a **design reference** for proven patterns that get reimplemented clean:

- Model gateway pattern: validation wall, structured outputs, one repair re-prompt, named hardware profiles.
- P11 perception semantics: sight cone ∧ occlusion ∨ hearing radius.
- Schema/contract discipline (Ajv for contract files, Zod for app logic; pydantic mirrors).
- The byte-equal legacy-replay fixture pattern.

Everything director-, scenario-, broadcast-, or viewer-shaped is not referenced at all.
