/** Side panel: selected agent state + the event feed at the cursor. */
import { useObserver } from "../store";

export function Inspector() {
  const world = useObserver((s) => s.world);
  const selected = useObserver((s) => s.selectedAgent);
  const agent = selected ? world.agents[selected] : null;
  const feed = agent
    ? world.feed.filter(
        (e) => e.agent_id === agent.id || e.data.partner === agent.id)
    : world.feed;

  return (
    <div style={{ width: 340, overflowY: "auto", padding: 12, fontSize: 12,
                  borderLeft: "1px solid #2a2a32" }}>
      {agent ? (
        <>
          <h3 style={{ margin: "4px 0" }}>{agent.id}</h3>
          <div>status: {agent.status}</div>
          <div>location: {agent.location ?? "the lanes"}</div>
          <div>pos: [{agent.pos[0]}, {agent.pos[1]}]</div>
          {agent.conversingWith && <div>talking to: {agent.conversingWith}</div>}
          {agent.lastUtterance && (
            <blockquote style={{ margin: "8px 0", color: "#a9b1d6" }}>
              “{agent.lastUtterance}”
            </blockquote>
          )}
          <hr style={{ borderColor: "#2a2a32" }} />
        </>
      ) : (
        <h3 style={{ margin: "4px 0" }}>event feed</h3>
      )}
      {feed.slice(-60).reverse().map((e) => (
        <div key={`${e.run_id}:${e.seq}`} style={{ marginBottom: 6, opacity: 0.9 }}>
          <span style={{ color: "#565f89" }}>t{e.tick}</span>{" "}
          <span style={{ color: "#7aa2f7" }}>{e.kind}</span>{" "}
          <span>{e.agent_id}</span>
          {e.kind === "utterance" && (
            <div style={{ color: "#a9b1d6" }}>“{String(e.data.text).slice(0, 120)}”</div>
          )}
        </div>
      ))}
    </div>
  );
}
