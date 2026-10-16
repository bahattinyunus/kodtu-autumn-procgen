"""
Procedural Micro-Structure Synthesizer (Campfires, Runic Stone Circles, Boardwalks)
and A* (A-Star) / Vector Flow-Field Pathfinding Solver.
"""

from __future__ import annotations
from dataclasses import dataclass
import heapq
import math
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from src.procgen.prng import Xoshiro256StarStar


@dataclass(frozen=True)
class StructurePlacement:
    """Represents a deterministic procedural micro-structure in the autumn world."""

    tile_x: int
    tile_y: int
    structure_type: str  # 'campfire', 'stone_circle', 'boardwalk'
    radius_tiles: int


def astar_shortest_path(
    walkable_grid: np.ndarray,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    max_steps: int = 1024,
) -> List[Tuple[int, int]]:
    """
    Computes an optimal 4-directional A* path on `walkable_grid` (where 0 = walkable)
    from `start` (x0, y0) to `goal` (x1, y1).
    """
    height, width = walkable_grid.shape
    sx, sy = start
    gx, gy = goal
    if start == goal:
        return [start]
    if not (0 <= gx < width and 0 <= gy < height) or walkable_grid[gy, gx] != 0:
        return [start]

    def _heuristic(ax: int, ay: int) -> int:
        return abs(ax - gx) + abs(ay - gy)

    open_heap: List[Tuple[int, int, Tuple[int, int]]] = []
    heapq.heappush(open_heap, (_heuristic(sx, sy), 0, start))
    came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: Dict[Tuple[int, int], int] = {start: 0}
    closed: Set[Tuple[int, int]] = set()

    steps = 0
    while open_heap and steps < max_steps:
        steps += 1
        _, current_g, current = heapq.heappop(open_heap)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        if current in closed:
            continue
        closed.add(current)
        cx, cy = current

        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if walkable_grid[ny, nx] != 0:
                continue
            neighbor = (nx, ny)
            if neighbor in closed:
                continue
            tentative_g = current_g + 1
            if tentative_g < g_score.get(neighbor, 10**9):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + _heuristic(nx, ny)
                heapq.heappush(open_heap, (f_score, tentative_g, neighbor))

    return [start]


def compute_flow_field_vectors(
    dijkstra_dist: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes a normalized 2D downhill gradient vector field (flow_vx, flow_vy)
    from a Dijkstra geodesic distance matrix so debug overlays and AI agents can
    inspect topological flow directions across the entire map.
    """
    height, width = dijkstra_dist.shape
    flow_vx = np.zeros((height, width), dtype=np.float64)
    flow_vy = np.zeros((height, width), dtype=np.float64)

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            center_d = int(dijkstra_dist[y, x])
            if center_d <= 0:
                continue
            best_dx = 0.0
            best_dy = 0.0
            best_d = center_d
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nd = int(dijkstra_dist[y + dy, x + dx])
                if 0 <= nd < best_d:
                    best_d = nd
                    best_dx = float(dx)
                    best_dy = float(dy)
            flow_vx[y, x] = best_dx
            flow_vy[y, x] = best_dy

    return flow_vx, flow_vy


def synthesize_autumn_structures(
    walkable_grid: np.ndarray,
    dijkstra_norm: np.ndarray,
    spawn_tile: Tuple[int, int],
    shrine_tile: Tuple[int, int],
    shortest_path: List[Tuple[int, int]],
    prng: Xoshiro256StarStar,
) -> List[StructurePlacement]:
    """
    Places deterministic autumn micro-structures:
    1. 'bilim_agaci' (ODTÜ Tree of Science Monument) in the starting glade
    2. 'stone_circle' framing the Ancient Autumn Shrine
    3. 'campfire' safe warmth beacons along mid-distance clearings (d in [0.35, 0.72])
    4. 'boardwalk' (Eymir Pier planks) along damp corridor crossings
    """
    height, width = walkable_grid.shape
    structures: List[StructurePlacement] = [
        StructurePlacement(
            tile_x=shrine_tile[0],
            tile_y=shrine_tile[1],
            structure_type="stone_circle",
            radius_tiles=2,
        )
    ]

    # Place ODTÜ Bilim Ağacı (Tree of Science Monument) 2 tiles North-East or North-West of spawn
    for ox, oy in ((2, -1), (-2, -1), (0, -2), (2, 1)):
        bx, by = spawn_tile[0] + ox, spawn_tile[1] + oy
        if 2 <= bx < width - 2 and 2 <= by < height - 2 and walkable_grid[by, bx] == 0:
            structures.append(
                StructurePlacement(
                    tile_x=bx,
                    tile_y=by,
                    structure_type="bilim_agaci",
                    radius_tiles=1,
                )
            )
            break

    # Select 2 open clearings for Alchemist Campfires
    candidates: List[Tuple[int, int]] = []
    for y in range(4, height - 4):
        for x in range(4, width - 4):
            if walkable_grid[y, x] != 0:
                continue
            d = float(dijkstra_norm[y, x])
            if 0.30 <= d <= 0.75:
                # Require 3x3 open space
                if np.all(walkable_grid[y - 1 : y + 2, x - 1 : x + 2] == 0):
                    candidates.append((x, y))

    prng.shuffle(candidates)
    placed_camps: List[Tuple[int, int]] = []
    for cx, cy in candidates:
        if len(placed_camps) >= 2:
            break
        if (cx - spawn_tile[0]) ** 2 + (cy - spawn_tile[1]) ** 2 < 25:
            continue
        if (cx - shrine_tile[0]) ** 2 + (cy - shrine_tile[1]) ** 2 < 25:
            continue
        if all((cx - px) ** 2 + (cy - py) ** 2 >= 64 for px, py in placed_camps):
            placed_camps.append((cx, cy))
            structures.append(
                StructurePlacement(
                    tile_x=cx,
                    tile_y=cy,
                    structure_type="campfire",
                    radius_tiles=1,
                )
            )

    # Select 1 or 2 open clearings for Historical ODTÜ Inscription Steles (Tarih Kitabeleri)
    placed_kitabes: List[Tuple[int, int]] = []
    for kx, ky in candidates:
        if len(placed_kitabes) >= 2:
            break
        if (kx, ky) in placed_camps:
            continue
        if (kx - spawn_tile[0]) ** 2 + (ky - spawn_tile[1]) ** 2 < 20:
            continue
        if (kx - shrine_tile[0]) ** 2 + (ky - shrine_tile[1]) ** 2 < 20:
            continue
        if all((kx - px) ** 2 + (ky - py) ** 2 >= 36 for px, py in placed_camps):
            if all((kx - kpx) ** 2 + (ky - kpy) ** 2 >= 49 for kpx, kpy in placed_kitabes):
                placed_kitabes.append((kx, ky))
                structures.append(
                    StructurePlacement(
                        tile_x=kx,
                        tile_y=ky,
                        structure_type="odtu_kitabe",
                        radius_tiles=1,
                    )
                )

    # Place wooden boardwalk tiles along a segment of the shortest path
    if len(shortest_path) > 10:
        mid_idx = len(shortest_path) // 2
        for bx, by in shortest_path[max(2, mid_idx - 3) : min(len(shortest_path) - 2, mid_idx + 4)]:
            if (bx, by) not in placed_camps and (bx, by) != spawn_tile and (bx, by) != shrine_tile:
                structures.append(
                    StructurePlacement(
                        tile_x=bx,
                        tile_y=by,
                        structure_type="boardwalk",
                        radius_tiles=0,
                    )
                )

    return structures
