/** Fluid playback is a PRESENTATION of the ledger: track sampling must walk
 * exactly the recorded path, and the incremental fold must equal a fresh
 * fold at every tick (or the playhead lies). */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { emptyWorld, foldTo, parseLedger, worldAt } from "./ledger";
import { buildTracks, sample } from "./tracks";

const FIXTURE = fileURLToPath(new URL(
  "../../tests/fixtures/ledger_scripted_seed42_3000.jsonl", import.meta.url));
const events = parseLedger(readFileSync(FIXTURE, "utf-8"));

describe("track sampling", () => {
  const track = [
    { tick: 0, pos: [2, 2] as [number, number] },
    { tick: 10, pos: [2, 2] as [number, number] },  // stood still, then
    { tick: 11, pos: [3, 2] as [number, number] },  // one step east
    { tick: 12, pos: [3, 3] as [number, number] },  // one step south
  ];

  it("clamps before the first and after the last keyframe", () => {
    expect(sample(track, -5).pos).toEqual([2, 2]);
    expect(sample(track, 99).pos).toEqual([3, 3]);
    expect(sample(track, 99).moving).toBe(false);
  });

  it("interpolates the walking segment, not the stationary gap", () => {
    expect(sample(track, 5).pos).toEqual([2, 2]);       // standing
    expect(sample(track, 5).moving).toBe(false);
    const mid = sample(track, 10.5);                     // mid-step east
    expect(mid.pos[0]).toBeCloseTo(2.5);
    expect(mid.moving).toBe(true);
    expect(mid.heading).toEqual([1, 0]);
  });

  it("turns the corner with the path", () => {
    const south = sample(track, 11.5);
    expect(south.pos[0]).toBeCloseTo(3);
    expect(south.pos[1]).toBeCloseTo(2.5);
    expect(south.heading).toEqual([0, 1]);
  });

  it("builds tracks for all 20 agents from the real fixture", () => {
    const tracks = buildTracks(events);
    expect(Object.keys(tracks)).toHaveLength(20);
    // commuters have more than an initial keyframe
    expect(Math.max(...Object.values(tracks).map((t) => t.length)))
      .toBeGreaterThan(10);
  });
});

describe("incremental fold parity", () => {
  it("forward foldTo equals a fresh worldAt at every step", () => {
    const world = emptyWorld();
    let index = 0;
    for (const tick of [0, 100, 750, 1500, 2999]) {
      index = foldTo(events, tick, world, index);
      expect(world).toEqual(worldAt(events, tick));
    }
  });
});
