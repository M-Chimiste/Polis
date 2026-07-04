/** Live ledger stream client (sim/stream.py sidecar, /ws/ledger). */
import { useEffect } from "react";

import { validateEvent } from "./ledger";
import { useObserver } from "./store";

export function useLedgerStream(url: string | null) {
  const appendLive = useObserver((s) => s.appendLive);
  useEffect(() => {
    if (!url) return;
    const ws = new WebSocket(url);
    ws.onmessage = (msg) => {
      const event = JSON.parse(msg.data);
      if (validateEvent(event)) appendLive(event);
      else console.error("dropped invalid ledger event", validateEvent.errors);
    };
    return () => ws.close();
  }, [url, appendLive]);
}
