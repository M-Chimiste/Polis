/** Relationship threads: a line per agent pair, opacity/width by how much
 * they've talked up to the cursor — metrics/graph.py's edges, drawn. Plus
 * bright links between currently-conversing pairs. */
import { Line } from "@react-three/drei";
import { useMemo } from "react";

import { conversationEdges } from "../ledger";
import { useObserver } from "../store";
import { cell } from "./Town";

export function Threads() {
  const events = useObserver((s) => s.events);
  const world = useObserver((s) => s.world);
  // recompute a few times per sim-hour, not per frame
  const coarseTick = Math.floor(world.tick / 60) * 60;

  const edges = useMemo(() => conversationEdges(events, coarseTick),
                        [events, coarseTick]);
  const maxWeight = Math.max(1, ...edges.values());

  return (
    <group>
      {[...edges.entries()].map(([pair, weight]) => {
        const [a, b] = pair.split("|");
        const va = world.agents[a];
        const vb = world.agents[b];
        if (!va || !vb) return null;
        const [ax, az] = cell(va.pos[0] + 0.5, va.pos[1] + 0.5);
        const [bx, bz] = cell(vb.pos[0] + 0.5, vb.pos[1] + 0.5);
        const conversingNow = va.conversingWith === b;
        const t = weight / maxWeight;
        return (
          <Line
            key={pair}
            points={[[ax, 0.35, az], [bx, 0.35, bz]]}
            color={conversingNow ? "#e0af68" : "#bb9af7"}
            lineWidth={conversingNow ? 2.5 : 1 + t * 2}
            transparent
            opacity={conversingNow ? 0.95 : 0.15 + t * 0.5}
          />
        );
      })}
    </group>
  );
}
