"""
Procedural Pixel-Art Banner & Technical Infographic Generator for README.md.

Generates high-resolution, pixel-perfect PNG visuals in `docs/banners/`:
1. `hero_odtu_kodtu_banner.png` (1280x360): ODTÜ × KODTÜ Hero Banner featuring
   the ODTÜ Bilim Ağacı, Autumn Forest, Verlet leaves, and 16-bit typography.
2. `pipeline_6stage_infographic.png` (1280x320): 6-Stage PCG Pipeline visual progression
   for seed "KODTU2026".
3. `palette_lut_infographic.png` (1280x260): 16-Color Sonbahar LUT & Sprite Showcase.
4. `section_divider_autumn.png` (1280x32): Pixel-art autumn foliage divider bar.
"""

from __future__ import annotations
import math
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pygame
import numpy as np

from src.core.asset_builder import AssetBank
from src.core.palette import (
    AUTUMN_16_PALETTE,
    AUTUMN_16_HEX,
    DEEP_VOID,
    PLUM_SHADOW,
    WITHERED_BARK,
    MULBERRY_DUSK,
    DAMSON_MOSS,
    CRIMSON_DECAY,
    OCHRE_CLAY,
    RUST_TERRACOTTA,
    COPPER_LEAF,
    BURNT_AMBER,
    HARVEST_GOLD,
    MUSTARD_GLOW,
    SUNLIT_BIRCH,
    PALE_SUNBEAM,
    SLATE_FOG,
    AUTUMN_MIST,
)
from src.procgen.pipeline import generate_autumn_world
from src.procgen.prng import Xoshiro256StarStar
from src.ui.pixel_font import PixelFontRenderer


def _draw_text_clean(
    surf: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    x: int,
    y: int,
    fg: tuple[int, int, int],
    shadow: tuple[int, int, int] = DEEP_VOID,
    center: bool = False,
) -> None:
    sh_s = font.render(text, False, shadow)
    fg_s = font.render(text, False, fg)
    dx = x - fg_s.get_width() // 2 if center else x
    surf.blit(sh_s, (dx + 2, y + 2))
    surf.blit(fg_s, (dx, y))


def generate_hero_banner(assets: AssetBank, out_path: Path) -> None:
    """
    Renders a 320x90 native pixel-art scene and integer-scales 4x to 1280x360,
    then overlays crisp pixel typography celebrating ODTÜ & KODTÜ Game Jam.
    """
    nw, nh = 320, 90
    canvas = pygame.Surface((nw, nh))

    # 1. Hue-shifted dusk sky bands in Sonbahar LUT
    bands = [
        (0, 18, DEEP_VOID),
        (18, 34, PLUM_SHADOW),
        (34, 48, MULBERRY_DUSK),
        (48, 60, WITHERED_BARK),
        (60, 74, DAMSON_MOSS),
        (74, 90, OCHRE_CLAY),
    ]
    for y0, y1, col in bands:
        pygame.draw.rect(canvas, col, (0, y0, nw, y1 - y0))

    # Dithered transitions between sky bands
    for y0, y1, col in bands[1:]:
        for x in range(0, nw, 2):
            canvas.set_at((x + (y0 % 2), y0), col)
            if y0 - 1 >= 0:
                canvas.set_at((x, y0 - 1), col)

    # 2. Sunlit harvest moon / emblem halo behind ODTÜ Bilim Ağacı
    pygame.draw.circle(canvas, CRIMSON_DECAY, (160, 46), 28)
    pygame.draw.circle(canvas, RUST_TERRACOTTA, (160, 46), 22)
    pygame.draw.circle(canvas, BURNT_AMBER, (160, 46), 16)
    pygame.draw.circle(canvas, HARVEST_GOLD, (160, 46), 11)

    # 3. Forest horizon of Maple, Birch, and Oak trees (ODTÜ Ormanı)
    rng = Xoshiro256StarStar("ODTU-HERO-BANNER-2026")
    tree_types = ["tree_maple", "tree_birch", "tree_oak"]
    for tx in range(8, nw - 8, 16):
        if 128 <= tx <= 192:
            continue
        tk = tree_types[(tx // 16) % 3]
        var = rng.randint(0, 2)
        ty = 46 + (tx % 5)
        canvas.blit(assets.prop_surfaces[(tk, var)], (tx - 16, ty))

    # Foreground floor carpet of crunchy golden leaves & mushrooms
    pygame.draw.rect(canvas, WITHERED_BARK, (0, 72, nw, 18))
    for lx in range(6, nw - 6, 14):
        if rng.random() < 0.65:
            canvas.blit(assets.prop_surfaces[("leaf_pile", lx % 3)], (lx, 68))
        else:
            canvas.blit(assets.prop_surfaces[("mushroom", lx % 3)], (lx, 69))

    # 4. Centerpiece: ODTÜ Bilim Ağacı Monument, Ancient Shrine, Campfires & Autumn Keeper
    canvas.blit(assets.bilim_agaci_surf, (160 - 16, 44))
    canvas.blit(assets.shrine_awake_surf, (112 - 16, 46))
    canvas.blit(assets.shrine_awake_surf, (208 - 16, 46))
    canvas.blit(assets.campfire_frames[0], (136 - 8, 62))
    canvas.blit(assets.campfire_frames[1], (184 - 8, 62))
    canvas.blit(assets.player_frames_right[1], (146 - 8, 60))
    canvas.blit(assets.entity_surfaces[("warden", 0)], (176 - 8, 60))
    canvas.blit(assets.entity_surfaces[("relic", 0)], (160 - 8, 26))

    # 5. Swirling pixel-art autumn leaves across the sky
    leaf_cols = [CRIMSON_DECAY, RUST_TERRACOTTA, BURNT_AMBER, HARVEST_GOLD, SUNLIT_BIRCH, PALE_SUNBEAM]
    for _ in range(95):
        lx = rng.randint(4, nw - 5)
        ly = rng.randint(4, nh - 8)
        col = rng.choice(leaf_cols)
        canvas.set_at((lx, ly), col)
        canvas.set_at((lx + 1, ly), col)

    # Border frame
    pygame.draw.rect(canvas, HARVEST_GOLD, (0, 0, nw, nh), 1)
    pygame.draw.rect(canvas, DEEP_VOID, (1, 1, nw - 2, nh - 2), 1)

    # Integer scale 4x -> 1280x360
    banner = pygame.transform.scale(canvas, (1280, 360))

    # Crisp pixel typography banner header
    f_title = pygame.font.SysFont("consolas,couriernew,monospace", 34, bold=True)
    f_sub = pygame.font.SysFont("consolas,couriernew,monospace", 16, bold=True)
    f_tag = pygame.font.SysFont("consolas,couriernew,monospace", 14, bold=True)

    # Top title backing ribbon
    ribbon = pygame.Surface((980, 96), pygame.SRCALPHA)
    pygame.draw.rect(ribbon, (*DEEP_VOID, 215), (0, 0, 980, 96))
    pygame.draw.rect(ribbon, (*HARVEST_GOLD, 255), (0, 0, 980, 96), 2)
    pygame.draw.rect(ribbon, (*CRIMSON_DECAY, 255), (4, 4, 972, 88), 1)
    banner.blit(ribbon, (150, 18))

    _draw_text_clean(
        banner,
        f_title,
        "KODTÜ × ODTÜ : AUTUMN PROCGEN ENGINE",
        640,
        28,
        PALE_SUNBEAM,
        DEEP_VOID,
        center=True,
    )
    _draw_text_clean(
        banner,
        f_sub,
        "ORTA DOĞU TEKNİK ÜNİVERSİTESİ (METU) • 16-BIT PIXEL ART & 6-STAGE PCG ARCHITECTURE",
        640,
        68,
        HARVEST_GOLD,
        DEEP_VOID,
        center=True,
    )
    _draw_text_clean(
        banner,
        f_tag,
        "XOSHIRO256** PRNG  •  MULTI-OCTAVE SIMPLEX FBM  •  B678/S345678 AUTOMATA  •  47-TILE BLOB  •  POISSON DISK  •  VERLET LEAVES",
        640,
        92,
        AUTUMN_MIST,
        DEEP_VOID,
        center=True,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(banner, str(out_path))


def generate_pipeline_infographic(out_path: Path) -> None:
    """
    Renders a 1280x320 visual diagram showing all 6 PCG Pipeline Stages side-by-side
    for the canonical seed 'KODTU2026'.
    """
    world = generate_autumn_world(seed="KODTU2026", width=56, height=42)
    surf = pygame.Surface((1280, 320))
    surf.fill(DEEP_VOID)
    pygame.draw.rect(surf, HARVEST_GOLD, (0, 0, 1280, 320), 2)

    f_hdr = pygame.font.SysFont("consolas,couriernew,monospace", 20, bold=True)
    f_card = pygame.font.SysFont("consolas,couriernew,monospace", 13, bold=True)
    f_sub = pygame.font.SysFont("consolas,couriernew,monospace", 11, bold=True)

    _draw_text_clean(
        surf,
        f_hdr,
        "6-STAGE DETERMINISTIC PCG PIPELINE PROGRESSION  —  SEED: 'KODTU2026' (0xDF04761EFADEBE5D)",
        640,
        12,
        SUNLIT_BIRCH,
        PLUM_SHADOW,
        center=True,
    )

    stages = [
        ("1. SIMPLEX FBM NOISE", "Elevation + Moisture Matrices"),
        ("2. CELLULAR AUTOMATA", "B678/S345678 + BFS Flood-Fill"),
        ("3. 47-TILE BLOB MASK", "8-Bit Corner-Reduced Autotile"),
        ("4. POISSON DISK O(N)", "Bridson Ecological Sampling"),
        ("5. DIJKSTRA & A* PATH", "Geodesic Threat Budgeting"),
        ("6. BIOME & WIND FIELD", "Verlet Vector Field + Relics"),
    ]

    w, h = world.width, world.height
    path_set = set(world.shortest_path)

    for idx, (title, subtitle) in enumerate(stages):
        card_x = 14 + idx * 209
        card_y = 46
        card_w = 198
        card_h = 258
        pygame.draw.rect(surf, PLUM_SHADOW, (card_x, card_y, card_w, card_h))
        pygame.draw.rect(surf, BURNT_AMBER, (card_x, card_y, card_w, card_h), 2)

        _draw_text_clean(surf, f_card, title, card_x + card_w // 2, card_y + 8, PALE_SUNBEAM, DEEP_VOID, center=True)
        _draw_text_clean(surf, f_sub, subtitle, card_x + card_w // 2, card_y + 26, AUTUMN_MIST, DEEP_VOID, center=True)

        # Render 56x42 map preview for this stage and scale 3x -> 168x126
        mini = pygame.Surface((w, h))
        mini.fill(DEEP_VOID)

        for y in range(h):
            for x in range(w):
                if idx == 0:
                    # Stage 1: Continuous fBm Elevation + Moisture
                    e = float(world.elevation[y, x])
                    m = float(world.moisture[y, x])
                    if e > 0.62:
                        col = WITHERED_BARK
                    elif m > 0.58:
                        col = CRIMSON_DECAY
                    elif m < 0.42:
                        col = HARVEST_GOLD
                    else:
                        col = BURNT_AMBER
                    mini.set_at((x, y), col)
                elif idx == 1:
                    # Stage 2: Binary Cellular Automata + BFS Flood-Fill Corridor
                    if world.walkable_grid[y, x] == 1:
                        col = DEEP_VOID
                    elif (x, y) in world.corridor_tiles:
                        col = PALE_SUNBEAM
                    else:
                        col = BURNT_AMBER
                    mini.set_at((x, y), col)
                elif idx == 2:
                    # Stage 3: 47-Tile Blob Bitmasking edge states
                    if world.walkable_grid[y, x] == 0:
                        col = PLUM_SHADOW
                    else:
                        b47 = int(world.wall_blob_47[y, x])
                        col = SUNLIT_BIRCH if b47 < 46 else WITHERED_BARK
                    mini.set_at((x, y), col)
                elif idx == 3:
                    # Stage 4: Poisson Disk Sampling points
                    col = DEEP_VOID if world.walkable_grid[y, x] == 1 else WITHERED_BARK
                    mini.set_at((x, y), col)
                elif idx == 4:
                    # Stage 5: Dijkstra Distance Field + A* Shortest Path
                    if world.walkable_grid[y, x] == 1:
                        col = DEEP_VOID
                    elif (x, y) in path_set:
                        col = PALE_SUNBEAM
                    else:
                        dn = float(world.dijkstra_norm[y, x])
                        if dn < 0.25:
                            col = MULBERRY_DUSK
                        elif dn < 0.50:
                            col = CRIMSON_DECAY
                        elif dn < 0.75:
                            col = BURNT_AMBER
                        else:
                            col = HARVEST_GOLD
                    mini.set_at((x, y), col)
                else:
                    # Stage 6: Final Biome Classification + Spawns + Structures
                    b = int(world.biome_grid[y, x])
                    if b == 0:
                        col = DEEP_VOID
                    elif b == 1:
                        col = CRIMSON_DECAY
                    elif b == 2:
                        col = RUST_TERRACOTTA
                    else:
                        col = HARVEST_GOLD
                    mini.set_at((x, y), col)

        if idx == 3:
            for p in world.props:
                px, py = int(p.x), int(p.y)
                c = SUNLIT_BIRCH if p.solid else HARVEST_GOLD
                mini.set_at((px, py), c)
        elif idx == 5:
            for sp in world.spawns:
                sx, sy = int(sp.x), int(sp.y)
                mini.set_at((sx, sy), PALE_SUNBEAM if sp.entity_type == "relic" else SUNLIT_BIRCH)

        scaled_mini = pygame.transform.scale(mini, (w * 3, h * 3))
        mx = card_x + (card_w - w * 3) // 2
        my = card_y + 50
        pygame.draw.rect(surf, DEEP_VOID, (mx - 2, my - 2, w * 3 + 4, h * 3 + 4))
        pygame.draw.rect(surf, HARVEST_GOLD, (mx - 2, my - 2, w * 3 + 4, h * 3 + 4), 1)
        surf.blit(scaled_mini, (mx, my))

        # Bottom metric badge inside each card
        metrics = [
            f"4 Octaves | H=0.52 | {world.timings_ms['1_fbm_noise']:.1f}ms",
            f"1 Component | 0 Orphans | {world.timings_ms['2_automata_bfs']:.1f}ms",
            f"256 -> 47 States | {world.timings_ms['3_autotile_47']:.1f}ms",
            f"{len(world.props)} Blue-Noise Props | {world.timings_ms['4_poisson_disk']:.1f}ms",
            f"Geodesic d in [0,1] | {world.timings_ms['5_threat_budget']:.1f}ms",
            f"{len(world.spawns)} Entities + Wind | {world.timings_ms['6_wind_field']:.1f}ms",
        ]
        _draw_text_clean(
            surf, f_sub, metrics[idx], card_x + card_w // 2, card_y + 195, SUNLIT_BIRCH, DEEP_VOID, center=True
        )
        _draw_text_clean(
            surf,
            f_sub,
            "100% DETERMINISTIC",
            card_x + card_w // 2,
            card_y + 216,
            HARVEST_GOLD,
            DEEP_VOID,
            center=True,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(out_path))


def generate_palette_infographic(assets: AssetBank, out_path: Path) -> None:
    """Renders a 1280x260 visual infographic of the 16-Color Sonbahar Chromatic Spectrum & Sprites."""
    surf = pygame.Surface((1280, 260))
    surf.fill(DEEP_VOID)
    pygame.draw.rect(surf, HARVEST_GOLD, (0, 0, 1280, 260), 2)

    f_hdr = pygame.font.SysFont("consolas,couriernew,monospace", 20, bold=True)
    f_hex = pygame.font.SysFont("consolas,couriernew,monospace", 11, bold=True)

    _draw_text_clean(
        surf,
        f_hdr,
        "16-COLOR SONBAHAR CHROMATIC SPECTRUM (HUE-SHIFTED LUT) & 16-BIT SPRITE ATLAS",
        640,
        12,
        SUNLIT_BIRCH,
        PLUM_SHADOW,
        center=True,
    )

    # 16 Color Swatches across the top row
    sw_w = 76
    sw_h = 82
    for i, (rgb, hex_str) in enumerate(zip(AUTUMN_16_PALETTE, AUTUMN_16_HEX)):
        sx = 18 + i * 78
        sy = 46
        pygame.draw.rect(surf, rgb, (sx, sy, sw_w, sw_h))
        pygame.draw.rect(surf, PALE_SUNBEAM if i in (0, 2, 5, 7, 9, 10, 12, 15) else WITHERED_BARK, (sx, sy, sw_w, sw_h), 1)
        _draw_text_clean(surf, f_hex, f"#{hex_str}", sx + sw_w // 2, sy + sw_h + 6, PALE_SUNBEAM, DEEP_VOID, center=True)
        _draw_text_clean(surf, f_hex, f"LUT[{i:02d}]", sx + sw_w // 2, sy + sw_h + 20, AUTUMN_MIST, DEEP_VOID, center=True)

    # Bottom row: 3x-scaled showcase of procedural pixel-art sprites
    showcase_items = [
        ("ODTÜ Bilim Ağacı", assets.bilim_agaci_surf),
        ("Autumn Keeper", assets.player_frames_right[1]),
        ("Crimson Maple", assets.prop_surfaces[("tree_maple", 0)]),
        ("Sunlit Birch", assets.prop_surfaces[("tree_birch", 0)]),
        ("Ancient Oak", assets.prop_surfaces[("tree_oak", 0)]),
        ("Autumn Shrine", assets.shrine_awake_surf),
        ("Stag Warden", assets.entity_surfaces[("warden", 0)]),
        ("Harvest Relic", assets.entity_surfaces[("relic", 0)]),
    ]
    for idx, (label, sp_surf) in enumerate(showcase_items):
        bx = 32 + idx * 154
        by = 162
        pygame.draw.rect(surf, PLUM_SHADOW, (bx, by, 140, 82))
        pygame.draw.rect(surf, BURNT_AMBER, (bx, by, 140, 82), 1)
        scale_f = 2 if sp_surf.get_height() == 32 else 3
        scaled_sp = pygame.transform.scale(
            sp_surf, (sp_surf.get_width() * scale_f, sp_surf.get_height() * scale_f)
        )
        surf.blit(
            scaled_sp,
            (bx + (140 - scaled_sp.get_width()) // 2, by + 6 + (52 - scaled_sp.get_height()) // 2),
        )
        _draw_text_clean(surf, f_hex, label, bx + 70, by + 63, SUNLIT_BIRCH, DEEP_VOID, center=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(out_path))


def generate_section_divider(out_path: Path) -> None:
    """Renders a 1280x28 pixel-art autumn leaf & ember divider bar."""
    nw, nh = 320, 7
    canvas = pygame.Surface((nw, nh))
    canvas.fill(DEEP_VOID)
    pygame.draw.line(canvas, WITHERED_BARK, (4, 3), (nw - 5, 3), 1)
    cols = [CRIMSON_DECAY, RUST_TERRACOTTA, BURNT_AMBER, HARVEST_GOLD, SUNLIT_BIRCH]
    for x in range(12, nw - 12, 8):
        c = cols[(x // 8) % len(cols)]
        canvas.set_at((x, 3), c)
        canvas.set_at((x + 1, 2), c)
        canvas.set_at((x - 1, 4), c)
    # Center ODTÜ crimson-gold diamond emblem
    cx = nw // 2
    for dx in range(-3, 4):
        for dy in range(-2, 3):
            if abs(dx) + abs(dy) <= 3:
                canvas.set_at((cx + dx, 3 + dy), PALE_SUNBEAM if abs(dx) + abs(dy) <= 1 else CRIMSON_DECAY)
    divider = pygame.transform.scale(canvas, (1280, 28))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(divider, str(out_path))


def generate_competitor_infographic(out_path: Path) -> None:
    """
    Renders a 1280x290 infographic comparing the 6 genre benchmarks (Hyper Light Drifter,
    Core Keeper, Nuclear Throne, Enter the Gungeon, Wizard of Legend, Don't Starve)
    and how KODTÜ: Autumn ProcGen Engine synthesizes their best pillars.
    """
    surf = pygame.Surface((1280, 290))
    surf.fill(DEEP_VOID)
    pygame.draw.rect(surf, HARVEST_GOLD, (0, 0, 1280, 290), 2)

    f_hdr = pygame.font.SysFont("consolas,couriernew,monospace", 19, bold=True)
    f_title = pygame.font.SysFont("consolas,couriernew,monospace", 13, bold=True)
    f_sub = pygame.font.SysFont("consolas,couriernew,monospace", 11, bold=False)

    _draw_text_clean(
        surf,
        f_hdr,
        "GENRE BENCHMARK & COMPETITOR ANALYSIS MATRIX  —  TOP-DOWN PIXEL-ART PROCGEN ROGUELITES",
        640,
        12,
        SUNLIT_BIRCH,
        PLUM_SHADOW,
        center=True,
    )

    competitors = [
        (
            "HYPER LIGHT DRIFTER",
            "Heart Machine (2016)",
            "Slash-Recharged Ammo [F]",
            "Dash Afterimage Ghosts",
            "Melee Orb Deflection",
            "Hue-Shifted Neon/Fall LUT",
        ),
        (
            "CORE KEEPER",
            "Pugstorm (2024)",
            "B678/S345678 Automata",
            "Multi-Biome Ecosystem",
            "47-Tile Blob Autotiling",
            "16x16 Spatial Chunk Hash",
        ),
        (
            "NUCLEAR THRONE",
            "Vlambeer (2015)",
            "Tactile Hit-Stop Freeze",
            "Trauma^2 Camera Shake",
            "Zero Dead-End Carvers",
            "Roguelite Boon Synergies",
        ),
        (
            "ENTER THE GUNGEON",
            "Dodge Roll (2016)",
            "Dijkstra Threat Budget",
            "3-Way Boss Orb Volleys",
            "Bullet-Deflect Slash",
            "320x180 Integer Scaling",
        ),
        (
            "WIZARD OF LEGEND",
            "Contingent99 (2018)",
            "3-Hit Solar Ember Combo",
            "360 Harvest Nova [Q]",
            "Autumn Gust Dash [SHF]",
            "5 ODTÜ Relic Boons [B]",
        ),
        (
            "DON'T STARVE / NOITA",
            "Klei / Nolla Games",
            "Lantern Warmth Survival",
            "ODTÜ Bilim Ağacı Buff",
            "Verlet 2D Wind Leaves",
            "64-Bit Xoshiro256** Seed",
        ),
    ]

    for idx, (name, studio, p1, p2, p3, p4) in enumerate(competitors):
        cx = 14 + idx * 209
        cy = 46
        cw = 198
        ch = 186
        pygame.draw.rect(surf, PLUM_SHADOW, (cx, cy, cw, ch))
        pygame.draw.rect(surf, BURNT_AMBER, (cx, cy, cw, ch), 2)
        pygame.draw.rect(surf, CRIMSON_DECAY, (cx + 2, cy + 2, cw - 4, 42))

        _draw_text_clean(surf, f_title, name, cx + cw // 2, cy + 7, PALE_SUNBEAM, DEEP_VOID, center=True)
        _draw_text_clean(surf, f_sub, studio, cx + cw // 2, cy + 25, AUTUMN_MIST, DEEP_VOID, center=True)

        for p_idx, pillar in enumerate((p1, p2, p3, p4)):
            py = cy + 56 + p_idx * 30
            pygame.draw.rect(surf, DEEP_VOID, (cx + 8, py - 2, cw - 16, 22))
            pygame.draw.rect(surf, WITHERED_BARK, (cx + 8, py - 2, cw - 16, 22), 1)
            _draw_text_clean(surf, f_sub, f"+ {pillar}", cx + 14, py + 2, SUNLIT_BIRCH, DEEP_VOID)

    # Bottom summary banner inside infographic
    pygame.draw.rect(surf, PLUM_SHADOW, (14, 242, 1252, 34))
    pygame.draw.rect(surf, SUNLIT_BIRCH, (14, 242, 1252, 34), 1)
    _draw_text_clean(
        surf,
        f_title,
        "KODTÜ: AUTUMN PROCGEN ENGINE SYNTHESIZES ALL 6 BENCHMARK PILLARS IN <35ms DETERMINISTIC PYTHON",
        640,
        251,
        PALE_SUNBEAM,
        DEEP_VOID,
        center=True,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(out_path))


def generate_odtu_campus_wallpaper(assets: AssetBank, out_path: Path) -> None:
    """
    Renders a stunning 1920x1080 Ultra HD Desktop Wallpaper:
    "ODTÜ & KODTÜ: Sonbahar Bozkırından Yükselen Orman"
    Features a sweeping sunset autumn sky with gradient dithering,
    the brutalist ODTÜ Bilim Ağacı monument glowing at twilight, Devrim Stadium
    autumn forest vista, Verlet foliage swirls, and authentic campus typography.
    """
    w, h = 1920, 1080
    surf = pygame.Surface((w, h))
    surf.fill(DEEP_VOID)

    # 1. Sky Gradient (Sunset Crimson to Plum Dusk)
    for y in range(h // 2):
        t = y / (h * 0.5)
        if t < 0.35:
            col = PLUM_SHADOW
        elif t < 0.65:
            col = CRIMSON_DECAY
        elif t < 0.85:
            col = BURNT_AMBER
        else:
            col = HARVEST_GOLD
        pygame.draw.line(surf, col, (0, y), (w, y))

    # 2. Golden Sunlit Horizon & Twilight Mist
    sun_cx, sun_cy = 960, 480
    for r in range(320, 40, -20):
        alpha = int(25 * (1.0 - r / 320.0))
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*PALE_SUNBEAM, alpha), (sun_cx, sun_cy), r)
        surf.blit(glow, (0, 0))

    # 3. Distant ODTÜ Campus Forest Canopy (Multi-layered Y-Sorted Mountains & Trees)
    tree_surfs = [
        assets.prop_surfaces[("tree_oak", 0)],
        assets.prop_surfaces[("tree_maple", 0)],
        assets.prop_surfaces[("tree_birch", 0)],
    ]
    # Distant silhouetted hills
    for x in range(0, w, 4):
        hy = int(480 + 35 * math.sin(x * 0.005) + 18 * math.sin(x * 0.015))
        pygame.draw.line(surf, WITHERED_BARK, (x, hy), (x, h))

    # Midground dense autumn forest layer (scaled 4x pixel trees)
    rng = np.random.default_rng(1956)
    for tx in range(-40, w + 40, 24):
        ty = int(510 + rng.uniform(-15, 60))
        t_idx = int(rng.integers(0, 3))
        scaled_tree = pygame.transform.scale(tree_surfs[t_idx], (96, 96))
        surf.blit(scaled_tree, (tx, ty))

    # Foreground ground plane
    pygame.draw.rect(surf, DAMSON_MOSS, (0, 680, w, h - 680))
    for y in range(680, h):
        t = (y - 680) / (h - 680)
        c = OCHRE_CLAY if t < 0.3 else (WITHERED_BARK if t < 0.7 else DEEP_VOID)
        pygame.draw.line(surf, c, (0, y), (w, y))

    # 4. Giant Majestic ODTÜ Bilim Ağacı Monument (Center Stage, 256x256 pixel art)
    scaled_monument = pygame.transform.scale(assets.bilim_agaci_surf, (280, 280))
    mon_x = 960 - 140
    mon_y = 680 - 240
    # Warm beacon aura beneath monument
    mon_glow = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.circle(mon_glow, (*PALE_SUNBEAM, 40), (960, mon_y + 140), 220)
    pygame.draw.circle(mon_glow, (*HARVEST_GOLD, 65), (960, mon_y + 140), 140)
    surf.blit(mon_glow, (0, 0))
    surf.blit(scaled_monument, (mon_x, mon_y))

    # 5. Devrim Lantern & Autumn Keeper Silhouette on a rock
    scaled_player = pygame.transform.scale(assets.player_frames_right[0], (72, 72))
    surf.blit(scaled_player, (720, 650))
    # Lantern flame glow
    p_glow = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.circle(p_glow, (*PALE_SUNBEAM, 110), (748, 672), 36)
    pygame.draw.circle(p_glow, (*HARVEST_GOLD, 50), (748, 672), 70)
    surf.blit(p_glow, (0, 0))

    # 6. Swirling Verlet Autumn Leaves in the Wind across 1920x1080 canvas
    for i in range(120):
        lx = int(rng.uniform(0, w))
        ly = int(rng.uniform(300, h - 40))
        lcol = PALE_SUNBEAM if i % 4 == 0 else (SUNLIT_BIRCH if i % 2 == 0 else COPPER_LEAF)
        lr = int(rng.integers(3, 8))
        pygame.draw.circle(surf, lcol, (lx, ly), lr)
        pygame.draw.circle(surf, DEEP_VOID, (lx, ly), lr, 1)

    # 7. Cinematic Branding & Typography Overlays
    pygame.font.init()
    f_huge = pygame.font.SysFont("segoeui,arial,verdana", 38, bold=True)
    f_sub = pygame.font.SysFont("segoeui,arial,verdana", 20, bold=True)
    f_quote = pygame.font.SysFont("segoeui,arial,verdana", 18, bold=True)
    f_creds = pygame.font.SysFont("consolas,monospace", 15, bold=False)

    # Top-Left ODTÜ Header Card
    card_w, card_h = 780, 115
    hcard = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
    hcard.fill((*DEEP_VOID, 230))
    pygame.draw.rect(hcard, HARVEST_GOLD, (0, 0, card_w, card_h), 2, border_radius=8)
    _draw_text_clean(hcard, f_huge, "ORTA DOĞU TEKNİK ÜNİVERSİTESİ", 28, 16, PALE_SUNBEAM, DEEP_VOID)
    _draw_text_clean(
        hcard, f_sub, "ODTÜ BİLGİSAYAR TOPLULUĞU (CClub)  •  KODTÜ GAME JAM 2026", 28, 70, SUNLIT_BIRCH, DEEP_VOID
    )
    surf.blit(hcard, (60, 50))

    # Bottom-Right Specs & Quote Card
    qcard_w, qcard_h = 780, 100
    qcard = pygame.Surface((qcard_w, qcard_h), pygame.SRCALPHA)
    qcard.fill((*DEEP_VOID, 235))
    pygame.draw.rect(qcard, BURNT_AMBER, (0, 0, qcard_w, qcard_h), 2, border_radius=8)
    _draw_text_clean(
        qcard,
        f_quote,
        "'Bozkırdan yükselen bu orman, her sonbaharda küllerinden yeniden doğar.'",
        24,
        18,
        PALE_SUNBEAM,
        DEEP_VOID,
    )
    _draw_text_clean(
        qcard,
        f_creds,
        "100% Deterministic PCG  •  16-Color Autumn Spectrum  •  Integer-Scaled Pixel Art",
        24,
        58,
        HARVEST_GOLD,
        DEEP_VOID,
    )
    surf.blit(qcard, (w - qcard_w - 60, h - qcard_h - 50))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(out_path))


def build_all_banners() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((320, 180))
    assets = AssetBank(REPO_ROOT / "assets")
    banners_dir = REPO_ROOT / "docs" / "banners"
    generate_hero_banner(assets, banners_dir / "hero_odtu_kodtu_banner.png")
    generate_pipeline_infographic(banners_dir / "pipeline_6stage_infographic.png")
    generate_palette_infographic(assets, banners_dir / "palette_lut_infographic.png")
    generate_competitor_infographic(banners_dir / "competitor_matrix_infographic.png")
    generate_section_divider(banners_dir / "section_divider_autumn.png")
    generate_odtu_campus_wallpaper(assets, banners_dir / "odtu_campus_wallpaper_1080p.png")
    pygame.quit()


if __name__ == "__main__":
    build_all_banners()

