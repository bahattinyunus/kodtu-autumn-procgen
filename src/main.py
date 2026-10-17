"""
KODTÜ: Autumn ProcGen Engine - Main Application & Game Loop.

Usage:
    python src/main.py --seed "KODTU2026" --debug-procgen
"""

from __future__ import annotations
import argparse
import math
import os
from pathlib import Path
import sys
from typing import List, Optional

# Ensure repository root is on sys.path when invoked as `python src/main.py`
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pygame

from src.core.asset_builder import AssetBank
from src.core.audio_synth import SoundEngine
from src.core.camera import PixelCamera, NATIVE_WIDTH, NATIVE_HEIGHT, TILE_SIZE
from src.core.palette import (
    DEEP_VOID,
    CRIMSON_DECAY,
    HARVEST_GOLD,
    SUNLIT_BIRCH,
    PALE_SUNBEAM,
)
from src.core.spatial_hash import ChunkSpatialHash
from src.entities.actors import (
    Player,
    EnemyAgent,
    CollectibleItem,
    FloatingText,
    Projectile,
    DashGhost,
    SteppeCompanion,
    spawn_world_entities,
)
from src.procgen.noise import compute_wind_vector_field
from src.procgen.pipeline import generate_autumn_world, WorldData
from src.procgen.prng import Xoshiro256StarStar, format_seed_code, hash_coords_2d
from src.rendering.particles import VerletLeafSystem
from src.rendering.renderer import (
    WorldRenderer,
    DEBUG_NONE,
    DEBUG_NOISE_BIOME,
    DEBUG_BITMASK_GRID,
    DEBUG_PATHFINDING,
)
from src.core.story import StoryManager
from src.ui.hud import GameHUD
from src.ui.modern_overlay import ModernStoryOverlay


class AutumnProcGenGame:
    """
    Main Engine & Gameplay Controller uniting the 6-Stage PCG Pipeline,
    Integer-Scaled 320x180 Pixel Renderer, High-Res 1280x720 Modern Story UI,
    Verlet Leaf Physics, and Audio Synthesizer.
    """

    def __init__(
        self,
        initial_seed: str = "KODTU2026",
        debug_procgen: bool = False,
        headless: bool = False,
        target_victory_depth: int = 3,
    ) -> None:
        self.headless = headless
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

        pygame.init()
        self.window_w = NATIVE_WIDTH * 4   # 1280
        self.window_h = NATIVE_HEIGHT * 4  # 720

        flags = 0 if headless else pygame.RESIZABLE
        self.screen = pygame.display.set_mode((self.window_w, self.window_h), flags)
        pygame.display.set_caption(
            f"ODTÜ: Sonbaharın Son Işığı | KODTÜ Jam | Seed: {initial_seed}"
        )
        if not headless and sys.platform == "win32":
            try:
                import ctypes
                hwnd = pygame.display.get_wm_info().get("window")
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    ctypes.windll.user32.BringWindowToTop(hwnd)
            except Exception:
                pass

        # Native 320x180 pixel-art canvas (strict integer scaling, zero bilinear blur)
        self.canvas = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
        self.clock = pygame.time.Clock()

        self.assets_dir = REPO_ROOT / "assets"
        self.assets = AssetBank(self.assets_dir)
        self.sound = SoundEngine(self.assets_dir / "audio", enabled=not headless)
        self.renderer = WorldRenderer(self.assets)
        self.camera = PixelCamera(NATIVE_WIDTH, NATIVE_HEIGHT)
        self.hud = GameHUD()
        self.story = StoryManager(show_intro_card=not headless and not debug_procgen)
        self.modern_ui = ModernStoryOverlay(self.assets)

        self.debug_procgen = debug_procgen
        self.debug_mode = DEBUG_NONE
        self.reseed_rng = Xoshiro256StarStar(f"{initial_seed}:reseed_stream")
        self.odtu_presets = [
            ("ODTU-1956-DEVRIM", "ODTÜ DEVRİM STADYUMU KORUSU"),
            ("KODTU-2026-EYMIR", "EYMİR GÖLÜ SONBAHAR KIYISI"),
            ("METU-BILIM-AGACI", "ODTÜ BİLİM AĞACI ANITI"),
            ("ODTU-YALINCAK-FALL", "YALINCAK SONBAHAR PATİKASI"),
        ]
        self.odtu_preset_idx = 0
        self.time_sec = 0.0
        self.wind_refresh_timer = 0.0
        self.bilim_aura_timer = 0.0
        self.hit_stop_timer = 0.0
        self.target_victory_depth = target_victory_depth
        self.is_paused = False
        self.tactical_map_open = False
        self.thunder_timer = 18.0

        # Active world state
        self.world: WorldData
        self.spatial_hash: ChunkSpatialHash
        self.player: Player
        self.items: List[CollectibleItem] = []
        self.enemies: List[EnemyAgent] = []
        self.floating_texts: List[FloatingText] = []
        self.projectiles: List[Projectile] = []
        self.dash_ghosts: List[DashGhost] = []
        self.leaf_system: VerletLeafSystem

        self.load_seed(initial_seed, depth_level=1)
        self.sound.start_ambience()
        self.sound.start_music()

    def spawn_floating_text(
        self, x: float, y: float, text: str, color: tuple[int, int, int] = SUNLIT_BIRCH
    ) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color))

    def load_seed(self, seed_str: str, depth_level: int = 1) -> None:
        """
        Executes the 6-stage deterministic PCG pipeline for `seed_str` and initializes
        spatial hashing, entities, camera, story chapter, and Verlet leaf particles.
        """
        prev_boons = getattr(self, "player", None).active_boons if hasattr(self, "player") else []
        self.world = generate_autumn_world(
            seed=seed_str, width=56, height=42, depth_level=depth_level
        )
        self.spatial_hash = ChunkSpatialHash(self.world.walkable_grid, self.world.props)
        self.renderer.bake_world_terrain(self.world)

        sx, sy = self.world.spawn_tile
        self.player = Player(float(sx) + 0.5, float(sy) + 0.5)
        self.companion = SteppeCompanion(float(sx) + 1.2, float(sy) + 0.6, name="Bozkır Kangalı")
        if depth_level > 1 and prev_boons:
            for _ in range(len(prev_boons)):
                self.player.grant_next_boon()
        self.items, self.enemies = spawn_world_entities(self.world.spawns)
        self.floating_texts.clear()
        self.projectiles.clear()
        self.dash_ghosts.clear()

        self.leaf_system = VerletLeafSystem(self.world.seed_uint64, max_leaves=160)
        world_px_w = self.world.width * TILE_SIZE
        world_px_h = self.world.height * TILE_SIZE
        self.leaf_system.populate_initial(world_px_w, world_px_h)

        self.camera.snap_to(
            self.player.x * TILE_SIZE,
            self.player.y * TILE_SIZE,
            world_px_w,
            world_px_h,
        )

        self.story.start_chapter(depth_level, self.world.seed_code)
        chapter_title, _ = self.story.get_chapter_meta()
        pygame.display.set_caption(
            f"ODTÜ: Sonbaharın Son Işığı | {chapter_title} | Seed: {self.world.seed_code}"
        )
        self.hud.show_banner(
            f"{chapter_title} — TOHUM: {self.world.seed_code} ({self.world.total_gen_ms:.1f}ms)"
        )

        if self.debug_procgen:
            print(
                f"[PCG] Seed='{self.world.seed_input}' (0x{self.world.seed_uint64:016X} / {self.world.seed_code}) "
                f"| Total={self.world.total_gen_ms:.2f}ms | Props={len(self.world.props)} "
                f"| Structs={len(self.world.structures)} | Spawns={len(self.world.spawns)}"
            )

    def instant_reseed(self) -> None:
        """[F3] Instant Re-Seed: Generates a new deterministic seed and rebuilds the world."""
        next_u64 = self.reseed_rng.next_uint64()
        new_code = format_seed_code(next_u64)
        self.load_seed(new_code, depth_level=1)
        self.sound.play("portal_activate")
        self.leaf_system.spawn_burst(
            self.player.x * TILE_SIZE, self.player.y * TILE_SIZE, count=24, golden_bias=True
        )

    def cycle_odtu_preset(self) -> None:
        """[F5] Cycles through curated ODTÜ / METU campus heritage seeds."""
        seed_code, title = self.odtu_presets[self.odtu_preset_idx]
        self.odtu_preset_idx = (self.odtu_preset_idx + 1) % len(self.odtu_presets)
        self.load_seed(seed_code, depth_level=1)
        self.hud.show_banner(f"[F5] {title} ({seed_code})", duration=3.2)
        self.sound.play("portal_activate")
        self.leaf_system.spawn_burst(
            self.player.x * TILE_SIZE, self.player.y * TILE_SIZE, count=28, golden_bias=True
        )

    def handle_events(self) -> bool:
        """Processes keyboard/mouse input, Story Intro Card, Debug Shortcuts ([F1]-[F5]), and Seed Modal."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.VIDEORESIZE:
                self.window_w, self.window_h = event.w, event.h
            elif event.type == pygame.KEYDOWN:
                if self.story.show_intro_card:
                    if event.key == pygame.K_ESCAPE:
                        self.story.show_intro_card = False
                        continue
                    elif event.key in (
                        pygame.K_RETURN,
                        pygame.K_SPACE,
                        pygame.K_e,
                        pygame.K_h,
                        pygame.K_w,
                        pygame.K_a,
                        pygame.K_s,
                        pygame.K_d,
                    ):
                        self.story.show_intro_card = False
                        self.sound.play("portal_activate")
                        continue

                if getattr(self.story, "show_victory_modal", False):
                    if event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                        self.story.show_victory_modal = False
                        continue
                    elif event.key in (pygame.K_r, pygame.K_RETURN):
                        self.story.show_victory_modal = False
                        self.load_seed("ODTU-1956-DEVRIM", depth_level=1)
                        self.sound.play("portal_activate")
                        continue
                    elif event.key == pygame.K_c and self.world.depth_level < 5:
                        self.story.show_victory_modal = False
                        next_depth = self.world.depth_level + 1
                        next_seed = f"{self.world.seed_input}-G{next_depth}"
                        self.load_seed(next_seed, depth_level=next_depth)
                        self.sound.play("portal_activate")
                        continue
                    elif event.key == pygame.K_F5:
                        self.story.show_victory_modal = False
                        self.cycle_odtu_preset()
                        continue

                if self.hud.seed_modal_open:
                    if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                        self.hud.seed_modal_open = False
                    elif event.key == pygame.K_RETURN:
                        entered = self.hud.seed_input_buffer.strip() or "KODTU2026"
                        self.hud.seed_modal_open = False
                        self.load_seed(entered, depth_level=1)
                        self.sound.play("portal_activate")
                    elif event.key == pygame.K_F3:
                        self.hud.seed_modal_open = False
                        self.instant_reseed()
                    elif event.key == pygame.K_F5:
                        self.hud.seed_modal_open = False
                        self.cycle_odtu_preset()
                    elif event.key == pygame.K_BACKSPACE:
                        self.hud.seed_input_buffer = self.hud.seed_input_buffer[:-1]
                    else:
                        ch = event.unicode
                        if ch and ch.isprintable() and len(self.hud.seed_input_buffer) < 22:
                            self.hud.seed_input_buffer += ch
                    continue

                if getattr(self.hud, "ledger_modal_open", False):
                    if event.key in (pygame.K_ESCAPE, pygame.K_j, pygame.K_SPACE, pygame.K_RETURN):
                        self.hud.ledger_modal_open = False
                        continue
                    elif event.key == pygame.K_c:
                        self.hud.ledger_modal_open = False
                        self.hud.codex_modal_open = True
                        continue
                    elif event.key == pygame.K_TAB:
                        self.hud.ledger_modal_open = False
                        self.hud.seed_modal_open = True
                        self.hud.seed_input_buffer = self.world.seed_input
                        continue
                    continue

                if getattr(self, "tactical_map_open", False):
                    if event.key in (pygame.K_ESCAPE, pygame.K_n, pygame.K_m, pygame.K_SPACE, pygame.K_RETURN):
                        self.tactical_map_open = False
                        continue
                    continue

                if self.is_paused:
                    if event.key in (pygame.K_p, pygame.K_SPACE, pygame.K_RETURN):
                        self.is_paused = False
                        self.hud.show_banner("OYUN DEVAM EDİYOR", duration=1.5)
                        continue
                    elif event.key == pygame.K_u:
                        is_muted = self.sound.toggle_mute()
                        self.hud.show_banner("SES: KAPALI (MUTED)" if is_muted else "SES: AÇIK (%100)", duration=2.0)
                        continue
                    elif event.key == pygame.K_h:
                        self.story.show_intro_card = not self.story.show_intro_card
                        continue
                    elif event.key == pygame.K_c:
                        self.hud.codex_modal_open = not self.hud.codex_modal_open
                        continue
                    elif event.key == pygame.K_j:
                        self.hud.ledger_modal_open = not self.hud.ledger_modal_open
                        continue
                    elif event.key == pygame.K_n:
                        self.tactical_map_open = not self.tactical_map_open
                        continue
                    elif event.key == pygame.K_ESCAPE:
                        return False
                    continue

                if event.key == pygame.K_ESCAPE:
                    if self.hud.ledger_modal_open:
                        self.hud.ledger_modal_open = False
                        continue
                    if self.hud.codex_modal_open:
                        self.hud.codex_modal_open = False
                        continue
                    return False
                elif event.key == pygame.K_p:
                    self.is_paused = not self.is_paused
                    self.hud.show_banner("OYUN DURAKLATILDI [P]" if self.is_paused else "OYUN DEVAM EDİYOR", duration=2.0)
                elif event.key == pygame.K_u:
                    is_muted = self.sound.toggle_mute()
                    self.hud.show_banner("SES: KAPALI (MUTED)" if is_muted else "SES: AÇIK (%100)", duration=2.0)
                elif event.key == pygame.K_h:
                    self.story.show_intro_card = not self.story.show_intro_card
                elif event.key == pygame.K_c:
                    self.hud.codex_modal_open = not self.hud.codex_modal_open
                    if self.hud.codex_modal_open:
                        self.hud.ledger_modal_open = False
                elif event.key == pygame.K_j:
                    self.hud.ledger_modal_open = not self.hud.ledger_modal_open
                    if self.hud.ledger_modal_open:
                        self.hud.codex_modal_open = False
                        self.tactical_map_open = False
                elif event.key == pygame.K_n:
                    self.tactical_map_open = not self.tactical_map_open
                elif event.key == pygame.K_TAB:
                    self.hud.codex_modal_open = False
                    self.hud.ledger_modal_open = False
                    self.hud.seed_modal_open = True
                    self.hud.seed_input_buffer = self.world.seed_input
                elif event.key == pygame.K_m:
                    self.hud.show_minimap = not self.hud.show_minimap
                elif event.key == pygame.K_F1:
                    self.debug_mode = (
                        DEBUG_NONE if self.debug_mode == DEBUG_NOISE_BIOME else DEBUG_NOISE_BIOME
                    )
                    self.hud.show_banner(
                        "[F1] FBM NOISE, BIOME & WIND OVERLAY"
                        if self.debug_mode == DEBUG_NOISE_BIOME
                        else "STANDARD RENDER"
                    )
                elif event.key == pygame.K_F2:
                    self.debug_mode = (
                        DEBUG_NONE if self.debug_mode == DEBUG_BITMASK_GRID else DEBUG_BITMASK_GRID
                    )
                    self.hud.show_banner(
                        "[F2] 47-TILE BLOB BITMASK & CHUNK DEBUG"
                        if self.debug_mode == DEBUG_BITMASK_GRID
                        else "STANDARD RENDER"
                    )
                elif event.key == pygame.K_F3:
                    self.instant_reseed()
                elif event.key == pygame.K_F4:
                    self.debug_mode = (
                        DEBUG_NONE if self.debug_mode == DEBUG_PATHFINDING else DEBUG_PATHFINDING
                    )
                    self.hud.show_banner(
                        "[F4] DIJKSTRA DISTANCE & FLOW-FIELD"
                        if self.debug_mode == DEBUG_PATHFINDING
                        else "STANDARD RENDER"
                    )
                elif event.key == pygame.K_F5:
                    self.cycle_odtu_preset()
                elif event.key in (pygame.K_z, pygame.K_v):
                    self._perform_devrim_overdrive()
                elif event.key == pygame.K_g:
                    self._perform_steppe_alchemy()
                elif event.key == pygame.K_SPACE:
                    self._perform_ember_attack()
                elif event.key == pygame.K_f:
                    self._perform_solar_bolt()
                elif event.key == pygame.K_b:
                    self._unlock_next_boon()
                elif event.key == pygame.K_q:
                    self._perform_harvest_nova()
                elif event.key in (pygame.K_x, pygame.K_r):
                    self._perform_blade_dance()
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self._perform_gust_dash()
                elif event.key == pygame.K_e:
                    self._try_interact_action()

            elif event.type == pygame.MOUSEBUTTONDOWN and not self.hud.seed_modal_open:
                if getattr(self, "tactical_map_open", False):
                    self.tactical_map_open = False
                    continue
                if self.is_paused:
                    self.is_paused = False
                    self.hud.show_banner("OYUN DEVAM EDİYOR", duration=1.5)
                    continue
                if self.story.show_intro_card:
                    self.story.show_intro_card = False
                    self.sound.play("portal_activate")
                    continue
                if getattr(self.story, "show_victory_modal", False):
                    self.story.show_victory_modal = False
                    self.sound.play("portal_activate")
                    continue
                if event.button == 1:
                    self._perform_ember_attack()
                elif event.button == 2:
                    self._perform_harvest_nova()
                elif event.button == 3:
                    self._perform_solar_bolt()

        return True

    def _get_move_vector(self) -> tuple[float, float]:
        if (
            self.is_paused
            or getattr(self, "tactical_map_open", False)
            or getattr(self.hud, "ledger_modal_open", False)
            or self.hud.seed_modal_open
            or self.hud.codex_modal_open
            or self.story.show_intro_card
            or getattr(self.story, "show_victory_modal", False)
        ):
            return 0.0, 0.0
        keys = pygame.key.get_pressed()
        mx = 0.0
        my = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            mx -= 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            mx += 1.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            my -= 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            my += 1.0
        return mx, my

    def _unlock_next_boon(self) -> None:
        boon = self.player.grant_next_boon()
        if boon is not None:
            _, title, desc = boon
            self.sound.play("level_up")
            self.hud.show_banner(f"KUTSAMA: {title} ({desc})", duration=3.5)
            self.spawn_floating_text(self.player.x, self.player.y - 0.5, f"+{title}!", PALE_SUNBEAM)
        else:
            self.hud.show_banner("TÜM 5 ODTÜ KUTSAMASI AKTİF!", duration=2.4)

    def _perform_solar_bolt(self) -> None:
        """[F] / Right Click: Fires a blazing Solar Ember Bolt (Hyper Light Drifter style)."""
        if not self.player.trigger_solar_bolt(self.projectiles):
            self.spawn_floating_text(self.player.x, self.player.y - 0.4, "RECHARGE BOLT BY SLASH!", CRIMSON_DECAY)
            return
        self.sound.play("slash_ember")
        self.camera.add_trauma(0.15)
        px_x = self.player.x * TILE_SIZE
        px_y = self.player.y * TILE_SIZE
        self.leaf_system.spawn_burst(px_x, px_y, count=6, golden_bias=True)

    def _perform_gust_dash(self) -> None:
        mx, my = self._get_move_vector()
        if self.player.trigger_dash(mx, my):
            self.sound.play_leaf_crunch()
            px_x = self.player.x * TILE_SIZE
            px_y = self.player.y * TILE_SIZE
            self.leaf_system.spawn_burst(px_x, px_y, count=12, golden_bias=True)
            self.leaf_system.apply_radial_impulse(px_x, px_y, radius_px=36.0, strength=2.4)
            self._smash_nearby_props(self.player.x, self.player.y, 1.25)

    def _smash_nearby_props(self, cx: float, cy: float, radius: float) -> None:
        """Destroys nearby pumpkins/shrubs/leaf piles, unearthing acorns, embers, and whooshing leaf drifts."""
        destroyed = self.spatial_hash.destroy_destructible_props(cx, cy, radius)
        for prop in destroyed:
            if prop.prop_type == "leaf_pile":
                self.sound.play("leaf_scatter")
                self.leaf_system.spawn_burst(
                    prop.x * TILE_SIZE, prop.y * TILE_SIZE, count=24, golden_bias=True
                )
                self.leaf_system.apply_radial_impulse(
                    prop.x * TILE_SIZE, prop.y * TILE_SIZE, radius_px=48.0, strength=3.4
                )
                if hash_coords_2d(int(prop.x * 10), int(prop.y * 10), 0xC001) % 100 < 35:
                    self.items.append(
                        CollectibleItem(x=prop.x, y=prop.y, kind="acorn", bob_phase=prop.x)
                    )
                    self.spawn_floating_text(prop.x, prop.y - 0.3, "+GİZLİ PALAMUT!", HARVEST_GOLD)
                else:
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + 4.0)
                    self.spawn_floating_text(prop.x, prop.y - 0.3, "+4 YAPRAK KÖZÜ", PALE_SUNBEAM)
            else:
                self.sound.play_leaf_crunch()
                self.leaf_system.spawn_burst(
                    prop.x * TILE_SIZE,
                    prop.y * TILE_SIZE,
                    count=14 if prop.prop_type == "pumpkin" else 8,
                    golden_bias=(prop.prop_type == "pumpkin"),
                )
                if prop.prop_type == "pumpkin":
                    self.items.append(
                        CollectibleItem(x=prop.x, y=prop.y, kind="acorn", bob_phase=prop.x)
                    )
                    self.spawn_floating_text(prop.x, prop.y - 0.3, "+ACORN DROP!", HARVEST_GOLD)

    def _deflect_nearby_orbs(self, radius: float) -> None:
        """Deflects incoming enemy Twilight Orbs back at 1.6x speed and 2x damage."""
        for proj in self.projectiles:
            if not proj.alive or proj.owner != "enemy":
                continue
            if math.hypot(proj.x - self.player.x, proj.y - self.player.y) <= radius:
                proj.owner = "player"
                proj.deflected = True
                proj.vx = -proj.vx * 1.65
                proj.vy = -proj.vy * 1.65
                proj.damage = 6 if self.player.has_boon("EYMIR_REFLECT") else 5
                proj.lifetime = 1.8
                self.player.orbs_deflected += 1
                ach = self.story.unlock_achievement("FIRST_DEFLECT")
                if ach:
                    self.sound.play("level_up")
                    self.hud.show_banner(f"🏆 BAŞARIM: {ach.title} — {ach.description}", duration=3.8)
                self.player.recharge_bolt_on_melee()
                if self.player.has_boon("EYMIR_REFLECT"):
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + 6.0)
                self.sound.play("parry_spark")
                self.sound.play("deflect_clash")
                self.leaf_system.spawn_burst(proj.x * TILE_SIZE, proj.y * TILE_SIZE, count=8, golden_bias=True)
                self.hit_stop_timer = max(self.hit_stop_timer, 0.04)
                self.camera.add_trauma(0.28)
                self.spawn_floating_text(proj.x, proj.y - 0.3, "DEFLECT!", PALE_SUNBEAM)

    def _perform_ember_attack(self) -> None:
        if not self.player.trigger_attack():
            return
        self.sound.play("slash_ember")
        is_crit = self.player.combo_step == 2
        overdrive_bonus = 2 if getattr(self.player, "is_in_overdrive", False) else 0
        bonus_dmg = (1 if self.player.has_boon("BILIM_SPARK") else 0) + overdrive_bonus
        dmg = (4 if is_crit else 2) + bonus_dmg
        base_reach = 2.15 if is_crit else 1.85
        reach = base_reach + (0.30 if getattr(self.player, "is_in_overdrive", False) else 0.0)

        px_x = self.player.x * TILE_SIZE
        px_y = self.player.y * TILE_SIZE
        sweep_cx = px_x + self.player.facing_x * 14.0
        sweep_cy = px_y + self.player.facing_y * 14.0
        self.leaf_system.apply_radial_impulse(
            sweep_cx, sweep_cy, radius_px=52.0 if is_crit else 42.0, strength=3.6 if is_crit else 3.0
        )
        self.leaf_system.spawn_burst(sweep_cx, sweep_cy, count=12 if is_crit else 7, golden_bias=True)

        # Deflect enemy Twilight Orbs & smash destructible flora within melee arc
        self._deflect_nearby_orbs(reach)
        self._smash_nearby_props(
            self.player.x + self.player.facing_x * 0.85,
            self.player.y + self.player.facing_y * 0.85,
            1.35,
        )

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            dx = enemy.x - self.player.x
            dy = enemy.y - self.player.y
            dist = math.hypot(dx, dy)
            if dist <= reach:
                dot = (dx * self.player.facing_x + dy * self.player.facing_y) / max(1e-5, dist)
                if dot >= (-0.45 if is_crit else -0.25) or dist < 0.85:
                    defeated = enemy.apply_hit(dmg, self.player.x, self.player.y, knockback=8.5)
                    self.player.recharge_bolt_on_melee()
                    self.player.increment_combo(1)
                    if self.player.combo_ready:
                        self.spawn_floating_text(self.player.x, self.player.y - 0.6, "[X] KILIÇ DANSI HAZIR!", SUNLIT_BIRCH)
                    self.camera.add_trauma(0.32 if is_crit else 0.20)
                    if is_crit or defeated:
                        self.hit_stop_timer = max(self.hit_stop_timer, 0.038)
                    label = f"CRIT -{dmg}!" if is_crit else f"-{dmg}"
                    self.spawn_floating_text(
                        enemy.x, enemy.y - 0.3, label, PALE_SUNBEAM if is_crit else HARVEST_GOLD
                    )
                    if defeated:
                        self._on_enemy_defeated(enemy)

    def _perform_harvest_nova(self) -> None:
        """[Q] / Middle Click: Unleashes a 360-degree Harvest Nova shockwave."""
        if not self.player.trigger_nova():
            return
        self.sound.play("slash_ember")
        self.camera.add_trauma(0.38)
        px_x = self.player.x * TILE_SIZE
        px_y = self.player.y * TILE_SIZE
        self.leaf_system.spawn_burst(px_x, px_y, count=28, golden_bias=True)
        self.leaf_system.apply_radial_impulse(px_x, px_y, radius_px=72.0, strength=4.8)
        self.spawn_floating_text(self.player.x, self.player.y - 0.5, "HARVEST NOVA!", PALE_SUNBEAM)

        # Deflect all enemy orbs & smash destructible flora in a wide 360-degree ring
        self._deflect_nearby_orbs(2.95)
        self._smash_nearby_props(self.player.x, self.player.y, 2.65)

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist <= 2.85:
                defeated = enemy.apply_hit(3, self.player.x, self.player.y, knockback=11.0)
                self.player.recharge_bolt_on_melee()
                self.player.increment_combo(1)
                self.spawn_floating_text(enemy.x, enemy.y - 0.3, "-3 NOVA", SUNLIT_BIRCH)
                if defeated:
                    self._on_enemy_defeated(enemy)

    def _perform_blade_dance(self) -> None:
        """[X] / [R]: Bozkır Kılıç Dansı combo finisher flurry."""
        if not self.player.trigger_blade_dance():
            self.spawn_floating_text(
                self.player.x,
                self.player.y - 0.4,
                f"KILIÇ DANSI: {self.player.combo_hits}/{self.player.combo_hits_max} VURUŞ GEREKİR",
                CRIMSON_DECAY,
            )
            return

        self.sound.play("blade_dance")
        self.camera.add_trauma(0.50)
        self.hit_stop_timer = 0.06
        px_x = self.player.x * TILE_SIZE
        px_y = self.player.y * TILE_SIZE
        self.leaf_system.spawn_burst(px_x, px_y, count=48, golden_bias=True)
        self.leaf_system.apply_radial_impulse(px_x, px_y, radius_px=88.0, strength=6.0)
        self.spawn_floating_text(
            self.player.x, self.player.y - 0.6, "BOZKIR KILIÇ DANSI!", PALE_SUNBEAM
        )
        ach = self.story.unlock_achievement("BLADE_DANCE")
        if ach:
            self.sound.play("level_up")
            self.hud.show_banner(f"🏆 BAŞARIM: {ach.title} — {ach.description}", duration=4.0)

        # Multi-hit omnidirectional slash flurry
        self._deflect_nearby_orbs(3.4)
        self._smash_nearby_props(self.player.x, self.player.y, 3.2)

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist <= 3.4:
                defeated = enemy.apply_hit(6, self.player.x, self.player.y, knockback=14.0)
                self.spawn_floating_text(enemy.x, enemy.y - 0.35, "-6 DANSE!", HARVEST_GOLD)
                if defeated:
                    self._on_enemy_defeated(enemy)

    def _perform_devrim_overdrive(self) -> None:
        """[Z] / [V]: Triggers ODTÜ Devrim Overdrive fiery mode."""
        if self.player.trigger_devrim_overdrive():
            self.sound.play("devrim_overdrive")
            self.camera.add_trauma(0.55)
            self.hit_stop_timer = 0.05
            px_x = self.player.x * TILE_SIZE
            px_y = self.player.y * TILE_SIZE
            self.leaf_system.spawn_burst(px_x, px_y, count=36, golden_bias=True)
            self.leaf_system.apply_radial_impulse(px_x, px_y, radius_px=80.0, strength=5.5)
            self.spawn_floating_text(self.player.x, self.player.y - 0.7, "🔥 DEVRİM OVERDRIVE!", PALE_SUNBEAM)
            self.hud.show_banner("🔥 ODTÜ DEVRİM OVERDRIVE! HIZ +35%, ÇİFT HASAR & MENZİL!", duration=3.5)
            ach = self.story.unlock_achievement("DEVRIM_OVERDRIVE")
            if ach:
                self.sound.play("level_up")
                self.hud.show_banner(f"🏆 BAŞARIM: {ach.title} — {ach.description}", duration=4.0)
            self._deflect_nearby_orbs(3.2)
            self._smash_nearby_props(self.player.x, self.player.y, 2.8)
        else:
            self.spawn_floating_text(
                self.player.x,
                self.player.y - 0.4,
                "OVERDRIVE İÇİN %70+ ISI VE KOMBO GEREKİR!",
                CRIMSON_DECAY,
            )

    def _perform_steppe_alchemy(self) -> None:
        """[G]: Bozkır Simyası — Transmutes 2 Acorns at Campfire or Shrine into permanent upgrades."""
        # Check proximity to Campfire, Bilim Ağacı, or Shrine (within 2.4 tiles)
        near_alchemy_site = False
        site_name = "Bozkır Ocağı"
        for st in self.world.structures:
            if st.structure_type in ("campfire", "bilim_agaci", "ancient_shrine"):
                if math.hypot(self.player.x - (st.tile_x + 0.5), self.player.y - (st.tile_y + 0.5)) <= 2.4:
                    near_alchemy_site = True
                    site_name = "Bozkır Ateşi" if st.structure_type == "campfire" else "Bilim Ağacı"
                    break
        if not near_alchemy_site:
            sx, sy = self.world.shrine_tile
            if math.hypot(self.player.x - (sx + 0.5), self.player.y - (sy + 0.5)) <= 2.4:
                near_alchemy_site = True
                site_name = "Kadim Tapınak"

        if not near_alchemy_site:
            self.spawn_floating_text(
                self.player.x,
                self.player.y - 0.4,
                "SİMYA İÇİN ATEŞ VEYA TAPINAK YANINA GİT!",
                CRIMSON_DECAY,
            )
            return

        res = self.player.transmute_acorns()
        if res:
            self.sound.play("alchemy_chime")
            self.camera.add_trauma(0.35)
            px_x = self.player.x * TILE_SIZE
            px_y = self.player.y * TILE_SIZE
            self.leaf_system.spawn_burst(px_x, px_y, count=28, golden_bias=True)
            self.leaf_system.apply_radial_impulse(px_x, px_y, radius_px=60.0, strength=3.8)
            self.spawn_floating_text(self.player.x, self.player.y - 0.6, f"+{res}!", PALE_SUNBEAM)
            self.hud.show_banner(f"🔮 BOZKIR SİMYASI ({site_name}): {res}", duration=3.8)
            ach = self.story.unlock_achievement("STEPPE_ALCHEMY")
            if ach:
                self.sound.play("level_up")
                self.hud.show_banner(f"🏆 BAŞARIM: {ach.title} — {ach.description}", duration=4.0)
        else:
            self.spawn_floating_text(
                self.player.x,
                self.player.y - 0.4,
                f"SİMYA İÇİN EN AZ 2 PALAMUT GEREKİR (Mevcut: {self.player.acorns_collected})",
                CRIMSON_DECAY,
            )

    def _try_interact_action(self) -> None:
        """[E] Interacts with Historical Kitabeler, Campfire, Spring, Bilim Ağacı, Shrine, or Steppe Kangal Companion."""
        closest_st = None
        closest_idx = -1
        closest_dist = 999.0
        for idx, st in enumerate(self.world.structures):
            cx, cy = st.tile_x + 0.5, st.tile_y + 0.5
            dist = math.hypot(self.player.x - cx, self.player.y - cy)
            max_r = 2.4 if st.structure_type in ("bilim_agaci", "eymir_pinari") else 2.0
            if dist <= max_r and dist < closest_dist:
                closest_dist = dist
                closest_st = st
                closest_idx = idx

        if closest_st is not None:
            st = closest_st
            if st.structure_type == "odtu_kitabe":
                kx, ky = st.tile_x + 0.5, st.tile_y + 0.5
                title, _ = self.story.on_read_kitabe(closest_idx)
                self.player.warmth = min(self.player.max_warmth, self.player.warmth + 15.0)
                self.player.leaf_boost_timer = max(self.player.leaf_boost_timer, 8.0)
                self.sound.play("kitabe_chime")
                self.spawn_floating_text(kx, ky - 0.5, "KADİM ODTÜ MİRASI +ISI & HIZ", PALE_SUNBEAM)
                self.leaf_system.spawn_burst(
                    kx * TILE_SIZE, ky * TILE_SIZE, count=18, golden_bias=True
                )
                if len(self.story.read_kitabes) >= 3:
                    ach = self.story.unlock_achievement("CHRONICLE_HISTORIAN")
                    if ach:
                        self.sound.play("level_up")
                        self.hud.show_banner(f"🏆 BAŞARIM: {ach.title} — {ach.description}", duration=4.0)
                return
            elif st.structure_type == "campfire":
                cx, cy = st.tile_x + 0.5, st.tile_y + 0.5
                self.sound.play("campfire_sizzle")
                self.player.warmth = self.player.max_warmth
                self.player.campfire_aura_timer = 25.0
                self.leaf_system.spawn_burst(
                    cx * TILE_SIZE, cy * TILE_SIZE, count=24, golden_bias=True
                )
                if self.player.acorns_collected > 0:
                    self.player.acorns_collected -= 1
                    self.hud.show_banner(
                        "KÖZDE BOZKIR KESTANESİ KAVRULDU! (TAM ISI + 25s SICAK KÖZ AURASI)",
                        duration=3.5,
                    )
                    self.spawn_floating_text(cx, cy - 0.5, "KÖZLENMİŞ KESTANE!", HARVEST_GOLD)
                else:
                    self.hud.show_banner(
                        "KAMP ATEŞİNDE DİNLENİLDİ (TAM ISI + SICAK KÖZ AURASI)",
                        duration=3.0,
                    )
                    self.spawn_floating_text(cx, cy - 0.5, "KAMP ATEŞİ DİNLENMESİ!", PALE_SUNBEAM)
                return
            elif st.structure_type == "eymir_pinari":
                px, py = st.tile_x + 0.5, st.tile_y + 0.5
                self.sound.play("spring_splash")
                self.player.warmth = self.player.max_warmth
                self.player.invuln_timer = max(self.player.invuln_timer, 2.5)
                self.player.leaf_boost_timer = max(self.player.leaf_boost_timer, 6.0)
                self.leaf_system.spawn_burst(px * TILE_SIZE, py * TILE_SIZE, count=24, golden_bias=True)
                self.hud.show_banner("EYMİR ŞİFA PINARI YUDUMLANDI! (TAM ISI + 6s HIZ + KORUMA)", duration=3.5)
                self.spawn_floating_text(px, py - 0.5, "ŞİFA PINARI!", PALE_SUNBEAM)
                return
            elif st.structure_type == "bilim_agaci":
                bx, by = st.tile_x + 0.5, st.tile_y + 0.5
                self.sound.play("bilim_chime")
                self.player.warmth = self.player.max_warmth
                self.player.bilim_ritual_timer = 30.0
                self.camera.add_trauma(0.40)
                self.leaf_system.spawn_burst(bx * TILE_SIZE, by * TILE_SIZE, count=36, golden_bias=True)
                self.hud.show_banner("ODTÜ BİLİM AĞACI AYİNİ AKTİF! (30s BİLİM HALESİ & TAM ISI)", duration=4.0)
                self.spawn_floating_text(bx, by - 0.7, "BİLİM AĞACI HARLANDI!", PALE_SUNBEAM)
                ach = self.story.unlock_achievement("BILIM_CEREMONY")
                if ach:
                    self.sound.play("level_up")
                    self.hud.show_banner(f"🏆 BAŞARIM: {ach.title} — {ach.description}", duration=4.0)
                return

        # 2. Check Shrine
        if self._try_interact_shrine():
            return

        # 3. Check proximity to Steppe Kangal Companion
        if hasattr(self, "companion") and self.companion is not None:
            comp_dist = math.hypot(self.player.x - self.companion.x, self.player.y - self.companion.y)
            if comp_dist <= 1.8:
                self.companion.pet(self.player)
                self.sound.play("companion_bark")
                self.leaf_system.spawn_burst(
                    self.companion.x * TILE_SIZE, self.companion.y * TILE_SIZE, count=24, golden_bias=True
                )
                self.spawn_floating_text(self.companion.x, self.companion.y - 0.5, "SEVİLDİ! <3", PALE_SUNBEAM)
                self.hud.show_banner("🐾 BOZKIR KANGALI SEVİLDİ! (+12 ISI & SADIK DOST ENERJİSİ)", duration=3.2)
                ach = self.story.unlock_achievement("COMPANION_FRIEND")
                if ach:
                    self.sound.play("level_up")
                    self.hud.show_banner(f"🏆 BAŞARIM: {ach.title} — {ach.description}", duration=4.0)
                return

    def _try_interact_shrine(self) -> bool:
        sx, sy = self.world.shrine_tile
        dist = math.hypot(self.player.x - (sx + 0.5), self.player.y - (sy + 0.5))
        if dist <= 2.2:
            if self.player.relics_collected >= self.world.total_relics:
                if self.world.depth_level >= getattr(self, "target_victory_depth", 3):
                    # Grand Victory Sequence!
                    self.story.show_victory_modal = True
                    self.sound.play("level_up")
                    self.leaf_system.spawn_burst(
                        self.player.x * TILE_SIZE, self.player.y * TILE_SIZE, count=64, golden_bias=True
                    )
                    self.spawn_floating_text(self.player.x, self.player.y - 0.8, "EBEDİ DÖNGÜ TAMAMLANDI!", PALE_SUNBEAM)
                else:
                    next_depth = self.world.depth_level + 1
                    next_seed = f"{self.world.seed_input}-G{next_depth}"
                    self.sound.play("portal_activate")
                    self.load_seed(next_seed, depth_level=next_depth)
            else:
                rem = self.world.total_relics - self.player.relics_collected
                self.hud.show_banner(f"KADİM TAPINAK UYKUDA: {rem} ANILIK KRİSTAL DAHA GEREKLİ")
            return True
        return False

    def update(self, dt: float) -> None:
        self.time_sec += dt
        self.hud.update(dt)
        typewriter_stepped = self.story.update(dt)
        if typewriter_stepped and int(self.time_sec * 24) % 3 == 0:
            self.sound.play("dialogue_blip")

        # Pause gameplay movement/enemies while reading Intro Card, Victory Modal, Tactical Map, Ledger, or when Paused
        if (
            self.is_paused
            or getattr(self, "tactical_map_open", False)
            or getattr(self.hud, "ledger_modal_open", False)
            or self.story.show_intro_card
            or getattr(self.story, "show_victory_modal", False)
        ):
            return

        # Vlambeer / Nuclear Throne style tactile Hit-Stop micro-freeze
        if self.hit_stop_timer > 0.0:
            self.hit_stop_timer = max(0.0, self.hit_stop_timer - dt)
            return

        # Update floating combat texts & dash afterimage ghosts
        alive_texts: List[FloatingText] = []
        for ft in self.floating_texts:
            ft.timer -= dt
            ft.y -= dt * 0.9
            if ft.timer > 0.0:
                alive_texts.append(ft)
        self.floating_texts = alive_texts

        alive_ghosts: List[DashGhost] = []
        for dg in self.dash_ghosts:
            dg.timer -= dt
            if dg.timer > 0.0:
                alive_ghosts.append(dg)
        self.dash_ghosts = alive_ghosts

        # Atmospheric weather cycle & dynamic gameplay effects
        w_phase = int((self.time_sec // 40.0) % 3)
        if w_phase == 1:
            # Twilight Frost: subtle extra cold decay (mitigated by 50% under campfire aura)
            frost_factor = 0.50 if self.player.campfire_aura_timer > 0.0 else 1.0
            self.player.warmth = max(0.0, self.player.warmth - dt * 0.70 * frost_factor)
            if self.player.warmth <= 0.0:
                self._respawn_player(reason="frost")
        elif w_phase == 2:
            # Steppe Gale Surge: tailwind acceleration when moving & rolling distant thunder
            if self.player.walk_timer > 0.0:
                self.player.leaf_boost_timer = max(self.player.leaf_boost_timer, 0.25)
            self.thunder_timer = getattr(self, "thunder_timer", 18.0) - dt
            if self.thunder_timer <= 0.0:
                self.thunder_timer = 22.0
                self.sound.play("distant_thunder")
                self.camera.add_trauma(0.18)

        # Periodically evolve the 2D Wind Vector Field with time
        self.wind_refresh_timer += dt
        if self.wind_refresh_timer >= 0.25:
            self.wind_refresh_timer = 0.0
            wind_mult = 2.2 if w_phase == 2 else 1.0
            vx, vy = compute_wind_vector_field(
                self.world.wind_noise, self.world.width, self.world.height, time_sec=self.time_sec
            )
            self.world.wind_vx, self.world.wind_vy = vx * wind_mult, vy * wind_mult

        mx, my = self._get_move_vector()
        stepped_leaves, stepped_mud = self.player.update(
            dt, mx, my, self.spatial_hash, self.world.biome_grid, self.dash_ghosts
        )

        # Update Steppe Kangal Companion
        if hasattr(self, "companion"):
            did_bark, did_distract, alert_msg = self.companion.update(
                dt, self.player.x, self.player.y, self.enemies, self.spatial_hash
            )
            if did_bark:
                self.sound.play("companion_bark")
            if alert_msg:
                self.spawn_floating_text(
                    self.companion.x, self.companion.y - 0.5, alert_msg, SUNLIT_BIRCH
                )

        # Warmth regeneration near Alchemist Campfires & ODTÜ Bilim Ağacı Monument
        self.bilim_aura_timer = max(0.0, self.bilim_aura_timer - dt)
        for st in self.world.structures:
            if st.structure_type == "campfire":
                if math.hypot(self.player.x - (st.tile_x + 0.5), self.player.y - (st.tile_y + 0.5)) <= 1.8:
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + dt * 9.0)
                    self.story.on_near_campfire()
            elif st.structure_type == "odtu_kitabe":
                if math.hypot(self.player.x - (st.tile_x + 0.5), self.player.y - (st.tile_y + 0.5)) <= 1.8:
                    self.hud.show_banner("[E] ODTÜ KADİM TARİH KİTABESİNİ OKU", duration=0.3)
            elif st.structure_type == "bilim_agaci":
                if math.hypot(self.player.x - (st.tile_x + 0.5), self.player.y - (st.tile_y + 0.5)) <= 2.4:
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + dt * 15.0)
                    self.story.on_near_bilim_agaci()
                    if self.bilim_aura_timer <= 0.0:
                        self.bilim_aura_timer = 2.8
                        self.spawn_floating_text(
                            st.tile_x + 0.5, st.tile_y - 0.4, "ODTÜ BİLİM MEŞALESİ +ISI", PALE_SUNBEAM
                        )
                        self.leaf_system.spawn_burst(
                            (st.tile_x + 0.5) * TILE_SIZE,
                            (st.tile_y + 0.5) * TILE_SIZE,
                            count=10,
                            golden_bias=True,
                        )

        if stepped_leaves:
            self.sound.play_leaf_crunch()
            self.leaf_system.spawn_burst(
                self.player.x * TILE_SIZE,
                self.player.y * TILE_SIZE,
                count=5,
                golden_bias=self.player.leaf_boost_timer > 0.0,
            )
            self.leaf_system.apply_radial_impulse(
                self.player.x * TILE_SIZE, self.player.y * TILE_SIZE, radius_px=20.0, strength=1.2
            )
        elif stepped_mud:
            self.sound.play("water_splash")

        # Update Collectibles (Relics also unlock ODTÜ Autumn Boons & Story Memories!)
        for item in self.items:
            if item.collected:
                continue
            if math.hypot(self.player.x - item.x, self.player.y - item.y) <= 0.68:
                item.collected = True
                if item.kind == "relic":
                    self.player.relics_collected += 1
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + 20.0)
                    boon = self.player.grant_next_boon()
                    self.sound.play("level_up" if boon else "harvest_chime")
                    boon_label = f"+ANI & {boon[1]}!" if boon else "+SONBAHAR ANISI!"
                    self.spawn_floating_text(item.x, item.y, boon_label, PALE_SUNBEAM)
                    self.leaf_system.spawn_burst(
                        item.x * TILE_SIZE, item.y * TILE_SIZE, count=18, golden_bias=True
                    )
                    self.story.on_relic_collected(
                        self.player.relics_collected, self.world.total_relics
                    )
                    if self.player.relics_collected >= self.world.total_relics:
                        self.sound.play("portal_activate")
                        self.hud.show_banner("TÜM ANILAR TOPLANDI! KADİM TAPINAĞA DÖN [E]")
                    else:
                        self.hud.show_banner(
                            f"SONBAHAR ANISI {self.player.relics_collected}/{self.world.total_relics} + {boon[1] if boon else 'ISI'}"
                        )
                else:
                    self.player.acorns_collected += 1
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + 10.0)
                    self.spawn_floating_text(item.x, item.y, "+10 ISI", HARVEST_GOLD)
                    self.sound.play("harvest_chime")

        # Update Enemies & check player contact & boss encounter dialogue
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if enemy.kind == "warden":
                if math.hypot(self.player.x - enemy.x, self.player.y - enemy.y) <= 8.5:
                    self.story.on_boss_encounter()
                if enemy.is_enraged and not getattr(enemy, "has_roared", False):
                    enemy.has_roared = True
                    self.sound.play("boss_roar")
                    self.camera.add_trauma(0.55)
                    self.spawn_floating_text(enemy.x, enemy.y - 0.8, "KADİM ÖFKE UYANDI!", PALE_SUNBEAM)
                    self.leaf_system.spawn_burst(enemy.x * TILE_SIZE, enemy.y * TILE_SIZE, count=36, golden_bias=True)
            enemy.update(
                dt,
                self.player.x,
                self.player.y,
                self.player.noise_ripple_radius,
                self.spatial_hash,
                self.projectiles,
            )
            if (
                self.player.invuln_timer <= 0.0
                and math.hypot(self.player.x - enemy.x, self.player.y - enemy.y)
                <= (self.player.radius + enemy.radius)
            ):
                self._apply_player_damage(enemy.damage)

        # Update Projectiles (Solar Bolts & Enemy Twilight Orbs)
        alive_projectiles: List[Projectile] = []
        for proj in self.projectiles:
            if not proj.alive:
                continue
            proj.lifetime -= dt
            if proj.lifetime <= 0.0:
                continue
            proj.x += proj.vx * dt
            proj.y += proj.vy * dt
            tx, ty = int(proj.x), int(proj.y)
            if (
                tx < 1
                or ty < 1
                or tx >= self.world.width - 1
                or ty >= self.world.height - 1
                or self.world.walkable_grid[ty, tx] == 1
            ):
                self.leaf_system.spawn_burst(proj.x * TILE_SIZE, proj.y * TILE_SIZE, count=5, golden_bias=proj.owner == "player")
                continue

            if proj.owner == "player":
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue
                    if math.hypot(proj.x - enemy.x, proj.y - enemy.y) <= (proj.radius + enemy.radius):
                        proj.alive = False
                        defeated = enemy.apply_hit(proj.damage, proj.x, proj.y, knockback=9.0)
                        self.camera.add_trauma(0.24)
                        self.spawn_floating_text(
                            enemy.x,
                            enemy.y - 0.3,
                            f"-{proj.damage} KÖZ!",
                            PALE_SUNBEAM if proj.deflected else SUNLIT_BIRCH,
                        )
                        self.leaf_system.spawn_burst(
                            enemy.x * TILE_SIZE, enemy.y * TILE_SIZE, count=12, golden_bias=True
                        )
                        if defeated:
                            self._on_enemy_defeated(enemy)
                            self.hit_stop_timer = max(self.hit_stop_timer, 0.035)
                        break
            else:
                if (
                    self.player.invuln_timer <= 0.0
                    and math.hypot(proj.x - self.player.x, proj.y - self.player.y)
                    <= (proj.radius + self.player.radius)
                ):
                    proj.alive = False
                    self._apply_player_damage(float(proj.damage))

            if proj.alive:
                alive_projectiles.append(proj)
        self.projectiles = alive_projectiles

        # Update Camera & Verlet Leaf Particles
        world_px_w = self.world.width * TILE_SIZE
        world_px_h = self.world.height * TILE_SIZE
        self.camera.update(
            dt,
            self.player.x * TILE_SIZE,
            self.player.y * TILE_SIZE,
            world_px_w,
            world_px_h,
        )
        self.leaf_system.update(
            dt, self.world.wind_vx, self.world.wind_vy, world_px_w, world_px_h
        )

    def _on_enemy_defeated(self, enemy: EnemyAgent) -> None:
        """Handles reward, particle burst, SFX, and narrative dialogue on enemy defeat."""
        self.player.enemies_defeated += 1
        if enemy.kind == "warden":
            self.player.warmth = min(self.player.max_warmth, self.player.warmth + 35.0)
            self.sound.play("level_up")
            self.camera.add_trauma(0.60)
            self.hit_stop_timer = max(self.hit_stop_timer, 0.08)
            self.leaf_system.spawn_burst(
                enemy.x * TILE_SIZE, enemy.y * TILE_SIZE, count=48, golden_bias=True
            )
            # Drop 3 Golden Acorns around defeated boss
            for offset_ang in (0.0, 2.094, 4.188):
                drop_x = enemy.x + math.cos(offset_ang) * 0.75
                drop_y = enemy.y + math.sin(offset_ang) * 0.75
                self.items.append(
                    CollectibleItem(x=drop_x, y=drop_y, kind="acorn", bob_phase=offset_ang)
                )
            self.hud.show_banner("KADİM ORMAN BEKÇİSİ DİZE GELDİ! ORMAN HUZURA KAVUŞTU", duration=4.5)
            self.spawn_floating_text(enemy.x, enemy.y - 0.7, "KADİM BEKÇİ YENİLDİ!", PALE_SUNBEAM)
            self.story.trigger_dialogue(
                speaker="KADİM ORMAN BEKÇİSİ",
                title="BOZKIRIN HUZURU",
                text="'Gözlerindeki köz... Gerçekten de 1956'da toprağa düşen o ilk tohumun ruhunu taşıyorsun. Yürü evlat; bu orman artık seninle nefes alıyor.'",
                duration=7.5,
                accent_type="gold",
                avatar_key="warden",
                once_key=f"warden_defeat_{self.world.depth_level}",
            )
        elif enemy.kind == "wolf":
            self.player.warmth = min(self.player.max_warmth, self.player.warmth + 14.0)
            self.items.append(
                CollectibleItem(x=enemy.x, y=enemy.y, kind="acorn", bob_phase=enemy.x)
            )
            self.spawn_floating_text(enemy.x, enemy.y - 0.4, "+BOZKIR REÇİNESİ!", HARVEST_GOLD)
            self.leaf_system.spawn_burst(
                enemy.x * TILE_SIZE, enemy.y * TILE_SIZE, count=16, golden_bias=False
            )
        elif enemy.kind == "raven":
            self.sound.play("raven_screech")
            self.player.leaf_boost_timer = max(self.player.leaf_boost_timer, 4.0)
            self.player.warmth = min(self.player.max_warmth, self.player.warmth + 10.0)
            self.items.append(
                CollectibleItem(x=enemy.x, y=enemy.y, kind="acorn", bob_phase=enemy.x)
            )
            self.spawn_floating_text(enemy.x, enemy.y - 0.4, "+KUZGUN HIZI!", PALE_SUNBEAM)
            self.hud.show_banner("BOZKIR KUZGUNU SAVUŞTURULDU! (+4s HIZ İVMESİ & PALAMUT)", duration=3.0)
            self.leaf_system.spawn_burst(
                enemy.x * TILE_SIZE, enemy.y * TILE_SIZE, count=18, golden_bias=True
            )
        else:
            self.player.warmth = min(self.player.max_warmth, self.player.warmth + 8.0)
            self.leaf_system.spawn_burst(
                enemy.x * TILE_SIZE, enemy.y * TILE_SIZE, count=12, golden_bias=False
            )

    def _respawn_player(self, reason: str = "damage") -> None:
        """Respawns player at spawn tile with full warmth, invulnerability, and VFX."""
        sx, sy = self.world.spawn_tile
        self.player.x = float(sx) + 0.5
        self.player.y = float(sy) + 0.5
        self.player.warmth = self.player.max_warmth
        self.player.invuln_timer = 1.5
        self.sound.play("portal_activate")
        self.camera.add_trauma(0.45)
        self.leaf_system.spawn_burst(
            self.player.x * TILE_SIZE, self.player.y * TILE_SIZE, count=24, golden_bias=True
        )
        if reason == "frost":
            self.hud.show_banner("AYAZ FENERİ SÖNDÜRDÜ: DEVRİM ATEŞİYLE YENİDEN DOĞDUN", duration=4.0)
            self.spawn_floating_text(self.player.x, self.player.y - 0.5, "AYAZDAN DİRİLİŞ!", PALE_SUNBEAM)
        else:
            self.hud.show_banner("DEVRİM FENERİ KORUNUN KALBİNDE YENİDEN YANDI", duration=4.0)
            self.spawn_floating_text(self.player.x, self.player.y - 0.5, "FENER YENİDEN HARLANDI!", PALE_SUNBEAM)

    def _apply_player_damage(self, damage: float) -> None:
        # Check for Perfect Parry timing: player was in active ember slash or dash
        if self.player.attack_timer > 0.04 or (self.player.dash_timer > 0.05 and self.player.invuln_timer <= 0.0):
            # Mükemmel Savurma / Perfect Parry Counter!
            self.sound.play("parry_spark")
            self.sound.play("deflect_clash")
            self.hit_stop_timer = 0.08
            self.camera.add_trauma(0.45)
            self.player.invuln_timer = 0.50
            self.player.warmth = min(self.player.max_warmth, self.player.warmth + 12.0)
            self.player.recharge_bolt_on_melee()
            self.player.increment_combo(2)
            self.player.perfect_parries += 1
            self.spawn_floating_text(self.player.x, self.player.y - 0.5, "MÜKEMMEL SAVURMA!", PALE_SUNBEAM)
            self.hud.show_banner("⚡ MÜKEMMEL SAVURMA! (HASAR BLOKLANDI +12 ISI & KÖZ DOLUMU)", duration=2.8)
            ach = self.story.unlock_achievement("PERFECT_PARRY")
            if ach:
                self.sound.play("level_up")
                self.hud.show_banner(f"🏆 BAŞARIM: {ach.title} — {ach.description}", duration=4.0)
            self.leaf_system.spawn_burst(self.player.x * TILE_SIZE, self.player.y * TILE_SIZE, count=16, golden_bias=True)
            for en in self.enemies:
                if en.alive and math.hypot(en.x - self.player.x, en.y - self.player.y) <= 2.2:
                    en.apply_hit(5, self.player.x, self.player.y, knockback=12.0)
                    self.spawn_floating_text(en.x, en.y - 0.3, "-5 PARRY!", HARVEST_GOLD)
            return

        self.player.warmth = max(0.0, self.player.warmth - damage)
        self.player.invuln_timer = 0.75
        self.camera.add_trauma(0.40)
        self.sound.play("hit_hurt")
        self.spawn_floating_text(
            self.player.x, self.player.y - 0.3, f"-{int(damage)} ISI", CRIMSON_DECAY
        )
        if self.player.warmth <= 0.0:
            self._respawn_player(reason="damage")

    def render(self) -> None:
        w_phase = int((self.time_sec // 40.0) % 3)
        w_names = ["ALTIN İKİNDİ", "ALACAKARANLIK AYAZI", "BOZKIR FIRTINASI"]
        w_name = w_names[w_phase]

        self.renderer.render_frame(
            canvas=self.canvas,
            world=self.world,
            camera=self.camera,
            spatial_hash=self.spatial_hash,
            player=self.player,
            items=self.items,
            enemies=self.enemies,
            leaf_system=self.leaf_system,
            time_sec=self.time_sec,
            debug_mode=self.debug_mode,
            floating_texts=self.floating_texts,
            projectiles=self.projectiles,
            dash_ghosts=self.dash_ghosts,
            weather_phase=w_phase,
            companion=getattr(self, "companion", None),
        )
        # Render low-res canvas HUD only when debug modes, modals, or procgen telemetry are active
        if (
            self.debug_mode != DEBUG_NONE
            or self.debug_procgen
            or self.hud.seed_modal_open
            or self.hud.codex_modal_open
        ):
            self.hud.render(
                canvas=self.canvas,
                world=self.world,
                player=self.player,
                items=self.items,
                fps=self.clock.get_fps(),
                debug_mode=self.debug_mode,
                show_procgen_telemetry=self.debug_procgen,
                draw_calls=self.renderer.last_draw_calls,
                culled_props=self.renderer.last_culled_props,
                enemies=self.enemies,
            )

        # Strict Integer Scaling onto the display window (Zero Bilinear Blur)
        scale, ox, oy, sw, sh = PixelCamera.compute_integer_viewport_rect(
            self.window_w, self.window_h
        )
        self.screen.fill(DEEP_VOID)
        scaled_surf = pygame.transform.scale(self.canvas, (sw, sh))
        self.screen.blit(scaled_surf, (ox, oy))

        # High-Resolution 1280x720 Modern Story & Objective Overlay on top of Pixelated World
        self.modern_ui.render_hd_overlay(
            screen=self.screen,
            world=self.world,
            player=self.player,
            items=self.items,
            enemies=self.enemies,
            story=self.story,
            show_minimap=self.hud.show_minimap,
            codex_open=self.hud.codex_modal_open,
            seed_modal_open=self.hud.seed_modal_open,
            seed_input_buffer=self.hud.seed_input_buffer,
            banner_text=self.hud.banner_text,
            banner_timer=self.hud.banner_timer,
            weather_name=w_name,
            is_paused=self.is_paused,
            tactical_map_open=getattr(self, "tactical_map_open", False),
            ledger_open=getattr(self.hud, "ledger_modal_open", False),
        )
        pygame.display.flip()

    def export_debug_quad_showcase(self, output_path: Path) -> None:
        """
        Renders a 1280x720 2x2 showcase grid comparing:
        - Top-Left: Standard 16-Bit Pixel-Perfect Render (Y-Sorted + Minimap + Ember Sweep)
        - Top-Right: [F1] Multi-Octave Simplex fBm Noise, Biome & 2D Wind Vector Field
        - Bottom-Left: [F2] 47-Tile Blob Bitmask Indices & 16x16 Spatial Hash Chunks
        - Bottom-Right: [F4] Dijkstra Geodesic Distance Field, Flow-Field & Shortest Path
        """
        quad_surf = pygame.Surface((NATIVE_WIDTH * 4, NATIVE_HEIGHT * 4))
        modes = [
            (DEBUG_NONE, (0, 0)),
            (DEBUG_NOISE_BIOME, (NATIVE_WIDTH * 2, 0)),
            (DEBUG_BITMASK_GRID, (0, NATIVE_HEIGHT * 2)),
            (DEBUG_PATHFINDING, (NATIVE_WIDTH * 2, NATIVE_HEIGHT * 2)),
        ]
        prev_mode = self.debug_mode
        for mode, dest in modes:
            self.debug_mode = mode
            self.render()
            panel = pygame.transform.scale(self.canvas, (NATIVE_WIDTH * 2, NATIVE_HEIGHT * 2))
            quad_surf.blit(panel, dest)
        self.debug_mode = prev_mode
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(quad_surf, str(output_path))

    def run(
        self,
        max_frames: Optional[int] = None,
        export_screenshot: Optional[Path] = None,
        export_quad_showcase: Optional[Path] = None,
    ) -> None:
        frame_count = 0
        running = True
        while running:
            dt = min(0.05, self.clock.tick(60) / 1000.0)
            if self.headless:
                dt = 1.0 / 60.0
            running = self.handle_events()
            self.update(dt)
            self.render()
            frame_count += 1
            if max_frames is not None and frame_count >= max_frames:
                if export_screenshot is not None:
                    export_screenshot.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(self.screen, str(export_screenshot))
                if export_quad_showcase is not None:
                    self.export_debug_quad_showcase(export_quad_showcase)
                break

        pygame.quit()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="KODTÜ: Autumn ProcGen Engine - 16-Bit Pixelated Autumn Procedural Game"
    )
    parser.add_argument(
        "--seed",
        type=str,
        default="KODTU2026",
        help="Deterministic 64-bit seed string or share code (e.g. 'KODTU2026', 'KODTU-8492-FALL')",
    )
    parser.add_argument(
        "--debug-procgen",
        action="store_true",
        help="Enable live PCG pipeline telemetry panel and console timing output",
    )
    parser.add_argument(
        "--headless-frames",
        type=int,
        default=None,
        help="Run N frames headlessly for automated verification and exit",
    )
    parser.add_argument(
        "--export-preview",
        type=str,
        default=None,
        help="Optional file path to save a rendered PNG screenshot when finishing",
    )
    parser.add_argument(
        "--export-quad-showcase",
        type=str,
        default=None,
        help="Optional file path to save a 2x2 [F1]-[F4] debug showcase PNG",
    )
    parser.add_argument(
        "--target-depth",
        type=int,
        default=3,
        help="Depth level required for Grand Victory epilogue (default: 3, supports up to 5 for full METU Saga)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    headless = args.headless_frames is not None
    game = AutumnProcGenGame(
        initial_seed=args.seed,
        debug_procgen=args.debug_procgen,
        headless=headless,
        target_victory_depth=args.target_depth,
    )
    preview_path = Path(args.export_preview) if args.export_preview else None
    quad_path = Path(args.export_quad_showcase) if args.export_quad_showcase else None
    game.run(
        max_frames=args.headless_frames,
        export_screenshot=preview_path,
        export_quad_showcase=quad_path,
    )


if __name__ == "__main__":
    main()
