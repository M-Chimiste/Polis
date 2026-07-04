import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useCallback } from "react";

import { parseLedger } from "./ledger";
import { parseMemories } from "./memories";
import { Agents } from "./scene/Agents";
import { DayNight } from "./scene/DayNight";
import { FollowCam, PlaybackDriver } from "./scene/FollowCam";
import { Threads } from "./scene/Threads";
import { Town } from "./scene/Town";
import { useObserver } from "./store";
import { Inspector } from "./ui/Inspector";
import { Scrubber } from "./ui/Scrubber";
import { useLedgerStream } from "./ws";

const WS_URL = new URLSearchParams(location.search).get("ws");

function OrbitControlsUnlessFollowing() {
  const follow = useObserver((s) => s.follow);
  return <OrbitControls makeDefault enabled={!follow} />;
}

/** Route a dropped file by its first record's shape: ledger events carry
 * `seq`, memory records carry `importance`. */
function routeFile(text: string): "ledger" | "memories" {
  const first = JSON.parse(text.slice(0, text.indexOf("\n")));
  return "seq" in first ? "ledger" : "memories";
}

export default function App() {
  const loadEvents = useObserver((s) => s.loadEvents);
  const loadMemories = useObserver((s) => s.loadMemories);
  const haveEvents = useObserver((s) => s.events.length > 0);
  const haveMemories = useObserver((s) => Object.keys(s.memories).length > 0);
  useLedgerStream(WS_URL); // ?ws=ws://host:8010/ws/ledger for live mode

  const onFiles = useCallback(
    async (files: FileList) => {
      for (const file of files) {
        const text = await file.text();
        if (routeFile(text) === "ledger") loadEvents(parseLedger(text));
        else loadMemories(parseMemories(text));
      }
    },
    [loadEvents, loadMemories],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div
          style={{ flex: 1, position: "relative" }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            void onFiles(e.dataTransfer.files);
          }}
        >
          {!haveEvents && (
            <div style={{ position: "absolute", inset: 0, display: "grid",
                          placeItems: "center", zIndex: 1, pointerEvents: "none" }}>
              <div style={{ textAlign: "center", opacity: 0.7 }}>
                <h2>POLIS observer</h2>
                <p>drop ledger.jsonl (+ memories.jsonl for minds & diffusion),
                   or open with ?ws=ws://host:8010/ws/ledger</p>
              </div>
            </div>
          )}
          {haveEvents && !haveMemories && (
            <div style={{ position: "absolute", top: 8, left: 12, zIndex: 1,
                          opacity: 0.55, fontSize: 12, pointerEvents: "none" }}>
              drop memories.jsonl for the mind inspector + diffusion overlay
            </div>
          )}
          <Canvas camera={{ position: [4, 26, 40], fov: 42 }} shadows={false}>
            <PlaybackDriver />
            <DayNight />
            <Town />
            <Threads />
            <Agents />
            <FollowCam />
            <OrbitControlsUnlessFollowing />
          </Canvas>
        </div>
        <Inspector />
      </div>
      <Scrubber />
    </div>
  );
}
