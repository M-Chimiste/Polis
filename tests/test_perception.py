"""P11 semantics: sight cone AND occlusion, hearing occlusion-exempt."""
from sim.content import load_agents, load_town
from sim.perception import PerceptionParams, perceive
from sim.world import World

TOWN = load_town()
SEEDS = load_agents()
PARAMS = PerceptionParams(sight_cone_half_angle_deg=65, sight_range=8, hearing_radius=3)


def make_world():
    return World(TOWN, SEEDS, master_seed=7)


def place(world, aid, pos, facing=(0, 1)):
    world.agents[aid].pos = pos
    world.agents[aid].facing = facing


def test_sees_agent_in_cone_same_space():
    world = make_world()
    place(world, "sela_crane", (2, 2), facing=(0, 1))   # outdoors
    place(world, "petra_quill", (2, 6))                  # straight ahead, outdoors
    result = perceive(world, PARAMS, "sela_crane")
    assert "petra_quill" in result["seen"]


def test_behind_is_invisible_but_audible():
    world = make_world()
    place(world, "sela_crane", (2, 10), facing=(0, 1))   # facing +y
    place(world, "petra_quill", (2, 8))                  # behind, 2 cells
    result = perceive(world, PARAMS, "sela_crane")
    assert "petra_quill" not in result["seen"]
    assert "petra_quill" in result["heard"]  # within hearing radius, cone-exempt


def test_out_of_range_invisible():
    world = make_world()
    place(world, "sela_crane", (2, 2), facing=(0, 1))
    place(world, "petra_quill", (2, 12))  # 10 > sight_range 8
    result = perceive(world, PARAMS, "sela_crane")
    assert "petra_quill" not in result["seen"]
    assert "petra_quill" not in result["heard"]


def test_occluder_blocks_sight_not_hearing():
    world = make_world()
    # market_stalls occluder at (23, 22) radius 1.5, inside market_square
    place(world, "sela_crane", (23, 20), facing=(0, 1))
    place(world, "petra_quill", (23, 23))  # dead behind the stalls, dist 3
    assert world.location_of("sela_crane") == "market_square"
    assert world.location_of("petra_quill") == "market_square"
    result = perceive(world, PARAMS, "sela_crane")
    assert "petra_quill" not in result["seen"]
    assert "petra_quill" in result["heard"]  # occlusion-exempt


def test_different_location_blocks_sight():
    world = make_world()
    tavern = next(l for l in TOWN["locations"] if l["id"] == "gilded_perch")
    x, y, w, h = tavern["rect"]
    place(world, "maren_alder", (x + 1, y + 1), facing=(1, 0))  # inside tavern
    place(world, "sela_crane", (x + 3, y - 2))                   # outside, in cone range
    result = perceive(world, PARAMS, "maren_alder")
    assert "sela_crane" not in result["seen"]


def test_perception_params_are_config():
    world = make_world()
    place(world, "sela_crane", (2, 2), facing=(0, 1))
    place(world, "petra_quill", (2, 6))
    deaf_blind = PerceptionParams(sight_cone_half_angle_deg=5, sight_range=1, hearing_radius=0.5)
    result = perceive(world, deaf_blind, "sela_crane")
    assert result == {"seen": [], "heard": []}


def test_perceive_is_pure():
    world = make_world()
    before = {aid: (a.pos, a.facing, a.status) for aid, a in world.agents.items()}
    for aid in world.agents:
        perceive(world, PARAMS, aid)
    after = {aid: (a.pos, a.facing, a.status) for aid, a in world.agents.items()}
    assert before == after
