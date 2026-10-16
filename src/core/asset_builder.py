"""
Deterministic Pixel-Art Sprite, 47-Tile Blob Tileset, Palette LUT, and GLSL Shader Builder.

All visual assets are strictly locked to the 16-Color Sonbahar Chromatic Spectrum
defined in Section 4 of README.md. Assets are saved to `assets/` on disk and loaded
into Pygame surfaces with Nearest-Neighbor pixel alignment.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from PIL import Image
import pygame

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
from src.procgen.autotile import (
    CANONICAL_47_MASKS,
    BIT_NW,
    BIT_N,
    BIT_NE,
    BIT_W,
    BIT_E,
    BIT_SW,
    BIT_S,
    BIT_SE,
)
from src.procgen.prng import Mulberry32, seed_to_uint64


PALETTE_QUANTIZE_GLSL = """#version 330 core
// KODTU Autumn ProcGen - 16-Color Sonbahar LUT Quantization & Hue-Shift Shader
in vec2 v_texcoord;
out vec4 frag_color;

uniform sampler2D u_screen_tex;
uniform sampler2D u_autumn_lut; // 16x1 16-Color Sonbahar LUT
uniform float u_mist_density;

const vec3 DEEP_VOID = vec3(0.102, 0.067, 0.094);    // #1A1118
const vec3 SUNLIT_BIRCH = vec3(0.961, 0.839, 0.482); // #F5D67B
const vec3 AUTUMN_MIST = vec3(0.831, 0.784, 0.745);  // #D4C8BE

void main() {
    vec4 src = texture(u_screen_tex, v_texcoord);
    vec3 col = mix(src.rgb, AUTUMN_MIST, clamp(u_mist_density, 0.0, 0.35));

    // Find nearest neighbor in the 16-Color Sonbahar LUT
    vec3 best_col = DEEP_VOID;
    float min_dist = 999.0;
    for (int i = 0; i < 16; ++i) {
        vec3 lut_col = texelFetch(u_autumn_lut, ivec2(i, 0), 0).rgb;
        vec3 diff = col - lut_col;
        // Perceptual RGB weighting
        float d = dot(diff * diff, vec3(0.299, 0.587, 0.114));
        if (d < min_dist) {
            min_dist = d;
            best_col = lut_col;
        }
    }
    frag_color = vec4(best_col, src.a);
}
"""

WIND_SWAY_GLSL = """#version 330 core
// KODTU Autumn ProcGen - Pixel-Snapped Foliage Wind Sway & Mist Shader
in vec2 v_texcoord;
out vec4 frag_color;

uniform sampler2D u_sprite_tex;
uniform float u_time;
uniform vec2 u_wind_vec;
uniform vec2 u_tex_size;

void main() {
    // Upper canopy sways with sinusoidal wind while trunk base stays anchored
    float height_factor = clamp(1.0 - v_texcoord.y, 0.0, 1.0);
    float sway_px = round(sin(u_time * 3.2 + v_texcoord.y * 4.0) * u_wind_vec.x * height_factor);
    vec2 snapped_uv = (floor(v_texcoord * u_tex_size + vec2(sway_px, 0.0)) + 0.5) / u_tex_size;
    frag_color = texture(u_sprite_tex, clamp(snapped_uv, 0.0, 1.0));
}
"""


def _write_palette_and_shaders(assets_dir: Path) -> None:
    palettes_dir = assets_dir / "palettes"
    shaders_dir = assets_dir / "shaders"
    palettes_dir.mkdir(parents=True, exist_ok=True)
    shaders_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write .hex palette file
    hex_path = palettes_dir / "autumn_16.hex"
    hex_path.write_text("\n".join(AUTUMN_16_HEX) + "\n", encoding="utf-8")

    # 2. Write .png LUT strip (16x1 and 256x32 swatch strip)
    lut_arr = np.zeros((16, 16 * 16, 3), dtype=np.uint8)
    for idx, rgb in enumerate(AUTUMN_16_PALETTE):
        lut_arr[:, idx * 16 : (idx + 1) * 16] = rgb
    Image.fromarray(lut_arr, mode="RGB").save(palettes_dir / "autumn_lut.png")

    # 3. Write GLSL Shaders
    (shaders_dir / "palette_quantize.glsl").write_text(PALETTE_QUANTIZE_GLSL, encoding="utf-8")
    (shaders_dir / "wind_sway.glsl").write_text(WIND_SWAY_GLSL, encoding="utf-8")


def _render_single_blob_tile(mask: int, tile_idx: int) -> np.ndarray:
    """
    Synthesizes a 16x16 RGBA pixel-art tile for one of the 47 canonical blob bitmasks.
    Walls represent dense autumn canopy / raised stone cliff edges with hue-shifted
    deep void shadows and warm amber/crimson overhanging foliage.
    """
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    rng = Mulberry32(0xA070 + tile_idx * 97)

    has_n = bool(mask & BIT_N)
    has_s = bool(mask & BIT_S)
    has_w = bool(mask & BIT_W)
    has_e = bool(mask & BIT_E)
    has_nw = bool(mask & BIT_NW)
    has_ne = bool(mask & BIT_NE)
    has_sw = bool(mask & BIT_SW)
    has_se = bool(mask & BIT_SE)

    for y in range(16):
        for x in range(16):
            # Distance to exposed cardinal edges
            dist_n = y if not has_n else 16
            dist_s = (15 - y) if not has_s else 16
            dist_w = x if not has_w else 16
            dist_e = (15 - x) if not has_e else 16

            min_edge = min(dist_n, dist_s, dist_w, dist_e)

            # Check inner concave corners (when cardinals are present but diagonal is missing)
            if has_n and has_w and not has_nw and x < 4 and y < 4:
                min_edge = min(min_edge, max(x, y))
            if has_n and has_e and not has_ne and x > 11 and y < 4:
                min_edge = min(min_edge, max(15 - x, y))
            if has_s and has_w and not has_sw and x < 4 and y > 11:
                min_edge = min(min_edge, max(x, 15 - y))
            if has_s and has_e and not has_se and x > 11 and y > 11:
                min_edge = min(min_edge, max(15 - x, 15 - y))

            # Round outer convex corners
            if not has_n and not has_w and (x + y) < 3:
                min_edge = -1
            if not has_n and not has_e and ((15 - x) + y) < 3:
                min_edge = -1
            if not has_s and not has_w and (x + (15 - y)) < 3:
                min_edge = -1
            if not has_s and not has_e and ((15 - x) + (15 - y)) < 3:
                min_edge = -1

            if min_edge < 0:
                # Transparent corner pixel (shows underlying biome floor)
                arr[y, x] = (0, 0, 0, 0)
            elif min_edge == 0:
                # Outer crisp pixel outline in Deep Void (#1A1118)
                arr[y, x] = (*DEEP_VOID, 255)
            elif min_edge == 1:
                # Sunlit top rim on North/West, deep plum cliff face on South/East
                if dist_n == 1 or dist_w == 1:
                    col = BURNT_AMBER if (x + y) % 2 == 0 else HARVEST_GOLD
                else:
                    col = WITHERED_BARK if (x % 3 != 0) else PLUM_SHADOW
                arr[y, x] = (*col, 255)
            elif min_edge == 2:
                if not has_s and dist_s == 2:
                    col = CRIMSON_DECAY if (x % 2 == 0) else WITHERED_BARK
                else:
                    col = RUST_TERRACOTTA if rng.random() < 0.6 else CRIMSON_DECAY
                arr[y, x] = (*col, 255)
            else:
                # Dense interior canopy cluster texture
                r = rng.random()
                cluster = ((x // 2) + (y // 2)) % 3
                if cluster == 0:
                    col = CRIMSON_DECAY if r < 0.65 else MULBERRY_DUSK
                elif cluster == 1:
                    col = WITHERED_BARK if r < 0.70 else PLUM_SHADOW
                else:
                    col = RUST_TERRACOTTA if r < 0.45 else DEEP_VOID
                arr[y, x] = (*col, 255)

    return arr


def _build_floor_tiles() -> List[np.ndarray]:
    """
    Builds 12 16x16 floor tiles:
    - 0..3: Damp Decay Biome (wet bark soil, crimson leaf litter, moss spots)
    - 4..7: Burnt Amber Grove (warm terracotta/ochre earth, amber leaf scatter)
    - 8..11: Crisp Golden Corridor (sunlit golden birch carpet, bright mustard accents)
    """
    tiles: List[np.ndarray] = []
    for biome_idx in range(3):
        for var in range(4):
            rng = Mulberry32(0xF100 + biome_idx * 100 + var * 17)
            arr = np.zeros((16, 16, 4), dtype=np.uint8)
            for y in range(16):
                for x in range(16):
                    r = rng.random()
                    if biome_idx == 0:
                        # Damp Decay
                        base = WITHERED_BARK if (x + y) % 2 == 0 else PLUM_SHADOW
                        if r < 0.08:
                            base = CRIMSON_DECAY
                        elif r < 0.16:
                            base = DAMSON_MOSS
                        elif r < 0.19 and var == 3:
                            base = RUST_TERRACOTTA
                    elif biome_idx == 1:
                        # Burnt Amber Grove
                        base = DAMSON_MOSS if (x + y) % 2 == 0 else OCHRE_CLAY
                        if r < 0.14:
                            base = RUST_TERRACOTTA
                        elif r < 0.22:
                            base = BURNT_AMBER
                        elif r < 0.26:
                            base = WITHERED_BARK
                    else:
                        # Crisp Golden Corridor
                        base = OCHRE_CLAY if (x + y) % 2 == 0 else RUST_TERRACOTTA
                        if r < 0.25:
                            base = BURNT_AMBER
                        elif r < 0.42:
                            base = HARVEST_GOLD
                        elif r < 0.48:
                            base = SUNLIT_BIRCH
                    arr[y, x] = (*base, 255)
            tiles.append(arr)
    return tiles


def _draw_circle_px(
    arr: np.ndarray, cx: int, cy: int, radius: int, fill_rgb: Tuple[int, int, int], outline_rgb: Tuple[int, int, int] = DEEP_VOID
) -> None:
    h, w, _ = arr.shape
    for y in range(max(0, cy - radius - 1), min(h, cy + radius + 2)):
        for x in range(max(0, cx - radius - 1), min(w, cx + radius + 2)):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if d2 <= (radius - 1) ** 2:
                arr[y, x] = (*fill_rgb, 255)
            elif d2 <= radius * radius:
                arr[y, x] = (*outline_rgb, 255)


def _build_tree_sprite(tree_kind: str, variant: int = 0) -> np.ndarray:
    """
    Renders a 32x32 pixel-art Autumn Tree (`tree_maple`, `tree_birch`, `tree_oak`)
    with Y-sortable trunk base, dappled leaf clusters, and Hue-Shifted highlights/shadows.
    """
    arr = np.zeros((32, 32, 4), dtype=np.uint8)
    rng = Mulberry32((seed_to_uint64(tree_kind) & 0xFFFFFFFF) + variant * 31)

    if tree_kind == "tree_maple":
        shadow_c, mid_c, light_c, spec_c = MULBERRY_DUSK, CRIMSON_DECAY, RUST_TERRACOTTA, BURNT_AMBER
        trunk_dark, trunk_light = DEEP_VOID, WITHERED_BARK
    elif tree_kind == "tree_birch":
        shadow_c, mid_c, light_c, spec_c = BURNT_AMBER, HARVEST_GOLD, MUSTARD_GLOW, SUNLIT_BIRCH
        trunk_dark, trunk_light = SLATE_FOG, AUTUMN_MIST
    else:  # tree_oak
        shadow_c, mid_c, light_c, spec_c = CRIMSON_DECAY, RUST_TERRACOTTA, BURNT_AMBER, HARVEST_GOLD
        trunk_dark, trunk_light = PLUM_SHADOW, WITHERED_BARK

    # 1. Ground shadow ellipse at base (y=26..30, x=9..22)
    for y in range(26, 31):
        for x in range(8, 24):
            if ((x - 15.5) / 7.5) ** 2 + ((y - 28.0) / 2.3) ** 2 <= 1.0:
                arr[y, x] = (*DEEP_VOID, 170)

    # 2. Tree trunk (y=17..29, x=13..18)
    for y in range(17, 29):
        width_mod = 1 if y > 25 else 0
        x0 = 13 - width_mod
        x1 = 18 + width_mod
        for x in range(x0, x1 + 1):
            if x == x0 or x == x1 or y == 28:
                arr[y, x] = (*DEEP_VOID, 255)
            elif x <= 15:
                # Birch has characteristic dark horizontal bark notches
                if tree_kind == "tree_birch" and (y % 3 == 0 and x == 15):
                    arr[y, x] = (*DEEP_VOID, 255)
                else:
                    arr[y, x] = (*trunk_light, 255)
            else:
                arr[y, x] = (*trunk_dark, 255)

    # 3. Multi-sphere foliage crown with pixel-art leaf clustering
    spheres = [
        (11, 14, 7),
        (20, 14, 7),
        (15, 9, 8),
        (15, 15, 7),
    ]
    for y in range(2, 23):
        for x in range(3, 29):
            inside = False
            min_edge_dist = 99.0
            for scx, scy, sr in spheres:
                d = ((x - scx) ** 2 + (y - scy) ** 2) ** 0.5
                if d <= sr:
                    inside = True
                    min_edge_dist = min(min_edge_dist, sr - d)
            if not inside:
                continue

            if min_edge_dist < 1.15:
                arr[y, x] = (*DEEP_VOID, 255)
            else:
                # Directional sunlight from Top-Left (NW)
                light_score = (16 - x) * 0.35 + (14 - y) * 0.65 + (rng.random() - 0.5) * 3.5
                if light_score > 4.2:
                    col = spec_c
                elif light_score > 0.8:
                    col = light_c
                elif light_score > -2.8:
                    col = mid_c
                else:
                    col = shadow_c
                arr[y, x] = (*col, 255)

    return arr


def _build_small_prop_sprite(prop_type: str, variant: int = 0) -> np.ndarray:
    """Renders 16x16 pixel-art sprites for bushes, leaf piles, glowing mushrooms, logs, and stones."""
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    rng = Mulberry32((seed_to_uint64(prop_type) & 0xFFFFFFFF) + variant * 53)

    if prop_type == "leaf_pile":
        # Crunchy scattered autumn leaf mound
        for y in range(6, 15):
            for x in range(2, 14):
                norm = ((x - 7.5) / 6.0) ** 2 + ((y - 10.5) / 4.2) ** 2
                if norm <= 1.0:
                    if norm > 0.76:
                        arr[y, x] = (*DEEP_VOID, 220)
                    else:
                        r = rng.random()
                        if r < 0.30:
                            col = HARVEST_GOLD
                        elif r < 0.65:
                            col = BURNT_AMBER
                        elif r < 0.88:
                            col = RUST_TERRACOTTA
                        else:
                            col = SUNLIT_BIRCH
                        arr[y, x] = (*col, 255)
    elif prop_type == "bush_amber":
        _draw_circle_px(arr, 6, 10, 4, RUST_TERRACOTTA)
        _draw_circle_px(arr, 10, 10, 4, BURNT_AMBER)
        _draw_circle_px(arr, 8, 8, 5, HARVEST_GOLD)
        # Add crimson berry/leaf accents
        arr[7, 6] = (*SUNLIT_BIRCH, 255)
        arr[9, 9] = (*CRIMSON_DECAY, 255)
        arr[8, 10] = (*CRIMSON_DECAY, 255)
    elif prop_type == "mushroom":
        # Cluster of 2 glowing autumn mushrooms
        for mx, my, mr in ((6, 9, 3), (10, 11, 2)):
            # Stalk
            for sy in range(my, my + 4):
                if sy < 15:
                    arr[sy, mx] = (*AUTUMN_MIST, 255)
                    arr[sy, mx - 1] = (*DEEP_VOID, 255)
                    arr[sy, mx + 1] = (*DEEP_VOID, 255)
            # Cap
            for cy in range(my - mr, my + 1):
                for cx in range(mx - mr - 1, mx + mr + 2):
                    if (cx - mx) ** 2 + (cy - my) ** 2 <= (mr + 0.5) ** 2:
                        if cy == my or abs(cx - mx) >= mr:
                            arr[cy, cx] = (*DEEP_VOID, 255)
                        elif (cx + cy) % 3 == 0:
                            arr[cy, cx] = (*SUNLIT_BIRCH, 255)
                        else:
                            cap_col = CRIMSON_DECAY if variant % 2 == 0 else HARVEST_GOLD
                            arr[cy, cx] = (*cap_col, 255)
    elif prop_type == "log":
        # Mossy fallen autumn trunk
        for y in range(8, 14):
            for x in range(2, 14):
                if y in (8, 13) or x in (2, 13):
                    arr[y, x] = (*DEEP_VOID, 255)
                elif x == 3:
                    arr[y, x] = (*OCHRE_CLAY, 255)
                elif y == 9 and (x % 3 == 0):
                    arr[y, x] = (*BURNT_AMBER, 255)
                else:
                    arr[y, x] = (*WITHERED_BARK, 255)
    else:  # stone
        # Ancient mossy runic stone
        for y in range(5, 15):
            for x in range(3, 13):
                d = ((x - 7.5) / 4.8) ** 2 + ((y - 10.0) / 4.8) ** 2
                if d <= 1.0:
                    if d > 0.72 or y == 14:
                        arr[y, x] = (*DEEP_VOID, 255)
                    elif y < 8:
                        arr[y, x] = (*AUTUMN_MIST, 255)
                    elif x == 7 and 8 <= y <= 11:
                        arr[y, x] = (*HARVEST_GOLD, 255)  # Glowing autumn rune
                    else:
                        arr[y, x] = (*SLATE_FOG, 255)

    return arr


def _build_player_frame(frame_idx: int) -> np.ndarray:
    """
    Renders a 16x16 pixel-art frame of the Autumn Keeper:
    - Pointed ranger hood in Crimson Decay & Burnt Amber
    - Flowing Harvest Gold scarf
    - Glowing Sunlit Birch lantern held forward
    """
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    bob = 1 if (frame_idx % 2 == 1) else 0

    # Ground shadow
    for x in range(5, 11):
        arr[15, x] = (*DEEP_VOID, 180)

    # Boots (walk cycle alternation)
    left_y = 14 - (1 if frame_idx == 1 else 0)
    right_y = 14 - (1 if frame_idx == 2 else 0)
    arr[left_y, 6] = (*DEEP_VOID, 255)
    arr[left_y, 7] = (*WITHERED_BARK, 255)
    arr[right_y, 9] = (*WITHERED_BARK, 255)
    arr[right_y, 10] = (*DEEP_VOID, 255)

    # Cloak body (y=7..13, x=4..11)
    for y in range(7 + bob, 14):
        half_w = 3 if y < 10 else 4
        for x in range(8 - half_w, 8 + half_w):
            if x == 8 - half_w or x == 8 + half_w - 1 or y == 13:
                arr[y, x] = (*DEEP_VOID, 255)
            elif y == 8 + bob:
                arr[y, x] = (*HARVEST_GOLD, 255)  # Golden scarf
            elif x < 8:
                arr[y, x] = (*BURNT_AMBER, 255)
            else:
                arr[y, x] = (*CRIMSON_DECAY, 255)

    # Hood & Head (y=2..7, x=5..11)
    for y in range(2 + bob, 8 + bob):
        for x in range(5, 11):
            if y == 2 + bob and x not in (7, 8):
                continue
            if x in (5, 10) or y == 2 + bob:
                arr[y, x] = (*DEEP_VOID, 255)
            elif 5 + bob <= y <= 6 + bob and 6 <= x <= 9:
                # Shadowed face with glowing eyes
                if x in (7, 9) and y == 5 + bob:
                    arr[y, x] = (*SUNLIT_BIRCH, 255)
                else:
                    arr[y, x] = (*DEEP_VOID, 255)
            else:
                hood_col = CRIMSON_DECAY if x >= 8 else RUST_TERRACOTTA
                arr[y, x] = (*hood_col, 255)

    # Sunlit Lantern on right hand (x=11..14, y=8..12)
    ly = 8 + bob
    arr[ly, 12] = (*DEEP_VOID, 255)
    arr[ly + 1, 11] = (*DEEP_VOID, 255)
    arr[ly + 1, 12] = (*PALE_SUNBEAM, 255)
    arr[ly + 1, 13] = (*SUNLIT_BIRCH, 255)
    arr[ly + 1, 14] = (*DEEP_VOID, 255)
    arr[ly + 2, 11] = (*DEEP_VOID, 255)
    arr[ly + 2, 12] = (*SUNLIT_BIRCH, 255)
    arr[ly + 2, 13] = (*HARVEST_GOLD, 255)
    arr[ly + 2, 14] = (*DEEP_VOID, 255)
    arr[ly + 3, 12] = (*DEEP_VOID, 255)
    arr[ly + 3, 13] = (*DEEP_VOID, 255)

    return arr


def _build_entity_sprite(kind: str, frame: int = 0) -> np.ndarray:
    """Renders 16x16 sprites for enemies (`wisp`, `stalker`, `golem`) and collectibles (`relic`, `acorn`)."""
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    bob = 1 if frame % 2 == 1 else 0

    if kind == "relic":
        # Floating Sunlit Harvest Relic (diamond crystal sigil)
        cx, cy = 8, 7 + bob
        for y in range(2, 14):
            for x in range(3, 14):
                md = abs(x - cx) + abs(y - cy)
                if md == 5:
                    arr[y, x] = (*DEEP_VOID, 255)
                elif md == 4:
                    arr[y, x] = (*BURNT_AMBER, 255)
                elif md == 3:
                    arr[y, x] = (*HARVEST_GOLD, 255)
                elif md == 2:
                    arr[y, x] = (*SUNLIT_BIRCH, 255)
                elif md <= 1:
                    arr[y, x] = (*PALE_SUNBEAM, 255)
    elif kind == "acorn":
        cx, cy = 8, 8 + bob
        _draw_circle_px(arr, cx, cy + 1, 4, HARVEST_GOLD)
        # Withered bark cap
        for y in range(cy - 3, cy):
            for x in range(cx - 4, cx + 5):
                if abs(x - cx) <= 4:
                    cap_c = DEEP_VOID if y == cy - 3 or abs(x - cx) == 4 else WITHERED_BARK
                    arr[y, x] = (*cap_c, 255)
        arr[cy - 4, cx] = (*DEEP_VOID, 255)
    elif kind == "wisp":
        # Floating Crimson/Mist Spore Wisp
        cx, cy = 8, 8 + bob
        _draw_circle_px(arr, cx, cy, 5, CRIMSON_DECAY)
        _draw_circle_px(arr, cx, cy, 3, AUTUMN_MIST)
        arr[cy, cx - 1] = (*DEEP_VOID, 255)
        arr[cy, cx + 1] = (*DEEP_VOID, 255)
        arr[cy - 4, cx] = (*SUNLIT_BIRCH, 255)
    elif kind == "stalker":
        # Thorny Bramble Stalker
        cx, cy = 8, 8 + bob
        _draw_circle_px(arr, cx, cy, 6, WITHERED_BARK)
        _draw_circle_px(arr, cx, cy, 4, MULBERRY_DUSK)
        # Glowing amber eyes
        arr[cy - 1, cx - 2] = (*SUNLIT_BIRCH, 255)
        arr[cy - 1, cx + 2] = (*SUNLIT_BIRCH, 255)
        # Crimson thorns
        for tx, ty in ((2, 5), (13, 5), (3, 12), (12, 12), (8, 2)):
            arr[ty, tx] = (*BURNT_AMBER, 255)
    elif kind == "warden":
        # Elder Stag Warden (Crowned Shrine Guardian with Golden Antlers)
        for y in range(4 + bob, 15):
            for x in range(3, 13):
                if y in (4 + bob, 14) or x in (3, 12):
                    arr[y, x] = (*DEEP_VOID, 255)
                elif y == 6 + bob and x in (5, 10):
                    arr[y, x] = (*PALE_SUNBEAM, 255)
                elif 8 + bob <= y <= 11 + bob and 6 <= x <= 9:
                    arr[y, x] = (*HARVEST_GOLD, 255)
                else:
                    w_col = CRIMSON_DECAY if (x + y) % 2 == 0 else WITHERED_BARK
                    arr[y, x] = (*w_col, 255)
        # Golden Stag Antlers
        for ax, ay in ((4, 1), (3, 2), (5, 2), (6, 3), (11, 1), (12, 2), (10, 2), (9, 3)):
            py = min(15, ay + bob)
            arr[py, ax] = (*SUNLIT_BIRCH, 255)
    else:  # golem
        # Heavy Hollow Bark Golem
        for y in range(2 + bob, 15):
            for x in range(2, 14):
                if y in (2 + bob, 14) or x in (2, 13):
                    arr[y, x] = (*DEEP_VOID, 255)
                elif 5 + bob <= y <= 7 + bob and x in (5, 6, 9, 10):
                    arr[y, x] = (*HARVEST_GOLD, 255)
                elif 9 + bob <= y <= 11 + bob and 6 <= x <= 9:
                    arr[y, x] = (*BURNT_AMBER, 255)  # Ember core
                else:
                    bark_c = WITHERED_BARK if (x + y) % 2 == 0 else PLUM_SHADOW
                    arr[y, x] = (*bark_c, 255)

    return arr


def _build_campfire_sprite(frame: int = 0) -> np.ndarray:
    """Renders a 16x16 flickering Alchemist Campfire with charred logs and golden flames."""
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    # Stone ring & crossed logs
    _draw_circle_px(arr, 8, 11, 5, WITHERED_BARK)
    for x in range(4, 13):
        arr[12, x] = (*DEEP_VOID, 255)
        arr[11, x] = (*OCHRE_CLAY, 255)
    # Flickering flame pyramid
    flame_top = 3 + (frame % 2)
    for y in range(flame_top, 12):
        half_w = max(1, (y - flame_top + 1) // 2)
        for x in range(8 - half_w, 8 + half_w + 1):
            if y <= flame_top + 1:
                col = SUNLIT_BIRCH
            elif abs(x - 8) <= 1 and y >= 8:
                col = PALE_SUNBEAM
            elif abs(x - 8) == half_w:
                col = CRIMSON_DECAY
            else:
                col = HARVEST_GOLD if (x + y + frame) % 2 == 0 else BURNT_AMBER
            arr[y, x] = (*col, 255)
    return arr


def _build_boardwalk_sprite() -> np.ndarray:
    """Renders a 16x16 rustic wooden boardwalk plank tile."""
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    for y in range(2, 14):
        for x in range(1, 15):
            if y in (2, 5, 6, 9, 10, 13) or x in (1, 14):
                arr[y, x] = (*DEEP_VOID, 255)
            elif x in (3, 12) and y in (3, 7, 11):
                arr[y, x] = (*SLATE_FOG, 255)  # Iron nail head
            else:
                plank_c = OCHRE_CLAY if ((x + y) % 3 != 0) else WITHERED_BARK
                arr[y, x] = (*plank_c, 255)
    return arr


def _build_bilim_agaci_sprite() -> np.ndarray:
    """
    Renders the iconic 32x32 ODTÜ Bilim Ağacı (Tree of Science Monument, 1966)
    in 16-bit Sonbahar pixel art with brutalist stone fins and golden torch embers.
    """
    arr = np.zeros((32, 32, 4), dtype=np.uint8)
    # Circular red-white/crimson-gold ODTÜ pedestal base
    _draw_circle_px(arr, 16, 26, 8, CRIMSON_DECAY)
    _draw_circle_px(arr, 16, 26, 6, AUTUMN_MIST)
    _draw_circle_px(arr, 16, 26, 4, WITHERED_BARK)

    # Central brutalist trunk flaring upward into dynamic fins
    for y in range(6, 26):
        t = (26 - y) / 20.0
        half_w = int(round(2.0 + (t * t) * 7.5))
        for x in range(16 - half_w, 16 + half_w + 1):
            offset = abs(x - 16)
            # Carve vertical dynamic brutalist ribs/fins
            if y < 16 and offset in (2, 5):
                continue
            if offset == half_w or y == 6:
                arr[y, x] = (*DEEP_VOID, 255)
            elif y <= 9 and offset % 2 == 0:
                arr[y, x] = (*SUNLIT_BIRCH, 255)  # Torch of Science golden crown
            elif x < 16:
                fin_l = AUTUMN_MIST if offset % 2 == 0 else SLATE_FOG
                arr[y, x] = (*fin_l, 255)
            else:
                fin_r = SLATE_FOG if offset % 2 == 0 else WITHERED_BARK
                arr[y, x] = (*fin_r, 255)

    # Glowing ODTÜ emblem spark at heart of monument
    arr[15, 16] = (*PALE_SUNBEAM, 255)
    arr[16, 16] = (*CRIMSON_DECAY, 255)
    return arr


def _build_kitabe_sprite() -> np.ndarray:
    """
    Renders a 16x24 Ancient ODTÜ Historical Inscription Stele (Tarih Kitabesi)
    with slate stone pedestal, engraved glowing runes, and golden autumn ivy.
    """
    arr = np.zeros((24, 16, 4), dtype=np.uint8)
    # Slate pedestal base
    for x in range(2, 14):
        arr[22, x] = (*DEEP_VOID, 255)
        arr[21, x] = (*WITHERED_BARK, 255)
        arr[20, x] = (*SLATE_FOG, 255)
    # Arched stone tablet body
    for y in range(4, 20):
        arch_cut = 2 if y <= 5 else (1 if y <= 6 else 0)
        for x in range(3 + arch_cut, 13 - arch_cut):
            if y == 4 or x in (3 + arch_cut, 12 - arch_cut):
                arr[y, x] = (*DEEP_VOID, 255)
            elif (y in (8, 11, 14, 17)) and (5 <= x <= 10):
                # Glowing engraved golden inscription line
                rune_c = HARVEST_GOLD if (x + y) % 2 == 0 else PALE_SUNBEAM
                arr[y, x] = (*rune_c, 255)
            else:
                c = SLATE_FOG if (x + y) % 2 == 0 else AUTUMN_MIST
                arr[y, x] = (*c, 255)
    # Autumn golden ivy leaf accents
    arr[18, 4] = (*SUNLIT_BIRCH, 255)
    arr[19, 5] = (*RUST_TERRACOTTA, 255)
    arr[17, 11] = (*HARVEST_GOLD, 255)
    return arr


def _build_shrine_sprite(awakened: bool = False) -> np.ndarray:
    """Renders the 32x32 Ancient Autumn Shrine (dormant or awakened with golden fire)."""
    arr = np.zeros((32, 32, 4), dtype=np.uint8)
    # Stone dais ring
    _draw_circle_px(arr, 16, 20, 11, SLATE_FOG)
    _draw_circle_px(arr, 16, 20, 9, WITHERED_BARK)
    _draw_circle_px(arr, 16, 20, 7, PLUM_SHADOW)

    # Obelisk pillars
    for px in (9, 21):
        for y in range(7, 23):
            for x in range(px, px + 3):
                if x == px or x == px + 2 or y == 7:
                    arr[y, x] = (*DEEP_VOID, 255)
                else:
                    pil_c = AUTUMN_MIST if y < 14 else SLATE_FOG
                    arr[y, x] = (*pil_c, 255)

    # Central Harvest Flame / Sigil
    core_col = PALE_SUNBEAM if awakened else CRIMSON_DECAY
    mid_col = SUNLIT_BIRCH if awakened else RUST_TERRACOTTA
    outer_col = HARVEST_GOLD if awakened else WITHERED_BARK
    _draw_circle_px(arr, 16, 16, 5, outer_col)
    _draw_circle_px(arr, 16, 16, 3, mid_col)
    _draw_circle_px(arr, 16, 16, 2, core_col)
    return arr


def _ndarray_to_surface(arr: np.ndarray) -> pygame.Surface:
    """Converts an (H, W, 4) RGBA uint8 numpy array into a per-pixel alpha Pygame Surface."""
    h, w, _ = arr.shape
    surf = pygame.image.frombuffer(arr.tobytes(), (w, h), "RGBA")
    return surf.convert_alpha() if pygame.display.get_init() and pygame.display.get_surface() else surf.copy()


class AssetBank:
    """
    Holds all pixel-art surfaces and ensures all files in `assets/` are generated on disk.
    """

    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = assets_dir
        _write_palette_and_shaders(assets_dir)

        sprites_dir = assets_dir / "sprites"
        sprites_dir.mkdir(parents=True, exist_ok=True)

        # 1. Build 47-Tile Blob Autotile sheet (47 tiles * 16x16)
        self.blob_47_surfaces: List[pygame.Surface] = []
        sheet_47 = np.zeros((16, 47 * 16, 4), dtype=np.uint8)
        for idx, mask in enumerate(CANONICAL_47_MASKS):
            tile_arr = _render_single_blob_tile(mask, idx)
            sheet_47[:, idx * 16 : (idx + 1) * 16] = tile_arr
            self.blob_47_surfaces.append(_ndarray_to_surface(tile_arr))
        Image.fromarray(sheet_47, mode="RGBA").save(sprites_dir / "autotile_47.png")

        # 2. Build Biome Floor Tiles (3 biomes * 4 variants)
        floor_arrays = _build_floor_tiles()
        self.floor_surfaces: Dict[int, List[pygame.Surface]] = {
            1: [_ndarray_to_surface(a) for a in floor_arrays[0:4]],
            2: [_ndarray_to_surface(a) for a in floor_arrays[4:8]],
            3: [_ndarray_to_surface(a) for a in floor_arrays[8:12]],
        }

        # 3. Build Foliage & Ecological Props sheet
        self.prop_surfaces: Dict[Tuple[str, int], pygame.Surface] = {}
        foliage_sheet = np.zeros((64, 32 * 9, 4), dtype=np.uint8)
        col_cursor = 0
        for tkind in ("tree_maple", "tree_birch", "tree_oak"):
            for var in range(3):
                t_arr = _build_tree_sprite(tkind, var)
                self.prop_surfaces[(tkind, var)] = _ndarray_to_surface(t_arr)
                foliage_sheet[0:32, col_cursor * 32 : (col_cursor + 1) * 32] = t_arr
                col_cursor += 1

        small_cursor = 0
        for pkind in ("leaf_pile", "bush_amber", "mushroom", "log", "stone"):
            for var in range(3):
                p_arr = _build_small_prop_sprite(pkind, var)
                self.prop_surfaces[(pkind, var)] = _ndarray_to_surface(p_arr)
                x0 = small_cursor * 16
                foliage_sheet[32:48, x0 : x0 + 16] = p_arr
                small_cursor += 1
        Image.fromarray(foliage_sheet, mode="RGBA").save(sprites_dir / "foliage_sheet.png")

        # 4. Build Player Sprite Sheet (3 animation frames + flipped variants)
        self.player_frames_right: List[pygame.Surface] = []
        self.player_frames_left: List[pygame.Surface] = []
        player_sheet = np.zeros((16, 16 * 3, 4), dtype=np.uint8)
        for f in range(3):
            p_arr = _build_player_frame(f)
            player_sheet[:, f * 16 : (f + 1) * 16] = p_arr
            surf_r = _ndarray_to_surface(p_arr)
            surf_l = pygame.transform.flip(surf_r, True, False)
            self.player_frames_right.append(surf_r)
            self.player_frames_left.append(surf_l)
        Image.fromarray(player_sheet, mode="RGBA").save(sprites_dir / "player_sheet.png")

        # 5. Build Entities, Structures & Shrine Sheet
        self.entity_surfaces: Dict[Tuple[str, int], pygame.Surface] = {}
        entities_sheet = np.zeros((32, 16 * 14, 4), dtype=np.uint8)
        ec = 0
        for ekind in ("relic", "acorn", "wisp", "stalker", "golem", "warden"):
            for f in range(2):
                e_arr = _build_entity_sprite(ekind, f)
                self.entity_surfaces[(ekind, f)] = _ndarray_to_surface(e_arr)
                entities_sheet[0:16, ec * 16 : (ec + 1) * 16] = e_arr
                ec += 1

        self.campfire_frames = [
            _ndarray_to_surface(_build_campfire_sprite(0)),
            _ndarray_to_surface(_build_campfire_sprite(1)),
        ]
        self.boardwalk_surf = _ndarray_to_surface(_build_boardwalk_sprite())
        self.bilim_agaci_surf = _ndarray_to_surface(_build_bilim_agaci_sprite())
        self.kitabe_surf = _ndarray_to_surface(_build_kitabe_sprite())

        shrine_dormant = _build_shrine_sprite(False)
        shrine_awake = _build_shrine_sprite(True)
        self.shrine_dormant_surf = _ndarray_to_surface(shrine_dormant)
        self.shrine_awake_surf = _ndarray_to_surface(shrine_awake)
        Image.fromarray(entities_sheet, mode="RGBA").save(sprites_dir / "entities_sheet.png")
