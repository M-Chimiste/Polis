/** The observer's contract with the ledger, tested against the REAL P1
 * byte-equal fixture — if the wall moves, this breaks loudly here too. */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { parseLedger, worldAt } from "./ledger";

const FIXTURE = fileURLToPath(new URL(
  "../../tests/fixtures/ledger_scripted_seed42_3000.jsonl", import.meta.url));
const events = parseLedger(readFileSync(FIXTURE, "utf-8"));

describe("parseLedger", () => {
  it("validates every fixture event against the shared JSON Schema", () => {
    expect(events.length).toBeGreaterThan(100);
    expect(events[0].kind).toBe("run_started");
    expect(events[events.length - 1].kind).toBe("run_finished");
  });

  it("rejects an event that violates the contract", () => {
    expect(() => parseLedger('{"seq": 0, "kind": "run_started"}')).toThrow(/invalid/);
  });
});

describe("worldAt (the replay fold)", () => {
  it("initializes all 20 agents at tick 0", () => {
    const world = worldAt(events, 0);
    expect(Object.keys(world.agents)).toHaveLength(20);
    for (const agent of Object.values(world.agents)) {
      expect(agent.pos).toHaveLength(2);
      expect(agent.status).toBeTruthy();
    }
  });

  it("is a pure function of the prefix: same tick, same world", () => {
    const a = worldAt(events, 1500);
    const b = worldAt(events, 1500);
    expect(a).toEqual(b);
  });

  it("moves agents over the day (commuters actually commute)", () => {
    const dawn = worldAt(events, 0);
    const noon = worldAt(events, 2999);
    const moved = Object.keys(dawn.agents).filter((id) => {
      const [x0, y0] = dawn.agents[id].pos;
      const [x1, y1] = noon.agents[id].pos;
      return x0 !== x1 || y0 !== y1;
    });
    expect(moved.length).toBeGreaterThan(0);
  });

  it("scrubbing backward reaches an earlier consistent state", () => {
    const late = worldAt(events, 2999);
    const early = worldAt(events, 10);
    expect(early.tick).toBe(10);
    expect(Object.keys(early.agents)).toEqual(Object.keys(late.agents));
  });
});
