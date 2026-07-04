/** Zustand store: loaded ledger, scrub cursor, live-stream state.
 * All read-only with respect to the sim — zero authority by construction. */
import { create } from "zustand";

import { LedgerEvent, WorldView, emptyWorld, worldAt } from "./ledger";

interface ObserverState {
  events: LedgerEvent[];
  cursor: number; // tick
  maxTick: number;
  world: WorldView;
  playing: boolean;
  live: boolean;
  selectedAgent: string | null;

  loadEvents(events: LedgerEvent[]): void;
  appendLive(event: LedgerEvent): void;
  scrub(tick: number): void;
  setPlaying(playing: boolean): void;
  selectAgent(id: string | null): void;
}

export const useObserver = create<ObserverState>((set, get) => ({
  events: [],
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
      world: worldAt(events, maxTick),
    });
  },

  appendLive(event) {
    const events = [...get().events, event];
    set({
      events, live: true, maxTick: event.tick, cursor: event.tick,
      world: worldAt(events, event.tick),
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
