# Active Context

Updated: 2026-07-03 (evening — live hardware session)

## Current state

**P0 is fully closed.** Development moved to Theseus (real computer): live LLM serving and a local Postgres are available. The remote-only standing constraint is lifted.

- **Serving:** metis + athena (LM Studio-class OpenAI-compatible, :1240 over Tailscale; endpoints in untracked `.env`), both serving qwen3.6-35b-a3b-mtp (thinking model) for both tiers + nomic-embed-text-v1.5 (768-dim). Profiles `metis`/`athena` in `services/serving/profiles.yaml`; mnemosyne yaml is historical.
- **Database:** local Postgres 14 + pgvector 0.8.0; `polis` (runs) + `polis_test` (suite) created, DDL applied; pg integration tests run live (no skips).
- **Gateway smoked live** and hardened for thinking models: request_extras (`enable_thinking: false`, best-effort — measured ignored), reasoning_content salvage on structured calls (metis grammar shunt: ~35 tok/call, effectively no-think), empty-content = typed failure, role budgets ≥1024. See decisionLog "Thinking-model serving facts".
- **Structured outputs on every call** (user directive): dialogue turns (`{"utterance"}`) and probe interviews (`{"answer"}`) got schemas — no freeform calls remain.
- **HTTPEmbedder** wired via profile `embedding:` block (asymmetric nomic prefixes; `embed_query` on the protocol; HashEmbedder aliases it prefix-free so fixtures hold).
- **First live cognition smoke** (2 Alder agents, morning, `--profile metis`): 29 completions, 0 gateway failures, real daily plans, 12 object uses, and a real 4-turn conversation at the Gilded Perch. HashEmbedder/fake-model/DeterministicJudge remain the offline stand-ins; runs using them stay non-conforming.

Suite: 140 tests green (pg integration live).

## P2 gate met LIVE (2026-07-03, same day)

`runs/p2_gate_live_metis_seed42` (local, gitignored): 5 agents, full day on metis — **1221 completions, 0 gateway failures, replay byte-equal from the completion log**. Coherent contextual dialogue (agents reference shared history across conversations hours apart). ~25 min wall, ~1.15 s/call, 264k prompt / 79k completion tokens → 20-agent sim-week soak ≈ 34k calls ≈ ~11 h (overnight job).

Live-day findings (pre-soak fix list):

- **27 intent rejections, two grounding gaps**: (a) real-model decompositions don't reliably lead `use_object` with a `move_to` (Sela used bakery objects from elsewhere, 19×); (b) agendas name hallucinated locations (`market_district`, `marketplace`, `supply_shop`). Fix at the schema layer: build response schemas dynamically at call time — location enum from the town spec in AGENDA_SCHEMA, object-id enum from the block's location in STEPS_SCHEMA. Grammar-constrained decoding then makes invalid grounding unrepresentable.
- **Real-model importance runs hot** vs the fake tiers → reflection trigger fired 168× in a day. Thresholds are experiment config by design; calibrate during soak and freeze into the config hash.
- **Era anachronism** in dialogue ("no phones") — prompt/bio era grounding; folds into Christian's content rejection pass.
- **Crossing-request conversation bug** (diagnosed from the started/ended imbalance): when requests cross in one tick (ilse→piet, maren→piet, piet→ilse at tick 7200), the world starts two conversations sharing one agent; the loser (piet↔maren) never gets a turn and is dropped with **no conversation_ended event** — a half-attached conversation dies without a ledger trace. Sleep wind-down itself emits correctly (runtime.py:385). Fix in the request/accept/attach path + deterministic regression test (two agents requesting the same partner in one tick).

## Open forks

1. **Judge model** (believability, offline): pick a different family from the sim model — minimax-m3, deepseek-v4-flash, gemma-4-26b are on the shelf. Decide at judge time with a rubric.
2. **Reasoning-on vs reasoning-off as a P6 ablation knob**: user confirms metis/athena are identical servers, so the shunt difference is version drift, not a hardware choice — the surviving question is whether thinking-enabled (freeform-style) calls versus grammar-suppressed calls change agent behavior enough to be a controlled condition.

## Immediate next action

Decision (user, 2026-07-03): **proceed to P5 — the north star path.** Order:

1. Dynamic schema enums (the grounding fix above) — small, high-leverage, pre-soak.
2. DB wiring completion: memory_records / completions / probes Postgres inserts alongside the ledger sink (soak runs should persist queryably).
3. Soak: 20 agents, full sim-week, unattended overnight; fix what breaks; calibrate thresholds.
4. Seeded-fact diffusion experiment across ≥8 seeds.

P4 observer stays parallel/deferred — not on the diffusion-curve path.

Still with Christian:

- Content rejection pass (names, tone, tension seeds, 90 objects + affordances) — still pending.
- Aletheia bundle rsync target (when P5 runs start producing bundles).
