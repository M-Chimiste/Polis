import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useCallback } from "react";

import { parseLedger } from "./ledger";
import { Agents } from "./scene/Agents";
import { Town } from "./scene/Town";
import { useObserver } from "./store";
import { Inspector } from "./ui/Inspector";
import { Scrubber } from "./ui/Scrubber";
import { useLedgerStream } from "./ws";

const WS_URL = new URLSearchParams(location.search).get("ws");

export default function App() {
  const loadEvents = useObserver((s) => s.loadEvents);
  const haveEvents = useObserver((s) => s.events.length > 0);
  useLedgerStream(WS_URL); // ?ws=ws://host:8010/ws/ledger for live mode

  const onFile = useCallback(
    async (file: File) => loadEvents(parseLedger(await file.text())),
    [loadEvents],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div
          style={{ flex: 1, position: "relative" }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files[0];
            if (f) void onFile(f);
          }}
        >
          {!haveEvents && (
            <div style={{ position: "absolute", inset: 0, display: "grid",
                          placeItems: "center", zIndex: 1, pointerEvents: "none" }}>
              <div style={{ textAlign: "center", opacity: 0.7 }}>
                <h2>POLIS observer</h2>
                <p>drop a ledger.jsonl here, or open with ?ws=ws://host:8010/ws/ledger</p>
              </div>
            </div>
          )}
          <Canvas camera={{ position: [0, 42, 34], fov: 45 }}>
            <ambientLight intensity={0.7} />
            <directionalLight position={[20, 40, 10]} intensity={1.2} />
            <Town />
            <Agents />
            <OrbitControls makeDefault />
          </Canvas>
        </div>
        <Inspector />
      </div>
      <Scrubber />
    </div>
  );
}
