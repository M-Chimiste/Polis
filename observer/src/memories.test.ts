/** Fact-check parity with metrics/probes.py: same STOPWORDS, same 60%
 * single-record token-overlap rule — the overlay must show what the
 * measurement plane would measure. */
import { describe, expect, it } from "vitest";

import { conversationEdges, LedgerEvent, treatmentFact } from "./ledger";
import {
  byAgent, factHolders, knowsFact, MemoryRecord, parseMemories,
  significantTokens,
} from "./memories";

const FACT = "there is a gathering at the tavern on day three";

function mem(agent: string, tick: number, text: string): MemoryRecord {
  return {
    id: `00000000-0000-0000-0000-${String(tick).padStart(12, "0")}`,
    run_id: "00000000-0000-0000-0000-000000000001",
    agent_id: agent, kind: "observation", tick, text, importance: 5,
  };
}

describe("significantTokens", () => {
  it("drops the probes.py stopwords, keeps content words", () => {
    const tokens = significantTokens(FACT);
    expect(tokens.has("gathering")).toBe(true);
    expect(tokens.has("tavern")).toBe(true);
    expect(tokens.has("the")).toBe(false);
    expect(tokens.has("on")).toBe(false);
  });
});

describe("knowsFact", () => {
  const records = [
    mem("a", 100, "walked to the well this morning"),
    mem("a", 200, "maren said to me: there is a gathering at the tavern on day three"),
  ];

  it("finds the fact once a carrying memory exists", () => {
    expect(knowsFact(records, FACT, 150)).toBe(false); // not yet heard
    expect(knowsFact(records, FACT, 200)).toBe(true);
  });

  it("partial overlap below 60% does not count", () => {
    const vague = [mem("b", 50, "the tavern was busy tonight")];
    expect(knowsFact(vague, FACT, 100)).toBe(false);
  });

  it("scrubbing time backward un-knows the fact (pure fold)", () => {
    expect(knowsFact(records, FACT, 199)).toBe(false);
  });
});

describe("factHolders / byAgent / parseMemories", () => {
  it("indexes and reports holders at the cursor", () => {
    const jsonl = [
      mem("maren_alder", 10, FACT),
      mem("piet_alder", 300, `overheard maren tell ilse: ${FACT}`),
      mem("sela_crane", 20, "kneaded the dough before dawn"),
    ].map((r) => JSON.stringify(r)).join("\n");
    const index = byAgent(parseMemories(jsonl));
    expect(factHolders(index, FACT, 100)).toEqual(new Set(["maren_alder"]));
    expect(factHolders(index, FACT, 400)).toEqual(
      new Set(["maren_alder", "piet_alder"]));
  });

  it("rejects a record that violates the contract", () => {
    expect(() => parseMemories('{"agent_id": "x", "importance": 99}')).toThrow();
  });
});

describe("conversationEdges / treatmentFact", () => {
  function utterance(tick: number, a: string, b: string): LedgerEvent {
    return { run_id: "r", seq: tick, tick, kind: "utterance", agent_id: a,
             data: { partner: b, text: "..." } };
  }

  it("accumulates pair weights up to the cursor, orientation-free", () => {
    const events = [
      utterance(1, "a", "b"), utterance(2, "b", "a"), utterance(9, "a", "c"),
    ];
    const at5 = conversationEdges(events, 5);
    expect(at5.get("a|b")).toBe(2);
    expect(at5.has("a|c")).toBe(false);
    expect(conversationEdges(events, 10).get("a|c")).toBe(1);
  });

  it("finds the seeded fact from the treatment event", () => {
    const events: LedgerEvent[] = [
      { run_id: "r", seq: 0, tick: 0, kind: "run_started", agent_id: null, data: {} },
      { run_id: "r", seq: 1, tick: 5, kind: "treatment_injected", agent_id: null,
        data: { kind: "seeded_fact", fact: FACT, target_agent: "maren_alder" } },
    ];
    expect(treatmentFact(events)).toBe(FACT);
    expect(treatmentFact([events[0]])).toBeNull();
  });
});
