# Active Context

Updated: 2026-07-03

## Current state

Project inception. Memory Bank drafted; MASTER_PLAN.md drafted with phases P0–P6. No code exists.

## Current focus

Founding decisions ratified 2026-07-03: logged-completion replay with per-model/per-role sampling config; Python sim; **from scratch — zero glasshouse code import** (patterns reimplemented from spec); Mnemosyne = inference server, sim runs on a Mac; metrics-before-agents confirmed.

Open forks still awaiting a call:

1. **Town content source:** hand-authored village layout + 20 agent seeds (Park used 25 hand-authored agents) vs. procedural generation. Recommendation: hand-author v1 — content variance is noise until the instrument works.
2. **tp split on Mnemosyne:** two single-GPU models (fast+slow) vs. tp=2 one larger model. Measure in P2; default to the split.

## Immediate next action

P0 bootstrap: repo scaffold on a Mac, uv project, schemas v0, Postgres schema on Nyx, fresh model-gateway implementation smoke-tested against Mnemosyne serving profiles.
