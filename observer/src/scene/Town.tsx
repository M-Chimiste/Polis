/** Harrowmere in simple-but-warm geometry — still no art pipeline, just
 * kind-aware volumes, roofs, grounds, and windows that light up where the
 * ledger says someone is awake. All scatter is hash-seeded (deterministic —
 * the same town every load, in the project spirit). */
import { Text } from "@react-three/drei";
import { useMemo } from "react";
import { CanvasTexture, Color, NearestFilter, RepeatWrapping } from "three";

import town from "../../../content/town.json";
import { useObserver } from "../store";
import { simHour, sunElevation } from "./DayNight";

interface Location {
  id: string;
  name: string;
  kind: string;
  rect: [number, number, number, number];
  door: [number, number];
}

interface Occluder {
  id: string;
  at: [number, number];
  radius: number;
}

export const GRID = { w: town.grid.width, h: town.grid.height };

export function cell(x: number, y: number): [number, number] {
  return [x - GRID.w / 2, y - GRID.h / 2];
}

/** deterministic [0,1) from a string — scatter without Math.random */
export function hash01(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 10000) / 10000;
}

const STYLE: Record<string, { wall: string; roof: string; height: number }> = {
  home: { wall: "#8a7355", roof: "#5d4a37", height: 1.5 },
  shop_home: { wall: "#9a7f5c", roof: "#634e38", height: 1.8 },
  tavern: { wall: "#8f6b4a", roof: "#4f3b2b", height: 2.1 },
  chapel: { wall: "#a49e8d", roof: "#6a6355", height: 2.6 },
  mill: { wall: "#93785a", roof: "#59452f", height: 2.3 },
  farm: { wall: "#8a7355", roof: "#5d4a37", height: 1.6 },
};

function jitter(color: string, id: string): Color {
  return new Color(color).multiplyScalar(0.92 + hash01(id) * 0.16);
}

function grassTexture(): CanvasTexture {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const t = hash01(`g${x},${y}`);
      const g = 44 + t * 14;
      ctx.fillStyle = `rgb(${g * 0.55}, ${g}, ${g * 0.5})`;
      ctx.fillRect(x, y, 1, 1);
    }
  }
  const texture = new CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = RepeatWrapping;
  texture.repeat.set(6, 6);
  texture.magFilter = NearestFilter;
  return texture;
}

function Tree({ x, z, scale = 1, id }: { x: number; z: number; scale?: number; id: string }) {
  const lean = (hash01(id) - 0.5) * 0.2;
  return (
    <group position={[x, 0, z]} rotation={[0, hash01(id + "r") * Math.PI, lean]}>
      <mesh position={[0, 0.5 * scale, 0]}>
        <cylinderGeometry args={[0.09 * scale, 0.14 * scale, 1.0 * scale, 6]} />
        <meshStandardMaterial color="#4f3a28" />
      </mesh>
      <mesh position={[0, 1.15 * scale, 0]}>
        <coneGeometry args={[0.55 * scale, 1.2 * scale, 7]} />
        <meshStandardMaterial color={jitter("#3d5a33", id)} />
      </mesh>
    </group>
  );
}

function Building({ loc, lit, night }: { loc: Location; lit: boolean; night: boolean }) {
  const [x, y, w, h] = loc.rect;
  const style = STYLE[loc.kind] ?? STYLE.home;
  const [cx, cz] = cell(x + w / 2, y + h / 2);
  const [dx, dz] = cell(loc.door[0] + 0.5, loc.door[1] + 0.5);
  // building volume is inset from the rect (the rect includes its yard)
  const bw = Math.max(2, w - 1.6);
  const bh = Math.max(2, h - 1.6);
  const roofH = 0.5 + Math.min(bw, bh) * 0.28;
  const windows: [number, number][] = [
    [-bw * 0.28, 0], [bw * 0.28, 0],
  ];
  return (
    <group>
      <mesh position={[cx, style.height / 2, cz]}>
        <boxGeometry args={[bw, style.height, bh]} />
        <meshStandardMaterial color={jitter(style.wall, loc.id)} />
      </mesh>
      <mesh position={[cx, style.height + roofH / 2, cz]} rotation={[0, Math.PI / 4, 0]}>
        <coneGeometry args={[Math.sqrt(bw * bw + bh * bh) / 2 + 0.25, roofH, 4]} />
        <meshStandardMaterial color={jitter(style.roof, loc.id + "roof")} flatShading />
      </mesh>
      {loc.kind === "chapel" && (
        <mesh position={[cx, style.height + roofH + 0.55, cz]}>
          <coneGeometry args={[0.28, 1.1, 4]} />
          <meshStandardMaterial color="#6a6355" />
        </mesh>
      )}
      {/* windows: warm light where the ledger says someone is awake */}
      {windows.map(([wx], i) => (
        <mesh key={i} position={[cx + wx, style.height * 0.55, cz + bh / 2 + 0.02]}>
          <planeGeometry args={[0.5, 0.6]} />
          <meshStandardMaterial
            color="#2a2118"
            emissive="#ffc86e"
            emissiveIntensity={lit ? (night ? 1.8 : 0.25) : 0}
          />
        </mesh>
      ))}
      {/* door step + lantern */}
      <mesh position={[dx, 0.03, dz]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1, 1]} />
        <meshStandardMaterial color="#6e6250" />
      </mesh>
      <mesh position={[dx + 0.42, 0.85, dz]}>
        <sphereGeometry args={[0.09, 8, 8]} />
        <meshStandardMaterial
          color="#3a3226" emissive="#ffb257"
          emissiveIntensity={night ? 2.2 : 0.1}
        />
      </mesh>
      <Text position={[cx, style.height + roofH + (loc.kind === "chapel" ? 1.3 : 0.7), cz]}
            fontSize={0.72} color="#d8d4c8" anchorX="center" anchorY="bottom"
            outlineWidth={0.045} outlineColor="#14141a">
        {loc.name}
      </Text>
    </group>
  );
}

function Ground({ loc }: { loc: Location }) {
  const [x, y, w, h] = loc.rect;
  const [cx, cz] = cell(x + w / 2, y + h / 2);
  const isOrchard = loc.id === "orchard";
  const isWell = loc.id === "village_well";
  const surface = isOrchard ? "#33452b" : isWell ? "#5f5b50" : "#6b6152";
  const trees = useMemo(() => {
    if (!isOrchard) return [];
    return Array.from({ length: 9 }, (_, i) => ({
      x: cx - w / 2 + 1 + hash01(`ox${i}`) * (w - 2),
      z: cz - h / 2 + 1 + hash01(`oz${i}`) * (h - 2),
      s: 0.8 + hash01(`os${i}`) * 0.5,
    }));
  }, [isOrchard, cx, cz, w, h]);
  return (
    <group>
      <mesh position={[cx, 0.01, cz]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[w, h]} />
        <meshStandardMaterial color={surface} />
      </mesh>
      {isWell && (
        <group position={[cx, 0, cz]}>
          <mesh position={[0, 0.35, 0]}>
            <cylinderGeometry args={[0.7, 0.8, 0.7, 10]} />
            <meshStandardMaterial color="#7d7869" />
          </mesh>
          <mesh position={[0, 1.5, 0]}>
            <coneGeometry args={[1.0, 0.7, 6]} />
            <meshStandardMaterial color="#5d4a37" flatShading />
          </mesh>
        </group>
      )}
      {loc.id === "market_square" && (
        <group>
          {[0, 1, 2].map((i) => (
            <group key={i} position={[cx - 3 + i * 3, 0, cz + 2.5]}>
              <mesh position={[0, 0.5, 0]}>
                <boxGeometry args={[1.8, 1.0, 1.0]} />
                <meshStandardMaterial color={jitter("#7d6a4f", `stall${i}`)} />
              </mesh>
              <mesh position={[0, 1.15, 0]} rotation={[0, 0, 0.06]}>
                <boxGeometry args={[2.2, 0.08, 1.4]} />
                <meshStandardMaterial color={jitter(i === 1 ? "#8a4a3a" : "#4a5d7a", `awn${i}`)} />
              </mesh>
            </group>
          ))}
        </group>
      )}
      {trees.map((t, i) => (
        <Tree key={i} x={t.x} z={t.z} scale={t.s} id={`orch${i}`} />
      ))}
      <Text position={[cx, 0.65, cz + h / 2 - 0.4]} fontSize={0.72} color="#c9c4b6"
            anchorX="center" anchorY="bottom"
            outlineWidth={0.045} outlineColor="#14141a">
        {loc.name}
      </Text>
    </group>
  );
}

function Farm({ loc, lit, night }: { loc: Location; lit: boolean; night: boolean }) {
  const [x, y, w, h] = loc.rect;
  const [cx, cz] = cell(x + w / 2, y + h / 2);
  // house on the west third, field rows on the rest
  const house: Location = { ...loc, rect: [x, y, Math.ceil(w * 0.45), h] };
  const rows = Array.from({ length: Math.floor(h - 2) }, (_, i) => i);
  return (
    <group>
      <Building loc={house} lit={lit} night={night} />
      {rows.map((i) => (
        <mesh key={i}
              position={[cx + w * 0.22, 0.06, cz - h / 2 + 1.5 + i]}
              rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[w * 0.42, 0.5]} />
          <meshStandardMaterial color={jitter("#4a5233", `row${i}`)} />
        </mesh>
      ))}
    </group>
  );
}

export function Town() {
  const locations = town.locations as unknown as Location[];
  const occluders = town.occluders as unknown as Occluder[];
  const world = useObserver((s) => s.world);
  const cursor = useObserver((s) => s.cursor);
  const night = sunElevation(simHour(cursor)) < 0.05;
  const texture = useMemo(grassTexture, []);

  const occupied = useMemo(() => {
    const set = new Set<string>();
    for (const agent of Object.values(world.agents)) {
      if (agent.location && agent.status !== "sleeping") set.add(agent.location);
    }
    return set;
  }, [world]);

  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]}>
        <planeGeometry args={[GRID.w + 10, GRID.h + 10]} />
        <meshStandardMaterial map={texture} />
      </mesh>
      {locations.map((loc) => {
        const lit = occupied.has(loc.id);
        if (loc.kind === "public") return <Ground key={loc.id} loc={loc} />;
        if (loc.kind === "farm") return <Farm key={loc.id} loc={loc} lit={lit} night={night} />;
        return <Building key={loc.id} loc={loc} lit={lit} night={night} />;
      })}
      {occluders.map((occ) => {
        const [ox, oz] = cell(occ.at[0] + 0.5, occ.at[1] + 0.5);
        if (occ.id === "market_stalls") return null; // stalls are drawn by the square
        return <Tree key={occ.id} x={ox} z={oz} scale={occ.radius * 1.4} id={occ.id} />;
      })}
    </group>
  );
}
