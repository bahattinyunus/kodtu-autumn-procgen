"""
Core Engine Package (Palette, Camera, Spatial Hash, Audio & Asset Builder).
"""

from src.core.palette import (
    AUTUMN_16_PALETTE,
    AUTUMN_16_HEX,
    DEEP_VOID,
    WITHERED_BARK,
    CRIMSON_DECAY,
    RUST_TERRACOTTA,
    BURNT_AMBER,
    HARVEST_GOLD,
    SUNLIT_BIRCH,
    AUTUMN_MIST,
    quantize_rgb,
    hue_shift_toward_light,
    hue_shift_toward_shadow,
)
from src.core.camera import PixelCamera, NATIVE_WIDTH, NATIVE_HEIGHT, TILE_SIZE
from src.core.spatial_hash import ChunkSpatialHash

__all__ = [
    "AUTUMN_16_PALETTE",
    "AUTUMN_16_HEX",
    "DEEP_VOID",
    "WITHERED_BARK",
    "CRIMSON_DECAY",
    "RUST_TERRACOTTA",
    "BURNT_AMBER",
    "HARVEST_GOLD",
    "SUNLIT_BIRCH",
    "AUTUMN_MIST",
    "quantize_rgb",
    "hue_shift_toward_light",
    "hue_shift_toward_shadow",
    "PixelCamera",
    "NATIVE_WIDTH",
    "NATIVE_HEIGHT",
    "TILE_SIZE",
    "ChunkSpatialHash",
]
