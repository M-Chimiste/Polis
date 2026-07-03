"""Pydantic mirrors (generated) stay in lockstep with the JSON Schemas:
the real content and contract fixtures must parse through both."""
import json

from pydantic import TypeAdapter

from schemas.models.agent_intent_schema import AgentIntent
from schemas.models.agent_seed_schema import AgentSeed
from schemas.models.relationships_schema import Relationships
from schemas.models.town_spec_schema import TownSpec
from sim.content import CONTENT_DIR


def test_town_parses_through_mirror():
    town = TownSpec.model_validate_json((CONTENT_DIR / "town.json").read_text())
    assert len(town.locations) == 16


def test_agents_parse_through_mirror():
    seeds = [
        AgentSeed.model_validate_json(p.read_text())
        for p in sorted((CONTENT_DIR / "agents").glob("*.json"))
    ]
    assert len(seeds) == 20


def test_relationships_parse_through_mirror():
    rels = Relationships.model_validate_json((CONTENT_DIR / "relationships.json").read_text())
    assert len(rels.edges) == 32


def test_intent_union_parses():
    adapter = TypeAdapter(AgentIntent)
    intent = adapter.validate_python(
        {"agent_id": "maren_alder", "tick": 0, "kind": "move_to", "destination": "gilded_perch"}
    )
    assert intent.root.kind == "move_to"
