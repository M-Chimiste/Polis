/**
 * Ledger parsing + the replay fold: events in, world-state-at-tick out.
 *
 * The observer holds ZERO authority — it only folds what the ledger says.
 * Scrubbing to tick T is folding the event prefix with tick <= T; the fold is
 * a pure function, so any cursor position is reproducible from the same
 * ledger bytes (the same property the byte-equal wall guarantees upstream).
 */
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";

import ledgerEventSchema from "../../schemas/json/ledger_event.schema.json";

export interface LedgerEvent {
  run_id: string;
  seq: number;
  tick: number;
  kind: string;
  agent_id: string | null;
  data: Record<string, unknown>;
}

const ajv = new Ajv2020({ strict: false });
addFormats(ajv);
export const validateEvent = ajv.compile<LedgerEvent>(ledgerEventSchema);

/** Parse canonical JSONL. Throws on schema violation — a bad ledger is a
 * bug upstream, never something to render around. */
export function parseLedger(jsonl: string): LedgerEvent[] {
  const events: LedgerEvent[] = [];
  for (const line of jsonl.split("\n")) {
    if (!line.trim()) continue;
    const event = JSON.parse(line);
    if (!validateEvent(event)) {
      throw new Error(
        `invalid ledger event at seq ${event?.seq}: ${ajv.errorsText(validateEvent.errors)}`,
      );
    }
    events.push(event);
  }
  return events;
}

export interface AgentView {
  id: string;
  pos: [number, number];
  status: string;
  location: string | null;
  lastUtterance: string | null;
  conversingWith: string | null;
}

export interface WorldView {
  runId: string | null;
  tick: number;
  agents: Record<string, AgentView>;
  objectStates: Record<string, string>;
  /** rolling tail of noteworthy events for the inspector */
  feed: LedgerEvent[];
}

export function emptyWorld(): WorldView {
  return { runId: null, tick: 0, agents: {}, objectStates: {}, feed: [] };
}

const FEED_KINDS = new Set([
  "utterance", "conversation_started", "conversation_ended",
  "conversation_declined", "treatment_injected", "intent_rejected",
  "object_state_changed",
]);
const FEED_LIMIT = 500;

/** Fold one event into the view (mutates and returns the same object —
 * callers own copying semantics). */
export function applyEvent(world: WorldView, event: LedgerEvent): WorldView {
  world.tick = event.tick;
  const agent = event.agent_id ? world.agents[event.agent_id] : undefined;
  switch (event.kind) {
    case "run_started":
      world.runId = event.run_id;
      break;
    case "agent_initialized":
      world.agents[event.agent_id!] = {
        id: event.agent_id!,
        pos: event.data.pos as [number, number],
        status: (event.data.status as string) ?? "idle",
        location: (event.data.location as string) ?? null,
        lastUtterance: null,
        conversingWith: null,
      };
      break;
    case "agent_moved":
      if (agent) agent.pos = event.data.to as [number, number];
      break;
    case "agent_arrived":
      if (agent) agent.location = (event.data.location as string) ?? null;
      break;
    case "agent_status_changed":
      if (agent) agent.status = event.data.status as string;
      break;
    case "utterance":
      if (agent) agent.lastUtterance = event.data.text as string;
      break;
    case "conversation_started":
      if (agent) agent.conversingWith = event.data.partner as string;
      if (world.agents[event.data.partner as string])
        world.agents[event.data.partner as string].conversingWith = event.agent_id;
      break;
    case "conversation_ended": {
      const a = world.agents[event.agent_id!];
      const b = world.agents[event.data.partner as string];
      if (a) a.conversingWith = null;
      if (b) b.conversingWith = null;
      break;
    }
    case "object_state_changed":
      world.objectStates[event.data.object_id as string] = event.data.to as string;
      break;
  }
  if (FEED_KINDS.has(event.kind)) {
    world.feed.push(event);
    if (world.feed.length > FEED_LIMIT) world.feed.shift();
  }
  return world;
}

/** The scrub: world state at cursor tick = fold of the prefix. */
export function worldAt(events: LedgerEvent[], tick: number): WorldView {
  const world = emptyWorld();
  for (const event of events) {
    if (event.tick > tick) break;
    applyEvent(world, event);
  }
  world.tick = tick;
  return world;
}
