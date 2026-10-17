"""
Verlet Integration Leaf Particle Engine & 2D Wind Vector Field Simulator.

Implements Section 2 (Stage 6) & Section 4 of README.md:
- Position-based Verlet Integration:
    x_{t+1} = x_t + (x_t - x_{t-1}) * drag + a(x_t, t) * dt^2
- Driven by the 2D Wind Vector Field + sinusoidal aerodynamic flutter:
    flutter = sin(omega * t + phi)
- Strict global pixel grid alignment (`round(pos.x), round(pos.y)`) with Rotsprite-style
  discrete 4-angle pixel clusters in Sonbahar LUT colors.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import List, Tuple
import numpy as np
import pygame

from src.core.camera import TILE_SIZE
from src.core.palette import (
    DEEP_VOID,
    CRIMSON_DECAY,
    RUST_TERRACOTTA,
    BURNT_AMBER,
    HARVEST_GOLD,
    SUNLIT_BIRCH,
    AUTUMN_MIST,
)
from src.procgen.prng import Xoshiro256StarStar

LEAF_PALETTE = [
    CRIMSON_DECAY,
    RUST_TERRACOTTA,
    BURNT_AMBER,
    HARVEST_GOLD,
    SUNLIT_BIRCH,
]

# Discrete 4-frame Rotsprite-style pixel offsets for tumbling autumn leaves
_LEAF_ROT_SHAPES = (
    ((0, 0), (1, 0), (0, 1)),      # 0 deg
    ((0, 0), (1, 1), (-1, 0)),     # 45 deg
    ((0, 0), (0, 1), (1, 1)),      # 90 deg
    ((0, 0), (-1, 1), (1, 0)),     # 135 deg
)


@dataclass
class VerletLeaf:
    """Single autumn leaf particle simulated with Verlet integration."""

    x: float
    y: float
    old_x: float
    old_y: float
    z: float              # Altitude above ground in pixels (0 = settled on ground)
    vz: float
    omega: float          # Sinusoidal flutter frequency
    phase: float          # Sinusoidal flutter phase phi
    color: Tuple[int, int, int]
    lifetime: float
    max_lifetime: float


class VerletLeafSystem:
    """
    Manages ambient canopy leaf fall and interactive leaf bursts across the viewport.
    """

    def __init__(self, seed: int, max_leaves: int = 160) -> None:
        self.prng = Xoshiro256StarStar(seed ^ 0xFA11)
        self.max_leaves = max_leaves
        self.leaves: List[VerletLeaf] = []
        self.time_sec = 0.0

    def populate_initial(self, world_px_w: int, world_px_h: int) -> None:
        self.leaves.clear()
        for _ in range(self.max_leaves):
            self._spawn_ambient_leaf(world_px_w, world_px_h, random_age=True)

    def _spawn_ambient_leaf(self, world_px_w: int, world_px_h: int, random_age: bool = False) -> None:
        x = self.prng.uniform(16.0, max(32.0, world_px_w - 16.0))
        y = self.prng.uniform(16.0, max(32.0, world_px_h - 16.0))
        z = self.prng.uniform(6.0, 28.0) if random_age else self.prng.uniform(18.0, 32.0)
        max_life = self.prng.uniform(4.5, 8.5)
        life = self.prng.uniform(0.5, max_life) if random_age else max_life
        col = self.prng.choice(LEAF_PALETTE)
        self.leaves.append(
            VerletLeaf(
                x=x,
                y=y,
                old_x=x - self.prng.uniform(0.1, 0.4),
                old_y=y - self.prng.uniform(0.05, 0.2),
                z=z,
                vz=-self.prng.uniform(2.5, 4.5),
                omega=self.prng.uniform(3.5, 6.8),
                phase=self.prng.uniform(0.0, math.pi * 2.0),
                color=col,
                lifetime=life,
                max_lifetime=max_life,
            )
        )

    def spawn_burst(
        self,
        world_px_x: float,
        world_px_y: float,
        count: int = 14,
        golden_bias: bool = False,
    ) -> None:
        """
        Spawns an explosive swirl of autumn leaves when the player steps on a crunchy
        leaf pile, dashes, or swings the Solar Ember Lantern.
        """
        for _ in range(count):
            angle = self.prng.uniform(0.0, math.pi * 2.0)
            speed = self.prng.uniform(0.6, 2.2)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            col = (
                self.prng.choice([HARVEST_GOLD, SUNLIT_BIRCH, BURNT_AMBER])
                if golden_bias
                else self.prng.choice(LEAF_PALETTE)
            )
            self.leaves.append(
                VerletLeaf(
                    x=world_px_x,
                    y=world_px_y,
                    old_x=world_px_x - vx,
                    old_y=world_px_y - vy,
                    z=self.prng.uniform(3.0, 10.0),
                    vz=self.prng.uniform(12.0, 24.0),
                    omega=self.prng.uniform(5.0, 9.0),
                    phase=self.prng.uniform(0.0, math.pi * 2.0),
                    color=col,
                    lifetime=self.prng.uniform(1.2, 2.4),
                    max_lifetime=2.4,
                )
            )

    def apply_radial_impulse(
        self, center_px_x: float, center_px_y: float, radius_px: float, strength: float = 2.6
    ) -> None:
        """Pushes nearby falling/settled leaves outward via Verlet velocity injection."""
        r_sq = radius_px * radius_px
        for leaf in self.leaves:
            dx = leaf.x - center_px_x
            dy = leaf.y - center_px_y
            d2 = dx * dx + dy * dy
            if 1.0 < d2 < r_sq:
                dist = math.sqrt(d2)
                falloff = 1.0 - (dist / radius_px)
                impulse = strength * falloff
                leaf.old_x -= (dx / dist) * impulse
                leaf.old_y -= (dy / dist) * impulse
                leaf.vz = max(leaf.vz, 14.0 * falloff)
                leaf.z = max(leaf.z, 2.0)

    def apply_vortex_impulse(
        self, center_px_x: float, center_px_y: float, radius_px: float, strength: float = 3.8
    ) -> None:
        """
        Pulls and swirls leaves in a high-speed orbital vortex around the center
        (used during Bozkır Rüzgarı Kasırgası / Leaf Cyclone).
        """
        r_sq = radius_px * radius_px
        for leaf in self.leaves:
            dx = leaf.x - center_px_x
            dy = leaf.y - center_px_y
            d2 = dx * dx + dy * dy
            if 1.0 < d2 < r_sq:
                dist = math.sqrt(d2)
                falloff = 1.0 - (dist / radius_px)
                tangent_x = -dy / dist
                tangent_y = dx / dist
                inward_x = -dx / dist
                inward_y = -dy / dist
                impulse_t = strength * falloff
                impulse_i = (strength * 0.45) * falloff
                leaf.old_x -= (tangent_x * impulse_t + inward_x * impulse_i)
                leaf.old_y -= (tangent_y * impulse_t + inward_y * impulse_i)
                leaf.vz = max(leaf.vz, 16.0 * falloff)
                leaf.z = max(leaf.z, 4.0)

    def update(
        self,
        dt: float,
        wind_vx: np.ndarray,
        wind_vy: np.ndarray,
        world_px_w: int,
        world_px_h: int,
    ) -> None:
        """Advances Verlet integration step for all active leaves."""
        self.time_sec += dt
        map_h, map_w = wind_vx.shape
        drag = 0.92
        dt_sq = dt * dt * 60.0

        alive_leaves: List[VerletLeaf] = []
        for leaf in self.leaves:
            leaf.lifetime -= dt
            if leaf.lifetime <= 0.0:
                continue

            # Sample 2D Wind Vector Field at leaf's tile coordinate
            tx = max(0, min(map_w - 1, int(leaf.x) // TILE_SIZE))
            ty = max(0, min(map_h - 1, int(leaf.y) // TILE_SIZE))
            wvx = float(wind_vx[ty, tx])
            wvy = float(wind_vy[ty, tx])

            if leaf.z > 0.2:
                # Airborne: apply sinusoidal flutter + wind vector field
                flutter = math.sin(leaf.omega * self.time_sec + leaf.phase)
                ax = wvx * 14.0 + flutter * 9.5
                ay = wvy * 10.0 + math.cos(leaf.omega * 0.7 * self.time_sec + leaf.phase) * 5.0

                vx = (leaf.x - leaf.old_x) * drag
                vy = (leaf.y - leaf.old_y) * drag
                leaf.old_x = leaf.x
                leaf.old_y = leaf.y
                leaf.x += vx + ax * dt_sq
                leaf.y += vy + ay * dt_sq

                # Altitude settling with occasional wind updrafts
                leaf.vz -= 18.0 * dt
                leaf.vz = max(-5.5, leaf.vz)
                leaf.z = max(0.0, leaf.z + leaf.vz * dt)
            else:
                # Settled on ground: strong friction unless kicked up by an impulse
                vx = (leaf.x - leaf.old_x) * 0.65
                vy = (leaf.y - leaf.old_y) * 0.65
                leaf.old_x = leaf.x
                leaf.old_y = leaf.y
                leaf.x += vx
                leaf.y += vy

            # Wrap around world bounds so ambient leaf density stays constant
            if leaf.x < 8.0 or leaf.x >= world_px_w - 8.0 or leaf.y < 8.0 or leaf.y >= world_px_h - 8.0:
                if len(alive_leaves) < self.max_leaves:
                    leaf.x = self.prng.uniform(16.0, world_px_w - 16.0)
                    leaf.y = self.prng.uniform(16.0, world_px_h - 16.0)
                    leaf.old_x = leaf.x
                    leaf.old_y = leaf.y
                    leaf.z = 24.0

            alive_leaves.append(leaf)

        self.leaves = alive_leaves
        while len(self.leaves) < self.max_leaves:
            self._spawn_ambient_leaf(world_px_w, world_px_h, random_age=False)

    def render(self, surface: pygame.Surface, cam_x: int, cam_y: int, view_w: int, view_h: int) -> int:
        """
        Renders only leaves inside the camera frustum, strictly snapped to integer
        pixel coordinates (`round(pos.x), round(pos.y)`).
        Returns the number of visible particles drawn.
        """
        drawn = 0
        for leaf in self.leaves:
            sx = int(round(leaf.x)) - cam_x
            sy = int(round(leaf.y - leaf.z * 0.5)) - cam_y
            if not (-4 <= sx < view_w + 4 and -4 <= sy < view_h + 4):
                continue

            drawn += 1
            # Draw ground shadow if airborne
            if leaf.z > 2.0:
                sh_y = int(round(leaf.y)) - cam_y
                if 0 <= sx < view_w and 0 <= sh_y < view_h:
                    surface.set_at((sx, sh_y), DEEP_VOID)

            # Select discrete Rotsprite orientation frame (0..3)
            rot_idx = int((self.time_sec * leaf.omega + leaf.phase) * 1.5) & 3
            shape = _LEAF_ROT_SHAPES[rot_idx]
            for ox, oy in shape:
                px, py = sx + ox, sy + oy
                if 0 <= px < view_w and 0 <= py < view_h:
                    surface.set_at((px, py), leaf.color)

        return drawn
