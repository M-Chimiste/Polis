/** Playback bar: fluid time. Slider seeks, play flows at the chosen speed,
 * live mode trails the stream head; follow toggles the ride-along camera. */
import { SPEEDS, useObserver } from "../store";

function clock(playhead: number): string {
  const simSeconds = playhead * 10;
  const day = Math.floor(simSeconds / 86400);
  const minute = Math.floor(simSeconds / 60) % (24 * 60);
  const h = String(Math.floor(minute / 60)).padStart(2, "0");
  const m = String(minute % 60).padStart(2, "0");
  return `day ${day} ${h}:${m}`;
}

function speedLabel(speed: number): string {
  const simPerWall = speed * 10; // sim-seconds per wall-second
  return simPerWall >= 60 ? `${Math.round(simPerWall / 60)}m/s` : `${simPerWall}s/s`;
}

export function Scrubber() {
  const { playhead, maxTick, playing, live, speed, selectedAgent, follow,
          seek, setPlaying, setSpeed, setFollow } = useObserver();

  return (
    <div style={{ display: "flex", gap: 10, alignItems: "center", padding: "8px 14px" }}>
      <button onClick={() => setPlaying(!playing)} disabled={live || maxTick === 0}
              style={{ width: 64 }}>
        {playing ? "pause" : "play"}
      </button>
      <span style={{ display: "flex", gap: 2 }}>
        {SPEEDS.map((s) => (
          <button key={s} onClick={() => setSpeed(s)}
                  style={{ opacity: s === speed ? 1 : 0.45, minWidth: 44 }}>
            {speedLabel(s)}
          </button>
        ))}
      </span>
      <input
        type="range"
        min={0}
        max={maxTick}
        step={0.25}
        value={playhead}
        onChange={(e) => seek(Number(e.target.value))}
        style={{ flex: 1 }}
        disabled={maxTick === 0}
      />
      {selectedAgent && (
        <button onClick={() => setFollow(!follow)}
                style={{ background: follow ? "#7aa2f7" : undefined }}>
          {follow ? `following ${selectedAgent.split("_")[0]}` : "follow"}
        </button>
      )}
      <span style={{ minWidth: 150, textAlign: "right" }}>
        {clock(playhead)}{live ? " · LIVE" : ""}
      </span>
    </div>
  );
}
