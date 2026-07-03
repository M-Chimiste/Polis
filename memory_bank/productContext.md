# Product Context

## Who this is for

Christian, as researcher. Secondary: the open-source/research community if results warrant a writeup (TheseusInsight pipeline is the natural publication path). Twitch is a possible *distribution* channel for replays, never an input.

## Research questions (ordered)

1. **Information diffusion.** Does a fact seeded in one agent propagate through the population via unscripted conversation, and what does the diffusion curve look like as a function of retrieval architecture, model size, and perception constraints?
2. **Relationship formation.** Do stable relationship structures (dyads, cliques) emerge from repeated interaction, and are they measurable from the ledger without human labeling?
3. **Unprompted coordination.** Do agents converge on shared activities (gatherings, routines, division of labor) without any injected pressure?
4. **Architecture ablations.** Which cognition components are load-bearing? Candidate knobs: retrieval scoring (full R×I×R vs. recency-only vs. salience+tag), reflection on/off, plan-interrupt threshold, model size per tier.
5. **Belief divergence.** Under information asymmetry, do agents form conflicting world models, and do those conflicts resolve, persist, or propagate?

## Primary metrics (decided before agents exist)

- **Diffusion curve:** % of population holding a seeded fact vs. sim-time; measured by periodic probe queries against each agent's memory (probe results logged, never fed back into cognition).
- **Relationship graph:** interaction-weighted graph snapshot per sim-hour; track density, clustering coefficient, community stability.
- **Coordination events:** ≥3 agents co-located + convergent stated intent within a window, detected by a ledger post-processor (no in-sim labeling).
- **Believability spot checks:** Park-style interview probes (self-knowledge, memory, plans, reactions) run against frozen agent states, scored by LLM-as-judge (TheseusInsight rubric infrastructure reused).
- **Cost telemetry:** tokens and wall-time per agent per sim-hour, per cognition tier — sustainability is a result, not an afterthought.

## Experiment protocol

Every run is an experiment record: config hash, seed, model manifest, completion log, ledger, metric outputs. Runs are compared, not watched. Statistical replication across ≥8 seeds per condition is the default; single anecdotal runs prove nothing.

## Viewing experience (deliberately minimal)

The observer renders the ledger: top-down or orbital town view, agent positions, current action labels, conversation transcripts on click, memory/plan inspector per agent, diffusion overlay (who holds the seeded fact, colored live). Replay scrubbing over exported ledgers. Nothing in the observer can write to the sim.
