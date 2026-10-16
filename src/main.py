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
    spawn_world_entities,
)
from src.procgen.noise import compute_wind_vector_field
from src.procgen.pipeline import generate_autumn_world, WorldData
from src.procgen.prng import Xoshiro256StarStar, format_seed_code
from src.rendering.particles import VerletLeafSystem
from src.rendering.renderer import (
    WorldRenderer,
    DEBUG_NONE,
    DEBUG_NOISE_BIOME,
    DEBUG_BITMASK_GRID,
    DEBUG_PATHFINDING,
)
from src.ui.hud import GameHUD


class AutumnProcGenGame:
    """
    Main Engine & Gameplay Controller uniting the 6-Stage PCG Pipeline,
    Integer-Scaled 320x180 Pixel Renderer, Verlet Leaf Physics, and Audio Synthesizer.
    """

    def __init__(
        self,
        initial_seed: str = "KODTU2026",
        debug_procgen: bool = False,
        headless: bool = False,
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
            f"KODTU: Autumn ProcGen Engine | Seed: {initial_seed} | 320x180 Pixel-Perfect"
        )

        # Native 320x180 pixel-art canvas (strict integer scaling, zero bilinear blur)
        self.canvas = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
        self.clock = pygame.time.Clock()

        self.assets_dir = REPO_ROOT / "assets"
        self.assets = AssetBank(self.assets_dir)
        self.sound = SoundEngine(self.assets_dir / "audio", enabled=not headless)
        self.renderer = WorldRenderer(self.assets)
        self.camera = PixelCamera(NATIVE_WIDTH, NATIVE_HEIGHT)
        self.hud = GameHUD()

        self.debug_procgen = debug_procgen
        self.debug_mode = DEBUG_NONE
        self.reseed_rng = Xoshiro256StarStar(f"{initial_seed}:reseed_stream")
        self.odtu_presets = [
            ("ODTU-1956-DEVRIM", "ODTU DEVRIM STADYUMU KORUSU"),
            ("KODTU-2026-EYMIR", "EYMIR GOLU SONBAHAR KIYISI"),
            ("METU-BILIM-AGACI", "ODTU BILIM AGACI ANITI"),
            ("ODTU-YALINCAK-FALL", "YALINCAK SONBAHAR PATIKASI"),
        ]
        self.odtu_preset_idx = 0
        self.time_sec = 0.0
        self.wind_refresh_timer = 0.0
        self.bilim_aura_timer = 0.0

        # Active world state
        self.world: WorldData
        self.spatial_hash: ChunkSpatialHash
        self.player: Player
        self.items: List[CollectibleItem] = []
        self.enemies: List[EnemyAgent] = []
        self.floating_texts: List[FloatingText] = []
        self.leaf_system: VerletLeafSystem

        self.load_seed(initial_seed, depth_level=1)
        self.sound.start_ambience()

    def spawn_floating_text(
        self, x: float, y: float, text: str, color: tuple[int, int, int] = SUNLIT_BIRCH
    ) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color))

    def load_seed(self, seed_str: str, depth_level: int = 1) -> None:
        """
        Executes the 6-stage deterministic PCG pipeline for `seed_str` and initializes
        spatial hashing, entities, camera, and Verlet leaf particles.
        """
        self.world = generate_autumn_world(
            seed=seed_str, width=56, height=42, depth_level=depth_level
        )
        self.spatial_hash = ChunkSpatialHash(self.world.walkable_grid, self.world.props)
        self.renderer.bake_world_terrain(self.world)

        sx, sy = self.world.spawn_tile
        self.player = Player(float(sx) + 0.5, float(sy) + 0.5)
        self.items, self.enemies = spawn_world_entities(self.world.spawns)
        self.floating_texts.clear()

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

        pygame.display.set_caption(
            f"KODTU: Autumn ProcGen | Seed: {self.world.seed_input} ({self.world.seed_code}) | {self.world.total_gen_ms:.1f}ms"
        )
        self.hud.show_banner(
            f"GROVE {depth_level}: {self.world.seed_code} ({self.world.total_gen_ms:.1f}ms)"
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
        """Processes keyboard/mouse input, Debug Shortcuts ([F1]-[F5]), and Seed Modal."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.VIDEORESIZE:
                self.window_w, self.window_h = event.w, event.h
            elif event.type == pygame.KEYDOWN:
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

                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_TAB:
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
                elif event.key == pygame.K_SPACE:
                    self._perform_ember_attack()
                elif event.key == pygame.K_q:
                    self._perform_harvest_nova()
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self._perform_gust_dash()
                elif event.key == pygame.K_e:
                    self._try_interact_shrine()

            elif event.type == pygame.MOUSEBUTTONDOWN and not self.hud.seed_modal_open:
                if event.button == 1:
                    self._perform_ember_attack()
                elif event.button == 2:
                    self._perform_harvest_nova()
                elif event.button == 3:
                    self._perform_gust_dash()

        return True

    def _get_move_vector(self) -> tuple[float, float]:
        if self.hud.seed_modal_open:
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

    def _perform_gust_dash(self) -> None:
        mx, my = self._get_move_vector()
        if self.player.trigger_dash(mx, my):
            self.sound.play_leaf_crunch()
            px_x = self.player.x * TILE_SIZE
            px_y = self.player.y * TILE_SIZE
            self.leaf_system.spawn_burst(px_x, px_y, count=12, golden_bias=True)
            self.leaf_system.apply_radial_impulse(px_x, px_y, radius_px=36.0, strength=2.4)

    def _perform_ember_attack(self) -> None:
        if not self.player.trigger_attack():
            return
        self.sound.play("slash_ember")
        is_crit = self.player.combo_step == 2
        dmg = 4 if is_crit else 2
        reach = 2.15 if is_crit else 1.85

        px_x = self.player.x * TILE_SIZE
        px_y = self.player.y * TILE_SIZE
        sweep_cx = px_x + self.player.facing_x * 14.0
        sweep_cy = px_y + self.player.facing_y * 14.0
        self.leaf_system.apply_radial_impulse(
            sweep_cx, sweep_cy, radius_px=52.0 if is_crit else 42.0, strength=3.6 if is_crit else 3.0
        )
        self.leaf_system.spawn_burst(sweep_cx, sweep_cy, count=12 if is_crit else 7, golden_bias=True)

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
                    self.camera.add_trauma(0.32 if is_crit else 0.20)
                    label = f"CRIT -{dmg}!" if is_crit else f"-{dmg}"
                    self.spawn_floating_text(
                        enemy.x, enemy.y - 0.3, label, PALE_SUNBEAM if is_crit else HARVEST_GOLD
                    )
                    if defeated:
                        self.player.enemies_defeated += 1
                        self.player.warmth = min(self.player.max_warmth, self.player.warmth + 8.0)
                        self.leaf_system.spawn_burst(
                            enemy.x * TILE_SIZE, enemy.y * TILE_SIZE, count=16, golden_bias=False
                        )

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

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            dist = math.hypot(enemy.x - self.player.x, enemy.y - self.player.y)
            if dist <= 2.85:
                defeated = enemy.apply_hit(3, self.player.x, self.player.y, knockback=11.0)
                self.spawn_floating_text(enemy.x, enemy.y - 0.3, "-3 NOVA", SUNLIT_BIRCH)
                if defeated:
                    self.player.enemies_defeated += 1
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + 8.0)

    def _try_interact_shrine(self) -> None:
        sx, sy = self.world.shrine_tile
        dist = math.hypot(self.player.x - (sx + 0.5), self.player.y - (sy + 0.5))
        if dist <= 2.2:
            if self.player.relics_collected >= self.world.total_relics:
                next_depth = self.world.depth_level + 1
                next_seed = f"{self.world.seed_input}-G{next_depth}"
                self.sound.play("portal_activate")
                self.load_seed(next_seed, depth_level=next_depth)
            else:
                rem = self.world.total_relics - self.player.relics_collected
                self.hud.show_banner(f"SHRINE DORMANT: COLLECT {rem} MORE RELICS")

    def update(self, dt: float) -> None:
        self.time_sec += dt
        self.hud.update(dt)

        # Update floating combat texts
        alive_texts: List[FloatingText] = []
        for ft in self.floating_texts:
            ft.timer -= dt
            ft.y -= dt * 0.9
            if ft.timer > 0.0:
                alive_texts.append(ft)
        self.floating_texts = alive_texts

        # Periodically evolve the 2D Wind Vector Field with time
        self.wind_refresh_timer += dt
        if self.wind_refresh_timer >= 0.25:
            self.wind_refresh_timer = 0.0
            self.world.wind_vx, self.world.wind_vy = compute_wind_vector_field(
                self.world.wind_noise, self.world.width, self.world.height, time_sec=self.time_sec
            )

        mx, my = self._get_move_vector()
        stepped_leaves, stepped_mud = self.player.update(
            dt, mx, my, self.spatial_hash, self.world.biome_grid
        )

        # Warmth regeneration near Alchemist Campfires & ODTÜ Bilim Ağacı Monument
        self.bilim_aura_timer = max(0.0, self.bilim_aura_timer - dt)
        for st in self.world.structures:
            if st.structure_type == "campfire":
                if math.hypot(self.player.x - (st.tile_x + 0.5), self.player.y - (st.tile_y + 0.5)) <= 1.8:
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + dt * 9.0)
            elif st.structure_type == "bilim_agaci":
                if math.hypot(self.player.x - (st.tile_x + 0.5), self.player.y - (st.tile_y + 0.5)) <= 2.4:
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + dt * 15.0)
                    if self.bilim_aura_timer <= 0.0:
                        self.bilim_aura_timer = 2.8
                        self.spawn_floating_text(
                            st.tile_x + 0.5, st.tile_y - 0.4, "ODTU BILIM MESALESI +WARMTH", PALE_SUNBEAM
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
            self.sound.play("mud_step")

        # Update Collectibles
        for item in self.items:
            if item.collected:
                continue
            if math.hypot(self.player.x - item.x, self.player.y - item.y) <= 0.68:
                item.collected = True
                if item.kind == "relic":
                    self.player.relics_collected += 1
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + 20.0)
                    self.sound.play("harvest_chime")
                    self.spawn_floating_text(item.x, item.y, "+RELIC!", PALE_SUNBEAM)
                    self.leaf_system.spawn_burst(
                        item.x * TILE_SIZE, item.y * TILE_SIZE, count=18, golden_bias=True
                    )
                    if self.player.relics_collected >= self.world.total_relics:
                        self.sound.play("portal_activate")
                        self.hud.show_banner("ALL RELICS GATHERED! RETURN TO SHRINE [E]")
                    else:
                        self.hud.show_banner(
                            f"HARVEST RELIC {self.player.relics_collected}/{self.world.total_relics} RECLAIMED"
                        )
                else:
                    self.player.acorns_collected += 1
                    self.player.warmth = min(self.player.max_warmth, self.player.warmth + 10.0)
                    self.spawn_floating_text(item.x, item.y, "+10 WARMTH", HARVEST_GOLD)
                    self.sound.play("harvest_chime")

        # Update Enemies & check player contact
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            enemy.update(
                dt,
                self.player.x,
                self.player.y,
                self.player.noise_ripple_radius,
                self.spatial_hash,
            )
            if (
                self.player.invuln_timer <= 0.0
                and math.hypot(self.player.x - enemy.x, self.player.y - enemy.y)
                <= (self.player.radius + enemy.radius)
            ):
                self.player.warmth = max(0.0, self.player.warmth - enemy.damage)
                self.player.invuln_timer = 0.75
                self.camera.add_trauma(0.40)
                self.sound.play("hit_hurt")
                self.spawn_floating_text(
                    self.player.x, self.player.y - 0.3, f"-{int(enemy.damage)} WARMTH", CRIMSON_DECAY
                )
                if self.player.warmth <= 0.0:
                    sx, sy = self.world.spawn_tile
                    self.player.x = float(sx) + 0.5
                    self.player.y = float(sy) + 0.5
                    self.player.warmth = self.player.max_warmth
                    self.hud.show_banner("LANTERN REKINDLED AT GROVE HEART")

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

    def render(self) -> None:
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
        )
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
        )

        # Strict Integer Scaling onto the display window (Zero Bilinear Blur)
        scale, ox, oy, sw, sh = PixelCamera.compute_integer_viewport_rect(
            self.window_w, self.window_h
        )
        self.screen.fill(DEEP_VOID)
        scaled_surf = pygame.transform.scale(self.canvas, (sw, sh))
        self.screen.blit(scaled_surf, (ox, oy))
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
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    headless = args.headless_frames is not None
    game = AutumnProcGenGame(
        initial_seed=args.seed,
        debug_procgen=args.debug_procgen,
        headless=headless,
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
