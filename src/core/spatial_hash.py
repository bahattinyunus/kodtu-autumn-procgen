"""
Chunk-Based Spatial Hashing Engine (O(1) Collision & Frustum Queries).

Implements Section 6 of README.md:
- Divides the map into 16x16 tile chunks.
- Collision detection and interactive entity lookups only inspect the player's
  current cell/chunk and immediate neighbors in O(1) time complexity.
"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple, TypeVar, Generic
import numpy as np

from src.procgen.poisson import PropPlacement

T = TypeVar("T")

CHUNK_SIZE_TILES = 16


@dataclass(frozen=True)
class CircleCollider:
    """Represents a circular physical obstacle in tile coordinates."""

    x: float
    y: float
    radius: float
    tag: str


class ChunkSpatialHash:
    """
    Spatial hash partitioning the world into 16x16 tile chunks (for frustum culling)
    and 2x2 tile micro-cells (for O(1) local circle-vs-tile and circle-vs-prop collision).
    """

    def __init__(self, walkable_grid: np.ndarray, props: Iterable[PropPlacement]) -> None:
        self.walkable_grid = walkable_grid
        self.height, self.width = walkable_grid.shape
        self.chunk_props: Dict[Tuple[int, int], List[PropPlacement]] = defaultdict(list)
        self.cell_colliders: Dict[Tuple[int, int], List[CircleCollider]] = defaultdict(list)
        self.leaf_pile_cells: Dict[Tuple[int, int], List[PropPlacement]] = defaultdict(list)
        self.mushroom_cells: Dict[Tuple[int, int], List[PropPlacement]] = defaultdict(list)

        for prop in props:
            cx = int(prop.x) // CHUNK_SIZE_TILES
            cy = int(prop.y) // CHUNK_SIZE_TILES
            self.chunk_props[(cx, cy)].append(prop)

            tx, ty = int(prop.x), int(prop.y)
            if prop.solid:
                radius = 0.34 if prop.prop_type.startswith("tree") else 0.30
                col = CircleCollider(x=prop.x, y=prop.y, radius=radius, tag=prop.prop_type)
                self.cell_colliders[(tx, ty)].append(col)
            elif prop.prop_type == "leaf_pile":
                self.leaf_pile_cells[(tx, ty)].append(prop)
            elif prop.prop_type == "mushroom":
                self.mushroom_cells[(tx, ty)].append(prop)

    def get_props_in_tile_bounds(self, x0: int, y0: int, x1: int, y1: int) -> List[PropPlacement]:
        """Returns all props residing in chunks overlapping the tile frustum [x0..x1, y0..y1]."""
        cx0 = max(0, x0 // CHUNK_SIZE_TILES)
        cy0 = max(0, y0 // CHUNK_SIZE_TILES)
        cx1 = x1 // CHUNK_SIZE_TILES
        cy1 = y1 // CHUNK_SIZE_TILES

        visible: List[PropPlacement] = []
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                for prop in self.chunk_props.get((cx, cy), ()):
                    if x0 - 2 <= prop.x <= x1 + 2 and y0 - 2 <= prop.y <= y1 + 2:
                        visible.append(prop)
        return visible

    def resolve_circle_collision(self, x: float, y: float, radius: float) -> Tuple[float, float, bool]:
        """
        Resolves collision of a moving entity at (x, y) with radius `radius` (in tile units)
        against solid map walls and solid Poisson props in O(1) time by checking only the
        3x3 surrounding tile neighborhood.
        Returns (resolved_x, resolved_y, hit_anything).
        """
        rx, ry = x, y
        hit = False
        tx = int(rx)
        ty = int(ry)

        # 1. Resolve against solid wall tiles in 3x3 neighborhood
        for ny in range(ty - 1, ty + 2):
            for nx in range(tx - 1, tx + 2):
                if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height or self.walkable_grid[ny, nx] != 0:
                    # Closest point on tile AABB [nx, nx+1] x [ny, ny+1]
                    closest_x = max(float(nx), min(rx, float(nx + 1)))
                    closest_y = max(float(ny), min(ry, float(ny + 1)))
                    dx = rx - closest_x
                    dy = ry - closest_y
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < radius * radius:
                        hit = True
                        if dist_sq > 1e-8:
                            dist = dist_sq ** 0.5
                            overlap = radius - dist
                            rx += (dx / dist) * overlap
                            ry += (dy / dist) * overlap
                        else:
                            rx += radius * 0.5

        # 2. Resolve against solid Poisson props (tree trunks, boulders, logs) in 3x3 neighborhood
        for ny in range(ty - 1, ty + 2):
            for nx in range(tx - 1, tx + 2):
                for col in self.cell_colliders.get((nx, ny), ()):
                    dx = rx - col.x
                    dy = ry - col.y
                    min_r = radius + col.radius
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < min_r * min_r:
                        hit = True
                        if dist_sq > 1e-8:
                            dist = dist_sq ** 0.5
                            overlap = min_r - dist
                            rx += (dx / dist) * overlap
                            ry += (dy / dist) * overlap
                        else:
                            rx += min_r * 0.5

        return rx, ry, hit
