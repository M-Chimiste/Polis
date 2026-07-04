/** Agents as little people WALKING their ledger paths: positions are
 * sampled per frame from the movement tracks at the float playhead (fluid
 * presentation of the exact A* routes the sim computed — no new physics),
 * with heading rotation and a small gait bob. Halo when holding the seeded
 * fact, amber while conversing, flat while asleep. */
import { Text } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { Group, MathUtils } from "three";

import { AgentView } from "../ledger";
import { factHolders } from "../memories";
import { useObserver } from "../store";
import { sample } from "../tracks";
import { cell, hash01 } from "./Town";

const STATUS_COLORS: Record<string, string> = {
  idle: "#7aa2f7",
  moving: "#9ece6a",
  sleeping: "#3d4466",
};

function Agent({ agent, holdsFact }: { agent: AgentView; holdsFact: boolean }) {
  const selected = useObserver((s) => s.selectedAgent);
  const selectAgent = useObserver((s) => s.selectAgent);
  const group = useRef<Group>(null);
  const body = useRef<Group>(null);
  const sleeping = agent.status === "sleeping";
  const conversing = agent.conversingWith !== null;
  const labelDx = (hash01(agent.id) - 0.5) * 1.1;

  useFrame((_, delta) => {
    const { tracks, playhead } = useObserver.getState();
    const track = tracks[agent.id];
    if (!group.current || !track) return;
    const s = sample(track, playhead);
    const [x, z] = cell(s.pos[0] + 0.5, s.pos[1] + 0.5);
    group.current.position.x = x;
    group.current.position.z = z;
    if (s.heading) {
      const target = Math.atan2(s.heading[0], s.heading[1]);
      // shortest-arc damp
      const current = group.current.rotation.y;
      let diff = target - current;
      while (diff > Math.PI) diff -= 2 * Math.PI;
      while (diff < -Math.PI) diff += 2 * Math.PI;
      group.current.rotation.y = current + diff * Math.min(1, delta * 10);
    }
    if (body.current) {
      const bob = s.moving ? Math.abs(Math.sin(playhead * 4)) * 0.08 : 0;
      const targetRot = sleeping ? Math.PI / 2 : 0;
      body.current.rotation.z = MathUtils.damp(
        body.current.rotation.z, targetRot, 6, delta);
      body.current.position.y = MathUtils.damp(
        body.current.position.y, (sleeping ? 0.32 : 0.62) + bob, 10, delta);
    }
  });

  const color = conversing ? "#e0af68" : (STATUS_COLORS[agent.status] ?? "#c0caf5");
  return (
    <group ref={group}>
      <group ref={body} position={[0, 0.62, 0]}
             onClick={(e) => {
               e.stopPropagation();
               selectAgent(agent.id === selected ? null : agent.id);
             }}>
        <mesh>
          <capsuleGeometry args={[0.26, 0.55, 4, 10]} />
          <meshStandardMaterial
            color={color}
            emissive={agent.id === selected ? "#ff5f87" : "#000000"}
            emissiveIntensity={agent.id === selected ? 0.55 : 0}
          />
        </mesh>
        <mesh position={[0, 0.62, 0]}>
          <sphereGeometry args={[0.2, 12, 12]} />
          <meshStandardMaterial color="#d9b99a" />
        </mesh>
      </group>
      {holdsFact && (
        <mesh position={[0, 0.06, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.55, 0.8, 32]} />
          <meshBasicMaterial color="#f7768e" transparent opacity={0.9} />
        </mesh>
      )}
      <Text position={[labelDx, sleeping ? 1.0 : 1.75, 0]} fontSize={0.5}
            color={sleeping ? "#8890b3" : "#f0f0f2"} anchorX="center"
            outlineWidth={0.04} outlineColor="#14141a"
            fillOpacity={sleeping ? 0.65 : 1}>
        {agent.id.split("_")[0]}
      </Text>
    </group>
  );
}

export function Agents() {
  const world = useObserver((s) => s.world);
  const memories = useObserver((s) => s.memories);
  const fact = useObserver((s) => s.fact);
  const tick = useObserver((s) => s.world.tick);

  const holders = useMemo(
    () => (fact ? factHolders(memories, fact, tick) : new Set<string>()),
    [memories, fact, tick],
  );

  return (
    <group>
      {Object.values(world.agents).map((agent) => (
        <Agent key={agent.id} agent={agent} holdsFact={holders.has(agent.id)} />
      ))}
    </group>
  );
}
