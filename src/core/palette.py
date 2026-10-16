"""
Sonbahar Chromatic Spectrum (16-Color Autumn LUT & Hue-Shifting Engine).

Strictly adheres to Section 4 of README.md:
- Deep Void / Shadow : #1A1118 (26, 17, 24)
- Withered Bark      : #3B2123 (59, 33, 35)
- Crimson Decay      : #6B2D26 (107, 45, 38)
- Rust / Terracotta  : #9E472A (158, 71, 42)
- Burnt Amber        : #C86D2B (200, 109, 43)
- Harvest Gold       : #E09F3E (224, 159, 62)
- Sunlit Birch       : #F5D67B (245, 214, 123)
- Autumn Mist        : #D4C8BE (212, 200, 190)

Plus 8 Hue-Shifted ramp bridging tones to form the complete 16-Color Autumn LUT.
"""

from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]

# Core 8 Chromatic Anchors from README.md
DEEP_VOID: RGB = (26, 17, 24)         # #1A1118 - Outlines, deepest shadows, hollows
WITHERED_BARK: RGB = (59, 33, 35)     # #3B2123 - Old tree trunks, wet soil, dark stones
CRIMSON_DECAY: RGB = (107, 45, 38)    # #6B2D26 - Red maple leaves, hazard/damage indicators
RUST_TERRACOTTA: RGB = (158, 71, 42)  # #9E472A - Mid-tone dried leaf clusters, rusted ruins
BURNT_AMBER: RGB = (200, 109, 43)     # #C86D2B - Primary autumn foliage, warm ground transitions
HARVEST_GOLD: RGB = (224, 159, 62)    # #E09F3E - Sunlit leaf tips, interactive objects
SUNLIT_BIRCH: RGB = (245, 214, 123)   # #F5D67B - Sparkles, wind trails, UI highlight text
AUTUMN_MIST: RGB = (212, 200, 190)    # #D4C8BE - Morning fog, breath vapor, atmospheric depth

# 8 Hue-Shifted Intermediate Ramp Colors (completing the 16-Color LUT)
PLUM_SHADOW: RGB = (44, 24, 32)       # #2C1820 - Deep purple-indigo shadow transition
MULBERRY_DUSK: RGB = (78, 34, 42)     # #4E222A - Hue-shifted shadow bark/stone
DAMSON_MOSS: RGB = (92, 54, 44)       # #5C362C - Damp earth & decaying log mid-shadow
OCHRE_CLAY: RGB = (133, 68, 43)       # #85442B - Warm forest path transition
COPPER_LEAF: RGB = (181, 89, 42)      # #B5592A - Rich copper-orange canopy tone
MUSTARD_GLOW: RGB = (235, 184, 91)    # #EBB85B - Bright sunlit gold transition
PALE_SUNBEAM: RGB = (250, 235, 172)   # #FAEBAC - Specular birch highlight
SLATE_FOG: RGB = (140, 122, 120)      # #8C7A78 - Cool misty stone & distant haze

# Complete 16-Color Autumn LUT
AUTUMN_16_PALETTE: List[RGB] = [
    DEEP_VOID,        # 0:  #1A1118
    PLUM_SHADOW,      # 1:  #2C1820
    WITHERED_BARK,    # 2:  #3B2123
    MULBERRY_DUSK,    # 3:  #4E222A
    DAMSON_MOSS,      # 4:  #5C362C
    CRIMSON_DECAY,    # 5:  #6B2D26
    OCHRE_CLAY,       # 6:  #85442B
    RUST_TERRACOTTA,  # 7:  #9E472A
    COPPER_LEAF,      # 8:  #B5592A
    BURNT_AMBER,      # 9:  #C86D2B
    HARVEST_GOLD,     # 10: #E09F3E
    MUSTARD_GLOW,     # 11: #EBB85B
    SUNLIT_BIRCH,     # 12: #F5D67B
    PALE_SUNBEAM,     # 13: #FAEBAC
    SLATE_FOG,        # 14: #8C7A78
    AUTUMN_MIST,      # 15: #D4C8BE
]

AUTUMN_16_HEX: List[str] = [
    f"{r:02X}{g:02X}{b:02X}" for (r, g, b) in AUTUMN_16_PALETTE
]

NAMED_PALETTE: Dict[str, RGB] = {
    "deep_void": DEEP_VOID,
    "plum_shadow": PLUM_SHADOW,
    "withered_bark": WITHERED_BARK,
    "mulberry_dusk": MULBERRY_DUSK,
    "damson_moss": DAMSON_MOSS,
    "crimson_decay": CRIMSON_DECAY,
    "ochre_clay": OCHRE_CLAY,
    "rust_terracotta": RUST_TERRACOTTA,
    "copper_leaf": COPPER_LEAF,
    "burnt_amber": BURNT_AMBER,
    "harvest_gold": HARVEST_GOLD,
    "mustard_glow": MUSTARD_GLOW,
    "sunlit_birch": SUNLIT_BIRCH,
    "pale_sunbeam": PALE_SUNBEAM,
    "slate_fog": SLATE_FOG,
    "autumn_mist": AUTUMN_MIST,
}

_PALETTE_NP = np.array(AUTUMN_16_PALETTE, dtype=np.int32)


def hue_shift_toward_light(color: RGB, amount: float) -> RGB:
    """
    Hue-shifts `color` toward Sunlit Birch (#F5D67B) as it receives light,
    rather than desaturating toward plain white.
    """
    t = max(0.0, min(1.0, amount))
    r = int(round(color[0] + (SUNLIT_BIRCH[0] - color[0]) * t))
    g = int(round(color[1] + (SUNLIT_BIRCH[1] - color[1]) * t))
    b = int(round(color[2] + (SUNLIT_BIRCH[2] - color[2]) * t))
    return quantize_rgb((r, g, b))


def hue_shift_toward_shadow(color: RGB, amount: float) -> RGB:
    """
    Hue-shifts `color` toward Deep Void / Plum Shadow (#1A1118) as it enters shadow,
    rather than muddying into generic brown/black.
    """
    t = max(0.0, min(1.0, amount))
    r = int(round(color[0] + (DEEP_VOID[0] - color[0]) * t))
    g = int(round(color[1] + (DEEP_VOID[1] - color[1]) * t))
    b = int(round(color[2] + (DEEP_VOID[2] - color[2]) * t))
    return quantize_rgb((r, g, b))


def quantize_rgb(color: RGB) -> RGB:
    """
    Snaps any arbitrary (R, G, B) tuple to the nearest color in the 16-Color Autumn LUT.
    """
    r, g, b = color
    best_color = AUTUMN_16_PALETTE[0]
    best_dist = 10**9
    for pr, pg, pb in AUTUMN_16_PALETTE:
        # Perceptually weighted Euclidean distance in RGB space
        dr = r - pr
        dg = g - pg
        db = b - pb
        dist = 2 * dr * dr + 4 * dg * dg + 3 * db * db
        if dist < best_dist:
            best_dist = dist
            best_color = (pr, pg, pb)
    return best_color
