# Tech Context

## Stack

- **Sim core:** Python 3.12, single authoritative process. Discrete tick (default 1 tick = 10 sim-seconds), pure-function world step where possible. asyncio for cognition dispatch. Not FastAPI — the sim is a process, not a service; a thin FastAPI sidecar exposes the live ledger stream (WebSocket) and control endpoints (start/stop/checkpoint).
- **Why Python, not Rust/Bevy:** the sim tick is trivial (grid pathfinding, proximity, object state for ≤25 agents); the bottleneck is LLM latency. Python keeps the cognition stack, measurement harness, and TheseusInsight tooling in one language. Vivarium keeps the Rust/wgpu ambitions; POLIS does not need them.
- **Cognition serving:** vLLM on Mnemosyne via the existing containerized vLLM manager proxy. Batched, continuous batching is the whole point — reflection and planning calls are throughput workloads.
- **Embeddings:** small embedder served on Nyx or in-process (sentence-transformers class); pgvector for retrieval.
- **Persistence:** Postgres + pgvector on Nyx. Schema: runs, agents, memory_records (with embedding), plans, ledger_events, completions (verbatim request+response for replay), probes, metrics.
- **Observer:** TypeScript + Vite + React + three.js/R3F + Zustand (glasshouse conventions), reading the WebSocket ledger stream or exported ledger JSON. Zero authority.
- **Schemas:** JSON Schema as source of truth (Ajv-validated on TS side, pydantic-generated on Python side). Never invent shapes schemas already define.
- **Tests:** pytest for sim/cognition/metrics; vitest for observer.

## Hardware allocation

| Node | Role |
|---|---|
| Mnemosyne (2× RTX PRO 6000 Blackwell) | vLLM serving: fast tier tp=1 on GPU0, slow tier tp=1 on GPU1 (or tp=2 for a single larger model — measure both). SLURM arbitration already in place. |
| Nyx (Mac mini) | Postgres + pgvector, embedder, sim process (or sim on Mnemosyne CPU — Threadripper is fine), metrics jobs |
| Athena/Metis (M3 Ultra) | Overflow/alternate serving profile (MLX) — the agent_model_service dual-hardware profiles carry over |
| Aletheia | Run archive: completion logs + ledgers per experiment |

Networking: Tailscale, as everywhere.

## Model tiers (initial; all swappable via config)

- **Fast tier** (dialogue turns, importance scoring, action selection within plan): Qwen3-class 8B, structured outputs, high concurrency.
- **Slow tier** (reflection synthesis, daily planning, plan decomposition): 32–70B class, batched, low priority. Reasoning budget capped server-side at vLLM launch (the glasshouse qwen3.6 lesson: request-level enable_thinking may be ignored; cap at the server).
- **Judge tier** (offline, believability probes): whatever TheseusInsight currently uses; not on the hot path.

## Determinism & replay (decided)

Sampling is allowed (temperature > 0) — behavioral diversity is the point. Determinism is achieved by **logged-completion replay**: every completion is persisted keyed by (run_id, agent_id, call_site, sequence); replay mode serves completions from the log instead of the model, making any run byte-reproducible after the fact. Sim-side randomness uses a seeded PRNG stream per subsystem. Byte-equal ledger fixtures (glasshouse's permanent-wall pattern) guard the sim core.

## Dev environment

Repo on Mnemosyne (Ubuntu stack already configured: Docker, uv, miniforge). uv-managed Python. Observer dev via Vite as usual.
