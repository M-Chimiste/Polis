"""Pathfinding: walls block, doors admit, paths are deterministic."""
from sim.content import load_town
from sim.grid import astar, build_blocked, locate

TOWN = load_town()
BLOCKED = build_blocked(TOWN)
W, H = TOWN["grid"]["width"], TOWN["grid"]["height"]


def loc(loc_id):
    return next(l for l in TOWN["locations"] if l["id"] == loc_id)


def test_walls_blocked_doors_open():
    tavern = loc("gilded_perch")
    x, y, w, h = tavern["rect"]
    door = tuple(tavern["door"])
    assert door not in BLOCKED
    perimeter_sample = (x, y)
    assert perimeter_sample in BLOCKED or perimeter_sample == door


def test_every_location_reachable_from_every_other():
    doors = [tuple(l["door"]) for l in TOWN["locations"]]
    start = doors[0]
    for goal in doors[1:]:
        path = astar(BLOCKED, W, H, start, goal)
        assert path is not None, f"unreachable: {goal}"
        assert path[-1] == goal


def test_path_deterministic_and_shortest_shape():
    a = tuple(loc("gilded_perch")["door"])
    b = tuple(loc("village_well")["door"])
    p1 = astar(BLOCKED, W, H, a, b)
    p2 = astar(BLOCKED, W, H, a, b)
    assert p1 == p2
    assert len(p1) >= abs(a[0] - b[0]) + abs(a[1] - b[1])
    # contiguous 4-neighbour steps, none through walls
    prev = a
    for cell in p1:
        assert abs(cell[0] - prev[0]) + abs(cell[1] - prev[1]) == 1
        assert cell not in BLOCKED or cell == b
        prev = cell


def test_locate_inside_outside():
    tavern = loc("gilded_perch")
    x, y, w, h = tavern["rect"]
    assert locate(TOWN, (x + 1, y + 1)) == "gilded_perch"
    assert locate(TOWN, (0, 0)) is None
