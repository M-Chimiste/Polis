/** Agents as little people at their ledger-folded positions: capsule bodies
 * with heads, smoothly lerped, lying down while asleep, halo'd when holding
 * the seeded fact (the live diffusion overlay), amber while conversing. */
import { Text } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { Group, MathUtils } from "three";

import { AgentView } from "../ledger";
import { factHolders } from "../memories";
import { useObserver } from "../store";
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
  const [tx, tz] = cell(agent.pos[0] + 0.5, agent.pos[1] + 0.5);
  const sleeping = agent.status === "sleeping";
  const conversing = agent.conversingWith !== null;
  // deterministic label offset so cohabitants' names don't collide
  const labelDx = (hash01(agent.id) - 0.5) * 1.1;

  useFrame((_, delta) => {
    if (group.current) {
      group.current.position.x = MathUtils.damp(group.current.position.x, tx, 8, delta);
      group.current.position.z = MathUtils.damp(group.current.position.z, tz, 8, delta);
    }
    if (body.current) {
      // ease down to lying flat when asleep, back upright on waking
      const target = sleeping ? Math.PI / 2 : 0;
      body.current.rotation.z = MathUtils.damp(body.current.rotation.z, target, 6, delta);
      body.current.position.y = MathUtils.damp(
        body.current.position.y, sleeping ? 0.32 : 0.62, 6, delta);
    }
  });

  const color = conversing ? "#e0af68" : (STATUS_COLORS[agent.status] ?? "#c0caf5");
  return (
    <group ref={group} position={[tx, 0, tz]}>
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
