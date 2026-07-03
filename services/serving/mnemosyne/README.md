# Mnemosyne vLLM serving profiles (record of intent — pending smoke test)

Mnemosyne (2× RTX PRO 6000 Blackwell) is the **inference server, exclusively**;
the sim runs on a Mac and reaches it over Tailscale through the existing
containerized vLLM manager proxy. SLURM arbitration is already in place.

Default split (the open tp fork, measured in P2): fast tier tp=1 on GPU0,
slow tier tp=1 on GPU1. The alternative — tp=2 for one larger model — gets
measured against it and the result recorded in decisionLog.

Reasoning budget is capped **at vLLM launch**, not per-request: the
glasshouse qwen3.6 lesson is that request-level `enable_thinking` may be
ignored, so the cap lives server-side.

- `fast_tier.yaml` — 8B class, GPU0: dialogue turns, importance scoring,
  action selection. Continuous batching, high concurrency.
- `slow_tier.yaml` — 32B class, GPU1: reflection synthesis, daily planning,
  plan decomposition. Batched, low priority.

These files are the in-repo record required by P0. Exact launch flags get
reconciled with the vLLM manager's config format during the smoke test, and
any drift recorded here.
