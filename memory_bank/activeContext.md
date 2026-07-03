# Active Context

Updated: 2026-07-03

## Current state

Project inception. Memory Bank drafted; MASTER_PLAN.md drafted with phases P0–P6. No code exists.

## Current focus

Founding decisions ratified 2026-07-03: logged-completion replay with per-model/per-role sampling config; Python sim; **from scratch — zero glasshouse code import** (patterns reimplemented from spec); Mnemosyne = inference server, sim runs on a Mac; metrics-before-agents confirmed.

Town fork closed 2026-07-03: **generate once, freeze as static content.** v1 content exists and validates — Harrowmere (16 locations, 48×48 grid, 2 occluders) + 20 agent seeds + 32-edge relationship list, all in `content/`, guarded by `scripts/validate_content.py`. Awaiting Christian's rejection pass on the content itself (names, tone, tension seeds).

Open fork still awaiting a call:

1. **tp split on Mnemosyne:** two single-GPU models (fast+slow) vs. tp=2 one larger model. Measure in P2; default to the split.

## Immediate next action

Content rejection pass (Christian), then P0 bootstrap: repo scaffold on a Mac, uv project, schemas v0 (town_spec + agent_seed schemas formalized from the existing content), Postgres schema on Nyx, fresh model-gateway implementation smoke-tested against Mnemosyne serving profiles.
