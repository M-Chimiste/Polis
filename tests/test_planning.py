"""Plan cache: fallbacks, grounding, block lookup."""
from cognition.planning import (
    PlanCache, fallback_agenda, fallback_steps, steps_from_payload,
)
from sim.content import load_agents, load_town
from sim.world import World

SEEDS = load_agents()
WORLD = World(load_town(), SEEDS, master_seed=1)


def test_fallback_agenda_is_anchor_shaped():
    agenda = fallback_agenda(SEEDS["sela_crane"])
    assert agenda[0]["start"] == SEEDS["sela_crane"]["daily_anchors"]["wake"]
    assert agenda[-1]["activity"] == "sleep"
    assert agenda[1]["location"] == SEEDS["sela_crane"]["workplace"]


def test_current_block_handles_midnight_wrap():
    cache = PlanCache(day=0, agenda=fallback_agenda(SEEDS["maren_alder"]))
    # maren sleeps 23:30 -> 06:00; 02:00 must land in the sleep block
    located = cache.current_block(2 * 60)
    assert located is not None and located[1]["activity"] == "sleep"


def test_steps_grounding_degrades_to_idle():
    block = {"start": "09:00", "end": "12:00", "activity": "work", "location": "gilded_perch"}
    payload = {"steps": [
        {"minutes": 30, "kind": "use_object", "object_id": "ale_barrel", "interaction": "tap"},
        {"minutes": 30, "kind": "use_object", "object_id": "ale_barrel", "interaction": "smash"},
        {"minutes": 30, "kind": "use_object", "object_id": "millstone", "interaction": "engage"},
        {"minutes": 30, "kind": "use_object", "object_id": "phantom", "interaction": "poke"},
        {"minutes": 5, "kind": "move_to"},
    ]}
    steps = steps_from_payload(payload, block, WORLD.objects)
    kinds = [(s.kind, s.object_id) for s in steps]
    assert kinds[0] == ("use_object", "ale_barrel")   # grounded
    assert kinds[1][0] == "idle"                       # bad verb
    assert kinds[2][0] == "idle"                       # object elsewhere
    assert kinds[3][0] == "idle"                       # unknown object
    assert kinds[4][0] == "idle"                       # move without destination


def test_fallback_steps_shapes():
    sleep_steps = fallback_steps({"activity": "sleep", "location": "weaver_cottage"})
    assert sleep_steps[0]["kind"] == "sleep"
    work_steps = fallback_steps({"activity": "work", "location": "vosse_smithy"})
    assert work_steps[0] == {"minutes": 1, "kind": "move_to", "destination": "vosse_smithy"}
