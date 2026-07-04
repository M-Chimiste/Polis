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

- **Contracts**: every incoming event is Ajv-validated against
  `schemas/json/ledger_event.schema.json` — the same source of truth the
  Python side mirrors. A bad event throws; the observer never renders around
  a broken ledger.
- **The replay fold** (`src/ledger.ts`): world-state-at-tick-T is a pure
  fold of the event prefix. The scrubber is just a cursor over that fold —
  the same reproducibility property as the byte-equal wall upstream.
- **Scene** (`src/scene/`): Harrowmere as simple geometry from
  `content/town.json` (no art pipeline, deliberately); agents as labeled
  spheres, colored by status, highlighted while conversing; click → inspector.

## Still to come (MASTER_PLAN P4)

- Memory/plan inspector (needs `memories.jsonl` loading alongside the ledger)
- Diffusion overlay (seeded-fact holders colored, from bundle probes)
- Relationship-thread view
