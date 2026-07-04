/** Side panel: selected agent's mind (memory stream at the cursor) and
 * state, or the run-wide event feed when nothing is selected. */
import { useObserver } from "../store";

const KIND_COLORS: Record<string, string> = {
  observation: "#7aa2f7",
  plan: "#9ece6a",
  reflection: "#bb9af7",
  conversation_summary: "#e0af68",
};

export function Inspector() {
  const world = useObserver((s) => s.world);
  const cursor = useObserver((s) => s.cursor);
  const memories = useObserver((s) => s.memories);
  const fact = useObserver((s) => s.fact);
  const selected = useObserver((s) => s.selectedAgent);
  const agent = selected ? world.agents[selected] : null;

  const mind = agent
    ? (memories[agent.id] ?? []).filter((m) => m.tick <= cursor)
    : [];
  const feed = agent
    ? world.feed.filter(
        (e) => e.agent_id === agent.id || e.data.partner === agent.id)
    : world.feed;

  return (
    <div style={{ width: 360, overflowY: "auto", padding: 12, fontSize: 12,
                  borderLeft: "1px solid #2a2a32" }}>
      {fact && (
        <div style={{ marginBottom: 8, padding: 6, border: "1px solid #f7768e",
                      borderRadius: 4, color: "#f7768e" }}>
          seeded fact: “{fact}”
        </div>
      )}
      {agent ? (
        <>
          <h3 style={{ margin: "4px 0" }}>{agent.id}</h3>
          <div>status: {agent.status}</div>
          <div>location: {agent.location ?? "the lanes"}</div>
          {agent.conversingWith && <div>talking to: {agent.conversingWith}</div>}
          {agent.lastUtterance && (
            <blockquote style={{ margin: "8px 0", color: "#a9b1d6" }}>
              “{agent.lastUtterance}”
            </blockquote>
          )}
          <h4 style={{ margin: "10px 0 4px" }}>
            mind at t{cursor} ({mind.length} memories)
          </h4>
          {mind.slice(-40).reverse().map((m) => (
            <div key={m.id} style={{ marginBottom: 6 }}>
              <span style={{ color: "#565f89" }}>t{m.tick}</span>{" "}
              <span style={{ color: KIND_COLORS[m.kind] ?? "#c0caf5" }}>{m.kind}</span>{" "}
              <span style={{ color: "#565f89" }}>imp {m.importance}</span>
              <div style={{ color: "#c0caf5" }}>{m.text.slice(0, 160)}</div>
            </div>
          ))}
          {mind.length === 0 && (
            <div style={{ opacity: 0.6 }}>
              (no memories loaded — drop memories.jsonl)
            </div>
          )}
        </>
      ) : (
        <>
          <h3 style={{ margin: "4px 0" }}>event feed</h3>
          {feed.slice(-60).reverse().map((e) => (
            <div key={`${e.run_id}:${e.seq}`} style={{ marginBottom: 6, opacity: 0.9 }}>
              <span style={{ color: "#565f89" }}>t{e.tick}</span>{" "}
              <span style={{ color: "#7aa2f7" }}>{e.kind}</span>{" "}
              <span>{e.agent_id}</span>
              {e.kind === "utterance" && (
                <div style={{ color: "#a9b1d6" }}>
                  “{String(e.data.text).slice(0, 120)}”
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
