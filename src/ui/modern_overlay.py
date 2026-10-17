"""
Modern High-Resolution (1280x720) Story & UI Overlay Renderer.

Combines a 100% Pixelated Autumn World with a clean, readable, modern HD
Turkish user interface, objective tracker, character portrait dialogue box,
and interactive story intro card (inspired by Celeste, Eastward, and Sea of Stars).
"""

from __future__ import annotations
import math
from typing import List, Optional
import pygame

from src.core.palette import (
    DEEP_VOID,
    PLUM_SHADOW,
    WITHERED_BARK,
    MULBERRY_DUSK,
    CRIMSON_DECAY,
    RUST_TERRACOTTA,
    BURNT_AMBER,
    HARVEST_GOLD,
    OCHRE_CLAY,
    SUNLIT_BIRCH,
    PALE_SUNBEAM,
    AUTUMN_MIST,
)
from src.core.asset_builder import AssetBank
from src.core.story import StoryManager, CHAPTER_INFO, evaluate_academic_grade
from src.entities.actors import Player, CollectibleItem, EnemyAgent, AUTUMN_BOONS
from src.procgen.pipeline import WorldData


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """Word-wraps a UTF-8 string to fit within `max_width` pixels."""
    words = text.split(" ")
    lines: List[str] = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


class ModernStoryOverlay:
    """
    Renders crisp 1280x720 HD UI panels, story dialogues, and title screen
    directly onto the display surface while preserving the integer-scaled
    pixel-art world underneath.
    """

    def __init__(self, assets: AssetBank) -> None:
        self.assets = assets
        pygame.font.init()
        font_names = "segoeui,verdana,tahoma,arial,consolas"
        self.f_title = pygame.font.SysFont(font_names, 28, bold=True)
        self.f_subtitle = pygame.font.SysFont(font_names, 17, bold=True)
        self.f_body = pygame.font.SysFont(font_names, 15, bold=False)
        self.f_body_bold = pygame.font.SysFont(font_names, 15, bold=True)
        self.f_small = pygame.font.SysFont(font_names, 13, bold=True)
        self.f_card_desc = pygame.font.SysFont(font_names, 13, bold=False)
        self.f_tiny = pygame.font.SysFont(font_names, 12, bold=False)

        self._minimap_surf: Optional[pygame.Surface] = None
        self._minimap_seed: Optional[int] = None

    def _get_minimap(self, world: WorldData) -> pygame.Surface:
        if self._minimap_surf is None or self._minimap_seed != world.seed_uint64:
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
                elif st.structure_type == "bilim_agaci":
                    surf.set_at((st.tile_x, st.tile_y), SUNLIT_BIRCH)
                elif st.structure_type == "odtu_kitabe":
                    surf.set_at((st.tile_x, st.tile_y), AUTUMN_MIST)
            self._minimap_surf = surf
            self._minimap_seed = world.seed_uint64
        return self._minimap_surf

    def render_hd_overlay(
        self,
        screen: pygame.Surface,
        world: WorldData,
        player: Player,
        items: List[CollectibleItem],
        enemies: List[EnemyAgent],
        story: StoryManager,
        show_minimap: bool = True,
        codex_open: bool = False,
        seed_modal_open: bool = False,
        seed_input_buffer: str = "",
        banner_text: str = "",
        banner_timer: float = 0.0,
        weather_name: str = "ALTIN İKİNDİ",
        is_paused: bool = False,
        tactical_map_open: bool = False,
        ledger_open: bool = False,
    ) -> None:
        sw, sh = screen.get_size()
        if sw < 640 or sh < 360:
            return

        # 0. Fiery Overdrive Screen Edge Vignette
        if getattr(player, "is_in_overdrive", False):
            self._render_overdrive_vignette(screen, sw, sh, getattr(player, "overdrive_timer", 0.0))

        # 1. Top-Left: Clean Modern Status & Objective Panel
        self._render_status_and_objective_panel(screen, world, player, items, story, weather_name)

        # 2. Top-Center: Directional Relic/Shrine Compass & Boss Health Bar
        self._render_compass_and_boss_bar(screen, sw, world, player, items, enemies)

        # 3. Top-Right: Chapter Title & Crisp 2x Minimap Radar
        if show_minimap and not seed_modal_open and not codex_open and not tactical_map_open and not ledger_open:
            self._render_minimap_panel(screen, sw, world, player, items)

        # 4. Bottom-Center: Story Dialogue Box (or Minimalist Control Hint Bar)
        if story.active_dialogue is not None and not story.show_intro_card:
            self._render_dialogue_box(screen, sw, sh, story)
        elif not story.show_intro_card:
            self._render_bottom_controls_bar(screen, sw, sh)

        # 5. Floating Event Notification Toast
        if banner_timer > 0.0 and banner_text and not story.show_intro_card:
            self._render_banner_toast(screen, sw, banner_text)

        # 6. Interactive Modals ([C] Codex, [J] Sefer Günlüğü, [TAB] Seed, Victory Modal, Intro Card)
        if story.show_intro_card:
            self._render_story_intro_card(screen, sw, sh, world)
        elif getattr(story, "show_victory_modal", False):
            self._render_victory_modal_hd(screen, sw, sh, world, player, story)
        elif is_paused:
            self._render_pause_modal_hd(screen, sw, sh)
        elif tactical_map_open:
            self._render_tactical_map_hd(screen, sw, sh, world, player, items, enemies, story)
        elif ledger_open:
            self._render_ledger_modal_hd(screen, sw, sh, world, player, story)
        elif codex_open:
            self._render_codex_modal_hd(screen, sw, sh, world, player, story)
        elif seed_modal_open:
            self._render_seed_modal_hd(screen, sw, sh, world, seed_input_buffer)

    def _render_status_and_objective_panel(
        self,
        screen: pygame.Surface,
        world: WorldData,
        player: Player,
        items: List[CollectibleItem],
        story: StoryManager,
        weather_name: str = "ALTIN İKİNDİ",
    ) -> None:
        px, py = 16, 16
        pw, ph = 390, 108
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((*DEEP_VOID, 225))
        pygame.draw.rect(panel, HARVEST_GOLD, (0, 0, pw, ph), 2, border_radius=6)
        pygame.draw.rect(panel, WITHERED_BARK, (3, 3, pw - 6, ph - 6), 1, border_radius=4)

        # Portrait of Autumn Keeper Ekin (scaled 2x -> 32x32)
        p_icon = pygame.transform.scale(self.assets.player_frames_right[0], (32, 32))
        pygame.draw.rect(panel, PLUM_SHADOW, (12, 12, 36, 36), border_radius=4)
        pygame.draw.rect(panel, BURNT_AMBER, (12, 12, 36, 36), 1, border_radius=4)
        panel.blit(p_icon, (14, 14))

        # Lantern Warmth Bar
        warm_pct = max(0.0, min(1.0, player.warmth / max(1.0, player.max_warmth)))
        if getattr(player, "is_in_overdrive", False):
            warm_title = f"DEVRİM OVERDRIVE: {player.overdrive_timer:.1f}s!"
            warm_col = PALE_SUNBEAM
        elif getattr(player, "overdrive_ready", False):
            warm_title = f"FENER %{int(round(warm_pct * 100))} • [Z] DEVRİM HARLA!"
            warm_col = HARVEST_GOLD
        else:
            warm_title = f"DEVRİM FENERİ ISISI: %{int(round(warm_pct * 100))}"
            warm_col = SUNLIT_BIRCH
        lbl_warm = self.f_small.render(warm_title, True, warm_col)
        panel.blit(lbl_warm, (56, 10))

        bar_x, bar_y, bar_w, bar_h = 56, 30, 195, 14
        pygame.draw.rect(panel, PLUM_SHADOW, (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = int(round(bar_w * warm_pct))
        if fill_w > 0:
            bar_col = HARVEST_GOLD if warm_pct > 0.35 else CRIMSON_DECAY
            pygame.draw.rect(panel, bar_col, (bar_x, bar_y, fill_w, bar_h), border_radius=4)
            pygame.draw.rect(
                panel, SUNLIT_BIRCH, (bar_x + 2, bar_y + 2, max(2, fill_w - 4), 4), border_radius=2
            )
        pygame.draw.rect(panel, BURNT_AMBER, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)

        # Solar Bolt Pips ([F]) on the right side of the top row
        lbl_bolt = self.f_small.render("KÖZ [F]:", True, AUTUMN_MIST)
        panel.blit(lbl_bolt, (262, 10))
        for i in range(player.max_solar_bolts):
            bx = 262 + i * 22
            by = 30
            pygame.draw.rect(panel, PLUM_SHADOW, (bx, by, 18, 14), border_radius=3)
            if i < player.solar_bolts:
                pygame.draw.rect(panel, PALE_SUNBEAM, (bx + 2, by + 2, 14, 10), border_radius=2)
            pygame.draw.rect(panel, HARVEST_GOLD, (bx, by, 18, 14), 1, border_radius=3)

        # Relic Crystals Progress & Active Boons Row
        relic_icon = pygame.transform.scale(self.assets.entity_surfaces[("relic", 0)], (22, 22))
        panel.blit(relic_icon, (14, 54))
        awakened = player.relics_collected >= world.total_relics
        relic_txt = (
            "TÜM ANILAR TOPLANDI! TAPINAĞA GİT [E]"
            if awakened
            else f"SONBAHAR ANISI: {player.relics_collected} / {world.total_relics}   |   KUTSAMA [C]: {len(player.active_boons)}/5"
        )
        lbl_relic = self.f_body_bold.render(
            relic_txt, True, PALE_SUNBEAM if awakened else HARVEST_GOLD
        )
        panel.blit(lbl_relic, (42, 55))

        # Clear Objective Line & Weather Status at the bottom of the card
        obj_str = story.get_current_objective_text(player.relics_collected, world.total_relics)
        lbl_obj = self.f_tiny.render(f"{obj_str}  •  [HAVA: {weather_name}]", True, AUTUMN_MIST)
        panel.blit(lbl_obj, (14, 83))

        screen.blit(panel, (px, py))

    def _render_compass_and_boss_bar(
        self,
        screen: pygame.Surface,
        sw: int,
        world: WorldData,
        player: Player,
        items: List[CollectibleItem],
        enemies: List[EnemyAgent],
    ) -> None:
        # Guidance compass pill at top-center
        uncollected = [it for it in items if not it.collected and it.kind == "relic"]
        if not uncollected:
            tx, ty = world.shrine_tile[0] + 0.5, world.shrine_tile[1] + 0.5
            target_label = ">> KADİM TAPINAK [E] <<"
            col = PALE_SUNBEAM
        else:
            nearest = min(
                uncollected, key=lambda it: (it.x - player.x) ** 2 + (it.y - player.y) ** 2
            )
            tx, ty = nearest.x, nearest.y
            if player.relics_collected == 0:
                target_label = ">> BU OKU TAKİP ET: 1. KRİSTAL <<"
            else:
                target_label = f"EN YAKIN KRİSTAL ({player.relics_collected}/{world.total_relics})"
            col = HARVEST_GOLD

        dx = tx - player.x
        dy = ty - player.y
        dist = int(round(math.hypot(dx, dy)))
        angle = math.atan2(dy, dx)

        cw, ch = 280, 44
        cx_box = (sw - cw) // 2
        cy_box = 16
        pill = pygame.Surface((cw, ch), pygame.SRCALPHA)
        pill.fill((*DEEP_VOID, 220))
        pygame.draw.rect(pill, BURNT_AMBER, (0, 0, cw, ch), 2, border_radius=20)

        # Draw compass circle & arrow inside pill
        ccx, ccy = 24, 22
        pygame.draw.circle(pill, PLUM_SHADOW, (ccx, ccy), 15)
        pygame.draw.circle(pill, col, (ccx, ccy), 15, 2)
        ax = int(round(ccx + math.cos(angle) * 11))
        ay = int(round(ccy + math.sin(angle) * 11))
        pygame.draw.line(pill, PALE_SUNBEAM, (ccx, ccy), (ax, ay), 3)
        pygame.draw.circle(pill, SUNLIT_BIRCH, (ax, ay), 3)

        t1 = self.f_small.render(target_label, True, col)
        t2 = self.f_tiny.render(f"Mesafe: {dist} adim (Ok yonunde yuru)", True, AUTUMN_MIST)
        pill.blit(t1, (48, 6))
        pill.blit(t2, (48, 23))
        screen.blit(pill, (cx_box, cy_box))

        # Boss Health Bar if Elder Stag Warden is nearby
        for en in enemies:
            if en.alive and en.kind == "warden":
                if math.hypot(en.x - player.x, en.y - player.y) <= 11.0:
                    bw, bh = 380, 44
                    bx = (sw - bw) // 2
                    by = 68
                    bpanel = pygame.Surface((bw, bh), pygame.SRCALPHA)
                    bpanel.fill((*DEEP_VOID, 235))
                    border_color = SUNLIT_BIRCH if en.is_enraged else CRIMSON_DECAY
                    pygame.draw.rect(bpanel, border_color, (0, 0, bw, bh), 2, border_radius=6)
                    
                    if en.is_enraged:
                        boss_title = "[!] KADİM ÖFKE: KADİM GEYİK (ENRAGED WARDEN)"
                        title_col = PALE_SUNBEAM
                    else:
                        boss_title = "[!] ORMAN MUHAFIZI: KADİM GEYİK (ELDER STAG WARDEN)"
                        title_col = SUNLIT_BIRCH
                        
                    b_lbl = self.f_small.render(boss_title, True, title_col)
                    bpanel.blit(b_lbl, ((bw - b_lbl.get_width()) // 2, 5))
                    pygame.draw.rect(bpanel, PLUM_SHADOW, (16, 26, bw - 32, 11), border_radius=4)
                    fill = max(0, int(round((bw - 32) * (en.hp / max(1, en.max_hp)))))
                    if fill > 0:
                        bar_col = SUNLIT_BIRCH if en.is_enraged else HARVEST_GOLD
                        pygame.draw.rect(bpanel, bar_col, (16, 26, fill, 11), border_radius=4)
                    pygame.draw.rect(bpanel, BURNT_AMBER, (16, 26, bw - 32, 11), 1, border_radius=4)
                    screen.blit(bpanel, (bx, by))
                break

    def _render_minimap_panel(
        self,
        screen: pygame.Surface,
        sw: int,
        world: WorldData,
        player: Player,
        items: List[CollectibleItem],
    ) -> None:
        mm_scale = 3
        mw = world.width * mm_scale
        mh = world.height * mm_scale
        pw = mw + 24
        ph = mh + 56
        px = sw - pw - 16
        py = 16

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((*DEEP_VOID, 225))
        pygame.draw.rect(panel, HARVEST_GOLD, (0, 0, pw, ph), 2, border_radius=6)

        ch_idx = min(3, max(1, world.depth_level))
        ch_title = f"BÖLÜM {ch_idx}: ODTÜ KORUSU"
        lbl_ch = self.f_small.render(ch_title, True, SUNLIT_BIRCH)
        lbl_seed = self.f_tiny.render(f"Tohum: {world.seed_code}", True, AUTUMN_MIST)
        panel.blit(lbl_ch, (12, 6))
        panel.blit(lbl_seed, (12, 24))

        base_mm = self._get_minimap(world).copy()
        for it in items:
            if not it.collected and it.kind == "relic":
                base_mm.set_at((int(it.x), int(it.y)), HARVEST_GOLD)
        sx, sy = world.shrine_tile
        base_mm.set_at((sx, sy), PALE_SUNBEAM)
        pl_x = max(0, min(world.width - 1, int(player.x)))
        pl_y = max(0, min(world.height - 1, int(player.y)))
        base_mm.set_at((pl_x, pl_y), PALE_SUNBEAM)

        scaled_mm = pygame.transform.scale(base_mm, (mw, mh))
        # Highlight player & relics clearly on scaled minimap
        for it in items:
            if not it.collected and it.kind == "relic":
                pygame.draw.circle(
                    scaled_mm, HARVEST_GOLD, (int(it.x * mm_scale), int(it.y * mm_scale)), 3
                )
        pygame.draw.circle(scaled_mm, PALE_SUNBEAM, (sx * mm_scale, sy * mm_scale), 4, 1)
        pygame.draw.circle(scaled_mm, SUNLIT_BIRCH, (pl_x * mm_scale, pl_y * mm_scale), 3)

        panel.blit(scaled_mm, (12, 44))
        pygame.draw.rect(panel, WITHERED_BARK, (12, 44, mw, mh), 1)
        screen.blit(panel, (px, py))

    def _render_dialogue_box(
        self, screen: pygame.Surface, sw: int, sh: int, story: StoryManager
    ) -> None:
        dlg = story.active_dialogue
        if dlg is None:
            return

        dw = min(860, sw - 60)
        dh = 118
        dx = (sw - dw) // 2
        dy = sh - dh - 18

        box = pygame.Surface((dw, dh), pygame.SRCALPHA)
        box.fill((*DEEP_VOID, 238))
        border_col = PALE_SUNBEAM if dlg.accent_type == "birch" else HARVEST_GOLD
        pygame.draw.rect(box, border_col, (0, 0, dw, dh), 2, border_radius=8)
        pygame.draw.rect(box, WITHERED_BARK, (4, 4, dw - 8, dh - 8), 1, border_radius=6)

        # Choose speaker pixel-art portrait
        avatar_k = getattr(dlg, "avatar_key", "player")
        if avatar_k == "bilim_agaci" or "BİLİM AĞACI" in dlg.speaker:
            raw_icon = self.assets.bilim_agaci_surf
        elif avatar_k == "relic" or "HATIRA" in dlg.speaker or "ANISI" in dlg.speaker:
            raw_icon = self.assets.entity_surfaces[("relic", 0)]
        elif avatar_k == "campfire" or "KAMP" in dlg.speaker:
            raw_icon = self.assets.campfire_frames[0]
        elif avatar_k == "kitabe" or "KİTABE" in dlg.speaker or "KEMAL" in dlg.speaker:
            raw_icon = self.assets.kitabe_surf
        elif avatar_k == "warden" or "GEYİK" in dlg.speaker:
            raw_icon = self.assets.entity_surfaces[("warden", 0)]
        else:
            raw_icon = self.assets.player_frames_right[0]

        portrait = pygame.transform.scale(raw_icon, (64, 64))
        pygame.draw.rect(box, PLUM_SHADOW, (18, 26, 72, 72), border_radius=6)
        pygame.draw.rect(box, border_col, (18, 26, 72, 72), 1, border_radius=6)
        box.blit(portrait, (22, 30))

        # Speaker badge & Title
        lbl_spk = self.f_tiny.render(dlg.speaker, True, AUTUMN_MIST)
        lbl_ttl = self.f_subtitle.render(dlg.title, True, SUNLIT_BIRCH)
        box.blit(lbl_spk, (106, 14))
        box.blit(lbl_ttl, (106, 32))

        # Typewriter revealed narrative lines
        visible_chars = getattr(dlg, "chars_revealed", len(dlg.text))
        visible_text = dlg.text[:visible_chars]
        wrapped = _wrap_text(visible_text, self.f_body, dw - 130)
        for i, line in enumerate(wrapped[:2]):
            l_surf = self.f_body.render(line, True, PALE_SUNBEAM)
            box.blit(l_surf, (106, 58 + i * 21))

        hint = self.f_tiny.render("[C] Günlük & Kutsamalar   |   [F5] ODTÜ Bölgesi Değiştir", True, HARVEST_GOLD)
        box.blit(hint, (dw - hint.get_width() - 16, 14))

        screen.blit(box, (dx, dy))

    def _render_bottom_controls_bar(self, screen: pygame.Surface, sw: int, sh: int) -> None:
        bw = min(960, sw - 40)
        bh = 32
        bx = (sw - bw) // 2
        by = sh - bh - 10
        bar = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bar.fill((*DEEP_VOID, 220))
        pygame.draw.rect(bar, BURNT_AMBER, (0, 0, bw, bh), 1, border_radius=6)

        txt = (
            "[WASD] Yürü  •  [SPACE] Kılıç & Parri  •  [F] Köz  •  [Z] DEVRİM  •  "
            "[X] KILIÇ DANSI  •  [E] Ayin/Közle  •  [G] SİMYA  •  [J] Sefer Günlüğü  •  [N] Harita  •  [P] Duraklat"
        )
        lbl = self.f_tiny.render(txt, True, SUNLIT_BIRCH)
        bar.blit(lbl, ((bw - lbl.get_width()) // 2, 8))
        screen.blit(bar, (bx, by))

    def _render_overdrive_vignette(self, screen: pygame.Surface, sw: int, sh: int, timer: float) -> None:
        """Renders an intense, pulsing golden-amber chromatic border when Devrim Overdrive is active."""
        pulse = 0.55 + 0.45 * math.sin(timer * 9.0)
        thick = int(6 + 6 * pulse)
        border_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        col = (245, 214, 123, int(120 * pulse))
        pygame.draw.rect(border_surf, col, (0, 0, sw, thick))
        pygame.draw.rect(border_surf, col, (0, sh - thick, sw, thick))
        pygame.draw.rect(border_surf, col, (0, 0, thick, sh))
        pygame.draw.rect(border_surf, col, (sw - thick, 0, thick, sh))
        pygame.draw.rect(
            border_surf,
            (255, 235, 175, int(180 * pulse)),
            (thick // 2, thick // 2, sw - thick, sh - thick),
            2,
        )
        screen.blit(border_surf, (0, 0))

    def _render_tactical_map_hd(
        self,
        screen: pygame.Surface,
        sw: int,
        sh: int,
        world: WorldData,
        player: Player,
        items: List[CollectibleItem],
        enemies: List[EnemyAgent],
        story: StoryManager,
    ) -> None:
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((*DEEP_VOID, 228))
        screen.blit(dim, (0, 0))

        tile_px = 13
        mw = world.width * tile_px
        mh = world.height * tile_px
        pw = mw + 60
        ph = mh + 104
        px = (sw - pw) // 2
        py = (sh - ph) // 2

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((*PLUM_SHADOW, 250))
        pygame.draw.rect(panel, HARVEST_GOLD, (0, 0, pw, ph), 2, border_radius=10)
        pygame.draw.rect(panel, BURNT_AMBER, (4, 4, pw - 8, ph - 8), 1, border_radius=8)

        t_str = f"ODTÜ BOZKIR TAKTİK HARİTASI & TOPOĞRAFYA — SEED: {world.seed_input}"
        t_lbl = self.f_title.render(t_str, True, PALE_SUNBEAM)
        panel.blit(t_lbl, ((pw - t_lbl.get_width()) // 2, 14))

        sub_str = f"Bölüm {story.chapter}: {story.chapter_title}   |   Boyut: 56x42 Koro   |   Derinlik: {world.depth_level}"
        s_lbl = self.f_small.render(sub_str, True, SUNLIT_BIRCH)
        panel.blit(s_lbl, ((pw - s_lbl.get_width()) // 2, 44))

        map_surf = pygame.Surface((mw, mh))
        map_surf.fill(DEEP_VOID)

        for ty in range(world.height):
            for tx in range(world.width):
                is_wall = world.walkable_grid[ty, tx] != 0
                b = int(world.biome_grid[ty, tx])
                if is_wall:
                    col = WITHERED_BARK if b != 1 else PLUM_SHADOW
                else:
                    if b == 0:
                        col = BURNT_AMBER
                    elif b == 1:
                        col = CRIMSON_DECAY
                    elif b == 2:
                        col = OCHRE_CLAY
                    else:
                        col = RUST_TERRACOTTA
                pygame.draw.rect(map_surf, col, (tx * tile_px, ty * tile_px, tile_px, tile_px))

        for st in world.structures:
            stx = int((st.tile_x + 0.5) * tile_px)
            sty = int((st.tile_y + 0.5) * tile_px)
            if st.structure_type == "campfire":
                pygame.draw.circle(map_surf, BURNT_AMBER, (stx, sty), 7)
                pygame.draw.circle(map_surf, PALE_SUNBEAM, (stx, sty), 4)
            elif st.structure_type == "bilim_agaci":
                pygame.draw.circle(map_surf, SUNLIT_BIRCH, (stx, sty), 8)
                pygame.draw.circle(map_surf, HARVEST_GOLD, (stx, sty), 4)
            elif st.structure_type == "odtu_kitabe":
                pygame.draw.rect(map_surf, AUTUMN_MIST, (stx - 4, sty - 5, 8, 10))

        shx, shy = world.shrine_tile
        ssx = int((shx + 0.5) * tile_px)
        ssy = int((shy + 0.5) * tile_px)
        pygame.draw.circle(map_surf, PALE_SUNBEAM, (ssx, ssy), 9)
        pygame.draw.circle(map_surf, HARVEST_GOLD, (ssx, ssy), 6)
        pygame.draw.circle(map_surf, CRIMSON_DECAY, (ssx, ssy), 3)

        for it in items:
            if not it.collected and it.kind == "relic":
                rx = int(it.x * tile_px)
                ry = int(it.y * tile_px)
                pygame.draw.circle(map_surf, PALE_SUNBEAM, (rx, ry), 5)
                pygame.draw.circle(map_surf, HARVEST_GOLD, (rx, ry), 3)

        plx = int(player.x * tile_px)
        ply = int(player.y * tile_px)
        pygame.draw.circle(map_surf, PALE_SUNBEAM, (plx, ply), 8, 2)
        pygame.draw.circle(map_surf, (255, 255, 255), (plx, ply), 4)
        adx = int(plx + player.facing_x * 8)
        ady = int(ply + player.facing_y * 8)
        pygame.draw.line(map_surf, (255, 255, 255), (plx, ply), (adx, ady), 2)

        pygame.draw.rect(map_surf, HARVEST_GOLD, (0, 0, mw, mh), 2)
        panel.blit(map_surf, (30, 66))

        leg_str = (
            "[N] / [ESC] Kapat  •  ▲ Ekin (Oyuncu)  •  ★ Kadim Tapınak  •  "
            "🔥 Kamp Ateşi [G: Simya]  •  ✦ Bilim Ağacı  •  📜 Kitabe  •  ◆ Sonbahar Anısı"
        )
        leg_lbl = self.f_small.render(leg_str, True, PALE_SUNBEAM)
        panel.blit(leg_lbl, ((pw - leg_lbl.get_width()) // 2, ph - 28))

        screen.blit(panel, (px, py))

    def _render_pause_modal_hd(self, screen: pygame.Surface, sw: int, sh: int) -> None:
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((*DEEP_VOID, 185))
        screen.blit(dim, (0, 0))

        pw, ph = 480, 220
        px = (sw - pw) // 2
        py = (sh - ph) // 2
        pnl = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pnl.fill((*PLUM_SHADOW, 245))
        pygame.draw.rect(pnl, HARVEST_GOLD, (0, 0, pw, ph), 2, border_radius=8)
        pygame.draw.rect(pnl, SUNLIT_BIRCH, (4, 4, pw - 8, ph - 8), 1, border_radius=6)

        t_lbl = self.f_title.render("OYUN DURAKLATILDI", True, PALE_SUNBEAM)
        pnl.blit(t_lbl, ((pw - t_lbl.get_width()) // 2, 20))

        sub_lbl = self.f_subtitle.render("Bozkırın Rüzgarı Dinginleşti...", True, HARVEST_GOLD)
        pnl.blit(sub_lbl, ((pw - sub_lbl.get_width()) // 2, 60))

        hints = [
            "[P] veya [SPACE] : Oyuna Devam Et",
            "[U] : Sesi Aç / Kapat (Mute Toggle)",
            "[H] : Başlangıç & Oynanış Kılavuzu",
            "[C] : Toplanan ODTÜ Kutsamaları ve Hikaye",
            "[ESC] : Oyundan Çık",
        ]
        curr_y = 96
        for h in hints:
            lbl = self.f_small.render(h, True, SUNLIT_BIRCH)
            pnl.blit(lbl, ((pw - lbl.get_width()) // 2, curr_y))
            curr_y += 22

        screen.blit(pnl, (px, py))

    def _render_banner_toast(self, screen: pygame.Surface, sw: int, text: str) -> None:
        lbl = self.f_body_bold.render(text, True, PALE_SUNBEAM)
        tw = lbl.get_width() + 36
        th = 34
        tx = (sw - tw) // 2
        ty = 72
        toast = pygame.Surface((tw, th), pygame.SRCALPHA)
        toast.fill((*DEEP_VOID, 230))
        pygame.draw.rect(toast, HARVEST_GOLD, (0, 0, tw, th), 2, border_radius=6)
        toast.blit(lbl, (18, 7))
        screen.blit(toast, (tx, ty))

    def _render_story_intro_card(
        self, screen: pygame.Surface, sw: int, sh: int, world: WorldData
    ) -> None:
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((*DEEP_VOID, 205))
        screen.blit(dim, (0, 0))

        cw = min(1040, sw - 32)
        ch = min(660, sh - 32)
        cx = (sw - cw) // 2
        cy = (sh - ch) // 2

        card = pygame.Surface((cw, ch), pygame.SRCALPHA)
        card.fill((*PLUM_SHADOW, 252))
        pygame.draw.rect(card, HARVEST_GOLD, (0, 0, cw, ch), 3, border_radius=12)
        pygame.draw.rect(card, SUNLIT_BIRCH, (6, 6, cw - 12, ch - 12), 1, border_radius=9)

        # Header Title with pixel sprites on each side
        t_main = self.f_title.render("ODTÜ : SONBAHARIN SON IŞIĞI — BAŞLANGIÇ KILAVUZU", True, PALE_SUNBEAM)
        tw = t_main.get_width()
        tx = (cw - tw) // 2
        card.blit(t_main, (tx, 14))

        s_bilim = pygame.transform.scale(self.assets.bilim_agaci_surf, (36, 36))
        s_shrine = pygame.transform.scale(self.assets.shrine_awake_surf, (36, 36))
        card.blit(s_bilim, (max(16, tx - 46), 11))
        card.blit(s_shrine, (min(cw - 52, tx + tw + 10), 11))

        # Golden Summary Pill (Crystal clear ELI5 banner)
        pill_w, pill_h = min(980, cw - 40), 32
        pill_x = (cw - pill_w) // 2
        pill_y = 52
        pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
        pill.fill((*DEEP_VOID, 230))
        pygame.draw.rect(pill, HARVEST_GOLD, (0, 0, pill_w, pill_h), 2, border_radius=8)
        s_txt = self.f_body_bold.render(
            ">> 10 SANİYEDE ÖZET: Ekranın tepesindeki ALTIN OKU TAKİP ET, 5 sarı kristali topla, tapınaktan [E] ile geç! <<",
            True,
            PALE_SUNBEAM,
        )
        pill.blit(s_txt, ((pill_w - s_txt.get_width()) // 2, 6))
        card.blit(pill, (pill_x, pill_y))

        # 3 Structured Columns
        col_margin = 16
        col_gap = 14
        col_w = (cw - 2 * col_margin - 2 * col_gap) // 3
        col_h = ch - 195
        col_y = 94

        columns_data = [
            (
                "[1] HEDEFİN NEDİR? (NE YAPACAKSIN)",
                HARVEST_GOLD,
                [
                    ("* Tepedeki Oku Takip Et!", "Ekranın tam tepesinde dönen altın bir pusula oku var. Nereye dönerse o yöne yürü; seni hedefe adım adım götürür!", SUNLIT_BIRCH),
                    ("* 5 Altın Kristali Topla!", "Ormana saçılmış 5 parlayan kristali topla. Her kristal fenerine kalıcı bir süper güç (ODTÜ Kutsaması) verir.", HARVEST_GOLD),
                    ("* Kadim Tapınaktan Geç [E]!", "5 kristal bitince pusula Tapınağı gösterecek. Tapınağın yanına varıp [E] tuşuna bas ve seviyeyi bitir!", PALE_SUNBEAM),
                    ("* Boss: Kadim Geyik Warden!", "Koru derinliğindeki ulu muhafızın mor mermilerini kılıcınla yansıtarak hakkından gel!", CRIMSON_DECAY),
                ],
            ),
            (
                "[2] KONTROLLER (HANGİ TUŞLAR)",
                SUNLIT_BIRCH,
                [
                    ("* [W, A, S, D] — Yürü", "Ormanda 8 yöne serbestçe hareket et (Ok tuşları da çalışır).", AUTUMN_MIST),
                    ("* [Sol Tık / SPACE] — Kılıç", "Düşmanları ve çalıları kes! Vurduğun her darbe sana Köz Mermisi doldurur.", SUNLIT_BIRCH),
                    ("* DEFLECT! — Mermi Yansıt", "Düşmanın attığı mor mermilere kılıç vurursan, mermi 2 kat hasarla düşmana geri uçar!", PALE_SUNBEAM),
                    ("* [Sağ Tık / F] — Köz Mermisi", "Doldurduğun köz mermisini uzaktan düşmana fırlat.", HARVEST_GOLD),
                    ("* [SHIFT] Dash  •  [Q] Nova", "Shift ile hızlıca sıyrıl, Q ile 360 derece şok dalgası patlat.", AUTUMN_MIST),
                ],
            ),
            (
                "[3] ÖLMEME REHBERİ (HAYATTA KALMA)",
                CRIMSON_DECAY,
                [
                    ("* Fener Isısı = Canındır!", "Sol üstteki sarı çubuk senin canındır. Soğukta durdukça azalır; ısı bitmeden ısın!", CRIMSON_DECAY),
                    ("* ODTÜ Bilim Ağacı'na Koş!", "Üşüdüğünde haritadaki dev metal Bilim Ağacı Anıtı'na git. Yanında durunca fenerin hemen %100 dolar!", PALE_SUNBEAM),
                    ("* Kamp Ateşlerinde Isın!", "Ormandaki yanan kamp ateşlerinin yanında durarak da donmaktan hemen kurtulursun.", HARVEST_GOLD),
                    ("* Palamut & Balkabağı Kes!", "Balkabaklarını kılıçla parçala; çıkan altın meşe palamutlarını alıp can tazele.", SUNLIT_BIRCH),
                    ("* [M] Harita  •  [C] Kutsamalar", "Bu kılavuzu istediğin an [H] tuşuna basarak tekrar açabilirsin.", AUTUMN_MIST),
                ],
            ),
        ]

        for i, (col_title, badge_col, items) in enumerate(columns_data):
            bx = col_margin + i * (col_w + col_gap)
            box_surf = pygame.Surface((col_w, col_h), pygame.SRCALPHA)
            box_surf.fill((*DEEP_VOID, 235))
            pygame.draw.rect(box_surf, badge_col, (0, 0, col_w, col_h), 2, border_radius=8)
            pygame.draw.rect(box_surf, WITHERED_BARK, (3, 3, col_w - 6, col_h - 6), 1, border_radius=6)

            # Column Badge Header
            hdr_rect = pygame.Rect(8, 8, col_w - 16, 28)
            pygame.draw.rect(box_surf, PLUM_SHADOW, hdr_rect, border_radius=6)
            pygame.draw.rect(box_surf, badge_col, hdr_rect, 1, border_radius=6)
            lbl_hdr = self.f_small.render(col_title, True, PALE_SUNBEAM)
            box_surf.blit(lbl_hdr, ((col_w - lbl_hdr.get_width()) // 2, 13))

            # Render item list
            item_y = 44
            for item_title, item_desc, title_col in items:
                lbl_it = self.f_body_bold.render(item_title, True, title_col)
                box_surf.blit(lbl_it, (12, item_y))
                item_y += 20
                wrapped = _wrap_text(item_desc, self.f_card_desc, col_w - 24)
                for line in wrapped:
                    l_s = self.f_card_desc.render(line, True, AUTUMN_MIST)
                    box_surf.blit(l_s, (14, item_y))
                    item_y += 18
                item_y += 12

            card.blit(box_surf, (bx, col_y))

        # Bottom Start Button
        btn_w, btn_h = min(560, cw - 60), 46
        btn_x = (cw - btn_w) // 2
        btn_y = ch - 72
        pygame.draw.rect(card, CRIMSON_DECAY, (btn_x, btn_y, btn_w, btn_h), border_radius=10)
        pygame.draw.rect(card, PALE_SUNBEAM, (btn_x, btn_y, btn_w, btn_h), 2, border_radius=10)
        btn_lbl = self.f_subtitle.render(
            "[ENTER / SPACE / TIKLA] HER ŞEYİ ANLADIM, OYUNA BAŞLA!", True, PALE_SUNBEAM
        )
        card.blit(btn_lbl, ((cw - btn_lbl.get_width()) // 2, btn_y + 11))

        sub_hint = self.f_tiny.render(
            "[i] İpucu: Bu kılavuzu oyun içinde istediğin an [H] tuşuna basarak tekrar açabilirsin.",
            True,
            AUTUMN_MIST,
        )
        card.blit(sub_hint, ((cw - sub_hint.get_width()) // 2, btn_y + btn_h + 4))

        screen.blit(card, (cx, cy))

    def _render_codex_modal_hd(
        self,
        screen: pygame.Surface,
        sw: int,
        sh: int,
        world: WorldData,
        player: Player,
        story: StoryManager,
    ) -> None:
        cw, ch = 680, 410
        cx = (sw - cw) // 2
        cy = (sh - ch) // 2
        card = pygame.Surface((cw, ch), pygame.SRCALPHA)
        card.fill((*DEEP_VOID, 245))
        pygame.draw.rect(card, HARVEST_GOLD, (0, 0, cw, ch), 2, border_radius=10)

        hdr = self.f_subtitle.render(
            "📜 ODTÜ SONBAHAR GÜNLÜĞÜ & KUTSAMA KODEKSİ [C]", True, SUNLIT_BIRCH
        )
        card.blit(hdr, ((cw - hdr.get_width()) // 2, 16))

        ch_key = min(3, max(1, world.depth_level))
        ch_title, ch_desc, _ = CHAPTER_INFO[ch_key]
        lbl_ch = self.f_body_bold.render(ch_title, True, HARVEST_GOLD)
        card.blit(lbl_ch, (28, 50))
        for i, line in enumerate(_wrap_text(ch_desc, self.f_body, cw - 56)[:2]):
            card.blit(self.f_body.render(line, True, AUTUMN_MIST), (28, 72 + i * 20))

        boon_descriptions_tr = [
            ("DEVRIM_TORCH", "🔥 Devrim Meşalesi", "Saniyede +2.5 Fener Isısı yeniler ve +1 Köz Mermisi ekler."),
            ("BILIM_SPARK", "⚡ Bilim Ağacı Kıvılcımı", "Kılıç ve Köz atışlarına +1 Hasar ekler, yaprak fırtınasını büyütür."),
            ("YALINCAK_GALE", "🍃 Yalıncak Rüzgarı", "Hareket hızını +%18 artırır ve Dash bekleme süresini kısaltır."),
            ("EYMIR_REFLECT", "🛡️ Eymir Ayna Kalkanı", "Düşman kürelerini yansıtmak (DEFLECT) +6 Fener Isısı iyileştirir."),
            ("HARVEST_CROWN", "👑 KODTÜ Hasat Tacı", "Köz Atışı [F] tek mermi yerine 3'lü yelpaze yaylım ateşi yapar!"),
        ]

        for idx, (b_id, b_title, b_desc) in enumerate(boon_descriptions_tr):
            by = 126 + idx * 44
            unlocked = player.has_boon(b_id)
            pygame.draw.rect(
                card,
                PLUM_SHADOW if unlocked else (*WITHERED_BARK, 120),
                (28, by, cw - 56, 38),
                border_radius=6,
            )
            pygame.draw.rect(
                card,
                PALE_SUNBEAM if unlocked else WITHERED_BARK,
                (28, by, cw - 56, 38),
                1,
                border_radius=6,
            )
            status = "[AKTİF]" if unlocked else "[KİLİTLİ - Anı Topla veya B'ye Bas]"
            t_s = self.f_body_bold.render(
                f"{b_title}   {status}", True, PALE_SUNBEAM if unlocked else AUTUMN_MIST
            )
            d_s = self.f_tiny.render(b_desc, True, SUNLIT_BIRCH if unlocked else AUTUMN_MIST)
            card.blit(t_s, (40, by + 3))
            card.blit(d_s, (40, by + 21))

        footer = self.f_small.render(
            f"İnfaz: {player.enemies_defeated}  |  Yansıtılan Küre: {player.orbs_deflected}  |  "
            f"Palamut: {player.acorns_collected}  |  [B] Kutsama Aç  |  [C / ESC] Kapat",
            True,
            HARVEST_GOLD,
        )
        card.blit(footer, ((cw - footer.get_width()) // 2, ch - 34))
        screen.blit(card, (cx, cy))

    def _render_ledger_modal_hd(
        self,
        screen: pygame.Surface,
        sw: int,
        sh: int,
        world: WorldData,
        player: Player,
        story: StoryManager,
    ) -> None:
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((*DEEP_VOID, 215))
        screen.blit(dim, (0, 0))

        cw = min(940, sw - 40)
        ch = min(590, sh - 40)
        cx = (sw - cw) // 2
        cy = (sh - ch) // 2
        card = pygame.Surface((cw, ch), pygame.SRCALPHA)
        card.fill((*PLUM_SHADOW, 250))
        pygame.draw.rect(card, HARVEST_GOLD, (0, 0, cw, ch), 3, border_radius=12)
        pygame.draw.rect(card, SUNLIT_BIRCH, (5, 5, cw - 10, ch - 10), 1, border_radius=9)

        # Header Title with Bilim Ağacı icon
        t_main = self.f_title.render("📜 ODTÜ SEFER GÜNLÜĞÜ & BOZKIR KRONİĞİ [J]", True, PALE_SUNBEAM)
        tw = t_main.get_width()
        tx = (cw - tw) // 2
        card.blit(t_main, (tx, 16))

        s_bilim = pygame.transform.scale(self.assets.bilim_agaci_surf, (36, 36))
        card.blit(s_bilim, (max(16, tx - 46), 12))

        t_sub = self.f_subtitle.render(
            f"Tohum: {world.seed_input} (0x{world.seed_uint64:016X})  •  Bölüm: Koru {world.depth_level}  •  Alan: {world.width}x{world.height} Parsel",
            True,
            HARVEST_GOLD,
        )
        card.blit(t_sub, ((cw - t_sub.get_width()) // 2, 52))

        # Academic Honor Grade Banner
        grade_letter, grade_title, total_score = evaluate_academic_grade(
            relics_collected=player.relics_collected,
            acorns_collected=player.acorns_collected,
            enemies_defeated=player.enemies_defeated,
            orbs_deflected=player.orbs_deflected,
            active_boons_count=len(player.active_boons),
            depth_level=world.depth_level,
        )
        gw = cw - 56
        gh = 36
        gx = 28
        gy = 84
        gsurf = pygame.Surface((gw, gh), pygame.SRCALPHA)
        gsurf.fill((*DEEP_VOID, 230))
        pygame.draw.rect(gsurf, BURNT_AMBER, (0, 0, gw, gh), 2, border_radius=6)
        grade_col = PALE_SUNBEAM if grade_letter == "S" else (SUNLIT_BIRCH if grade_letter == "A" else HARVEST_GOLD)
        lbl_grade = self.f_body_bold.render(
            f"🎓 CANLI AKADEMİK BAŞARI DERECESİ: [{grade_letter}] {grade_title}  •  TOPLAM SKOR: {total_score:,} PUAN",
            True,
            grade_col,
        )
        gsurf.blit(lbl_grade, ((gw - lbl_grade.get_width()) // 2, 8))
        card.blit(gsurf, (gx, gy))

        # 4 Statistical Grid Boxes
        stat_y = 130
        stat_w = (cw - 56 - 36) // 4
        stat_h = 76
        stats = [
            ("ANIT & KİTABELER", f"{getattr(story, 'steles_read', 0)} Okundu • {'HALELİ' if getattr(player, 'bilim_ritual_timer', 0.0) > 0.0 else 'HAZIR'}", PALE_SUNBEAM),
            ("BOZKIR YOLDAŞI", f"{getattr(player, 'pets_count', 0)} Kez Sevildi • Sadık Dost", SUNLIT_BIRCH),
            ("KUSURSUZ PARRİ", f"{getattr(player, 'perfect_parries', 0)} Parri / {player.orbs_deflected} Deflect", HARVEST_GOLD),
            ("BOZKIR SAVAŞI", f"{player.enemies_defeated} İnfaz • {player.combo_hits_max} Max Kombo", RUST_TERRACOTTA),
        ]
        for i, (stitle, sval, scol) in enumerate(stats):
            sx = 28 + i * (stat_w + 12)
            sb = pygame.Surface((stat_w, stat_h), pygame.SRCALPHA)
            sb.fill((*DEEP_VOID, 230))
            pygame.draw.rect(sb, WITHERED_BARK, (0, 0, stat_w, stat_h), 1, border_radius=6)
            lbl_st = self.f_small.render(stitle, True, AUTUMN_MIST)
            lbl_sv = self.f_subtitle.render(sval, True, scol)
            sb.blit(lbl_st, ((stat_w - lbl_st.get_width()) // 2, 14))
            sb.blit(lbl_sv, ((stat_w - lbl_sv.get_width()) // 2, 42))
            card.blit(sb, (sx, stat_y))

        # Chapter Narrative & Lore Summary
        ch_key = min(3, max(1, world.depth_level))
        ch_title, ch_desc, ch_obj = CHAPTER_INFO[ch_key]
        lw = cw - 56
        lh = 100
        lx = 28
        ly = 216
        lsurf = pygame.Surface((lw, lh), pygame.SRCALPHA)
        lsurf.fill((*DEEP_VOID, 235))
        pygame.draw.rect(lsurf, HARVEST_GOLD, (0, 0, lw, lh), 1, border_radius=8)

        lbl_ct = self.f_body_bold.render(f"📖 AKTİF BÖLÜM: {ch_title}", True, SUNLIT_BIRCH)
        lbl_co = self.f_small.render(f"🎯 GÖREV: {ch_obj}", True, PALE_SUNBEAM)
        lsurf.blit(lbl_ct, (16, 10))
        lsurf.blit(lbl_co, (16, 30))
        for j, line in enumerate(_wrap_text(ch_desc, self.f_body, lw - 32)[:3]):
            lsurf.blit(self.f_body.render(line, True, AUTUMN_MIST), (16, 52 + j * 18))
        card.blit(lsurf, (lx, ly))

        # Curated Seed Roster Quick Reference
        rw = cw - 56
        rh = 146
        rx = 28
        ry = 326
        rsurf = pygame.Surface((rw, rh), pygame.SRCALPHA)
        rsurf.fill((*DEEP_VOID, 230))
        pygame.draw.rect(rsurf, WITHERED_BARK, (0, 0, rw, rh), 1, border_radius=8)

        ach_count = len(getattr(story, "unlocked_achievements", set()))
        lbl_rt = self.f_small.render(f"🗺️ KODTÜ RESMİ SEFER TOHUMLARI & 🏆 BOZKIR BAŞARIMLARI ({ach_count}/8 Açıldı)", True, HARVEST_GOLD)
        rsurf.blit(lbl_rt, (16, 8))

        curated = [
            ("ODTU-KORULUK-1956", "Kemal Kurdaş Ağaçlandırma Seferi • Dengeli Bozkır & Kitabeler"),
            ("EYMIR-GOLU-1962", "Eymir Şifa Pınarı Kıyısı • Geniş Göletler & Yoğun Söğütlük"),
            ("DEVRIM-BOZKIR-GIZEMI", "Bozkır Fırtınası & Yüksek Rüzgar • Zengin Palamut Rezervi"),
            ("BILIM-AGACI-ANITI", "Anıt Meydanı Odaklı Tohum • Hızlı Isı ve Ayin Merkezi"),
            ("YALINCAK-GALE-1956", "Hızlı Rüzgar & Çevik Kurt Sürüleri • Zorlu Hayatta Kalma"),
        ]
        for k, (c_seed, c_note) in enumerate(curated):
            sy = 30 + k * 22
            lbl_seed = self.f_tiny.render(f"• {c_seed:<22}", True, PALE_SUNBEAM)
            lbl_note = self.f_tiny.render(f"| {c_note}", True, AUTUMN_MIST)
            rsurf.blit(lbl_seed, (16, sy))
            rsurf.blit(lbl_note, (180, sy))
        card.blit(rsurf, (rx, ry))

        # Bottom Instructions Footer
        ft_txt = "[J] veya [ESC] : Günlüğü Kapat  •  [TAB] : Tohum Değiştir  •  [C] : Kutsama Kodeksi  •  [M] : Harita"
        lbl_ft = self.f_small.render(ft_txt, True, SUNLIT_BIRCH)
        card.blit(lbl_ft, ((cw - lbl_ft.get_width()) // 2, ch - 26))

        screen.blit(card, (cx, cy))

    def _render_seed_modal_hd(
        self,
        screen: pygame.Surface,
        sw: int,
        sh: int,
        world: WorldData,
        seed_input_buffer: str,
    ) -> None:
        cw, ch = 540, 230
        cx = (sw - cw) // 2
        cy = (sh - ch) // 2
        card = pygame.Surface((cw, ch), pygame.SRCALPHA)
        card.fill((*DEEP_VOID, 245))
        pygame.draw.rect(card, HARVEST_GOLD, (0, 0, cw, ch), 2, border_radius=10)

        t1 = self.f_subtitle.render(
            "🎲 PROSEDÜREL DÜNYA TOHUMU (SEED) SEÇİCİ", True, SUNLIT_BIRCH
        )
        t2 = self.f_body.render(
            f"Mevcut Tohum: {world.seed_input}  ({world.seed_code})", True, AUTUMN_MIST
        )
        card.blit(t1, ((cw - t1.get_width()) // 2, 20))
        card.blit(t2, ((cw - t2.get_width()) // 2, 54))

        pygame.draw.rect(card, PLUM_SHADOW, (40, 94, cw - 80, 44), border_radius=6)
        pygame.draw.rect(card, PALE_SUNBEAM, (40, 94, cw - 80, 44), 2, border_radius=6)
        cursor = "_" if (pygame.time.get_ticks() // 400) % 2 == 0 else " "
        inp = self.f_subtitle.render(f"> {seed_input_buffer}{cursor}", True, PALE_SUNBEAM)
        card.blit(inp, (56, 104))

        t3 = self.f_small.render(
            "[ENTER] Bu Tohumu Üret   |   [F3] Rastgele   |   [F5] ODTÜ Tohumu   |   [TAB] Kapat",
            True,
            HARVEST_GOLD,
        )
        card.blit(t3, ((cw - t3.get_width()) // 2, 166))
        screen.blit(card, (cx, cy))

    def _render_victory_modal_hd(
        self,
        screen: pygame.Surface,
        sw: int,
        sh: int,
        world: WorldData,
        player: Player,
        story: StoryManager,
    ) -> None:
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((*DEEP_VOID, 220))
        screen.blit(dim, (0, 0))

        cw = min(980, sw - 40)
        ch = min(610, sh - 40)
        cx = (sw - cw) // 2
        cy = (sh - ch) // 2
        card = pygame.Surface((cw, ch), pygame.SRCALPHA)
        card.fill((*PLUM_SHADOW, 252))
        pygame.draw.rect(card, HARVEST_GOLD, (0, 0, cw, ch), 3, border_radius=12)
        pygame.draw.rect(card, SUNLIT_BIRCH, (6, 6, cw - 12, ch - 12), 1, border_radius=9)

        # Header Title with Bilim Ağacı and Awakened Shrine sprites
        t_main = self.f_title.render("ODTÜ : DEVRİM VE EBEDİ DÖNGÜ TAMAMLANDI!", True, PALE_SUNBEAM)
        tw = t_main.get_width()
        tx = (cw - tw) // 2
        card.blit(t_main, (tx, 18))

        s_bilim = pygame.transform.scale(self.assets.bilim_agaci_surf, (40, 40))
        s_shrine = pygame.transform.scale(self.assets.shrine_awake_surf, (40, 40))
        card.blit(s_bilim, (max(16, tx - 52), 14))
        card.blit(s_shrine, (min(cw - 56, tx + tw + 12), 14))

        t_sub = self.f_subtitle.render(
            ">> Sonbaharın Son Işığı Bozkırda Ebediyen Parlayacak • KODTÜ Şampiyonluk Seferi <<",
            True,
            HARVEST_GOLD,
        )
        card.blit(t_sub, ((cw - t_sub.get_width()) // 2, 58))

        # Poetic Epilogue Box
        pw, ph = cw - 64, 115
        px = 32
        py = 92
        p_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        p_surf.fill((*DEEP_VOID, 235))
        pygame.draw.rect(p_surf, BURNT_AMBER, (0, 0, pw, ph), 2, border_radius=8)

        poem_lines = [
            "Bozkırın ortasına 1956'dan beri ellerle dikilen fidanlar bugün bir ormana, o orman ise ebedi bir hakikate dönüştü.",
            "Kemal Kurdaş'ın ve binlerce gencin inancı, tabiatın entropisini aklın ve emeğin zaferine dönüştürdü.",
            "Sen, Devrim Feneri'nin közünü taşıyarak soğuğu yendin; Ouroboros ebedi döngüsü mühürlendi.",
            "Artık orman güvende. Dökülen her sarı yaprak, baharın yeniden doğuşuna adanmış bir selamdır!",
        ]
        for i, line in enumerate(poem_lines):
            l_s = self.f_body.render(line, True, PALE_SUNBEAM if i == 3 else SUNLIT_BIRCH)
            p_surf.blit(l_s, (16, 12 + i * 24))
        card.blit(p_surf, (px, py))

        # 4 Statistical Cards Grid
        stat_y = 226
        stat_w = (cw - 64 - 36) // 4
        stat_h = 95
        stats = [
            ("TOPLAM SEFER", f"KORU {world.depth_level} (TAMAM)", HARVEST_GOLD),
            ("SONBAHAR ANILARI", f"{player.relics_collected} / {world.total_relics} Kristal", SUNLIT_BIRCH),
            ("ODTÜ KUTSAMALARI", f"{len(player.active_boons)} / 5 Sinerji", PALE_SUNBEAM),
            ("MERMİ YANSITMA", f"{player.orbs_deflected} Deflect", HARVEST_GOLD),
        ]
        for i, (stitle, sval, scol) in enumerate(stats):
            sx = 32 + i * (stat_w + 12)
            sb = pygame.Surface((stat_w, stat_h), pygame.SRCALPHA)
            sb.fill((*DEEP_VOID, 230))
            pygame.draw.rect(sb, WITHERED_BARK, (0, 0, stat_w, stat_h), 1, border_radius=6)
            lbl_st = self.f_small.render(stitle, True, AUTUMN_MIST)
            lbl_sv = self.f_subtitle.render(sval, True, scol)
            sb.blit(lbl_st, ((stat_w - lbl_st.get_width()) // 2, 20))
            sb.blit(lbl_sv, ((stat_w - lbl_sv.get_width()) // 2, 50))
            card.blit(sb, (sx, stat_y))

        # Academic Honor Rank Strip
        grade_letter, grade_title, total_score = evaluate_academic_grade(
            relics_collected=player.relics_collected,
            acorns_collected=player.acorns_collected,
            enemies_defeated=player.enemies_defeated,
            orbs_deflected=player.orbs_deflected,
            active_boons_count=len(player.active_boons),
            depth_level=world.depth_level,
        )
        grade_y = 330
        grade_w = cw - 64
        grade_surf = pygame.Surface((grade_w, 34), pygame.SRCALPHA)
        grade_surf.fill((*PLUM_SHADOW, 230))
        pygame.draw.rect(grade_surf, HARVEST_GOLD, (0, 0, grade_w, 34), 2, border_radius=6)
        grade_col = PALE_SUNBEAM if grade_letter == "S" else (SUNLIT_BIRCH if grade_letter == "A" else HARVEST_GOLD)
        lbl_grade = self.f_body_bold.render(
            f"🎓 [DERECENİZ: {grade_letter}] {grade_title}  •  AKADEMİK BAŞARI SKORU: {total_score:,} PUAN",
            True,
            grade_col,
        )
        grade_surf.blit(lbl_grade, ((grade_w - lbl_grade.get_width()) // 2, 7))
        card.blit(grade_surf, (32, grade_y))

        # Seed Sharing Strip
        strip_y = 372
        strip_w = cw - 64
        strip = pygame.Surface((strip_w, 34), pygame.SRCALPHA)
        strip.fill((*DEEP_VOID, 240))
        pygame.draw.rect(strip, WITHERED_BARK, (0, 0, strip_w, 34), 1, border_radius=6)
        lbl_seed = self.f_small.render(
            f"MÜHÜRLENEN ŞAMPİYONLUK TOHUMU: {world.seed_code}  (Arkadaşlarınla Paylaş)",
            True,
            PALE_SUNBEAM,
        )
        strip.blit(lbl_seed, ((strip_w - lbl_seed.get_width()) // 2, 8))
        card.blit(strip, (32, strip_y))

        # Bottom 3 Action Buttons
        btn_y = ch - 78
        btn_h = 44
        btn_w = (cw - 64 - 24) // 3

        btn_specs = [
            ("[R / ENTER] YENİ BİR DÖNGÜ BAŞLAT", CRIMSON_DECAY, PALE_SUNBEAM),
            ("[F5] BAŞKA BİR ODTÜ BÖLGESİ", PLUM_SHADOW, SUNLIT_BIRCH),
            ("[ESC] SONSUZ KEŞFE DEVAM ET", DEEP_VOID, AUTUMN_MIST),
        ]
        for i, (blbl, bg_col, border_col) in enumerate(btn_specs):
            bx = 32 + i * (btn_w + 12)
            pygame.draw.rect(card, bg_col, (bx, btn_y, btn_w, btn_h), border_radius=8)
            pygame.draw.rect(card, border_col, (bx, btn_y, btn_w, btn_h), 2, border_radius=8)
            b_text = self.f_small.render(blbl, True, PALE_SUNBEAM)
            card.blit(b_text, (bx + (btn_w - b_text.get_width()) // 2, btn_y + 12))

        screen.blit(card, (cx, cy))
