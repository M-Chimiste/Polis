/** Harrowmere in simple geometry — no art pipeline (deliberate). */
import { Text } from "@react-three/drei";

import town from "../../../content/town.json";

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

const KIND_COLORS: Record<string, string> = {
  public: "#3a4a5a",
  commercial: "#4a3a2a",
  home: "#2f3a2f",
  civic: "#44384f",
};

export const GRID = { w: town.grid.width, h: town.grid.height };

/** grid cell -> scene coords, centered on origin, y-up, 1 unit = 1 cell */
export function cell(x: number, y: number): [number, number] {
  return [x - GRID.w / 2, y - GRID.h / 2];
}

export function Town() {
  const locations = town.locations as unknown as Location[];
  const occluders = town.occluders as unknown as Occluder[];
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]}>
        <planeGeometry args={[GRID.w, GRID.h]} />
        <meshStandardMaterial color="#1a2418" />
      </mesh>
      {occluders.map((occ) => {
        const [ox, oz] = cell(occ.at[0] + 0.5, occ.at[1] + 0.5);
        return (
          <mesh key={occ.id} position={[ox, occ.radius, oz]}>
            <cylinderGeometry args={[occ.radius * 0.6, occ.radius, occ.radius * 2, 10]} />
            <meshStandardMaterial color="#31402e" />
          </mesh>
        );
      })}
      {locations.map((loc) => {
        const [x, y, w, h] = loc.rect;
        const [cx, cz] = cell(x + w / 2, y + h / 2);
        const [dx, dz] = cell(loc.door[0] + 0.5, loc.door[1] + 0.5);
        return (
          <group key={loc.id}>
            <mesh position={[cx, 0.4, cz]}>
              <boxGeometry args={[w, 0.8, h]} />
              <meshStandardMaterial
                color={KIND_COLORS[loc.kind] ?? "#3d3d46"}
                transparent
                opacity={0.85}
              />
            </mesh>
            <mesh position={[dx, 0.05, dz]} rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[1, 1]} />
              <meshBasicMaterial color="#c8b478" />
            </mesh>
            <Text
              position={[cx, 1.4, cz]}
              fontSize={0.9}
              color="#cfd2d6"
              anchorX="center"
              anchorY="bottom"
            >
              {loc.name}
            </Text>
          </group>
        );
      })}
    </group>
  );
}
