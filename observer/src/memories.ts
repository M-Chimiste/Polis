/**
 * Memory stream loading + the diffusion fact-check, ported from
 * metrics/probes.py (same STOPWORDS, same single-record token-overlap rule)
 * so the overlay shows exactly what the measurement plane would measure.
 */
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";

import memoryRecordSchema from "../../schemas/json/memory_record.schema.json";

export interface MemoryRecord {
  id: string;
  run_id: string;
  agent_id: string;
  kind: string;
  tick: number;
  text: string;
  importance: number;
  citations?: string[];
}

const ajv = new Ajv2020({ strict: false });
addFormats(ajv);
export const validateMemory = ajv.compile<MemoryRecord>(memoryRecordSchema);

export function parseMemories(jsonl: string): MemoryRecord[] {
  const records: MemoryRecord[] = [];
  for (const line of jsonl.split("\n")) {
    if (!line.trim()) continue;
    const record = JSON.parse(line);
    if (!validateMemory(record)) {
      throw new Error(
        `invalid memory record: ${ajv.errorsText(validateMemory.errors)}`,
      );
    }
    records.push(record);
  }
  return records;
}

export function byAgent(records: MemoryRecord[]): Record<string, MemoryRecord[]> {
  const index: Record<string, MemoryRecord[]> = {};
  for (const r of records) (index[r.agent_id] ??= []).push(r);
  for (const list of Object.values(index)) list.sort((a, b) => a.tick - b.tick);
  return index;
}

// metrics/probes.py parity — keep in lockstep
const STOPWORDS = new Set([
  "a", "an", "the", "is", "are", "was", "at", "on", "in", "of", "to",
  "and", "or", "there", "be", "will", "for", "with", "about",
]);

export function significantTokens(text: string): Set<string> {
  const tokens = text.toLowerCase().match(/[a-z0-9']+/g) ?? [];
  return new Set(tokens.filter((t) => !STOPWORDS.has(t)));
}

/** True if any single memory record written by `tick` carries enough of the
 * fact (>= 60% token overlap — the probes.py rule, verbatim). */
export function knowsFact(
  records: MemoryRecord[], fact: string, tick: number, threshold = 0.6,
): boolean {
  const factTokens = significantTokens(fact);
  if (factTokens.size === 0) return false;
  return records.some((r) => {
    if (r.tick > tick) return false;
    const overlap = [...significantTokens(r.text)]
      .filter((t) => factTokens.has(t)).length;
    return overlap / factTokens.size >= threshold;
  });
}

/** Which agents hold the fact at cursor tick — the diffusion overlay. */
export function factHolders(
  index: Record<string, MemoryRecord[]>, fact: string, tick: number,
): Set<string> {
  return new Set(
    Object.keys(index).filter((aid) => knowsFact(index[aid], fact, tick)),
  );
}
