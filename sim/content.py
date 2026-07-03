"""Loaders for the frozen static world content in content/.

The sim only ever reads content/; it never generates (decision 2026-07-03).
Loading validates every file against its JSON Schema, so malformed hand
edits fail at startup, not mid-run. content_hash() feeds
experiment_config.content_hash — content is a controlled variable.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import schemas

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"


def load_town(content_dir: pathlib.Path = CONTENT_DIR) -> dict:
    town = json.loads((content_dir / "town.json").read_text())
    schemas.validate("town_spec", town)
    return town


def load_agents(content_dir: pathlib.Path = CONTENT_DIR) -> dict[str, dict]:
    agents: dict[str, dict] = {}
    for path in sorted((content_dir / "agents").glob("*.json")):
        seed = json.loads(path.read_text())
        schemas.validate("agent_seed", seed)
        if seed["id"] != path.stem:
            raise ValueError(f"{path.name}: id '{seed['id']}' != filename")
        agents[seed["id"]] = seed
    return agents


def load_relationships(content_dir: pathlib.Path = CONTENT_DIR) -> list[dict]:
    rels = json.loads((content_dir / "relationships.json").read_text())
    schemas.validate("relationships", rels)
    return rels["edges"]


def content_hash(content_dir: pathlib.Path = CONTENT_DIR) -> str:
    """sha256 over every file under content/, ordered by relative path."""
    h = hashlib.sha256()
    for path in sorted(content_dir.rglob("*")):
        if path.is_file():
            h.update(str(path.relative_to(content_dir)).encode())
            h.update(path.read_bytes())
    return h.hexdigest()
