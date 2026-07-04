/** Agents as labeled spheres at their ledger-folded positions: smoothly
 * lerped between ticks, halo'd when holding the seeded fact (the live
 * diffusion overlay), amber while conversing. */
import { Text } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { Group, MathUtils } from "three";

import { AgentView } from "../ledger";
import { factHolders } from "../memories";
import { useObserver } from "../store";
import { cell } from "./Town";

const STATUS_COLORS: Record<string, string> = {
  idle: "#7aa2f7",
  moving: "#9ece6a",
  sleeping: "#565f89",
};

function Agent({ agent, holdsFact }: { agent: AgentView; holdsFact: boolean }) {
  const selected = useObserver((s) => s.selectedAgent);
  const selectAgent = useObserver((s) => s.selectAgent);
  const group = useRef<Group>(null);
  const [tx, tz] = cell(agent.pos[0] + 0.5, agent.pos[1] + 0.5);

  useFrame((_, delta) => {
    if (!group.current) return;
    group.current.position.x = MathUtils.damp(group.current.position.x, tx, 8, delta);
    group.current.position.z = MathUtils.damp(group.current.position.z, tz, 8, delta);
  });

  const conversing = agent.conversingWith !== null;
  return (
    <group ref={group} position={[tx, 0, tz]}>
      <mesh
        position={[0, 1.1, 0]}
        onClick={(e) => {
          e.stopPropagation();
          selectAgent(agent.id === selected ? null : agent.id);
        }}
      >
        <sphereGeometry args={[0.45, 16, 16]} />
        <meshStandardMaterial
          color={conversing ? "#e0af68" : (STATUS_COLORS[agent.status] ?? "#c0caf5")}
          emissive={agent.id === selected ? "#ff5f87" : "#000000"}
          emissiveIntensity={agent.id === selected ? 0.6 : 0}
        />
      </mesh>
      {holdsFact && (
        <mesh position={[0, 0.12, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.6, 0.85, 32]} />
          <meshBasicMaterial color="#f7768e" transparent opacity={0.9} />
        </mesh>
      )}
      <Text position={[0, 2.1, 0]} fontSize={0.7} color="#e8e8ea" anchorX="center">
        {agent.id.split("_")[0]}
      </Text>
    </group>
  );
}

export function Agents() {
  const world = useObserver((s) => s.world);
  const memories = useObserver((s) => s.memories);
  const fact = useObserver((s) => s.fact);
  const cursor = useObserver((s) => s.cursor);

  const holders = useMemo(
    () => (fact ? factHolders(memories, fact, cursor) : new Set<string>()),
    [memories, fact, cursor],
  );

  return (
    <group>
      {Object.values(world.agents).map((agent) => (
        <Agent key={agent.id} agent={agent} holdsFact={holders.has(agent.id)} />
      ))}
    </group>
  );
}
