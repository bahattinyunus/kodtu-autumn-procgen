"""
Cellular Automata (B678/S345678), BFS Flood-Fill Connectivity Solver,
Bresenham + Drunkard's Walk Corridor Carver, and Dijkstra Threat Budgeting.
"""

from __future__ import annotations
from collections import deque
from typing import List, Tuple, Dict
import numpy as np
from src.procgen.prng import Xoshiro256StarStar


def bresenham_line(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    """
    Classic Bresenham integer line rasterization algorithm between (x0, y0) and (x1, y1).
    """
    points: List[Tuple[int, int]] = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
    return points


def step_cellular_automata_b678_s345678(grid: np.ndarray) -> np.ndarray:
    """
    Executes one Cellular Automata iteration using the B678/S345678 rule on a binary matrix
    where 1 = solid wall/canopy and 0 = walkable clearing.
    - A walkable cell (0) becomes wall (1) if it has 6, 7, or 8 wall neighbors (B678).
    - A wall cell (1) survives as wall (1) if it has 3..8 wall neighbors (S345678).
    Border cells (margin=2) are kept solid (1) to enclose the map.
    """
    height, width = grid.shape
    padded = np.pad(grid, pad_width=1, mode="constant", constant_values=1)

    # Sum 8 Moore neighbors
    neighbor_walls = (
        padded[0:height, 0:width]
        + padded[0:height, 1 : width + 1]
        + padded[0:height, 2 : width + 2]
        + padded[1 : height + 1, 0:width]
        + padded[1 : height + 1, 2 : width + 2]
        + padded[2 : height + 2, 0:width]
        + padded[2 : height + 2, 1 : width + 1]
        + padded[2 : height + 2, 2 : width + 2]
    )

    born = (grid == 0) & (neighbor_walls >= 6)
    survive = (grid == 1) & (neighbor_walls >= 3)
    next_grid = np.where(born | survive, 1, 0).astype(np.int32)

    # Enforce outer perimeter wall
    next_grid[0:2, :] = 1
    next_grid[-2:, :] = 1
    next_grid[:, 0:2] = 1
    next_grid[:, -2:] = 1
    return next_grid


def carve_drunkard_bresenham_corridor(
    grid: np.ndarray,
    start: Tuple[int, int],
    end: Tuple[int, int],
    prng: Xoshiro256StarStar,
    radius: int = 1,
) -> List[Tuple[int, int]]:
    """
    Carves an organic forest path between `start` (x0, y0) and `end` (x1, y1)
    using a hybrid of Bresenham's Line Algorithm and Drunkard's Walk jitter.
    Returns the list of spine points carved.
    """
    height, width = grid.shape
    line_pts = bresenham_line(start[0], start[1], end[0], end[1])
    carved_spine: List[Tuple[int, int]] = []

    jitter_x, jitter_y = 0, 0
    for idx, (bx, by) in enumerate(line_pts):
        if 0 < idx < len(line_pts) - 1 and prng.random() < 0.45:
            jitter_x = max(-1, min(1, jitter_x + prng.randint(-1, 1)))
            jitter_y = max(-1, min(1, jitter_y + prng.randint(-1, 1)))
        else:
            jitter_x = 0
            jitter_y = 0

        cx = max(3, min(width - 4, bx + jitter_x))
        cy = max(3, min(height - 4, by + jitter_y))
        carved_spine.append((cx, cy))

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = cx + dx, cy + dy
                if 2 <= nx < width - 2 and 2 <= ny < height - 2:
                    grid[ny, nx] = 0

    return carved_spine


def find_connected_clearings(grid: np.ndarray) -> List[List[Tuple[int, int]]]:
    """
    Runs 4-directional Breadth-First Search (BFS) Flood-Fill across the binary grid
    to find all connected components of walkable tiles (grid == 0).
    Returns components sorted largest-first.
    """
    height, width = grid.shape
    visited = np.zeros((height, width), dtype=bool)
    components: List[List[Tuple[int, int]]] = []

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y, x] == 0 and not visited[y, x]:
                comp: List[Tuple[int, int]] = []
                queue = deque([(x, y)])
                visited[y, x] = True
                while queue:
                    cx, cy = queue.popleft()
                    comp.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            if grid[ny, nx] == 0 and not visited[ny, nx]:
                                visited[ny, nx] = True
                                queue.append((nx, ny))
                components.append(comp)

    components.sort(key=len, reverse=True)
    return components


def sculpt_connected_topology(
    elevation: np.ndarray,
    prng: Xoshiro256StarStar,
    wall_threshold: float = 0.56,
    ca_iterations: int = 4,
    min_clearing_size: int = 18,
) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
    """
    Full Stage-2 Topological Sculpting Pipeline:
    1. Converts fBm elevation matrix into a binary obstacle matrix.
    2. Carves initial organic glade seeds via Drunkard's Walk so dense seeds remain rich.
    3. Runs B678/S345678 Cellular Automata iterations.
    4. Runs BFS Flood-Fill:
       - Connects significant secondary clearings (>= min_clearing_size) to the main
         clearing via Bresenham + Drunkard's Walk corridors.
       - Culls tiny unreachable orphan pockets (< min_clearing_size) by filling them.
    5. Guarantees 100% single-component connectivity of all walkable tiles.
    """
    height, width = elevation.shape
    grid = (elevation >= wall_threshold).astype(np.int32)

    # Outer border enclosure
    grid[0:2, :] = 1
    grid[-2:, :] = 1
    grid[:, 0:2] = 1
    grid[:, -2:] = 1

    # Seed a central clearing and 4 satellite clearings so any noise distribution yields rich glades
    cx, cy = width // 2, height // 2
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            if dx * dx + dy * dy <= 18:
                grid[cy + dy, cx + dx] = 0

    for _ in range(4):
        gx = prng.randint(8, width - 9)
        gy = prng.randint(8, height - 9)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                if dx * dx + dy * dy <= 10:
                    grid[gy + dy, gx + dx] = 0

    # Cellular Automata smoothing iterations (B678/S345678)
    for _ in range(ca_iterations):
        grid = step_cellular_automata_b678_s345678(grid)

    # Identify connected components via BFS Flood-Fill
    components = find_connected_clearings(grid)
    corridor_tiles: List[Tuple[int, int]] = []

    if not components:
        # Fallback guarantee if everything became solid
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                grid[cy + dy, cx + dx] = 0
        components = find_connected_clearings(grid)

    main_comp = components[0]
    for comp in components[1:]:
        if len(comp) >= min_clearing_size:
            # Connect this glade to the nearest tile in main_comp using Bresenham + Drunkard's Walk
            rep_a = comp[len(comp) // 2]
            # Sample candidate anchor points from main_comp for speed
            step = max(1, len(main_comp) // 40)
            best_b = min(
                main_comp[::step],
                key=lambda p: (p[0] - rep_a[0]) ** 2 + (p[1] - rep_a[1]) ** 2,
            )
            carved = carve_drunkard_bresenham_corridor(grid, rep_a, best_b, prng, radius=1)
            corridor_tiles.extend(carved)
            main_comp.extend(comp)
        else:
            # Orphan culling: fill tiny unreachable pockets
            for ox, oy in comp:
                grid[oy, ox] = 1

    # Final verification BFS pass to guarantee 100% single connected component
    final_components = find_connected_clearings(grid)
    if len(final_components) > 1:
        for orphan in final_components[1:]:
            for ox, oy in orphan:
                grid[oy, ox] = 1

    return grid, corridor_tiles


def compute_dijkstra_distance_field(
    grid: np.ndarray,
    spawn_tile: Tuple[int, int],
) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int], List[Tuple[int, int]]]:
    """
    Computes an exact Dijkstra / BFS geodesic distance field from `spawn_tile`
    across all walkable tiles (grid == 0).

    Returns:
    - dist_matrix: int32 array of step distances (-1 for walls)
    - norm_dist: float64 array normalized to [0.0, 1.0] for Threat Budgeting & [F4] overlay
    - shrine_tile: (x, y) coordinates of the Ancient Autumn Shrine near maximum geodesic distance
    - shortest_path: list of (x, y) tiles forming the shortest path from spawn_tile to shrine_tile
    """
    height, width = grid.shape
    dist_matrix = np.full((height, width), -1, dtype=np.int32)
    parent_map: Dict[Tuple[int, int], Tuple[int, int]] = {}

    sx, sy = spawn_tile
    dist_matrix[sy, sx] = 0
    queue = deque([(sx, sy)])

    max_dist = 0
    farthest_candidates: List[Tuple[int, int]] = [(sx, sy)]

    while queue:
        cx, cy = queue.popleft()
        cd = int(dist_matrix[cy, cx])
        if cd > max_dist:
            max_dist = cd
            farthest_candidates = [(cx, cy)]
        elif cd == max_dist:
            farthest_candidates.append((cx, cy))

        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < width and 0 <= ny < height:
                if grid[ny, nx] == 0 and dist_matrix[ny, nx] == -1:
                    dist_matrix[ny, nx] = cd + 1
                    parent_map[(nx, ny)] = (cx, cy)
                    queue.append((nx, ny))

    # Prefer a shrine tile that has open neighbors so the shrine sits in a clearing
    shrine_tile = farthest_candidates[0]
    for fx, fy in reversed(farthest_candidates):
        if 3 <= fx < width - 3 and 3 <= fy < height - 3:
            shrine_tile = (fx, fy)
            break

    # Reconstruct shortest path from spawn_tile to shrine_tile
    shortest_path: List[Tuple[int, int]] = []
    curr = shrine_tile
    while curr in parent_map:
        shortest_path.append(curr)
        curr = parent_map[curr]
    shortest_path.append(spawn_tile)
    shortest_path.reverse()

    norm_dist = np.zeros((height, width), dtype=np.float64)
    if max_dist > 0:
        valid = dist_matrix >= 0
        norm_dist[valid] = dist_matrix[valid] / float(max_dist)

    return dist_matrix, norm_dist, shrine_tile, shortest_path
