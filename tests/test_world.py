"""World step: intents are the only mutation path; bad intents bounce."""
from sim.content import load_agents, load_town
from sim.world import World

TOWN = load_town()
SEEDS = load_agents()


def make_world():
    return World(TOWN, SEEDS, master_seed=7)


def step_until(world, agent_id, predicate, limit=500):
    for _ in range(limit):
        if predicate(world):
            return True
        world.step({})
    return predicate(world)


def test_move_intent_walks_agent_to_destination():
    world = make_world()
    aid = "sela_crane"
    events = world.step({aid: {"agent_id": aid, "tick": 0, "kind": "move_to", "destination": "village_well"}})
    assert not any(k == "intent_rejected" for k, _, _ in events)
    assert step_until(world, aid, lambda w: w.location_of(aid) == "village_well")
    assert world.agents[aid].status == "idle"


def test_arrival_emits_event_once():
    world = make_world()
    aid = "sela_crane"
    world.step({aid: {"agent_id": aid, "tick": 0, "kind": "move_to", "destination": "village_well"}})
    arrived = []
    for _ in range(500):
        arrived += [e for e in world.step({}) if e[0] == "agent_arrived"]
        if arrived:
            break
    assert len(arrived) == 1
    assert arrived[0][2]["location"] == "village_well"


def test_freeform_and_malformed_intents_rejected():
    world = make_world()
    aid = "sela_crane"
    for bad in [
        "saunter to the well",
        {"agent_id": aid, "tick": 0, "kind": "dramatic_reveal"},
        {"agent_id": aid, "tick": 0, "kind": "move_to"},
        {"agent_id": aid, "tick": 0, "kind": "move_to", "destination": "atlantis"},
        {"agent_id": "somebody_else", "tick": 0, "kind": "idle"},
    ]:
        events = world.step({aid: bad})
        kinds = [k for k, _, _ in events]
        assert "intent_rejected" in kinds, bad
    # nothing moved
    assert world.agents[aid].pos == world.doors[SEEDS[aid]["home"]]


def test_conversation_request_accept_decline():
    world = make_world()
    # spouses start at the same door (same home)
    a, b = "maren_alder", "piet_alder"
    events = world.step({a: {"agent_id": a, "tick": 0, "kind": "converse_with", "partner_id": b, "mode": "request"}})
    assert ("conversation_requested", a, {"partner": b}) in events
    events = world.step({b: {"agent_id": b, "tick": 1, "kind": "converse_with", "partner_id": a, "mode": "accept"}})
    assert ("conversation_started", b, {"partner": a}) in events
    # accept again: no pending request left
    events = world.step({b: {"agent_id": b, "tick": 2, "kind": "converse_with", "partner_id": a, "mode": "accept"}})
    assert any(k == "intent_rejected" for k, _, _ in events)


def test_conversation_requires_colocation():
    world = make_world()
    a, b = "maren_alder", "odile_marsh"  # different homes
    if world.co_located(a, b):
        return
    events = world.step({a: {"agent_id": a, "tick": 0, "kind": "converse_with", "partner_id": b, "mode": "request"}})
    assert any(k == "intent_rejected" for k, _, _ in events)


def test_use_object_transitions_state():
    world = make_world()
    aid = "maren_alder"  # starts at the gilded_perch door, where the ale barrel is
    assert world.objects["ale_barrel"]["state"] == "sealed"
    events = world.step({aid: {"agent_id": aid, "tick": 0, "kind": "use_object", "object_id": "ale_barrel", "interaction": "tap"}})
    assert ("object_state_changed", aid,
            {"object_id": "ale_barrel", "interaction": "tap", "from": "sealed", "to": "tapped"}) in events
    assert world.objects["ale_barrel"]["state"] == "tapped"


def test_use_object_semantic_rejections():
    world = make_world()
    at_perch, elsewhere = "maren_alder", "sela_crane"
    cases = [
        (at_perch, {"object_id": "phantom_chair", "interaction": "sit"}),   # unknown object
        (elsewhere, {"object_id": "ale_barrel", "interaction": "tap"}),      # wrong location
        (at_perch, {"object_id": "ale_barrel", "interaction": "smash"}),    # verb not allowed
    ]
    for tick, (aid, params) in enumerate(cases):
        intent = {"agent_id": aid, "tick": tick, "kind": "use_object", **params}
        events = world.step({aid: intent})
        assert any(k == "intent_rejected" for k, _, _ in events), params
    assert world.objects["ale_barrel"]["state"] == "sealed"


def test_sleep_wake_status_events():
    world = make_world()
    aid = "sela_crane"
    events = world.step({aid: {"agent_id": aid, "tick": 0, "kind": "idle"}})
    assert ("agent_status_changed", aid, {"status": "idle"}) in events
    events = world.step({aid: {"agent_id": aid, "tick": 1, "kind": "sleep"}})
    assert ("agent_status_changed", aid, {"status": "sleeping"}) in events
    # idempotent: sleeping again emits nothing
    events = world.step({aid: {"agent_id": aid, "tick": 2, "kind": "sleep"}})
    assert events == []
