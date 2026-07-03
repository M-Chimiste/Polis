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

## Open forks

1. **Judge model** (believability, offline): pick a different family from the sim model — minimax-m3, deepseek-v4-flash, gemma-4-26b are available on the shelf. Decide at judge time with a rubric.
2. **metis vs athena cost/behavior**: metis's grammar path skips thinking on structured calls (~30× cheaper); athena reasons fully. Measure both on the same run shape (telemetry is ready) and decide the default profile — and whether reasoning-on is itself an ablation condition.

## Immediate next action

1. **P2 gate re-run live**: the full 5-agent unscripted day via `python -m cognition.runner --ticks 8640 --agents <five> --profile metis --out-dir ...` — watch latency, failures, believability of plans/dialogue. This is the remaining P2 gate check.
2. DB wiring completion: memory_records / completions / probes Postgres inserts alongside the ledger sink.
3. Then the P5 path: multi-day soak, seed-sweep diffusion harness — or P4 observer in parallel.

Still with Christian:

- Content rejection pass (names, tone, tension seeds, 90 objects + affordances) — still pending.
- Aletheia bundle rsync target (when P5 runs start producing bundles).
