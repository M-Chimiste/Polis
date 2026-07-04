/** Sim-time-driven lighting: the sun follows the cursor's clock. Pure
 * function of the tick — scrubbing to dawn always gives you dawn. Night is
 * moonlit and readable, never a void; lit windows carry the warmth. */
import { Stars } from "@react-three/drei";
import { useMemo } from "react";
import { Color } from "three";

import { useObserver } from "../store";

export function simHour(tick: number): number {
  return ((tick * 10) / 3600) % 24;
}

/** sun elevation in [-1, 1]: -1 midnight, +1 noon */
export function sunElevation(hour: number): number {
  return Math.sin(((hour - 6) / 12) * Math.PI);
}

const NIGHT_SKY = new Color("#141a2e");
const DAY_SKY = new Color("#7aa5c4");
const DAWN_SKY = new Color("#c4886a");

export function skyColor(hour: number): Color {
  const el = sunElevation(hour);
  if (el <= 0) {
    // deep night, with a hint of dawn/dusk near the horizon crossings
    return NIGHT_SKY.clone().lerp(DAWN_SKY, Math.max(0, 0.35 + el) * 0.6);
  }
  // sunrise -> day -> sunset
  return DAWN_SKY.clone().lerp(DAY_SKY, Math.min(1, el * 1.8));
}

export function DayNight() {
  const cursor = useObserver((s) => s.cursor);
  const hour = simHour(cursor);
  const el = sunElevation(hour);

  const { sky, sunPos, sunIntensity, ambient, moon } = useMemo(() => {
    const angle = ((hour - 6) / 12) * Math.PI; // 06:00 east horizon, 18:00 west
    return {
      sky: skyColor(hour),
      sunPos: [Math.cos(angle) * 60, Math.max(2, Math.sin(angle) * 60), 12] as
        [number, number, number],
      sunIntensity: Math.max(0, el) * 1.35,
      // night floor keeps the town readable: shapes visible, windows do the mood
      ambient: 0.34 + Math.max(0, el) * 0.5,
      moon: 0.42 * Math.max(0.25, -el),
    };
  }, [hour, el]);

  return (
    <>
      <color attach="background" args={[sky]} />
      <fog attach="fog" args={[sky, 70, 190]} />
      {el < 0.08 && <Stars radius={130} depth={40} count={1600} factor={3}
                           saturation={0} fade speed={0.4} />}
      <ambientLight intensity={ambient} color={el > 0 ? "#fff6e8" : "#b8c4e8"} />
      <directionalLight position={sunPos} intensity={sunIntensity} color="#ffe9c4" />
      <directionalLight position={[-24, 34, -14]} intensity={moon} color="#93a4d6" />
    </>
  );
}
