# Observer (P4 — scaffolded 2026-07-03)

Zero-authority ledger viewer: Vite + React + R3F + Zustand. Reads either an
exported `ledger.jsonl` (drag-and-drop onto the canvas) or the live
WebSocket sidecar (`?ws=ws://host:8010/ws/ledger`). It can never write back
into the sim.

```bash
pnpm install
pnpm dev        # http://localhost:5173
pnpm test       # vitest — validates against the shared JSON Schemas and the
                # real P1 byte-equal fixture
pnpm build
```

## How it works

- **Contracts**: every incoming event and memory record is Ajv-validated
  against `schemas/json/*.schema.json` — the same source of truth the
  Python side mirrors. A bad record throws; the observer never renders
  around a broken ledger.
- **The replay fold** (`src/ledger.ts`): world-state-at-tick-T is a pure
  fold of the event prefix. The scrubber is just a cursor over that fold —
  the same reproducibility property as the byte-equal wall upstream.
- **Minds** (`src/memories.ts`): drop `memories.jsonl` too and clicking an
  agent shows their memory stream as of the cursor (observations, plans,
  reflections, conversation summaries — importance and all).
- **Diffusion overlay**: the seeded fact is read from the ledger's
  `treatment_injected` event; holders get a red halo, computed by the same
  STOPWORDS + 60%-token-overlap rule as `metrics/probes.py` (parity-tested),
  live as you scrub. Watch the fact spread through the town.
- **Relationship threads** (`src/scene/Threads.tsx`): a line per agent pair,
  weighted by accumulated conversation up to the cursor; currently-talking
  pairs glow amber.
- **Day/night**: lighting is a pure function of sim time — the sun rises at
  06:00, sets at 18:00, and scrubbing to dawn always gives you dawn.
- **Scene**: Harrowmere as simple geometry from `content/town.json` (no art
  pipeline, deliberately); occluders rendered; agents as status-colored
  labeled spheres with smoothed movement.

Demo data: `runs/demo_treated_fake/` (fake-model treated day, non-conforming)
— drop its `ledger.jsonl` + `memories.jsonl` in and scrub past 06:40 to watch
the seeded fact reach the Alder household.

## Still to come (MASTER_PLAN P4)

- Live gate check (sidecar up, human eyes on a real run)
