#!/usr/bin/env python3
"""Validate content/ after any hand edit. Exit nonzero on failure.

Checks:
  - every agent's home/workplace is a real location id
  - agent ids unique; every agent file's id matches its filename
  - relationship edges reference real agents; no self-edges; no duplicate pairs
  - every agent appears in at least one relationship edge (no orphans)
  - locations fit the grid; rects don't overlap; doors on rect perimeter
  - daily anchors parse as HH:MM and are present
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
errors = []

town = json.loads((CONTENT / "town.json").read_text())
rels = json.loads((CONTENT / "relationships.json").read_text())["edges"]
agent_files = sorted((CONTENT / "agents").glob("*.json"))
agents = {p.stem: json.loads(p.read_text()) for p in agent_files}

loc_ids = {l["id"] for l in town["locations"]}
gw, gh = town["grid"]["width"], town["grid"]["height"]

# --- locations ---
rects = {}
for l in town["locations"]:
    x, y, w, h = l["rect"]
    if not (0 <= x and 0 <= y and x + w <= gw and y + h <= gh):
        errors.append(f"location {l['id']}: rect out of grid")
    dx, dy = l["door"]
    on_perim = (dx in (x, x + w) and y <= dy <= y + h) or \
               (dy in (y, y + h) and x <= dx <= x + w)
    if not on_perim:
        errors.append(f"location {l['id']}: door {l['door']} not on rect perimeter {l['rect']}")
    rects[l["id"]] = (x, y, w, h)

ids = list(rects)
for i, a in enumerate(ids):
    ax, ay, aw, ah = rects[a]
    for b in ids[i + 1:]:
        bx, by, bw, bh = rects[b]
        if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
            errors.append(f"locations overlap: {a} and {b}")

# --- agents ---
for stem, a in agents.items():
    if a["id"] != stem:
        errors.append(f"{stem}.json: id field '{a['id']}' != filename")
    for field in ("home", "workplace"):
        if a[field] not in loc_ids:
            errors.append(f"agent {a['id']}: {field} '{a[field]}' is not a location id")
    anch = a.get("daily_anchors", {})
    for k in ("wake", "work_start", "midday_meal", "work_end", "sleep"):
        v = anch.get(k, "")
        parts = v.split(":")
        if len(parts) != 2 or not all(p.isdigit() for p in parts) \
           or not (0 <= int(parts[0]) < 24 and 0 <= int(parts[1]) < 60):
            errors.append(f"agent {a['id']}: daily_anchors.{k} '{v}' is not HH:MM")
    if not a.get("bio") or not a.get("initial_memories"):
        errors.append(f"agent {a['id']}: missing bio or initial_memories")

# --- relationships ---
seen_pairs = set()
in_graph = set()
for e in rels:
    a, b = e["a"], e["b"]
    if a == b:
        errors.append(f"self-edge: {a}")
    for x in (a, b):
        if x not in agents:
            errors.append(f"edge {a}--{b}: unknown agent '{x}'")
    pair = tuple(sorted((a, b)))
    if pair in seen_pairs:
        errors.append(f"duplicate edge: {a}--{b}")
    seen_pairs.add(pair)
    if not (0.0 <= e["closeness"] <= 1.0):
        errors.append(f"edge {a}--{b}: closeness out of [0,1]")
    if not e.get("a_view") or not e.get("b_view"):
        errors.append(f"edge {a}--{b}: missing a_view/b_view")
    in_graph.update(pair)

for aid in agents:
    if aid not in in_graph:
        errors.append(f"agent {aid}: orphan — appears in no relationship edge")

# --- report ---
if errors:
    print(f"FAIL — {len(errors)} problem(s):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"OK — {len(town['locations'])} locations, {len(agents)} agents, "
      f"{len(rels)} relationship edges, all consistent")
