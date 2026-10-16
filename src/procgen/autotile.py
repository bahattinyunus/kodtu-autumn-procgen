"""
47-Tile Blob Bitmasking & 4-Directional Autotiling Engine.

Bit layout (Section 3.3 of README.md):
    [NW: 1]  [N: 2]   [NE: 4]
    [W: 8]   [TILE]   [E: 16]
    [SW: 32] [S: 64]  [SE: 128]

Diagonal bits (NW, NE, SW, SE) are masked out unless both adjacent cardinal bits
are present, collapsing the 256 possible 8-bit states into exactly 47 unique
blob tile indices (0..46).
"""

from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np

BIT_NW = 1
BIT_N = 2
BIT_NE = 4
BIT_W = 8
BIT_E = 16
BIT_SW = 32
BIT_S = 64
BIT_SE = 128


def sanitize_blob_mask(raw_mask: int) -> int:
    """
    Eliminates redundant corner bits when either adjacent cardinal neighbor is missing.
    Reduces 256 raw 8-bit states to exactly 47 canonical states.
    """
    mask = raw_mask & 0xFF
    if not ((mask & BIT_N) and (mask & BIT_W)):
        mask &= ~BIT_NW
    if not ((mask & BIT_N) and (mask & BIT_E)):
        mask &= ~BIT_NE
    if not ((mask & BIT_S) and (mask & BIT_W)):
        mask &= ~BIT_SW
    if not ((mask & BIT_S) and (mask & BIT_E)):
        mask &= ~BIT_SE
    return mask


def _build_47_lookup_tables() -> Tuple[List[int], Dict[int, int], np.ndarray]:
    canonical_set = sorted({sanitize_blob_mask(m) for m in range(256)})
    assert len(canonical_set) == 47, f"Expected 47 canonical blob masks, got {len(canonical_set)}"
    mask_to_idx = {m: idx for idx, m in enumerate(canonical_set)}
    lut_array = np.array([mask_to_idx[sanitize_blob_mask(m)] for m in range(256)], dtype=np.int32)
    return canonical_set, mask_to_idx, lut_array


CANONICAL_47_MASKS, MASK_TO_47_INDEX, RAW_TO_47_LUT = _build_47_lookup_tables()


def compute_raw_8bit_mask_grid(binary_grid: np.ndarray, target_value: int = 1) -> np.ndarray:
    """
    Computes the raw 8-bit neighbor bitmask (0..255) for every cell in `binary_grid`
    matching `target_value`. Out-of-bounds neighbors are treated as matching `target_value`.
    """
    height, width = binary_grid.shape
    match = (binary_grid == target_value).astype(np.int32)
    padded = np.pad(match, pad_width=1, mode="constant", constant_values=1)

    nw = padded[0:height, 0:width] * BIT_NW
    n = padded[0:height, 1 : width + 1] * BIT_N
    ne = padded[0:height, 2 : width + 2] * BIT_NE
    w = padded[1 : height + 1, 0:width] * BIT_W
    e = padded[1 : height + 1, 2 : width + 2] * BIT_E
    sw = padded[2 : height + 2, 0:width] * BIT_SW
    s = padded[2 : height + 2, 1 : width + 1] * BIT_S
    se = padded[2 : height + 2, 2 : width + 2] * BIT_SE

    return (nw | n | ne | w | e | sw | s | se).astype(np.int32)


def compute_47_blob_grid(binary_grid: np.ndarray, target_value: int = 1) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes both the sanitized 8-bit mask grid and the 47-Tile Blob index grid (0..46)
    for all cells in `binary_grid`.
    """
    raw_masks = compute_raw_8bit_mask_grid(binary_grid, target_value=target_value)
    blob_indices = RAW_TO_47_LUT[raw_masks]
    sanitized_masks = np.array(CANONICAL_47_MASKS, dtype=np.int32)[blob_indices]
    return sanitized_masks, blob_indices


def compute_4dir_mask_grid(binary_grid: np.ndarray, target_value: int = 1) -> np.ndarray:
    """
    Computes the 4-directional cardinal bitmask (0..15: N=1, E=2, S=4, W=8)
    for secondary terrain transitions (such as leaf piles and damp mud edges).
    """
    height, width = binary_grid.shape
    match = (binary_grid == target_value).astype(np.int32)
    padded = np.pad(match, pad_width=1, mode="edge")

    n = padded[0:height, 1 : width + 1] * 1
    e = padded[1 : height + 1, 2 : width + 2] * 2
    s = padded[2 : height + 2, 1 : width + 1] * 4
    w = padded[1 : height + 1, 0:width] * 8
    return (n | e | s | w).astype(np.int32)
