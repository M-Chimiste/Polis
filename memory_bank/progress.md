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
