"""
Player, AI Agents (Wisp, Bramble Stalker, Hollow Golem, Elder Stag Warden),
Floating Combat Popups, and Interactive Autumn Entities.
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


@dataclass
class FloatingText:
    """Pixel-snapped floating combat/status text in world coordinates."""

    x: float
    y: float
    text: str
    color: Tuple[int, int, int]
    timer: float = 0.85
    max_timer: float = 0.85


@dataclass
class Projectile:
    """
    Active projectile in world space (Solar Ember Bolt or Enemy Twilight Orb).
    Supports melee deflection ('Hyper Light Drifter' / 'Enter the Gungeon' style).
    """

    x: float
    y: float
    vx: float
    vy: float
    owner: str          # 'player' or 'enemy'
    damage: int = 3
    radius: float = 0.22
    lifetime: float = 1.85
    alive: bool = True
    deflected: bool = False


@dataclass
class DashGhost:
    """Pixel-snapped afterimage silhouette spawned during Autumn Gust Dash."""

    x: float
    y: float
    facing_right: bool
    anim_frame: int
    timer: float = 0.16
    max_timer: float = 0.16


AUTUMN_BOONS: List[Tuple[str, str, str]] = [
    ("DEVRIM_TORCH", "DEVRIM MESALESI", "+2.5/s Warmth Regen & +1 Max Solar Bolt"),
    ("BILIM_SPARK", "BILIM AGACI KIVILCIMI", "+1 Slash/Bolt Damage & Crit Shockwave"),
    ("YALINCAK_GALE", "YALINCAK RUZGARI", "+18% Move Speed & Faster Gust Dash"),
    ("EYMIR_REFLECT", "EYMIR AYNA KALKANI", "Deflects Enemy Orbs for 2x DMG & +Warmth"),
    ("HARVEST_CROWN", "KODTU HASAT TACI", "Solar Bolt [F] Fires a 3-Way Ember Volley"),
]


class EnemyAgent:
    """
    Autonomous Autumn Enemy AI (`wisp`, `stalker`, `golem`, `warden`).
    Responds to line-of-sight distance AND acoustic leaf-crunch ripples!
    `wisp` and `warden` also fire dodgeable/deflectable Twilight Orbs.
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
        self.shoot_cooldown = 1.6 + (seed_phase % 1.2)
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
        elif kind == "wolf":
            self.max_hp = 3
            self.speed = 3.65
            self.aggro_range = 7.2
            self.radius = 0.32
            self.damage = 14.0
        elif kind == "raven":
            self.max_hp = 2
            self.speed = 3.90
            self.aggro_range = 8.0
            self.radius = 0.28
            self.damage = 10.0
        elif kind == "lynx":
            self.max_hp = 4
            self.speed = 3.45
            self.aggro_range = 7.8
            self.radius = 0.30
            self.damage = 18.0
        elif kind == "warden":
            self.max_hp = 12
            self.speed = 2.65
            self.aggro_range = 8.5
            self.radius = 0.44
            self.damage = 28.0
        else:  # golem
            self.max_hp = 7
            self.speed = 1.85
            self.aggro_range = 6.0
            self.radius = 0.42
            self.damage = 26.0

        self.hp = self.max_hp
        self.has_roared = False
        self.distraction_timer = 0.0

    @property
    def is_enraged(self) -> bool:
        """Warden enters Enraged Phase 2 ('Kadim Öfke') when HP falls to 50% or below."""
        return self.kind == "warden" and self.hp <= (self.max_hp // 2)

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
        projectiles: Optional[List[Projectile]] = None,
    ) -> None:
        if not self.alive:
            return

        self.phase += dt * (6.0 if self.is_enraged else 4.5)
        if self.hit_flash > 0.0:
            self.hit_flash = max(0.0, self.hit_flash - dt)
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        self.distraction_timer = max(0.0, self.distraction_timer - dt)
        if self.distraction_timer > 0.0:
            return

        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)

        effective_aggro = (self.aggro_range * (1.3 if self.is_enraged else 1.0)) + player_noise_radius
        if 0.05 < dist <= effective_aggro:
            dir_x = dx / dist
            dir_y = dy / dist
            current_speed = self.speed
            if self.kind == "wisp":
                perp_x, perp_y = -dir_y, dir_x
                weave = math.sin(self.phase * 1.4) * 0.45
                dir_x += perp_x * weave
                dir_y += perp_y * weave
                if projectiles is not None and self.shoot_cooldown <= 0.0 and dist <= 5.8:
                    self.shoot_cooldown = 2.6
                    projectiles.append(
                        Projectile(
                            x=self.x,
                            y=self.y,
                            vx=(dx / dist) * 4.8,
                            vy=(dy / dist) * 4.8,
                            owner="enemy",
                            damage=10,
                            radius=0.20,
                            lifetime=1.9,
                        )
                    )
            elif self.kind == "wolf":
                # Bozkır Kurdu: Circling flank at range, pounces with speed burst when close
                if dist > 3.0:
                    perp_x, perp_y = -dir_y, dir_x
                    flank = math.sin(self.phase * 2.2) * 0.65
                    dir_x = (dir_x * 0.70) + (perp_x * flank)
                    dir_y = (dir_y * 0.70) + (perp_y * flank)
                else:
                    pounce = 1.65 if math.sin(self.phase * 3.6) > 0.25 else 0.85
                    dir_x *= pounce
                    dir_y *= pounce
            elif self.kind == "raven":
                # Bozkır Kuzgunu: Airborne aerial predator swoops in arcs and dives
                perp_x, perp_y = -dir_y, dir_x
                swoop = math.sin(self.phase * 3.2) * 0.75
                dive = 1.35 if math.sin(self.phase * 2.4) > 0.3 else 0.90
                dir_x = (dir_x * dive) + (perp_x * swoop)
                dir_y = (dir_y * dive) + (perp_x * swoop)
            elif self.kind == "lynx":
                # Anadolu Bozkır Vaşağı: Stealth stalking in autumn brush; leaps with agile burst when close
                if dist > 2.8:
                    current_speed = self.speed * 0.70
                else:
                    leap = 1.95 if math.sin(self.phase * 4.2) > 0.15 else 0.85
                    dir_x *= leap
                    dir_y *= leap
                    current_speed = self.speed * 1.30
            elif self.kind == "warden":
                # Elder Stag Warden: Phase 1 has rhythmic surges & 3-way orbs; Phase 2 (Enraged) has rapid charges & 8-way ring volley
                if self.is_enraged:
                    current_speed = 3.45
                    surge = 1.45 if math.sin(self.phase * 1.3) > 0.3 else 1.10
                    dir_x *= surge
                    dir_y *= surge
                    if projectiles is not None and self.shoot_cooldown <= 0.0 and dist <= 8.5:
                        self.shoot_cooldown = 1.75
                        # 8-way circular radial Twilight Orb storm!
                        for i in range(8):
                            ang = (i / 8.0) * 2.0 * math.pi + (self.phase * 0.2)
                            projectiles.append(
                                Projectile(
                                    x=self.x,
                                    y=self.y,
                                    vx=math.cos(ang) * 5.2,
                                    vy=math.sin(ang) * 5.2,
                                    owner="enemy",
                                    damage=16,
                                    radius=0.22,
                                    lifetime=2.2,
                                )
                            )
                else:
                    surge = 1.35 if math.sin(self.phase * 0.8) > 0.55 else 0.90
                    dir_x *= surge
                    dir_y *= surge
                    if projectiles is not None and self.shoot_cooldown <= 0.0 and dist <= 7.2:
                        self.shoot_cooldown = 2.2
                        base_ang = math.atan2(dy, dx)
                        for spread in (-0.28, 0.0, 0.28):
                            ang = base_ang + spread
                            projectiles.append(
                                Projectile(
                                    x=self.x,
                                    y=self.y,
                                    vx=math.cos(ang) * 5.4,
                                    vy=math.sin(ang) * 5.4,
                                    owner="enemy",
                                    damage=14,
                                    radius=0.22,
                                    lifetime=2.1,
                                )
                            )
            self.vx = dir_x * current_speed
            self.vy = dir_y * current_speed
        else:
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
            nx = max(2.2, min(float(spatial_hash.width - 2.2), nx))
            ny = max(2.2, min(float(spatial_hash.height - 2.2), ny))
            if spatial_hash.walkable_grid[int(ny), int(nx)] == 0:
                self.x, self.y = nx, ny
        else:
            rx, ry, _ = spatial_hash.resolve_circle_collision(nx, ny, self.radius)
            self.x, self.y = rx, ry



class SteppeCompanion:
    """
    ODTÜ Bozkır Yoldaşı (Steppe Guardian Kangal Companion):
    A loyal campus dog companion following the player through the autumn forest.
    - Follows player at a faithful distance (spring/steering physics).
    - Alerts the player by barking when enemies approach or hidden relics are nearby.
    - Can be petted ([E]) to restore +12 Warmth and trigger happy leaf bursts.
    - Staggers or distracts nearby enemies periodically in combat.
    """

    def __init__(self, x: float, y: float, name: str = "Bozkır Kangalı") -> None:
        self.x = x
        self.y = y
        self.name = name
        self.kind = "companion"
        self.facing_right = True
        self.is_moving = False
        self.anim_timer = 0.0
        self.bark_cooldown = 0.0
        self.alert_cooldown = 0.0
        self.distract_cooldown = 0.0
        self.tail_wag_timer = 0.0
        self.pet_timer = 0.0
        self.petted_count = 0
        self.base_speed = 4.2
        self.radius = 0.30
        self.bark_alert_trigger = False
        self.loyalty_tier = 1
        self.dig_cooldown = 0.0
        self.dig_timer = 0.0
        self.treasures_found = 0

    @property
    def anim_frame(self) -> int:
        if self.dig_timer > 0.0:
            return 1 if int(self.dig_timer * 8.0) % 2 == 0 else 0
        if self.is_moving:
            return int(self.anim_timer * 7.0) % 2
        return 1 if self.tail_wag_timer > 0.0 and int(self.tail_wag_timer * 6.0) % 2 == 0 else 0

    def pet(self, player: Optional[Any] = None) -> bool:
        """[E] Interactively pet the companion, boosting morale and warmth."""
        self.petted_count += 1
        self.tail_wag_timer = 3.5
        self.pet_timer = 1.2
        if player is not None:
            player.warmth = min(player.max_warmth, player.warmth + 12.0)
            if hasattr(player, "pets_count"):
                player.pets_count += 1
        return True

    def command_dig(self, player: Optional[Any] = None) -> Optional[Tuple[str, int]]:
        """
        [K]: Commands Kangal to sniff and dig into the autumn soil for hidden campus treasures.
        Unearths bonus acorns or ancient relic shards, strengthening the companion bond.
        """
        if self.dig_cooldown > 0.0:
            return None
        self.dig_cooldown = 10.0
        self.dig_timer = 1.6
        self.tail_wag_timer = 4.0
        self.treasures_found += 1
        if self.treasures_found >= 3:
            self.loyalty_tier = 3
        elif self.treasures_found >= 1:
            self.loyalty_tier = 2

        if self.treasures_found % 3 == 0:
            kind = "relic_shard"
            amount = 1
        else:
            kind = "acorn"
            amount = 3

        if player is not None:
            if kind == "acorn":
                player.acorns_collected += amount
            elif kind == "relic_shard":
                player.warmth = min(player.max_warmth, player.warmth + 20.0)
            if hasattr(player, "kangal_treasures_found"):
                player.kangal_treasures_found += 1

        return kind, amount

    def update(
        self,
        dt: float,
        player_x: float = 0.0,
        player_y: float = 0.0,
        enemies: Optional[List[EnemyAgent]] = None,
        spatial_hash: Optional[ChunkSpatialHash] = None,
        target_x: Optional[float] = None,
        target_y: Optional[float] = None,
    ) -> Tuple[bool, bool, Optional[str]]:
        """
        Updates companion position, barking alerts, and combat support.
        Returns (did_bark, did_distract_enemy, alert_message).
        """
        if target_x is not None:
            player_x = target_x
        if target_y is not None:
            player_y = target_y
        if enemies is None:
            enemies = []

        self.bark_cooldown = max(0.0, self.bark_cooldown - dt)
        self.alert_cooldown = max(0.0, self.alert_cooldown - dt)
        self.distract_cooldown = max(0.0, self.distract_cooldown - dt)
        self.tail_wag_timer = max(0.0, self.tail_wag_timer - dt)
        self.pet_timer = max(0.0, self.pet_timer - dt)
        self.dig_cooldown = max(0.0, self.dig_cooldown - dt)
        self.dig_timer = max(0.0, self.dig_timer - dt)
        self.bark_alert_trigger = False

        # 1. Follow Player Behavior
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)

        did_bark = False
        did_distract = False
        alert_msg: Optional[str] = None

        target_follow_dist = 1.6
        if dist > target_follow_dist:
            self.is_moving = True
            self.anim_timer += dt
            speed_mult = 1.55 if dist > 4.0 else (1.20 if dist > 2.5 else 1.0)
            step = min(dist - target_follow_dist, self.base_speed * speed_mult * dt)
            nx_dir = dx / max(1e-5, dist)
            ny_dir = dy / max(1e-5, dist)

            if abs(nx_dir) > 0.05:
                self.facing_right = nx_dir > 0.0

            cand_x = self.x + nx_dir * step
            cand_y = self.y + ny_dir * step
            if spatial_hash is not None:
                rx, ry, _ = spatial_hash.resolve_circle_collision(cand_x, cand_y, self.radius)
                self.x, self.y = rx, ry
            else:
                self.x, self.y = cand_x, cand_y
        else:
            self.is_moving = False

        # 2. Alert Bark on Approaching Enemies (within 5.5 tiles)
        nearby_threats = [
            en for en in enemies if en.alive and math.hypot(en.x - self.x, en.y - self.y) <= 5.5
        ]
        if nearby_threats and self.bark_cooldown <= 0.0 and self.alert_cooldown <= 0.0:
            self.bark_cooldown = 7.0
            self.alert_cooldown = 7.0
            self.tail_wag_timer = 2.0
            self.bark_alert_trigger = True
            did_bark = True
            alert_msg = "HAV! 🐾 YOLDAŞ TEHLİKEYİ SEZDİ!"

        # 3. Combat Distraction / Stagger on Closest Enemy (within 2.2 tiles)
        close_threats = [
            en for en in enemies if en.alive and math.hypot(en.x - self.x, en.y - self.y) <= 2.2
        ]
        if close_threats and self.distract_cooldown <= 0.0:
            target = min(close_threats, key=lambda en: math.hypot(en.x - self.x, en.y - self.y))
            self.distract_cooldown = 7.5
            target.distraction_timer = 2.0
            target.apply_hit(3, self.x, self.y, knockback=7.0)
            did_distract = True
            did_bark = True
            alert_msg = f"🐾 {self.name.upper()} ATILDI! (-3 DARBE)"

        return did_bark, did_distract, alert_msg


class Player:
    """
    The Autumn Keeper controlled by the user.
    Features:
    - O(1) Spatial-Hashed movement & biome interaction
    - Crunchy Leaf Pile acoustic ripple & Wind-Step speed boost
    - 3-Hit Solar Ember Sweep combo (`SPACE` / Left Click) that recharges Solar Bolts
    - Ranged Solar Ember Bolt (`F` key) with 3-way volley upgrade
    - Autumn Gust Dash (`SHIFT` / Right Click) with afterimage ghost trails
    - Harvest Nova 360-degree whirlwind (`Q` / Middle Click) & Orb Deflection
    - Roguelite ODTÜ Autumn Boons (`active_boons`)
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
        self.orbs_deflected = 0
        self.pets_count = 0

        # Hyper Light Drifter style Ranged Solar Bolt ammo (recharged by melee hits & time)
        self.max_solar_bolts = 4
        self.solar_bolts = 4
        self.bolt_recharge_timer = 0.0
        self.bolt_cooldown = 0.0

        # Active Roguelite ODTÜ Autumn Boons
        self.active_boons: List[str] = []

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
        self.ghost_spawn_timer = 0.0

        # Solar Ember Sweep 3-stage combo state
        self.attack_timer = 0.0
        self.attack_cooldown = 0.0
        self.attack_angle = 0.0
        self.combo_step = 0
        self.combo_reset_timer = 0.0

        # Harvest Nova 360-degree shockwave state
        self.nova_timer = 0.0
        self.nova_cooldown = 0.0

        # Bozkır Kılıç Dansı / Leaf Blade Dance Combo Finisher ([X] / [R])
        self.combo_hits = 0
        self.combo_hits_max = 6
        self.blade_dance_timer = 0.0
        self.blade_dance_slash_count = 0
        self.blade_dance_slash_cooldown = 0.0

        # Közlenmiş Kestane / Campfire Warmth Aura (slower warmth decay + increased aura)
        self.campfire_aura_timer = 0.0

        # ODTÜ Devrim Overdrive Mode ([Z] / [V])
        self.overdrive_timer = 0.0
        self.overdrive_max_duration = 10.0

        # Bozkır Simyası / Acorn Alchemy Transmutations ([G])
        self.transmute_count = 0
        self.dash_cooldown_mult = 1.0

        # ODTÜ Bilim Ağacı Ayini / Science Tree Activation Aura ([E])
        self.bilim_ritual_timer = 0.0
        self.perfect_parries = 0

        # Yalıncak Antik Bozkır Kalkanı / Ancient Steppe Aegis Blessing ([E])
        self.yalincak_blessing_timer = 0.0

        # Bozkır Rüzgarı Kasırgası / Leaf Cyclone Vortex ([T])
        self.cyclone_timer = 0.0
        self.cyclone_cooldown = 0.0
        self.kangal_treasures_found = 0

    @property
    def is_in_overdrive(self) -> bool:
        """True when player is channeling ODTÜ Devrim Overdrive Mode."""
        return self.overdrive_timer > 0.0

    @property
    def overdrive_ready(self) -> bool:
        """Overdrive is ready when warmth is high and combo is maxed or at least 1 relic is gathered."""
        return (
            self.overdrive_timer <= 0.0
            and self.warmth >= 70.0
            and (self.combo_hits >= self.combo_hits_max or self.relics_collected >= 1)
        )

    def trigger_devrim_overdrive(self) -> bool:
        """[Z] / [V]: Unleashes ODTÜ Devrim Overdrive with fiery aura, twin crescent slashes, and speed."""
        if not self.overdrive_ready:
            return False
        self.overdrive_timer = self.overdrive_max_duration
        self.solar_bolts = self.max_solar_bolts
        self.leaf_boost_timer = max(self.leaf_boost_timer, self.overdrive_max_duration)
        self.combo_hits = 0
        return True

    def transmute_acorns(self) -> Optional[str]:
        """[G]: Transmutes 2 Acorns into a permanent run upgrade at a Campfire or Ancient Shrine."""
        if self.acorns_collected < 2:
            return None
        self.acorns_collected -= 2
        self.transmute_count += 1
        upgrade_type = (self.transmute_count - 1) % 3
        if upgrade_type == 0:
            self.max_solar_bolts += 1
            self.solar_bolts = self.max_solar_bolts
            return "+1 MAKS GÜNEŞ KÖZÜ (KAPASİTE ARTTI)"
        elif upgrade_type == 1:
            self.dash_cooldown_mult *= 0.75
            return "RÜZGAR ADIMI TILSIMI (ATILMA BEKLEMESİ -%25)"
        else:
            self.max_warmth += 15.0
            self.warmth = self.max_warmth
            return "KÖZ KALKAN SİMYASI (+15 MAKS FENER ISISI)"

    @property
    def combo_ready(self) -> bool:
        """True when combo meter reaches 6 hits, enabling Bozkır Kılıç Dansı."""
        return self.combo_hits >= self.combo_hits_max

    @property
    def anim_frame(self) -> int:
        if self.dash_timer > 0.0:
            return 1
        if self.walk_timer <= 0.0:
            return 0
        return 1 + (int(self.walk_timer * 8.0) % 2)

    def has_boon(self, boon_id: str) -> bool:
        return boon_id in self.active_boons

    def grant_next_boon(self) -> Optional[Tuple[str, str, str]]:
        """Unlocks the next ODTÜ Autumn Boon not yet held by the player."""
        for boon_id, title, desc in AUTUMN_BOONS:
            if boon_id not in self.active_boons:
                self.active_boons.append(boon_id)
                if boon_id == "DEVRIM_TORCH":
                    self.max_solar_bolts += 1
                    self.solar_bolts = self.max_solar_bolts
                elif boon_id == "YALINCAK_GALE":
                    self.base_speed *= 1.18
                return (boon_id, title, desc)
        return None

    def recharge_bolt_on_melee(self) -> None:
        """Recharges +1 Solar Bolt when landing a melee hit (Hyper Light Drifter style)."""
        if self.solar_bolts < self.max_solar_bolts:
            self.solar_bolts += 1

    def trigger_solar_bolt(self, projectiles: List[Projectile]) -> bool:
        """[F] Fires a high-velocity Solar Ember Bolt (or 3-way volley with HARVEST_CROWN)."""
        if self.bolt_cooldown > 0.0 or self.solar_bolts <= 0:
            return False
        self.solar_bolts -= 1
        self.bolt_cooldown = 0.22
        base_ang = math.atan2(self.facing_y, self.facing_x)
        base_dmg = 4 if self.has_boon("BILIM_SPARK") else 3
        spreads = (-0.22, 0.0, 0.22) if self.has_boon("HARVEST_CROWN") else (0.0,)
        for sp in spreads:
            ang = base_ang + sp
            projectiles.append(
                Projectile(
                    x=self.x + math.cos(ang) * 0.45,
                    y=self.y + math.sin(ang) * 0.45,
                    vx=math.cos(ang) * 11.5,
                    vy=math.sin(ang) * 11.5,
                    owner="player",
                    damage=base_dmg,
                    radius=0.22,
                    lifetime=1.45,
                )
            )
        return True

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
        self.dash_cooldown = (0.45 if self.has_boon("YALINCAK_GALE") else 0.65) * self.dash_cooldown_mult
        self.invuln_timer = max(self.invuln_timer, 0.22)
        return True

    def trigger_attack(self) -> bool:
        if self.attack_cooldown > 0.0:
            return False
        if self.combo_reset_timer > 0.0:
            self.combo_step = (self.combo_step + 1) % 3
        else:
            self.combo_step = 0
        self.combo_reset_timer = 0.85
        self.attack_timer = 0.20 if self.combo_step == 2 else 0.17
        self.attack_cooldown = 0.28
        self.attack_angle = math.atan2(self.facing_y, self.facing_x)
        return True

    def trigger_nova(self) -> bool:
        """Triggers the 360-degree Harvest Nova whirlwind if cooldown & warmth permit."""
        if self.nova_cooldown > 0.0 or self.warmth < 15.0:
            return False
        self.warmth = max(1.0, self.warmth - 12.0)
        self.nova_timer = 0.30
        self.nova_cooldown = 1.60
        self.invuln_timer = max(self.invuln_timer, 0.30)
        return True

    def increment_combo(self, amount: int = 1) -> None:
        """Increments combo meter up to maximum (6 hits)."""
        self.combo_hits = min(self.combo_hits_max, self.combo_hits + amount)

    def trigger_blade_dance(self) -> bool:
        """[X] / [R]: Triggers Bozkır Kılıç Dansı (Leaf Blade Dance) if combo meter is full."""
        if not self.combo_ready or self.blade_dance_timer > 0.0:
            return False
        self.combo_hits = 0
        self.blade_dance_timer = 0.65
        self.blade_dance_slash_count = 4
        self.blade_dance_slash_cooldown = 0.0
        self.invuln_timer = max(self.invuln_timer, 0.70)
        return True

    def trigger_cyclone(self) -> bool:
        """[T]: Unleashes Bozkır Rüzgarı Kasırgası (Leaf Cyclone), gathering leaves in a 360-deg whirlwind."""
        if self.cyclone_cooldown > 0.0 or self.warmth < 15.0:
            return False
        self.warmth = max(1.0, self.warmth - 14.0)
        self.cyclone_timer = 1.85
        self.cyclone_cooldown = 3.60
        self.invuln_timer = max(self.invuln_timer, 0.45)
        return True

    def update(
        self,
        dt: float,
        move_x: float,
        move_y: float,
        spatial_hash: ChunkSpatialHash,
        biome_grid: np.ndarray,
        dash_ghosts: Optional[List[DashGhost]] = None,
    ) -> Tuple[bool, bool]:
        """
        Updates player movement, collision, passive boons, and biome triggers.
        Returns (stepped_on_dry_leaves, stepped_on_damp_mud).
        """
        self.step_sfx_cooldown = max(0.0, self.step_sfx_cooldown - dt)
        self.leaf_boost_timer = max(0.0, self.leaf_boost_timer - dt)
        self.invuln_timer = max(0.0, self.invuln_timer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.combo_reset_timer = max(0.0, self.combo_reset_timer - dt)
        self.nova_timer = max(0.0, self.nova_timer - dt)
        self.nova_cooldown = max(0.0, self.nova_cooldown - dt)
        self.bolt_cooldown = max(0.0, self.bolt_cooldown - dt)
        self.noise_ripple_radius = max(0.0, self.noise_ripple_radius - dt * 4.5)
        self.blade_dance_timer = max(0.0, self.blade_dance_timer - dt)
        self.campfire_aura_timer = max(0.0, self.campfire_aura_timer - dt)
        self.overdrive_timer = max(0.0, self.overdrive_timer - dt)
        self.bilim_ritual_timer = max(0.0, self.bilim_ritual_timer - dt)
        self.yalincak_blessing_timer = max(0.0, self.yalincak_blessing_timer - dt)
        self.cyclone_timer = max(0.0, self.cyclone_timer - dt)
        self.cyclone_cooldown = max(0.0, self.cyclone_cooldown - dt)

        # Passive Solar Bolt recharge, Devrim Torch warmth aura & Bilim Ağacı ritual halo
        if self.solar_bolts < self.max_solar_bolts:
            self.bolt_recharge_timer += dt
            if self.bolt_recharge_timer >= 2.4:
                self.bolt_recharge_timer = 0.0
                self.solar_bolts += 1
        if self.has_boon("DEVRIM_TORCH"):
            self.warmth = min(self.max_warmth, self.warmth + dt * 2.5)
        if self.bilim_ritual_timer > 0.0:
            self.warmth = min(self.max_warmth, self.warmth + dt * 4.0)

        stepped_dry_leaves = False
        stepped_mud = False

        if self.dash_timer > 0.0:
            self.dash_timer = max(0.0, self.dash_timer - dt)
            speed = self.base_speed * 2.65
            vx = self.dash_dir_x * speed
            vy = self.dash_dir_y * speed
            self.ghost_spawn_timer -= dt
            if dash_ghosts is not None and self.ghost_spawn_timer <= 0.0:
                self.ghost_spawn_timer = 0.035
                dash_ghosts.append(
                    DashGhost(
                        x=self.x,
                        y=self.y,
                        facing_right=self.facing_right,
                        anim_frame=self.anim_frame,
                    )
                )
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
                if self.overdrive_timer > 0.0:
                    boost *= 1.35
                    if dash_ghosts is not None and int(self.walk_timer * 18.0) % 2 == 0:
                        dash_ghosts.append(
                            DashGhost(
                                x=self.x,
                                y=self.y,
                                facing_right=self.facing_right,
                                anim_frame=self.anim_frame,
                            )
                        )
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
