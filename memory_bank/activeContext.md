# Active Context

Updated: 2026-07-03

## Current state

Project inception. Memory Bank drafted; MASTER_PLAN.md drafted with phases P0–P6. No code exists.

## Current focus

Review and rejection pass on the Memory Bank + plan (Christian). Open forks awaiting a call:

1. **Town content source:** hand-authored village layout + 20 agent seeds (Park used 25 hand-authored agents) vs. procedural generation. Recommendation: hand-author v1 — content variance is noise until the instrument works.
2. **Sim host:** Nyx vs. Mnemosyne CPU-side. Recommendation: Mnemosyne, colocated with serving, one less network hop on the hot path.
3. **tp split on Mnemosyne:** two single-GPU models (fast+slow) vs. tp=2 one larger model. Measure in P2; default to the split.

## Immediate next action

P0 bootstrap after plan approval: repo scaffold, schemas, uv project, Postgres schema on Nyx, salvage import of agent_model_service.
