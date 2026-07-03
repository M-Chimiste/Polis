"""Grid walkability and deterministic A* pathfinding.

Location rects are rooms: perimeter cells are walls except the door cell.
Interiors and open ground are walkable. Ties in A* break on (f, g, cell) so
paths are identical across runs and platforms.
"""
from __future__ import annotations

import heapq

Cell = tuple[int, int]


def build_blocked(town: dict) -> set[Cell]:
    blocked: set[Cell] = set()
    doors: set[Cell] = set()
    for loc in town["locations"]:
        x, y, w, h = loc["rect"]
        doors.add(tuple(loc["door"]))
        for cx in range(x, x + w + 1):
            blocked.add((cx, y))
            blocked.add((cx, y + h))
        for cy in range(y, y + h + 1):
            blocked.add((x, cy))
            blocked.add((x + w, cy))
    return blocked - doors


def locate(town: dict, cell: Cell) -> str | None:
    """Location id containing the cell, or None (outdoors).

    A door cell belongs to its own location — doors may lie on a neighbouring
    rect's edge, so doors resolve first. Rect membership is strictly interior:
    perimeter cells are walls and belong to no location.
    """
    for loc in town["locations"]:
        if tuple(loc["door"]) == cell:
            return loc["id"]
    for loc in town["locations"]:
        x, y, w, h = loc["rect"]
        if x < cell[0] < x + w and y < cell[1] < y + h:
            return loc["id"]
    return None


def astar(blocked: set[Cell], width: int, height: int, start: Cell, goal: Cell) -> list[Cell] | None:
    """4-neighbour shortest path, excluding start, including goal. None if unreachable."""
    if start == goal:
        return []

    def h(c: Cell) -> int:
        return abs(c[0] - goal[0]) + abs(c[1] - goal[1])

    frontier: list[tuple[int, int, Cell]] = [(h(start), 0, start)]
    came_from: dict[Cell, Cell] = {}
    cost: dict[Cell, int] = {start: 0}
    while frontier:
        _, g, current = heapq.heappop(frontier)
        if current == goal:
            path = [current]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            return path[1:]
        if g > cost.get(current, g):
            continue
        cx, cy = current
        for nxt in ((cx, cy - 1), (cx - 1, cy), (cx + 1, cy), (cx, cy + 1)):
            if not (0 <= nxt[0] < width and 0 <= nxt[1] < height):
                continue
            if nxt in blocked and nxt != goal:
                continue
            ng = g + 1
            if ng < cost.get(nxt, 1 << 30):
                cost[nxt] = ng
                came_from[nxt] = current
                heapq.heappush(frontier, (ng + h(nxt), ng, nxt))
    return None
