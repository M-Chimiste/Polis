/** Agents as labeled spheres at their ledger-folded positions. */
import { Text } from "@react-three/drei";

import { useObserver } from "../store";
import { cell } from "./Town";

const STATUS_COLORS: Record<string, string> = {
  idle: "#7aa2f7",
  moving: "#9ece6a",
  sleeping: "#565f89",
};

export function Agents() {
  const world = useObserver((s) => s.world);
  const selected = useObserver((s) => s.selectedAgent);
  const selectAgent = useObserver((s) => s.selectAgent);

  return (
    <group>
      {Object.values(world.agents).map((agent) => {
        const [x, z] = cell(agent.pos[0] + 0.5, agent.pos[1] + 0.5);
        const conversing = agent.conversingWith !== null;
        return (
          <group key={agent.id} position={[x, 0, z]}>
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
            <Text position={[0, 2.1, 0]} fontSize={0.7} color="#e8e8ea" anchorX="center">
              {agent.id.split("_")[0]}
            </Text>
          </group>
        );
      })}
    </group>
  );
}
