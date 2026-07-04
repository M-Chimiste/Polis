/** Replay scrubber: slide to any tick; play advances the cursor. */
import { useEffect } from "react";

import { useObserver } from "../store";

function hhmm(tick: number): string {
  const minute = Math.floor((tick * 10) / 60) % (24 * 60);
  const day = Math.floor((tick * 10) / 86400);
  const h = String(Math.floor(minute / 60)).padStart(2, "0");
  const m = String(minute % 60).padStart(2, "0");
  return `day ${day} ${h}:${m}`;
}

const PLAY_TICKS_PER_FRAME = 6; // 1 real second ~ 1 sim-minute at 60fps

export function Scrubber() {
  const { cursor, maxTick, playing, live, scrub, setPlaying } = useObserver();

  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    const step = () => {
      const { cursor: c, maxTick: max } = useObserver.getState();
      if (c >= max) setPlaying(false);
      else scrub(Math.min(c + PLAY_TICKS_PER_FRAME, max));
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [playing, scrub, setPlaying]);

  return (
    <div style={{ display: "flex", gap: 12, alignItems: "center", padding: "8px 16px" }}>
      <button onClick={() => setPlaying(!playing)} disabled={live || maxTick === 0}>
        {playing ? "pause" : "play"}
      </button>
      <input
        type="range"
        min={0}
        max={maxTick}
        value={cursor}
        onChange={(e) => scrub(Number(e.target.value))}
        style={{ flex: 1 }}
        disabled={maxTick === 0}
      />
      <span style={{ minWidth: 140, textAlign: "right" }}>
        {hhmm(cursor)} · t{cursor}{live ? " · LIVE" : ""}
      </span>
    </div>
  );
}
