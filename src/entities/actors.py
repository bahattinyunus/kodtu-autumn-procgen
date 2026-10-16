"""
Player, AI Agents (Wisp, Bramble Stalker, Hollow Golem), and Interactive Autumn Entities.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import List, Optional, Tuple
import numpy as np

from src.core.spatial_hash import ChunkSpatialHash
from src.procgen.noise import BIOME_DAMP_DECAY, BIOME_CRISP_GOLDEN
from src.procgen.pipeline import EntitySpawn


@dataclass
class CollectibleItem:
    """Interactive autumn pickup (Harvest Relic or Golden Acorn)."""

    x: float
    y: float
    kind: str  # 'relic' or 'acorn'
    collected: bool = False
    bob_phase: float = 0.0


class EnemyAgent:
    """
    Autonomous Autumn Enemy AI (`wisp`, `stalker`, `golem`).
    Responds to line-of-sight distance AND acoustic leaf-crunch ripples!
    """

    def __init__(self, x: float, y: float, kind: str, seed_phase: float = 0.0) -> None:
        self.x = x
        self.y = y
        self.home_x = x
        self.home_y = y
        self.kind = kind
        self.phase = seed_phase
        self.vx = 0.0
        self.vy = 0.0
        self.kb_vx = 0.0
        self.kb_vy = 0.0
        self.hit_flash = 0.0
        self.alive = True

        if kind == "wisp":
            self.max_hp = 2
            self.speed = 2.55
            self.aggro_range = 6.5
            self.radius = 0.30
            self.damage = 12.0
        elif kind == "stalker":
            self.max_hp = 4
            self.speed = 3.10
            self.aggro_range = 7.5
            self.radius = 0.35
            self.damage = 18.0
        else:  # golem
            self.max_hp = 7
            self.speed = 1.85
            self.aggro_range = 6.0
            self.radius = 0.42
            self.damage = 26.0

        self.hp = self.max_hp

    def apply_hit(self, dmg: int, source_x: float, source_y: float, knockback: float = 7.5) -> bool:
        """Applies damage and radial knockback impulse. Returns True if defeated."""
        self.hp -= dmg
        self.hit_flash = 0.18
        dx = self.x - source_x
        dy = self.y - source_y
        dist = math.hypot(dx, dy)
        if dist > 1e-5:
            self.kb_vx = (dx / dist) * knockback
            self.kb_vy = (dy / dist) * knockback
        else:
            self.kb_vx = knockback
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def update(
        self,
        dt: float,
        player_x: float,
        player_y: float,
        player_noise_radius: float,
        spatial_hash: ChunkSpatialHash,
    ) -> None:
        if not self.alive:
            return

        self.phase += dt * 4.5
        if self.hit_flash > 0.0:
            self.hit_flash = max(0.0, self.hit_flash - dt)

        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)

        effective_aggro = self.aggro_range + player_noise_radius
        if 0.05 < dist <= effective_aggro:
            # Pursue player with slight sinusoidal weave for wisps
            dir_x = dx / dist
            dir_y = dy / dist
            if self.kind == "wisp":
                perp_x, perp_y = -dir_y, dir_x
                weave = math.sin(self.phase * 1.4) * 0.45
                dir_x += perp_x * weave
                dir_y += perp_y * weave
            self.vx = dir_x * self.speed
            self.vy = dir_y * self.speed
        else:
            # Gentle idle orbit around home clearing
            orbit_x = self.home_x + math.cos(self.phase * 0.45) * 1.1
            orbit_y = self.home_y + math.sin(self.phase * 0.45) * 1.1
            odx = orbit_x - self.x
            ody = orbit_y - self.y
            odist = math.hypot(odx, ody)
            if odist > 0.15:
                self.vx = (odx / odist) * (self.speed * 0.45)
                self.vy = (ody / odist) * (self.speed * 0.45)
            else:
                self.vx, self.vy = 0.0, 0.0

        # Apply movement + knockback decay
        nx = self.x + (self.vx + self.kb_vx) * dt
        ny = self.y + (self.vy + self.kb_vy) * dt
        self.kb_vx *= math.exp(-10.0 * dt)
        self.kb_vy *= math.exp(-10.0 * dt)

        if self.kind == "wisp":
            # Wisps float over low props, only blocked by outer map boundaries
            nx = max(2.2, min(float(spatial_hash.width - 2.2), nx))
            ny = max(2.2, min(float(spatial_hash.height - 2.2), ny))
            if spatial_hash.walkable_grid[int(ny), int(nx)] == 0:
                self.x, self.y = nx, ny
        else:
            rx, ry, _ = spatial_hash.resolve_circle_collision(nx, ny, self.radius)
            self.x, self.y = rx, ry


class Player:
    """
    The Autumn Keeper controlled by the user.
    Features:
    - O(1) Spatial-Hashed movement & biome interaction
    - Crunchy Leaf Pile acoustic ripple & Wind-Step speed boost
    - Solar Ember Sweep attack (`SPACE` / Left Click)
    - Autumn Gust Dash (`SHIFT` / Right Click)
    """

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.radius = 0.32
        self.base_speed = 5.4
        self.facing_x = 1.0
        self.facing_y = 0.0
        self.facing_right = True

        self.max_warmth = 100.0
        self.warmth = 100.0
        self.relics_collected = 0
        self.acorns_collected = 0
        self.enemies_defeated = 0

        # Animation & timers
        self.walk_timer = 0.0
        self.step_sfx_cooldown = 0.0
        self.leaf_boost_timer = 0.0
        self.noise_ripple_radius = 0.0
        self.invuln_timer = 0.0

        # Dash state
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.dash_dir_x = 1.0
        self.dash_dir_y = 0.0

        # Solar Ember Sweep attack state
        self.attack_timer = 0.0
        self.attack_cooldown = 0.0
        self.attack_angle = 0.0

    @property
    def anim_frame(self) -> int:
        if self.dash_timer > 0.0:
            return 1
        if self.walk_timer <= 0.0:
            return 0
        return 1 + (int(self.walk_timer * 8.0) % 2)

    def trigger_dash(self, move_x: float, move_y: float) -> bool:
        if self.dash_cooldown > 0.0 or self.dash_timer > 0.0:
            return False
        mag = math.hypot(move_x, move_y)
        if mag > 1e-4:
            self.dash_dir_x = move_x / mag
            self.dash_dir_y = move_y / mag
        else:
            self.dash_dir_x = self.facing_x
            self.dash_dir_y = self.facing_y
        self.dash_timer = 0.16
        self.dash_cooldown = 0.65
        self.invuln_timer = max(self.invuln_timer, 0.22)
        return True

    def trigger_attack(self) -> bool:
        if self.attack_cooldown > 0.0:
            return False
        self.attack_timer = 0.18
        self.attack_cooldown = 0.32
        self.attack_angle = math.atan2(self.facing_y, self.facing_x)
        return True

    def update(
        self,
        dt: float,
        move_x: float,
        move_y: float,
        spatial_hash: ChunkSpatialHash,
        biome_grid: np.ndarray,
    ) -> Tuple[bool, bool]:
        """
        Updates player movement, collision, and biome triggers.
        Returns (stepped_on_dry_leaves, stepped_on_damp_mud).
        """
        self.step_sfx_cooldown = max(0.0, self.step_sfx_cooldown - dt)
        self.leaf_boost_timer = max(0.0, self.leaf_boost_timer - dt)
        self.invuln_timer = max(0.0, self.invuln_timer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.noise_ripple_radius = max(0.0, self.noise_ripple_radius - dt * 4.5)

        stepped_dry_leaves = False
        stepped_mud = False

        if self.dash_timer > 0.0:
            self.dash_timer = max(0.0, self.dash_timer - dt)
            speed = self.base_speed * 2.65
            vx = self.dash_dir_x * speed
            vy = self.dash_dir_y * speed
        else:
            mag = math.hypot(move_x, move_y)
            if mag > 1e-4:
                nx_dir = move_x / mag
                ny_dir = move_y / mag
                self.facing_x = nx_dir
                self.facing_y = ny_dir
                if abs(nx_dir) > 0.05:
                    self.facing_right = nx_dir > 0.0
                boost = 1.24 if self.leaf_boost_timer > 0.0 else 1.0
                vx = nx_dir * self.base_speed * boost
                vy = ny_dir * self.base_speed * boost
                self.walk_timer += dt
            else:
                vx, vy = 0.0, 0.0
                self.walk_timer = 0.0

        # Resolve movement in X/Y with O(1) spatial hash collision
        target_x = self.x + vx * dt
        target_y = self.y + vy * dt
        rx, ry, _ = spatial_hash.resolve_circle_collision(target_x, target_y, self.radius)
        self.x, self.y = rx, ry

        tx, ty = int(self.x), int(self.y)
        if 0 <= tx < spatial_hash.width and 0 <= ty < spatial_hash.height:
            current_biome = int(biome_grid[ty, tx])
            on_leaf_pile = len(spatial_hash.leaf_pile_cells.get((tx, ty), ())) > 0
            on_mushroom = len(spatial_hash.mushroom_cells.get((tx, ty), ())) > 0

            if on_mushroom:
                # Glowing autumn mushrooms gently warm the lantern
                self.warmth = min(self.max_warmth, self.warmth + dt * 4.5)

            if self.walk_timer > 0.0 and self.step_sfx_cooldown <= 0.0:
                if on_leaf_pile or current_biome == BIOME_CRISP_GOLDEN:
                    stepped_dry_leaves = True
                    self.step_sfx_cooldown = 0.24
                    if on_leaf_pile:
                        self.leaf_boost_timer = 1.25
                        self.noise_ripple_radius = 3.2
                elif current_biome == BIOME_DAMP_DECAY:
                    stepped_mud = True
                    self.step_sfx_cooldown = 0.30
                else:
                    stepped_dry_leaves = True
                    self.step_sfx_cooldown = 0.32

        return stepped_dry_leaves, stepped_mud


def spawn_world_entities(spawns: List[EntitySpawn]) -> Tuple[List[CollectibleItem], List[EnemyAgent]]:
    """Instantiates runtime CollectibleItems and EnemyAgents from deterministic Stage-5 spawns."""
    items: List[CollectibleItem] = []
    enemies: List[EnemyAgent] = []
    for idx, sp in enumerate(spawns):
        if sp.entity_type in ("relic", "acorn"):
            items.append(
                CollectibleItem(
                    x=sp.x,
                    y=sp.y,
                    kind=sp.entity_type,
                    bob_phase=idx * 0.9,
                )
            )
        else:
            enemies.append(
                EnemyAgent(
                    x=sp.x,
                    y=sp.y,
                    kind=sp.entity_type,
                    seed_phase=idx * 1.3,
                )
            )
    return items, enemies
