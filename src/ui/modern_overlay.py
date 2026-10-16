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
from src.core.story import StoryManager, CHAPTER_INFO
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
    ) -> None:
        sw, sh = screen.get_size()
        if sw < 640 or sh < 360:
            return

        # 1. Top-Left: Clean Modern Status & Objective Panel
        self._render_status_and_objective_panel(screen, world, player, items, story)

        # 2. Top-Center: Directional Relic/Shrine Compass & Boss Health Bar
        self._render_compass_and_boss_bar(screen, sw, world, player, items, enemies)

        # 3. Top-Right: Chapter Title & Crisp 2x Minimap Radar
        if show_minimap and not seed_modal_open and not codex_open:
            self._render_minimap_panel(screen, sw, world, player, items)

        # 4. Bottom-Center: Story Dialogue Box (or Minimalist Control Hint Bar)
        if story.active_dialogue is not None and not story.show_intro_card:
            self._render_dialogue_box(screen, sw, sh, story)
        elif not story.show_intro_card:
            self._render_bottom_controls_bar(screen, sw, sh)

        # 5. Floating Event Notification Toast
        if banner_timer > 0.0 and banner_text and not story.show_intro_card:
            self._render_banner_toast(screen, sw, banner_text)

        # 6. Interactive Modals ([C] Story & Boon Codex, [TAB] Seed Input, or Story Intro Card)
        if story.show_intro_card:
            self._render_story_intro_card(screen, sw, sh, world)
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
        lbl_warm = self.f_small.render(
            f"DEVRİM FENERİ ISISI: %{int(round(warm_pct * 100))}", True, SUNLIT_BIRCH
        )
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

        # Clear Objective Line at the bottom of the card
        obj_str = story.get_current_objective_text(player.relics_collected, world.total_relics)
        lbl_obj = self.f_tiny.render(obj_str, True, AUTUMN_MIST)
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
            target_label = "KADİM TAPINAK [E]"
            col = PALE_SUNBEAM
        else:
            nearest = min(
                uncollected, key=lambda it: (it.x - player.x) ** 2 + (it.y - player.y) ** 2
            )
            tx, ty = nearest.x, nearest.y
            target_label = "EN YAKIN ANI KRİSTALİ"
            col = HARVEST_GOLD

        dx = tx - player.x
        dy = ty - player.y
        dist = int(round(math.hypot(dx, dy)))
        angle = math.atan2(dy, dx)

        cw, ch = 250, 44
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
        t2 = self.f_tiny.render(f"Mesafe: {dist} adım", True, AUTUMN_MIST)
        pill.blit(t1, (48, 6))
        pill.blit(t2, (48, 23))
        screen.blit(pill, (cx_box, cy_box))

        # Boss Health Bar if Elder Stag Warden is nearby
        for en in enemies:
            if en.alive and en.kind == "warden":
                if math.hypot(en.x - player.x, en.y - player.y) <= 11.0:
                    bw, bh = 360, 42
                    bx = (sw - bw) // 2
                    by = 68
                    bpanel = pygame.Surface((bw, bh), pygame.SRCALPHA)
                    bpanel.fill((*DEEP_VOID, 230))
                    pygame.draw.rect(bpanel, CRIMSON_DECAY, (0, 0, bw, bh), 2, border_radius=6)
                    b_lbl = self.f_small.render(
                        "🦌 ORMAN MUHAFIZI: KADİM GEYİK (ELDER STAG WARDEN)", True, SUNLIT_BIRCH
                    )
                    bpanel.blit(b_lbl, ((bw - b_lbl.get_width()) // 2, 5))
                    pygame.draw.rect(bpanel, PLUM_SHADOW, (16, 25, bw - 32, 10), border_radius=4)
                    fill = max(0, int(round((bw - 32) * (en.hp / max(1, en.max_hp)))))
                    if fill > 0:
                        pygame.draw.rect(bpanel, HARVEST_GOLD, (16, 25, fill, 10), border_radius=4)
                    pygame.draw.rect(bpanel, BURNT_AMBER, (16, 25, bw - 32, 10), 1, border_radius=4)
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
        bw = min(900, sw - 40)
        bh = 32
        bx = (sw - bw) // 2
        by = sh - bh - 10
        bar = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bar.fill((*DEEP_VOID, 210))
        pygame.draw.rect(bar, WITHERED_BARK, (0, 0, bw, bh), 1, border_radius=6)

        txt = (
            "[WASD] Yürü   •   [SPACE / Sol Tık] Kılıç & Yansıtma   •   "
            "[F / Sağ Tık] Köz Atışı   •   [Q] Nova   •   [SHIFT] Atıl   •   "
            "[C] Günlük   •   [F5] ODTÜ Tohumu"
        )
        lbl = self.f_tiny.render(txt, True, AUTUMN_MIST)
        bar.blit(lbl, ((bw - lbl.get_width()) // 2, 8))
        screen.blit(bar, (bx, by))

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
        dim.fill((*DEEP_VOID, 185))
        screen.blit(dim, (0, 0))

        cw, ch = 740, 430
        cx = (sw - cw) // 2
        cy = (sh - ch) // 2
        card = pygame.Surface((cw, ch), pygame.SRCALPHA)
        card.fill((*PLUM_SHADOW, 248))
        pygame.draw.rect(card, HARVEST_GOLD, (0, 0, cw, ch), 3, border_radius=12)
        pygame.draw.rect(card, SUNLIT_BIRCH, (6, 6, cw - 12, ch - 12), 1, border_radius=9)

        # Top decorative sprites (Bilim Ağacı, Autumn Keeper, Shrine)
        s_bilim = pygame.transform.scale(self.assets.bilim_agaci_surf, (64, 64))
        s_player = pygame.transform.scale(self.assets.player_frames_right[0], (48, 48))
        s_shrine = pygame.transform.scale(self.assets.shrine_awake_surf, (64, 64))
        card.blit(s_bilim, (cw // 2 - 110, 22))
        card.blit(s_player, (cw // 2 - 24, 34))
        card.blit(s_shrine, (cw // 2 + 46, 22))

        t_main = self.f_title.render("🍁 ODTÜ : SONBAHARIN SON IŞIĞI", True, PALE_SUNBEAM)
        t_sub = self.f_subtitle.render(
            "Prosedürel Bir Sonbahar Hikayesi  •  KODTÜ Game Jam", True, HARVEST_GOLD
        )
        card.blit(t_main, ((cw - t_main.get_width()) // 2, 96))
        card.blit(t_sub, ((cw - t_sub.get_width()) // 2, 132))

        story_lines = [
            "Bozkır ayazı Orta Doğu Teknik Üniversitesi (ODTÜ) ormanına erken çöktü.",
            "Bilim Ağacı'nın meşalesi sönmek üzereyken, genç orman bekçisi Ekin elinde",
            "Devrim Feneri ile her adımda yeniden şekillenen (Procedural Generation)",
            "büyülü sonbahar korusuna adım atar.",
            "",
            "🎯 OYUNUN AMACI (Çok Basit ve Net):",
            "1. Pusula okunu takip ederek ormandaki 5 Altın Sonbahar Anısını (Kristal) topla.",
            "2. Fenerin üşüdüğünde ODTÜ Bilim Ağacı Anıtı veya Kamp Ateşlerinin yanında ısın.",
            "3. 5 Anıyı tamamladığında Kadim Tapınağa [E] giderek yeni korunun kapısını aç!",
        ]
        for idx, line in enumerate(story_lines):
            col = SUNLIT_BIRCH if line.startswith("🎯") else AUTUMN_MIST
            font_use = self.f_body_bold if line.startswith("🎯") else self.f_body
            ls = font_use.render(line, True, col)
            card.blit(ls, (48, 172 + idx * 22))

        # Start button pill
        btn_w, btn_h = 420, 40
        btn_x = (cw - btn_w) // 2
        btn_y = ch - 56
        pygame.draw.rect(card, CRIMSON_DECAY, (btn_x, btn_y, btn_w, btn_h), border_radius=8)
        pygame.draw.rect(card, PALE_SUNBEAM, (btn_x, btn_y, btn_w, btn_h), 2, border_radius=8)
        btn_lbl = self.f_subtitle.render(
            "[ENTER / SPACE / TIKLA] HİKAYEYE BAŞLA", True, PALE_SUNBEAM
        )
        card.blit(btn_lbl, ((cw - btn_lbl.get_width()) // 2, btn_y + 8))

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
