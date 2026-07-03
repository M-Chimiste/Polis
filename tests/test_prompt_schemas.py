"""Grounding schemas are built per call with enums of what exists — a
hallucinated location/object/partner must be unrepresentable under
grammar-constrained decoding (live-gate lesson 2026-07-03)."""
import jsonschema
import pytest

from cognition import prompts

LOCATIONS = ["crane_bakery", "gilded_perch", "village_well"]
OBJECTS = [
    {"id": "bread_oven", "interactions": ["fire", "bake"]},
    {"id": "kneading_table", "interactions": ["knead"]},
]


def valid(schema, instance) -> bool:
    try:
        jsonschema.validate(instance, schema)
        return True
    except jsonschema.ValidationError:
        return False


def test_agenda_locations_are_town_enum():
    schema = prompts.agenda_schema(LOCATIONS)
    block = {"start": "06:00", "end": "12:00", "activity": "bake", "location": "crane_bakery"}
    assert valid(schema, {"agenda": [block]})
    assert not valid(schema, {"agenda": [{**block, "location": "market_district"}]})


def test_steps_objects_are_location_enum():
    schema = prompts.steps_schema(LOCATIONS, OBJECTS)
    assert valid(schema, {"steps": [
        {"minutes": 5, "kind": "move_to", "destination": "crane_bakery"},
        {"minutes": 30, "kind": "use_object", "object_id": "bread_oven", "interaction": "bake"},
    ]})
    # object from another location: unrepresentable
    assert not valid(schema, {"steps": [
        {"minutes": 30, "kind": "use_object", "object_id": "well_bucket", "interaction": "draw"}]})
    # hallucinated destination: unrepresentable
    assert not valid(schema, {"steps": [
        {"minutes": 5, "kind": "move_to", "destination": "marketplace"}]})


def test_steps_without_objects_offer_no_use_object():
    schema = prompts.steps_schema(LOCATIONS, [])
    assert not valid(schema, {"steps": [
        {"minutes": 30, "kind": "use_object", "object_id": "bread_oven", "interaction": "bake"}]})
    assert valid(schema, {"steps": [{"minutes": 5, "kind": "idle"}]})


def test_reaction_partner_is_candidate_enum():
    schema = prompts.reaction_schema(["ilse_alder", "piet_alder"])
    assert valid(schema, {"action": "start_conversation", "partner": "piet_alder"})
    assert not valid(schema, {"action": "start_conversation", "partner": "sela_crane"})


def test_reaction_without_candidates_forces_continue():
    schema = prompts.reaction_schema([])
    assert valid(schema, {"action": "continue"})
    assert not valid(schema, {"action": "start_conversation"})
