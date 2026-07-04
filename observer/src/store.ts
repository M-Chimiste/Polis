/** Zustand store: loaded ledger + memories, scrub cursor, live-stream state.
 * All read-only with respect to the sim — zero authority by construction. */
import { create } from "zustand";

import {
  LedgerEvent, WorldView, applyEvent, emptyWorld, treatmentFact, worldAt,
} from "./ledger";
import { MemoryRecord, byAgent } from "./memories";

interface ObserverState {
  events: LedgerEvent[];
  memories: Record<string, MemoryRecord[]>;
  fact: string | null; // seeded fact from treatment_injected, if any
  cursor: number; // tick
  maxTick: number;
  world: WorldView;
  playing: boolean;
  live: boolean;
  selectedAgent: string | null;

  loadEvents(events: LedgerEvent[]): void;
  loadMemories(records: MemoryRecord[]): void;
  appendLive(event: LedgerEvent): void;
  scrub(tick: number): void;
  setPlaying(playing: boolean): void;
  selectAgent(id: string | null): void;
}

export const useObserver = create<ObserverState>((set, get) => ({
  events: [],
  memories: {},
  fact: null,
  cursor: 0,
  maxTick: 0,
  world: emptyWorld(),
  playing: false,
  live: false,
  selectedAgent: null,

  loadEvents(events) {
    const maxTick = events.length ? events[events.length - 1].tick : 0;
    set({
      events, maxTick, cursor: maxTick, live: false, playing: false,
      fact: treatmentFact(events),
      world: worldAt(events, maxTick),
    });
  },

  loadMemories(records) {
    set({ memories: byAgent(records) });
  },

  appendLive(event) {
    // incremental fold at the head — no O(n^2) refold on a live stream
    const state = get();
    state.events.push(event);
    const world = applyEvent(state.world, event);
    set({
      events: state.events, live: true, maxTick: event.tick, cursor: event.tick,
      fact: state.fact ?? (event.kind === "treatment_injected"
        ? (event.data.fact as string) : null),
      world: { ...world },
    });
  },

  scrub(tick) {
    set({ cursor: tick, live: false, world: worldAt(get().events, tick) });
  },

  setPlaying(playing) {
    set({ playing });
  },

  selectAgent(id) {
    set({ selectedAgent: id });
  },
}));
