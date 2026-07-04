/** Zustand store: loaded ledger + memories, a FLOAT playhead driven by wall
 * clock, incremental world folding, follow-cam state. All read-only with
 * respect to the sim — zero authority by construction. */
import { create } from "zustand";

import {
  LedgerEvent, WorldView, emptyWorld, foldTo, treatmentFact, worldAt,
} from "./ledger";
import { MemoryRecord, byAgent } from "./memories";
import { Track, appendToTracks, buildTracks } from "./tracks";

/** playback speeds in ticks per wall second (1 tick = 10 sim-seconds);
 * 6 t/s = one sim-minute per second */
export const SPEEDS = [2, 6, 24, 96, 384];

interface ObserverState {
  events: LedgerEvent[];
  memories: Record<string, MemoryRecord[]>;
  tracks: Record<string, Track>;
  fact: string | null;
  playhead: number; // float ticks
  maxTick: number;
  world: WorldView; // folded at floor(playhead)
  foldIndex: number; // next event index to apply
  playing: boolean;
  speed: number; // ticks per wall second
  live: boolean;
  selectedAgent: string | null;
  follow: boolean;

  loadEvents(events: LedgerEvent[]): void;
  loadMemories(records: MemoryRecord[]): void;
  appendLive(event: LedgerEvent): void;
  seek(playhead: number): void;
  advance(dt: number): void; // wall-clock frame driver
  setPlaying(playing: boolean): void;
  setSpeed(speed: number): void;
  selectAgent(id: string | null): void;
  setFollow(follow: boolean): void;
}

export const useObserver = create<ObserverState>((set, get) => ({
  events: [],
  memories: {},
  tracks: {},
  fact: null,
  playhead: 0,
  maxTick: 0,
  world: emptyWorld(),
  foldIndex: 0,
  playing: false,
  speed: SPEEDS[1],
  live: false,
  selectedAgent: null,
  follow: false,

  loadEvents(events) {
    const maxTick = events.length ? events[events.length - 1].tick : 0;
    const world = emptyWorld();
    const foldIndex = foldTo(events, 0, world);
    set({
      events, maxTick, playhead: 0, live: false, playing: false,
      fact: treatmentFact(events),
      tracks: buildTracks(events),
      world: { ...world }, foldIndex,
    });
  },

  loadMemories(records) {
    set({ memories: byAgent(records) });
  },

  appendLive(event) {
    const state = get();
    state.events.push(event);
    appendToTracks(state.tracks, event);
    set({
      live: true, playing: true, maxTick: event.tick,
      fact: state.fact ?? (event.kind === "treatment_injected"
        ? (event.data.fact as string) : null),
    });
  },

  seek(playhead) {
    const state = get();
    const clamped = Math.max(0, Math.min(playhead, state.maxTick));
    const tick = Math.floor(clamped);
    if (tick >= state.world.tick) {
      const foldIndex = foldTo(state.events, tick, state.world, state.foldIndex);
      set({ playhead: clamped, world: { ...state.world }, foldIndex, live: false });
    } else {
      // backward: refold from scratch (user-initiated, O(prefix) is fine)
      const world = worldAt(state.events, tick);
      const foldIndex = state.events.findIndex((e) => e.tick > tick);
      set({
        playhead: clamped, world,
        foldIndex: foldIndex === -1 ? state.events.length : foldIndex,
        live: false,
      });
    }
  },

  advance(dt) {
    const state = get();
    if (state.live) {
      // trail the head by a tick so interpolation always has both endpoints;
      // stalls while the model thinks are honest — the town is thinking
      const target = Math.max(0, state.maxTick - 1);
      const next = Math.min(target, state.playhead + dt * Math.max(state.speed, 24));
      if (next === state.playhead) return;
      const tick = Math.floor(next);
      const foldIndex = foldTo(state.events, tick, state.world, state.foldIndex);
      set({ playhead: next, world: { ...state.world }, foldIndex });
      return;
    }
    if (!state.playing) return;
    const next = state.playhead + dt * state.speed;
    if (next >= state.maxTick) {
      const foldIndex = foldTo(state.events, state.maxTick, state.world, state.foldIndex);
      set({ playhead: state.maxTick, world: { ...state.world }, foldIndex,
            playing: false });
      return;
    }
    const tick = Math.floor(next);
    const foldIndex = tick >= state.world.tick
      ? foldTo(state.events, tick, state.world, state.foldIndex)
      : state.foldIndex;
    set({ playhead: next, world: { ...state.world }, foldIndex });
  },

  setPlaying(playing) {
    set({ playing });
  },

  setSpeed(speed) {
    set({ speed });
  },

  selectAgent(id) {
    set({ selectedAgent: id, follow: id === null ? false : get().follow });
  },

  setFollow(follow) {
    set({ follow });
  },
}));
