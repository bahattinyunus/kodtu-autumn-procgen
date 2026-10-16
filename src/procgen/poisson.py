"""
Bridson's Fast Poisson Disk Sampling (O(N) Blue-Noise Distribution) &
Ecological Autumn Foliage Distributor.

Guarantees minimum Euclidean distance `r` between all sampled points while
preventing artificial clustering or void gaps.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import List, Set, Tuple
import numpy as np
from src.procgen.prng import Xoshiro256StarStar
from src.procgen.noise import (
    BIOME_DAMP_DECAY,
    BIOME_AMBER_GROVE,
    BIOME_CRISP_GOLDEN,
)


@dataclass(frozen=True)
class PropPlacement:
    """Represents a deterministically placed ecological object in the autumn forest."""

    x: float          # Tile-space X coordinate
    y: float          # Tile-space Y coordinate
    prop_type: str    # 'tree_maple', 'tree_birch', 'tree_oak', 'bush_amber', 'leaf_pile', 'mushroom', 'log', 'stone'
    solid: bool       # Whether this prop has a physical collision trunk/base
    biome: int        # Biome ID where it spawned
    variant: int      # Visual sprite sub-variant


def fast_poisson_disk_sampling(
    width: float,
    height: float,
    min_dist: float,
    prng: Xoshiro256StarStar,
    k_candidates: int = 30,
    margin: float = 2.5,
) -> List[Tuple[float, float]]:
    """
    Bridson's O(N) Fast Poisson Disk Sampling in a 2D domain [margin, width-margin] x [margin, height-margin].
    Every pair of returned points (p_i, p_j) strictly satisfies ||p_i - p_j||_2 >= min_dist.
    """
    cell_size = min_dist / math.sqrt(2.0)
    grid_w = max(1, int(math.ceil(width / cell_size)))
    grid_h = max(1, int(math.ceil(height / cell_size)))

    # -1 indicates empty cell; otherwise stores index in `samples`
    accel_grid = [-1] * (grid_w * grid_h)
    samples: List[Tuple[float, float]] = []
    active_list: List[int] = []

    min_dist_sq = min_dist * min_dist

    def _insert_point(pt: Tuple[float, float]) -> None:
        idx = len(samples)
        samples.append(pt)
        active_list.append(idx)
        gx = int(pt[0] / cell_size)
        gy = int(pt[1] / cell_size)
        accel_grid[gy * grid_w + gx] = idx

    def _is_valid(px: float, py: float) -> bool:
        if px < margin or px >= width - margin or py < margin or py >= height - margin:
            return False
        gx = int(px / cell_size)
        gy = int(py / cell_size)
        x0 = max(0, gx - 2)
        x1 = min(grid_w - 1, gx + 2)
        y0 = max(0, gy - 2)
        y1 = min(grid_h - 1, gy + 2)
        for ny in range(y0, y1 + 1):
            row_offset = ny * grid_w
            for nx in range(x0, x1 + 1):
                s_idx = accel_grid[row_offset + nx]
                if s_idx != -1:
                    sx, sy = samples[s_idx]
                    dx = px - sx
                    dy = py - sy
                    if dx * dx + dy * dy < min_dist_sq:
                        return False
        return True

    # Initial point near center of domain
    init_x = prng.uniform(margin, width - margin)
    init_y = prng.uniform(margin, height - margin)
    _insert_point((init_x, init_y))

    while active_list:
        active_pos = prng.randint(0, len(active_list) - 1)
        center_idx = active_list[active_pos]
        cx, cy = samples[center_idx]
        found = False

        for _ in range(k_candidates):
            angle = prng.uniform(0.0, 2.0 * math.pi)
            radius = prng.uniform(min_dist, 2.0 * min_dist)
            nx = cx + math.cos(angle) * radius
            ny = cy + math.sin(angle) * radius
            if _is_valid(nx, ny):
                _insert_point((nx, ny))
                found = True
                break

        if not found:
            # Swap-and-pop from active list in O(1)
            active_list[active_pos] = active_list[-1]
            active_list.pop()

    return samples


def distribute_ecological_props(
    walkable_grid: np.ndarray,
    biome_grid: np.ndarray,
    moisture_grid: np.ndarray,
    spawn_tile: Tuple[int, int],
    shrine_tile: Tuple[int, int],
    shortest_path: List[Tuple[int, int]],
    prng: Xoshiro256StarStar,
    min_dist: float = 2.6,
) -> List[PropPlacement]:
    """
    Distributes autumn trees, bushes, crunchy leaf piles, glowing mushrooms, mossy logs,
    and runic stones across walkable clearings using Fast Poisson Disk Sampling.
    Never blocks narrow corridors or the guaranteed shortest path between Spawn and Shrine.
    """
    height, width = walkable_grid.shape
    raw_points = fast_poisson_disk_sampling(
        float(width), float(height), min_dist=min_dist, prng=prng, margin=3.0
    )

    # Protect the shortest path spine so solid trees/logs cannot sever topological connectivity
    protected_tiles: Set[Tuple[int, int]] = set(shortest_path)
    sx, sy = spawn_tile
    ex, ey = shrine_tile

    props: List[PropPlacement] = []

    for px, py in raw_points:
        tx, ty = int(px), int(py)
        if not (2 <= tx < width - 2 and 2 <= ty < height - 2):
            continue
        if walkable_grid[ty, tx] != 0:
            continue

        # Exclusion radius around player spawn and Ancient Shrine
        dist_spawn_sq = (px - (sx + 0.5)) ** 2 + (py - (sy + 0.5)) ** 2
        dist_shrine_sq = (px - (ex + 0.5)) ** 2 + (py - (ey + 0.5)) ** 2
        if dist_spawn_sq < 9.0 or dist_shrine_sq < 10.0:
            continue

        # Check if tile has all 8 walkable neighbors (safe for solid tree trunks)
        open_neighbors = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if walkable_grid[ty + dy, tx + dx] == 0:
                    open_neighbors += 1
        can_place_solid = (open_neighbors == 9) and ((tx, ty) not in protected_tiles)

        biome = int(biome_grid[ty, tx])
        moisture = float(moisture_grid[ty, tx])
        roll = prng.random()
        variant = prng.randint(0, 2)

        if biome == BIOME_DAMP_DECAY:
            # High moisture: Crimson maples, glowing mushrooms, mossy logs
            if can_place_solid and roll < 0.34:
                prop_type = "tree_maple"
                solid = True
            elif can_place_solid and roll < 0.48:
                prop_type = "log"
                solid = True
            elif roll < 0.80:
                prop_type = "mushroom"
                solid = False
            else:
                prop_type = "leaf_pile"
                solid = False
        elif biome == BIOME_CRISP_GOLDEN:
            # Low moisture: Sunlit golden birches, abundant crunchy leaf piles, runic stones
            if can_place_solid and roll < 0.32:
                prop_type = "tree_birch"
                solid = True
            elif can_place_solid and roll < 0.42:
                prop_type = "stone"
                solid = True
            elif roll < 0.85:
                prop_type = "leaf_pile"
                solid = False
            else:
                prop_type = "bush_amber"
                solid = False
        else:
            # Balanced Burnt Amber Grove: Oaks, Maples, Birches, Amber Bushes, Leaf Piles
            if can_place_solid and roll < 0.38:
                if moisture > 0.52:
                    prop_type = "tree_maple"
                elif moisture < 0.46:
                    prop_type = "tree_birch"
                else:
                    prop_type = "tree_oak"
                solid = True
            elif can_place_solid and roll < 0.46:
                prop_type = "stone" if prng.random() < 0.5 else "log"
                solid = True
            elif roll < 0.72:
                prop_type = "leaf_pile"
                solid = False
            elif roll < 0.90:
                prop_type = "bush_amber"
                solid = False
            else:
                prop_type = "mushroom"
                solid = False

        # Snap to tile center for crisp pixel-grid alignment
        props.append(
            PropPlacement(
                x=float(tx) + 0.5,
                y=float(ty) + 0.5,
                prop_type=prop_type,
                solid=solid,
                biome=biome,
                variant=variant,
            )
        )

    return props
