/** Follow camera: ride along behind the selected agent at street level —
 * the way to feel whether the town works or doesn't. */
import { useFrame } from "@react-three/fiber";

import { useObserver } from "../store";
import { sample } from "../tracks";
import { cell } from "./Town";

export function FollowCam() {
  useFrame(({ camera }, delta) => {
    const { follow, selectedAgent, tracks, playhead } = useObserver.getState();
    if (!follow || !selectedAgent) return;
    const track = tracks[selectedAgent];
    if (!track) return;
    const s = sample(track, playhead);
    const [x, z] = cell(s.pos[0] + 0.5, s.pos[1] + 0.5);
    const k = Math.min(1, delta * 3);
    camera.position.x += (x + 5 - camera.position.x) * k;
    camera.position.y += (4.5 - camera.position.y) * k;
    camera.position.z += (z + 6.5 - camera.position.z) * k;
    camera.lookAt(x, 1.0, z);
  });
  return null;
}

/** Frame driver: advances the playhead by wall clock. */
export function PlaybackDriver() {
  useFrame((_, delta) => {
    useObserver.getState().advance(Math.min(delta, 0.1));
  });
  return null;
}
