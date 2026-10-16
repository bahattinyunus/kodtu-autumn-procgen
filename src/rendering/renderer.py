"""
Pixel-Perfect World Renderer, Y-Sorting (Painter's Algorithm), Frustum Culling,
Procedural Micro-Structure Rendering, and Live PCG Debug Overlays ([F1], [F2], [F4]).
"""

from __future__ import annotations
import math
from typing import Callable, List, Optional, Tuple
import pygame

from src.core.asset_builder import AssetBank
from src.core.camera import PixelCamera, TILE_SIZE, NATIVE_WIDTH, NATIVE_HEIGHT
from src.core.palette import (
    DEEP_VOID,
    PLUM_SHADOW,
    WITHERED_BARK,
    CRIMSON_DECAY,
    RUST_TERRACOTTA,
    BURNT_AMBER,
    HARVEST_GOLD,
    SUNLIT_BIRCH,
    PALE_SUNBEAM,
    AUTUMN_MIST,
    hue_shift_toward_light,
    hue_shift_toward_shadow,
)
from src.core.spatial_hash import ChunkSpatialHash, CHUNK_SIZE_TILES
from src.entities.actors import (
    Player,
    EnemyAgent,
    CollectibleItem,
    FloatingText,
    Projectile,
    DashGhost,
)
from src.procgen.pipeline import WorldData
from src.procgen.prng import hash_coords_2d

DEBUG_NONE = 0
DEBUG_NOISE_BIOME = 1      # [F1] Elevation, Moisture & Biome Overlay + Wind Vectors
DEBUG_BITMASK_GRID = 2     # [F2] 47-Tile Blob Bitmask Indices, Chunk Bounds & Colliders
DEBUG_PATHFINDING = 4      # [F4] Dijkstra Distance Field Heatmap, Flow-Field & BFS Shortest Path

from src.rendering.particles import VerletLeafSystem
from src.ui.pixel_font import draw_micro_number, PixelFontRenderer


class WorldRenderer:
    """
    Renders the procedural autumn world onto the native 320x180 pixel canvas.
    """

    def __init__(self, assets: AssetBank) -> None:
        self.assets = assets
        self.font = PixelFontRenderer()
        self.baked_terrain: Optional[pygame.Surface] = None
        self.baked_seed_uint64: Optional[int] = None
        self.last_draw_calls = 0
        self.last_culled_props = 0

    def bake_world_terrain(self, world: WorldData) -> None:
        """
        Pre-bakes the static biome floor tiles, boardwalk planks, and 47-Tile Blob Bitmask
        cliff/canopy tiles onto a world surface for O(1) frustum blitting.
        """
        px_w = world.width * TILE_SIZE
        px_h = world.height * TILE_SIZE
        surf = pygame.Surface((px_w, px_h))
        surf.fill(DEEP_VOID)

        for ty in range(world.height):
            for tx in range(world.width):
                dest = (tx * TILE_SIZE, ty * TILE_SIZE)
                b_id = int(world.biome_grid[ty, tx])
                floor_biome = b_id if b_id in (1, 2, 3) else 2
                var_idx = int(hash_coords_2d(tx, ty, world.seed_uint64 & 0xFFFF) * 4) % 4
                surf.blit(self.assets.floor_surfaces[floor_biome][var_idx], dest)

                if world.walkable_grid[ty, tx] == 1:
                    blob_idx = int(world.wall_blob_47[ty, tx])
                    surf.blit(self.assets.blob_47_surfaces[blob_idx], dest)

        # Bake boardwalk structures onto the terrain
        for st in world.structures:
            if st.structure_type == "boardwalk":
                surf.blit(
                    self.assets.boardwalk_surf,
                    (st.tile_x * TILE_SIZE, st.tile_y * TILE_SIZE),
                )

        self.baked_terrain = surf
        self.baked_seed_uint64 = world.seed_uint64

    def render_frame(
        self,
        canvas: pygame.Surface,
        world: WorldData,
        camera: PixelCamera,
        spatial_hash: ChunkSpatialHash,
        player: Player,
        items: List[CollectibleItem],
        enemies: List[EnemyAgent],
        leaf_system: VerletLeafSystem,
        time_sec: float,
        debug_mode: int = DEBUG_NONE,
        floating_texts: Optional[List[FloatingText]] = None,
        projectiles: Optional[List[Projectile]] = None,
        dash_ghosts: Optional[List[DashGhost]] = None,
    ) -> None:
        if self.baked_terrain is None or self.baked_seed_uint64 != world.seed_uint64:
            self.bake_world_terrain(world)

        canvas.fill(DEEP_VOID)
        draw_calls = 0

        # 1. Frustum-culled terrain blit
        assert self.baked_terrain is not None
        src_rect = pygame.Rect(camera.x, camera.y, NATIVE_WIDTH, NATIVE_HEIGHT)
        canvas.blit(self.baked_terrain, (0, 0), src_rect)
        draw_calls += 1

        # Compute visible tile frustum [x0..x1, y0..y1]
        x0, y0, x1, y1 = camera.get_visible_tile_bounds(world.width, world.height, margin_tiles=2)

        # 2. If [F1] or [F4] Debug Overlay is active, render tile-level heatmaps before entities
        if debug_mode == DEBUG_NOISE_BIOME:
            self._render_f1_noise_biome_overlay(canvas, world, camera, x0, y0, x1, y1)
        elif debug_mode == DEBUG_PATHFINDING:
            self._render_f4_dijkstra_overlay(canvas, world, camera, enemies, player, x0, y0, x1, y1)

        # 3. Gather Y-sortable entities inside the camera frustum (Painter's Algorithm)
        y_sort_queue: List[Tuple[float, Callable[[], None]]] = []

        # 3a. Ecological Props from Spatial Hash Chunks
        visible_props = spatial_hash.get_props_in_tile_bounds(x0, y0, x1, y1)
        self.last_culled_props = len(world.props) - len(visible_props)

        for prop in visible_props:
            px_x = prop.x * TILE_SIZE
            px_y = prop.y * TILE_SIZE
            sx, sy = camera.world_to_screen(px_x, px_y)
            sprite = self.assets.prop_surfaces.get((prop.prop_type, prop.variant))
            if sprite is None:
                continue

            if prop.prop_type.startswith("tree"):
                sway = int(round(math.sin(time_sec * 2.2 + prop.x * 0.9) * 1.0))
                draw_x = sx - 16 + sway
                draw_y = sy - 28
                sort_y = px_y
                y_sort_queue.append((sort_y, lambda s=sprite, dx=draw_x, dy=draw_y: canvas.blit(s, (dx, dy))))
            else:
                draw_x = sx - 8
                draw_y = sy - 12
                sort_y = (px_y - 6.0) if prop.prop_type == "leaf_pile" else px_y
                y_sort_queue.append((sort_y, lambda s=sprite, dx=draw_x, dy=draw_y: canvas.blit(s, (dx, dy))))

        # 3b. Alchemist Campfires & ODTÜ Bilim Ağacı (Procedural Micro-Structures)
        camp_frame = int(time_sec * 6.0) % 2
        camp_surf = self.assets.campfire_frames[camp_frame]
        bilim_surf = self.assets.bilim_agaci_surf
        for st in world.structures:
            if st.structure_type == "campfire":
                cx_px = (st.tile_x + 0.5) * TILE_SIZE
                cy_px = (st.tile_y + 0.5) * TILE_SIZE
                csx, csy = camera.world_to_screen(cx_px, cy_px)
                if -24 <= csx <= NATIVE_WIDTH + 24 and -24 <= csy <= NATIVE_HEIGHT + 24:
                    def _draw_camp(dx: int = csx, dy: int = csy) -> None:
                        pygame.draw.circle(canvas, BURNT_AMBER, (dx, dy), 14, 1)
                        pygame.draw.circle(canvas, HARVEST_GOLD, (dx, dy), 9, 1)
                        canvas.blit(camp_surf, (dx - 8, dy - 10))
                    y_sort_queue.append((cy_px, _draw_camp))
            elif st.structure_type == "bilim_agaci":
                bx_px = (st.tile_x + 0.5) * TILE_SIZE
                by_px = (st.tile_y + 0.5) * TILE_SIZE
                bsx, bsy = camera.world_to_screen(bx_px, by_px)
                if -32 <= bsx <= NATIVE_WIDTH + 32 and -32 <= bsy <= NATIVE_HEIGHT + 32:
                    def _draw_bilim(dx: int = bsx, dy: int = bsy) -> None:
                        pygame.draw.circle(canvas, CRIMSON_DECAY, (dx, dy), 15, 1)
                        pygame.draw.circle(canvas, SUNLIT_BIRCH, (dx, dy), 11, 1)
                        canvas.blit(bilim_surf, (dx - 16, dy - 26))
                    y_sort_queue.append((by_px, _draw_bilim))

        # 3c. Ancient Autumn Shrine (32x32)
        shx = (world.shrine_tile[0] + 0.5) * TILE_SIZE
        shy = (world.shrine_tile[1] + 0.5) * TILE_SIZE
        sh_sx, sh_sy = camera.world_to_screen(shx, shy)
        if -32 <= sh_sx <= NATIVE_WIDTH + 32 and -32 <= sh_sy <= NATIVE_HEIGHT + 32:
            awakened = player.relics_collected >= world.total_relics
            sh_surf = self.assets.shrine_awake_surf if awakened else self.assets.shrine_dormant_surf
            y_sort_queue.append(
                (shy, lambda s=sh_surf, dx=sh_sx - 16, dy=sh_sy - 20: canvas.blit(s, (dx, dy)))
            )

        # 3d. Collectibles (Relics & Acorns)
        for item in items:
            if item.collected:
                continue
            ix = item.x * TILE_SIZE
            iy = item.y * TILE_SIZE
            isx, isy = camera.world_to_screen(ix, iy)
            if not (-16 <= isx <= NATIVE_WIDTH + 16 and -16 <= isy <= NATIVE_HEIGHT + 16):
                continue
            frame = int((time_sec * 3.5 + item.bob_phase)) % 2
            isurf = self.assets.entity_surfaces[(item.kind, frame)]
            bob_px = int(round(math.sin(time_sec * 4.0 + item.bob_phase) * 1.5))
            y_sort_queue.append(
                (iy, lambda s=isurf, dx=isx - 8, dy=isy - 10 + bob_px: canvas.blit(s, (dx, dy)))
            )

        # 3e. Autumn Enemies & Elder Stag Warden
        for enemy in enemies:
            if not enemy.alive:
                continue
            ex = enemy.x * TILE_SIZE
            ey = enemy.y * TILE_SIZE
            esx, esy = camera.world_to_screen(ex, ey)
            if not (-16 <= esx <= NATIVE_WIDTH + 16 and -16 <= esy <= NATIVE_HEIGHT + 16):
                continue
            eframe = int(enemy.phase) % 2
            esurf = self.assets.entity_surfaces[(enemy.kind, eframe)]

            def _draw_enemy(
                s: pygame.Surface = esurf,
                dx: int = esx - 8,
                dy: int = esy - 12,
                flash: bool = enemy.hit_flash > 0.0,
                hp: int = enemy.hp,
                max_hp: int = enemy.max_hp,
                is_boss: bool = enemy.kind == "warden",
            ) -> None:
                canvas.blit(s, (dx, dy))
                if flash:
                    pygame.draw.rect(canvas, PALE_SUNBEAM, (dx + 3, dy + 3, 10, 10), 1)
                if hp < max_hp or is_boss:
                    bw = 14 if is_boss else 10
                    bx = dx + 8 - bw // 2
                    by = dy - 3
                    fill_w = max(1, int(round(bw * (hp / max(1, max_hp)))))
                    pygame.draw.rect(canvas, DEEP_VOID, (bx - 1, by - 1, bw + 2, 3))
                    pygame.draw.rect(canvas, SUNLIT_BIRCH if is_boss else CRIMSON_DECAY, (bx, by, fill_w, 1))

            y_sort_queue.append((ey, _draw_enemy))

        # 3f. Player (Autumn Keeper)
        pl_px_x = player.x * TILE_SIZE
        pl_px_y = player.y * TILE_SIZE
        pl_sx, pl_sy = camera.world_to_screen(pl_px_x, pl_px_y)
        p_frames = self.assets.player_frames_right if player.facing_right else self.assets.player_frames_left
        p_surf = p_frames[player.anim_frame]

        def _draw_player() -> None:
            # Subtle warm lantern ground halo
            pygame.draw.circle(canvas, HARVEST_GOLD, (pl_sx, pl_sy), 9, 1)
            if player.nova_timer > 0.0:
                # 360-degree Harvest Nova expanding ring
                nova_prog = 1.0 - (player.nova_timer / 0.30)
                nr = int(round(8 + nova_prog * 34))
                pygame.draw.circle(canvas, PALE_SUNBEAM, (pl_sx, pl_sy - 4), nr, 1)
                pygame.draw.circle(canvas, HARVEST_GOLD, (pl_sx, pl_sy - 4), max(2, nr - 3), 1)
            if player.dash_timer > 0.0:
                trail_x = int(round(pl_sx - player.dash_dir_x * 6))
                trail_y = int(round(pl_sy - player.dash_dir_y * 6))
                pygame.draw.circle(canvas, SUNLIT_BIRCH, (trail_x, trail_y - 4), 4, 1)
            canvas.blit(p_surf, (pl_sx - 8, pl_sy - 14))
            if player.attack_timer > 0.0:
                self._draw_ember_sweep(
                    canvas,
                    pl_sx,
                    pl_sy - 4,
                    player.attack_angle,
                    player.attack_timer,
                    is_crit=(player.combo_step == 2),
                )

        y_sort_queue.append((pl_px_y, _draw_player))

        # 3g. Dash Afterimage Ghosts (Hyper Light Drifter style silhouette trails)
        if dash_ghosts:
            for dg in dash_ghosts:
                gsx, gsy = camera.world_to_screen(dg.x * TILE_SIZE, dg.y * TILE_SIZE)
                if 0 <= gsx < NATIVE_WIDTH and 0 <= gsy < NATIVE_HEIGHT:
                    col = HARVEST_GOLD if dg.timer > 0.08 else BURNT_AMBER
                    y_sort_queue.append(
                        (
                            dg.y * TILE_SIZE - 1.0,
                            lambda dx=gsx, dy=gsy, c=col: pygame.draw.rect(
                                canvas, c, (dx - 3, dy - 10, 6, 9), 1
                            ),
                        )
                    )

        # Execute Painter's Algorithm (strict Y-order sort)
        y_sort_queue.sort(key=lambda entry: entry[0])
        for _, draw_fn in y_sort_queue:
            draw_fn()
            draw_calls += 1

        # 3h. Active Projectiles (Solar Ember Bolts & Deflectable Enemy Twilight Orbs)
        if projectiles:
            for proj in projectiles:
                if not proj.alive:
                    continue
                psx, psy = camera.world_to_screen(proj.x * TILE_SIZE, proj.y * TILE_SIZE)
                if -8 <= psx <= NATIVE_WIDTH + 8 and -8 <= psy <= NATIVE_HEIGHT + 8:
                    if proj.owner == "player":
                        outer = PALE_SUNBEAM if proj.deflected else HARVEST_GOLD
                        inner = SUNLIT_BIRCH
                        pygame.draw.circle(canvas, outer, (psx, psy - 4), 4)
                        pygame.draw.circle(canvas, inner, (psx, psy - 4), 2)
                        canvas.set_at(
                            (max(0, min(NATIVE_WIDTH - 1, psx)), max(0, min(NATIVE_HEIGHT - 1, psy - 4))),
                            PALE_SUNBEAM,
                        )
                    else:
                        pygame.draw.circle(canvas, DEEP_VOID, (psx, psy - 4), 4)
                        pygame.draw.circle(canvas, CRIMSON_DECAY, (psx, psy - 4), 3)
                        pygame.draw.circle(canvas, RUST_TERRACOTTA, (psx, psy - 4), 1)
                    draw_calls += 1

        # 4. Verlet Integration Falling Leaf Particles
        drawn_leaves = leaf_system.render(canvas, camera.x, camera.y, NATIVE_WIDTH, NATIVE_HEIGHT)
        draw_calls += drawn_leaves

        # 5. Floating Combat / Status Popups
        if floating_texts:
            for ft in floating_texts:
                fsx, fsy = camera.world_to_screen(ft.x * TILE_SIZE, ft.y * TILE_SIZE)
                if 0 <= fsx < NATIVE_WIDTH and 0 <= fsy < NATIVE_HEIGHT:
                    self.font.draw_text(canvas, ft.text, fsx, fsy - 14, ft.color, align_center=True)

        # 6. Subtle Drifting Autumn Mist (#D4C8BE) wisps near top/bottom edges
        self._render_autumn_mist_wisps(canvas, camera.x, camera.y, time_sec)

        # 7. If [F2] Bitmask & Grid Debug is active, render crisp grid, chunk bounds, bitmask IDs & colliders
        if debug_mode == DEBUG_BITMASK_GRID:
            self._render_f2_bitmask_grid_overlay(
                canvas, world, camera, spatial_hash, player, enemies, visible_props, x0, y0, x1, y1
            )

        self.last_draw_calls = draw_calls

    def _draw_ember_sweep(
        self,
        canvas: pygame.Surface,
        cx: int,
        cy: int,
        angle: float,
        timer: float,
        is_crit: bool = False,
    ) -> None:
        """Draws a pixel-art crescent Solar Ember wave in front of the player."""
        progress = 1.0 - (timer / (0.20 if is_crit else 0.17))
        base_r = (16.0 if is_crit else 13.5) + progress * 7.0
        half_steps = 8 if is_crit else 6
        arc_span = 1.45 if is_crit else 1.15
        for step in range(-half_steps, half_steps + 1):
            theta = angle + (step / float(half_steps)) * arc_span
            px = int(round(cx + math.cos(theta) * base_r))
            py = int(round(cy + math.sin(theta) * base_r))
            px_in = int(round(cx + math.cos(theta) * (base_r - 3.0)))
            py_in = int(round(cy + math.sin(theta) * (base_r - 3.0)))
            col_out = PALE_SUNBEAM if (is_crit or abs(step) <= 2) else SUNLIT_BIRCH
            col_in = SUNLIT_BIRCH if is_crit else (HARVEST_GOLD if abs(step) <= 3 else BURNT_AMBER)
            if 0 <= px < NATIVE_WIDTH and 0 <= py < NATIVE_HEIGHT:
                canvas.set_at((px, py), col_out)
                if px + 1 < NATIVE_WIDTH:
                    canvas.set_at((px + 1, py), col_out)
            if 0 <= px_in < NATIVE_WIDTH and 0 <= py_in < NATIVE_HEIGHT:
                canvas.set_at((px_in, py_in), col_in)

    def _render_autumn_mist_wisps(
        self, canvas: pygame.Surface, cam_x: int, cam_y: int, time_sec: float
    ) -> None:
        """Draws pixel-snapped drifting Autumn Mist (#D4C8BE) atmospheric particles."""
        for i in range(6):
            mx = int((i * 73 + time_sec * (10 + i * 2) - cam_x * 0.4) % (NATIVE_WIDTH + 40)) - 20
            my = int((i * 39 + math.sin(time_sec + i) * 6 - cam_y * 0.2) % NATIVE_HEIGHT)
            for dx in range(0, 14, 2):
                px = mx + dx
                if 0 <= px < NATIVE_WIDTH and 0 <= my < NATIVE_HEIGHT:
                    canvas.set_at((px, my), AUTUMN_MIST)

    def _render_f1_noise_biome_overlay(
        self,
        canvas: pygame.Surface,
        world: WorldData,
        camera: PixelCamera,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
    ) -> None:
        """
        [F1] Noise & Biome Overlay:
        Visualizes the multi-octave Simplex fBm Elevation & Moisture matrices,
        biome classification colors, and 2D Wind Vector Field directions.
        """
        overlay = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT), pygame.SRCALPHA)
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                sx, sy = camera.world_to_screen(tx * TILE_SIZE, ty * TILE_SIZE)
                elev = float(world.elevation[ty, tx])
                moist = float(world.moisture[ty, tx])
                biome = int(world.biome_grid[ty, tx])

                if biome == 0:
                    col = (*DEEP_VOID, 175)
                elif biome == 1:
                    c = hue_shift_toward_shadow(CRIMSON_DECAY, (1.0 - moist) * 0.4)
                    col = (*c, 155)
                elif biome == 2:
                    c = hue_shift_toward_light(BURNT_AMBER, (elev - 0.3) * 0.5)
                    col = (*c, 155)
                else:
                    c = hue_shift_toward_light(HARVEST_GOLD, (0.5 - moist) * 0.6)
                    col = (*c, 165)

                pygame.draw.rect(overlay, col, (sx, sy, TILE_SIZE, TILE_SIZE))

                # Draw 2D Wind Vector Field arrows on every 2nd tile
                if tx % 2 == 0 and ty % 2 == 0:
                    cx = sx + 8
                    cy = sy + 8
                    vx = float(world.wind_vx[ty, tx])
                    vy = float(world.wind_vy[ty, tx])
                    ex = int(round(cx + vx * 6.0))
                    ey = int(round(cy + vy * 6.0))
                    pygame.draw.line(overlay, (*SUNLIT_BIRCH, 210), (cx, cy), (ex, ey), 1)
                    overlay.set_at(
                        (max(0, min(NATIVE_WIDTH - 1, ex)), max(0, min(NATIVE_HEIGHT - 1, ey))),
                        (*PALE_SUNBEAM, 255),
                    )

        canvas.blit(overlay, (0, 0))

    def _render_f2_bitmask_grid_overlay(
        self,
        canvas: pygame.Surface,
        world: WorldData,
        camera: PixelCamera,
        spatial_hash: ChunkSpatialHash,
        player: Player,
        enemies: List[EnemyAgent],
        visible_props: List,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
    ) -> None:
        """
        [F2] Bitmask & Grid Debug:
        Displays 16x16 tile boundaries, 16x16-tile Spatial Hash Chunk borders,
        47-Tile Blob Bitmask indices (0..46) on wall tiles, and collision hitboxes.
        """
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                sx, sy = camera.world_to_screen(tx * TILE_SIZE, ty * TILE_SIZE)
                pygame.draw.rect(canvas, WITHERED_BARK, (sx, sy, TILE_SIZE, TILE_SIZE), 1)

                if tx % CHUNK_SIZE_TILES == 0:
                    pygame.draw.line(canvas, HARVEST_GOLD, (sx, sy), (sx, sy + TILE_SIZE), 1)
                if ty % CHUNK_SIZE_TILES == 0:
                    pygame.draw.line(canvas, HARVEST_GOLD, (sx, sy), (sx + TILE_SIZE, sy), 1)

                if world.walkable_grid[ty, tx] == 1:
                    blob_id = int(world.wall_blob_47[ty, tx])
                    draw_micro_number(canvas, str(blob_id), sx + 4, sy + 5, SUNLIT_BIRCH, DEEP_VOID)
                else:
                    m4 = int(world.biome_mask_4dir[ty, tx])
                    if m4 > 0:
                        draw_micro_number(canvas, str(m4), sx + 5, sy + 6, BURNT_AMBER, DEEP_VOID)

        for prop in visible_props:
            if prop.solid:
                psx, psy = camera.world_to_screen(prop.x * TILE_SIZE, prop.y * TILE_SIZE)
                r_px = int(round((0.34 if prop.prop_type.startswith("tree") else 0.30) * TILE_SIZE))
                pygame.draw.circle(canvas, CRIMSON_DECAY, (psx, psy), r_px, 1)

        for enemy in enemies:
            if enemy.alive:
                esx, esy = camera.world_to_screen(enemy.x * TILE_SIZE, enemy.y * TILE_SIZE)
                pygame.draw.circle(canvas, CRIMSON_DECAY, (esx, esy), int(round(enemy.radius * TILE_SIZE)), 1)

        pl_sx, pl_sy = camera.world_to_screen(player.x * TILE_SIZE, player.y * TILE_SIZE)
        pygame.draw.circle(canvas, SUNLIT_BIRCH, (pl_sx, pl_sy), int(round(player.radius * TILE_SIZE)), 1)

    def _render_f4_dijkstra_overlay(
        self,
        canvas: pygame.Surface,
        world: WorldData,
        camera: PixelCamera,
        enemies: List[EnemyAgent],
        player: Player,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
    ) -> None:
        """
        [F4] Pathfinding / Flood-Fill Visualizer:
        Renders the Dijkstra Geodesic Distance Field heatmap across walkable tiles,
        Flow-Field gradient arrows, the guaranteed BFS shortest path, and AI vectors.
        """
        overlay = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT), pygame.SRCALPHA)
        path_set = set(world.shortest_path)

        for ty in range(y0, y1):
            for tx in range(x0, x1):
                if world.walkable_grid[ty, tx] != 0:
                    continue
                sx, sy = camera.world_to_screen(tx * TILE_SIZE, ty * TILE_SIZE)
                d_norm = float(world.dijkstra_norm[ty, tx])
                dist_steps = int(world.dijkstra_dist[ty, tx])

                if d_norm < 0.25:
                    col = PLUM_SHADOW
                elif d_norm < 0.50:
                    col = CRIMSON_DECAY
                elif d_norm < 0.75:
                    col = BURNT_AMBER
                else:
                    col = HARVEST_GOLD

                alpha = 195 if (tx, ty) in path_set else 135
                pygame.draw.rect(overlay, (*col, alpha), (sx + 1, sy + 1, TILE_SIZE - 2, TILE_SIZE - 2))

                if (tx, ty) in path_set:
                    pygame.draw.rect(overlay, (*SUNLIT_BIRCH, 240), (sx + 2, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4), 1)

                if (tx + ty) % 2 == 0 and dist_steps >= 0:
                    draw_micro_number(overlay, str(dist_steps), sx + 3, sy + 5, AUTUMN_MIST, DEEP_VOID)
                else:
                    # Draw Flow-Field vector pointing down the geodesic gradient
                    fvx = float(world.flow_vx[ty, tx])
                    fvy = float(world.flow_vy[ty, tx])
                    if abs(fvx) > 0.0 or abs(fvy) > 0.0:
                        cx, cy = sx + 8, sy + 8
                        ex = int(round(cx + fvx * 5.0))
                        ey = int(round(cy + fvy * 5.0))
                        pygame.draw.line(overlay, (*PALE_SUNBEAM, 190), (cx, cy), (ex, ey), 1)

        pl_sx, pl_sy = camera.world_to_screen(player.x * TILE_SIZE, player.y * TILE_SIZE)
        for enemy in enemies:
            if not enemy.alive:
                continue
            esx, esy = camera.world_to_screen(enemy.x * TILE_SIZE, enemy.y * TILE_SIZE)
            dist = math.hypot(player.x - enemy.x, player.y - enemy.y)
            if dist <= enemy.aggro_range + player.noise_ripple_radius:
                pygame.draw.line(overlay, (*SUNLIT_BIRCH, 230), (esx, esy), (pl_sx, pl_sy), 1)

        canvas.blit(overlay, (0, 0))
