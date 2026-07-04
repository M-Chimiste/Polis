/**
 * Position tracks: each agent's movement history as a sampled curve.
 *
 * The sim is tick-quantized (that's the instrument); fluid motion is a
 * PRESENTATION of the ledger, not new physics. Every agent_moved event is a
 * keyframe; sampling at a float playhead walks the agent along the exact A*
 * path the sim computed, at the exact pace it happened.
 */
import { LedgerEvent } from "./ledger";

export interface Keyframe {
  tick: number;
  pos: [number, number];
}

export type Track = Keyframe[];

export interface Sample {
  pos: [number, number];
  /** unit heading while moving, null at rest */
  heading: [number, number] | null;
  moving: boolean;
}

export function buildTracks(events: LedgerEvent[]): Record<string, Track> {
  const tracks: Record<string, Track> = {};
  for (const event of events) appendToTracks(tracks, event);
  return tracks;
}

/** Incremental variant for live streams. */
export function appendToTracks(
  tracks: Record<string, Track>, event: LedgerEvent,
): void {
  if (event.kind === "agent_initialized") {
    tracks[event.agent_id!] = [
      { tick: event.tick, pos: event.data.pos as [number, number] },
    ];
  } else if (event.kind === "agent_moved") {
    tracks[event.agent_id!]?.push(
      { tick: event.tick, pos: event.data.to as [number, number] });
  }
}

/** Interpolated position at a float playhead. A keyframe at tick T means
 * "arrived at T": between T-1 and T the agent walks the segment. */
export function sample(track: Track, playhead: number): Sample {
  if (track.length === 0) return { pos: [0, 0], heading: null, moving: false };
  if (playhead <= track[0].tick) {
    return { pos: track[0].pos, heading: null, moving: false };
  }
  const last = track[track.length - 1];
  if (playhead >= last.tick) return { pos: last.pos, heading: null, moving: false };

  // binary search: greatest keyframe with tick <= playhead
  let lo = 0, hi = track.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (track[mid].tick <= playhead) lo = mid;
    else hi = mid - 1;
  }
  const a = track[lo];
  const b = track[lo + 1];
  const span = b.tick - a.tick;
  // only interpolate contiguous steps; after a stationary gap the agent
  // stands at `a` until one tick before `b`, then walks the last segment
  const start = Math.max(a.tick, b.tick - 1);
  if (playhead < start) return { pos: a.pos, heading: null, moving: false };
  const t = span === 0 ? 1 : (playhead - start) / (b.tick - start);
  const dx = b.pos[0] - a.pos[0];
  const dy = b.pos[1] - a.pos[1];
  const len = Math.hypot(dx, dy) || 1;
  return {
    pos: [a.pos[0] + dx * t, a.pos[1] + dy * t],
    heading: [dx / len, dy / len],
    moving: true,
  };
}
