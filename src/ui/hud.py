"""
Pixel-Art HUD, Live Minimap Radar, Directional Relic/Shrine Compass,
PCG Telemetry Panel, and Interactive Seed Entry/Share Modal.
"""

from __future__ import annotations
import math
from typing import List, Optional, Tuple
import pygame

from src.core.camera import NATIVE_WIDTH, NATIVE_HEIGHT
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
)
from src.entities.actors import Player, CollectibleItem
from src.procgen.pipeline import WorldData
from src.rendering.renderer import (
    DEBUG_NONE,
    DEBUG_NOISE_BIOME,
    DEBUG_BITMASK_GRID,
    DEBUG_PATHFINDING,
)
from src.ui.pixel_font import PixelFontRenderer


class GameHUD:
    """Renders the pixel-perfect HUD, live minimap radar, telemetry overlay, and Seed Modal."""

    def __init__(self) -> None:
        self.font = PixelFontRenderer()
        self.seed_modal_open = False
        self.seed_input_buffer = ""
        self.banner_text = ""
        self.banner_timer = 0.0
        self.show_minimap = True
        self._minimap_base_surf: Optional[pygame.Surface] = None
        self._minimap_seed_u64: Optional[int] = None

    def show_banner(self, text: str, duration: float = 2.6) -> None:
        self.banner_text = text
        self.banner_timer = duration

    def update(self, dt: float) -> None:
        if self.banner_timer > 0.0:
            self.banner_timer = max(0.0, self.banner_timer - dt)

    def _ensure_minimap_base(self, world: WorldData) -> pygame.Surface:
        if self._minimap_base_surf is None or self._minimap_seed_u64 != world.seed_uint64:
            surf = pygame.Surface((world.width, world.height))
            surf.fill(DEEP_VOID)
            for ty in range(world.height):
                for tx in range(world.width):
                    b = int(world.biome_grid[ty, tx])
                    if b == 1:
                        surf.set_at((tx, ty), CRIMSON_DECAY)
                    elif b == 2:
                        surf.set_at((tx, ty), WITHERED_BARK)
                    elif b == 3:
                        surf.set_at((tx, ty), RUST_TERRACOTTA)
            for st in world.structures:
                if st.structure_type == "campfire":
                    surf.set_at((st.tile_x, st.tile_y), BURNT_AMBER)
            self._minimap_base_surf = surf
            self._minimap_seed_u64 = world.seed_uint64
        return self._minimap_base_surf

    def render(
        self,
        canvas: pygame.Surface,
        world: WorldData,
        player: Player,
        items: List[CollectibleItem],
        fps: float,
        debug_mode: int,
        show_procgen_telemetry: bool,
        draw_calls: int,
        culled_props: int,
    ) -> None:
        # 1. Top-Left: Lantern Warmth Bar & Relic Status
        pygame.draw.rect(canvas, DEEP_VOID, (4, 4, 102, 24))
        pygame.draw.rect(canvas, WITHERED_BARK, (4, 4, 102, 24), 1)

        # Warmth bar
        bar_w = int(round(68 * (player.warmth / max(1.0, player.max_warmth))))
        bar_col = HARVEST_GOLD if player.warmth > 35.0 else CRIMSON_DECAY
        pygame.draw.rect(canvas, PLUM_SHADOW, (32, 7, 68, 6))
        if bar_w > 0:
            pygame.draw.rect(canvas, bar_col, (32, 7, bar_w, 6))
            pygame.draw.line(canvas, SUNLIT_BIRCH, (32, 7), (32 + max(0, bar_w - 1), 7))
        self.font.draw_text(canvas, "WARM", 7, 5, SUNLIT_BIRCH)

        # Relic count & Shrine state
        awakened = player.relics_collected >= world.total_relics
        relic_str = (
            "SHRINE AWAKE [E]"
            if awakened
            else f"RELIC {player.relics_collected}/{world.total_relics} ACORN {player.acorns_collected}"
        )
        relic_col = PALE_SUNBEAM if awakened else HARVEST_GOLD
        self.font.draw_text(canvas, relic_str, 7, 16, relic_col)

        # 2. Top-Right: Seed String & Share Code + Live Minimap Radar
        seed_box_w = 126
        seed_box_x = NATIVE_WIDTH - seed_box_w - 4
        pygame.draw.rect(canvas, DEEP_VOID, (seed_box_x, 4, seed_box_w, 24))
        pygame.draw.rect(canvas, WITHERED_BARK, (seed_box_x, 4, seed_box_w, 24), 1)

        short_seed = world.seed_input[:12]
        self.font.draw_text(
            canvas, f"SEED:{short_seed}", NATIVE_WIDTH - 8, 5, SUNLIT_BIRCH, align_right=True
        )
        self.font.draw_text(
            canvas,
            f"{world.seed_code} D:{world.depth_level}",
            NATIVE_WIDTH - 8,
            16,
            AUTUMN_MIST,
            align_right=True,
        )

        if self.show_minimap and not self.seed_modal_open:
            mm_base = self._ensure_minimap_base(world)
            mm_x = NATIVE_WIDTH - world.width - 5
            mm_y = 31
            pygame.draw.rect(
                canvas, DEEP_VOID, (mm_x - 1, mm_y - 1, world.width + 2, world.height + 2)
            )
            pygame.draw.rect(
                canvas, WITHERED_BARK, (mm_x - 1, mm_y - 1, world.width + 2, world.height + 2), 1
            )
            canvas.blit(mm_base, (mm_x, mm_y))

            # Draw uncollected relics on minimap
            for it in items:
                if not it.collected and it.kind == "relic":
                    canvas.set_at((mm_x + int(it.x), mm_y + int(it.y)), HARVEST_GOLD)

            # Draw Shrine on minimap
            sx, sy = world.shrine_tile
            canvas.set_at((mm_x + sx, mm_y + sy), PALE_SUNBEAM)

            # Draw Player on minimap
            px, py = max(0, min(world.width - 1, int(player.x))), max(0, min(world.height - 1, int(player.y)))
            canvas.set_at((mm_x + px, mm_y + py), SUNLIT_BIRCH)

        # 3. Directional Compass Arrow toward nearest uncollected Relic or Awakened Shrine
        target_xy = self._find_guidance_target(world, player, items)
        if target_xy is not None:
            tx, ty, is_shrine = target_xy
            dx = tx - player.x
            dy = ty - player.y
            dist = math.hypot(dx, dy)
            if dist > 1.2:
                angle = math.atan2(dy, dx)
                cx = NATIVE_WIDTH // 2
                cy = 14
                ax = int(round(cx + math.cos(angle) * 7.0))
                ay = int(round(cy + math.sin(angle) * 7.0))
                col = PALE_SUNBEAM if is_shrine else HARVEST_GOLD
                pygame.draw.circle(canvas, DEEP_VOID, (cx, cy), 9)
                pygame.draw.circle(canvas, WITHERED_BARK, (cx, cy), 9, 1)
                pygame.draw.line(canvas, col, (cx, cy), (ax, ay), 2)
                canvas.set_at((ax, ay), SUNLIT_BIRCH)

        # 4. PCG Telemetry & Debug Overlay Bar
        if show_procgen_telemetry or debug_mode != DEBUG_NONE:
            self._render_telemetry_panel(canvas, world, fps, debug_mode, draw_calls, culled_props)
        else:
            pygame.draw.rect(canvas, DEEP_VOID, (4, NATIVE_HEIGHT - 14, NATIVE_WIDTH - 8, 11))
            self.font.draw_text(
                canvas,
                "[F1-F4]Debug [SPC]Slash [Q]Nova [SHF]Dash [TAB]Seed [M]Map",
                NATIVE_WIDTH // 2,
                NATIVE_HEIGHT - 13,
                AUTUMN_MIST,
                align_center=True,
            )

        # 5. Floating Banner Notification
        if self.banner_timer > 0.0 and self.banner_text:
            bw = min(NATIVE_WIDTH - 20, len(self.banner_text) * 6 + 16)
            bx = (NATIVE_WIDTH - bw) // 2
            by = 32
            pygame.draw.rect(canvas, DEEP_VOID, (bx, by, bw, 15))
            pygame.draw.rect(canvas, HARVEST_GOLD, (bx, by, bw, 15), 1)
            self.font.draw_text(
                canvas, self.banner_text, NATIVE_WIDTH // 2, by + 3, PALE_SUNBEAM, align_center=True
            )

        # 6. Interactive Seed Input Modal ([TAB])
        if self.seed_modal_open:
            self._render_seed_modal(canvas, world)

    def _find_guidance_target(
        self, world: WorldData, player: Player, items: List[CollectibleItem]
    ) -> Optional[Tuple[float, float, bool]]:
        uncollected = [it for it in items if not it.collected and it.kind == "relic"]
        if not uncollected:
            return (world.shrine_tile[0] + 0.5, world.shrine_tile[1] + 0.5, True)
        nearest = min(
            uncollected, key=lambda it: (it.x - player.x) ** 2 + (it.y - player.y) ** 2
        )
        return (nearest.x, nearest.y, False)

    def _render_telemetry_panel(
        self,
        canvas: pygame.Surface,
        world: WorldData,
        fps: float,
        debug_mode: int,
        draw_calls: int,
        culled_props: int,
    ) -> None:
        panel_x = 4
        panel_y = NATIVE_HEIGHT - 44
        panel_w = NATIVE_WIDTH - 8
        panel_h = 40
        pygame.draw.rect(canvas, DEEP_VOID, (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(canvas, BURNT_AMBER, (panel_x, panel_y, panel_w, panel_h), 1)

        mode_names = {
            DEBUG_NONE: "STANDARD RENDER (Y-SORT + LUT)",
            DEBUG_NOISE_BIOME: "[F1] FBM NOISE & BIOME + WIND",
            DEBUG_BITMASK_GRID: "[F2] 47-BLOB BITMASK & CHUNKS",
            DEBUG_PATHFINDING: "[F4] DIJKSTRA & FLOW-FIELD",
        }
        m_label = mode_names.get(debug_mode, "DEBUG")
        self.font.draw_text(canvas, m_label, panel_x + 4, panel_y + 3, SUNLIT_BIRCH)
        self.font.draw_text(
            canvas,
            f"FPS:{int(fps)} DC:{draw_calls} CULL:{culled_props}",
            panel_x + panel_w - 4,
            panel_y + 3,
            HARVEST_GOLD,
            align_right=True,
        )

        t_fbm = world.timings_ms.get("1_fbm_noise", 0.0)
        t_ca = world.timings_ms.get("2_automata_bfs", 0.0)
        t_auto = world.timings_ms.get("3_autotile_47", 0.0)
        t_pois = world.timings_ms.get("4_poisson_disk", 0.0)
        self.font.draw_text(
            canvas,
            f"PCG:{world.total_gen_ms:.1f}ms (fBm:{t_fbm:.1f} CA+BFS:{t_ca:.1f} Blob47:{t_auto:.1f} Pois:{t_pois:.1f})",
            panel_x + 4,
            panel_y + 15,
            AUTUMN_MIST,
        )

        walkable_pct = 100.0 * float((world.walkable_grid == 0).sum()) / float(world.width * world.height)
        self.font.draw_text(
            canvas,
            f"64b:0x{world.seed_uint64:016X} | FLOOR:{walkable_pct:.0f}% | PROPS:{len(world.props)}",
            panel_x + 4,
            panel_y + 27,
            BURNT_AMBER,
        )

    def _render_seed_modal(self, canvas: pygame.Surface, world: WorldData) -> None:
        mw, mh = 236, 78
        mx = (NATIVE_WIDTH - mw) // 2
        my = (NATIVE_HEIGHT - mh) // 2
        pygame.draw.rect(canvas, DEEP_VOID, (mx, my, mw, mh))
        pygame.draw.rect(canvas, HARVEST_GOLD, (mx, my, mw, mh), 2)

        self.font.draw_text(
            canvas,
            "DETERMINISTIC SEED SERIALIZER",
            NATIVE_WIDTH // 2,
            my + 6,
            SUNLIT_BIRCH,
            medium=True,
            align_center=True,
        )
        self.font.draw_text(
            canvas,
            f"Current Share Code: {world.seed_code}",
            NATIVE_WIDTH // 2,
            my + 21,
            AUTUMN_MIST,
            align_center=True,
        )

        pygame.draw.rect(canvas, PLUM_SHADOW, (mx + 14, my + 35, mw - 28, 16))
        pygame.draw.rect(canvas, BURNT_AMBER, (mx + 14, my + 35, mw - 28, 16), 1)
        cursor = "_" if (pygame.time.get_ticks() // 400) % 2 == 0 else " "
        self.font.draw_text(
            canvas,
            f"> {self.seed_input_buffer}{cursor}",
            mx + 18,
            my + 38,
            PALE_SUNBEAM,
        )

        self.font.draw_text(
            canvas,
            "[ENTER] Synthesize Seed   [F3] Random   [ESC/TAB] Close",
            NATIVE_WIDTH // 2,
            my + 58,
            HARVEST_GOLD,
            align_center=True,
        )
