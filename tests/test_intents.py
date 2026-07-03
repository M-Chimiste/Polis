"""The intent wall: only grammar-conforming intents may touch world state."""
import pytest

import schemas

VALID = [
    {"agent_id": "maren_alder", "tick": 0, "kind": "move_to", "destination": "gilded_perch"},
    {"agent_id": "piet_alder", "tick": 12, "kind": "use_object", "object_id": "ale_barrel", "interaction": "tap"},
    {"agent_id": "ilse_alder", "tick": 40, "kind": "converse_with", "partner_id": "corin_hale", "mode": "request"},
    {"agent_id": "corin_hale", "tick": 41, "kind": "converse_with", "partner_id": "ilse_alder", "mode": "accept"},
    {"agent_id": "nan_weaver", "tick": 99, "kind": "idle"},
    {"agent_id": "anselm", "tick": 500, "kind": "sleep"},
]

INVALID = [
    # freeform action strings never mutate world state
    "walk over to the tavern and say hi",
    # unknown kind
    {"agent_id": "maren_alder", "tick": 0, "kind": "dramatic_reveal"},
    # move without destination
    {"agent_id": "maren_alder", "tick": 0, "kind": "move_to"},
    # extra payload smuggled past the grammar
    {"agent_id": "maren_alder", "tick": 0, "kind": "idle", "narration": "she sighs meaningfully"},
    # bad converse mode
    {"agent_id": "a", "tick": 0, "kind": "converse_with", "partner_id": "b", "mode": "monologue"},
    # negative tick
    {"agent_id": "maren_alder", "tick": -1, "kind": "sleep"},
    # missing agent
    {"tick": 0, "kind": "sleep"},
]


@pytest.mark.parametrize("intent", VALID)
def test_valid_intents_pass(intent):
    assert schemas.errors("agent_intent", intent) == []


@pytest.mark.parametrize("intent", INVALID)
def test_invalid_intents_rejected(intent):
    assert schemas.errors("agent_intent", intent) != []
