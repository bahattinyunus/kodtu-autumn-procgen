"""
Unit Tests for KODTÜ: Autumn ProcGen Engine.

Verifies:
1. 64-Bit Seed Determinism (Xoshiro256**, Mulberry32, SplitMix64)
2. Multi-Octave Simplex fBm Synthesis Bounds & Variance
3. B678/S345678 Cellular Automata & BFS Flood-Fill 100% Single-Component Connectivity
4. 47-Tile Blob Bitmasking Canonical Reduction (256 -> 47 states)
5. Bridson's Fast Poisson Disk Sampling Minimum Exclusion Distance Invariant
6. Dijkstra Geodesic Distance Field & Threat Budgeting
7. Sonbahar 16-Color LUT Compliance
"""

from __future__ import annotations
import math
from pathlib import Path
import sys
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.palette import AUTUMN_16_HEX, AUTUMN_16_PALETTE, quantize_rgb
from src.procgen.prng import Xoshiro256StarStar, seed_to_uint64, format_seed_code
from src.procgen.noise import SimplexNoise2D
from src.procgen.automata import find_connected_clearings
from src.procgen.autotile import CANONICAL_47_MASKS, sanitize_blob_mask, compute_47_blob_grid
from src.procgen.poisson import fast_poisson_disk_sampling
from src.procgen.pipeline import generate_autumn_world


def test_seed_serialization_and_xoshiro256_determinism() -> None:
    """Identical seed strings must produce identical 64-bit hashes and PRNG streams."""
    u1 = seed_to_uint64("KODTU2026")
    u2 = seed_to_uint64("KODTU2026")
    u3 = seed_to_uint64("KODTU-8492-FALL")
    assert u1 == u2
    assert u1 != u3
    assert 0 <= u1 <= 0xFFFFFFFFFFFFFFFF

    rng_a = Xoshiro256StarStar("KODTU2026")
    rng_b = Xoshiro256StarStar("KODTU2026")
    seq_a = [rng_a.next_uint64() for _ in range(50)]
    seq_b = [rng_b.next_uint64() for _ in range(50)]
    assert seq_a == seq_b
    assert format_seed_code(u1).startswith("KODTU-")


def test_multi_octave_simplex_fbm_bounds() -> None:
    """fBm noise grids must be deterministic, bounded in [0.0, 1.0], and exhibit spatial variance."""
    n1 = SimplexNoise2D("KODTU2026")
    n2 = SimplexNoise2D("KODTU2026")
    grid_a = n1.fbm_grid(40, 30, octaves=4, persistence=0.5, lacunarity=2.0)
    grid_b = n2.fbm_grid(40, 30, octaves=4, persistence=0.5, lacunarity=2.0)

    assert np.array_equal(grid_a, grid_b)
    assert float(grid_a.min()) >= 0.0
    assert float(grid_a.max()) <= 1.0
    assert float(grid_a.std()) > 0.04


@pytest.mark.parametrize(
    "seed_str",
    ["KODTU2026", "KODTU-8492-FALL", "AUTUMN-JAM-01", "SONBAHAR-1923", "PIXEL-FOREST"],
)
def test_topology_single_component_connectivity_and_dijkstra(seed_str: str) -> None:
    """
    Every generated world must have 100% single-component connectivity of walkable tiles
    (zero unreachable orphan pockets) and a continuous shortest path from Spawn to Shrine.
    """
    world = generate_autumn_world(seed=seed_str, width=48, height=36)
    components = find_connected_clearings(world.walkable_grid)
    assert len(components) == 1, f"Seed {seed_str} produced {len(components)} disconnected clearings!"

    # Every walkable cell (0) must be reachable by Dijkstra BFS (dijkstra_dist >= 0)
    walkable_mask = world.walkable_grid == 0
    unreachable = np.sum(walkable_mask & (world.dijkstra_dist < 0))
    assert unreachable == 0, f"Found {unreachable} unreachable walkable tiles in {seed_str}"

    # Verify shortest path continuity between spawn_tile and shrine_tile
    assert world.shortest_path[0] == world.spawn_tile
    assert world.shortest_path[-1] == world.shrine_tile
    for (x0, y0), (x1, y1) in zip(world.shortest_path[:-1], world.shortest_path[1:]):
        assert abs(x1 - x0) + abs(y1 - y0) == 1
        assert world.walkable_grid[y1, x1] == 0


def test_47_tile_blob_autotiling_lut() -> None:
    """8-neighbor corner-masked bitmasks must collapse 256 states into exactly 47 canonical states."""
    assert len(CANONICAL_47_MASKS) == 47
    unique_sanitized = {sanitize_blob_mask(m) for m in range(256)}
    assert len(unique_sanitized) == 47

    dummy_grid = np.zeros((16, 16), dtype=np.int32)
    dummy_grid[4:12, 4:12] = 1
    masks, blob_indices = compute_47_blob_grid(dummy_grid, target_value=1)
    assert int(blob_indices.min()) >= 0
    assert int(blob_indices.max()) < 47


def test_poisson_disk_sampling_exclusion_zone() -> None:
    """Bridson's Fast Poisson Disk Sampling must strictly enforce ||p_i - p_j|| >= min_dist."""
    prng = Xoshiro256StarStar("POISSON-TEST-2026")
    min_r = 2.8
    pts = fast_poisson_disk_sampling(50.0, 40.0, min_dist=min_r, prng=prng, margin=2.5)
    assert len(pts) > 25

    for i in range(len(pts)):
        x0, y0 = pts[i]
        for j in range(i + 1, len(pts)):
            x1, y1 = pts[j]
            dist = math.hypot(x1 - x0, y1 - y0)
            assert dist >= min_r - 1e-6, f"Poisson violation: {dist:.4f} < {min_r}"


def test_full_world_pipeline_determinism() -> None:
    """Two runs of generate_autumn_world with the same seed must match bit-for-bit."""
    w1 = generate_autumn_world(seed="KODTU2026", width=48, height=36)
    w2 = generate_autumn_world(seed="KODTU2026", width=48, height=36)
    w3 = generate_autumn_world(seed="DIFFERENT_SEED", width=48, height=36)

    assert w1.seed_uint64 == w2.seed_uint64
    assert np.array_equal(w1.elevation, w2.elevation)
    assert np.array_equal(w1.moisture, w2.moisture)
    assert np.array_equal(w1.walkable_grid, w2.walkable_grid)
    assert np.array_equal(w1.wall_blob_47, w2.wall_blob_47)
    assert w1.props == w2.props
    assert w1.spawns == w2.spawns
    assert not np.array_equal(w1.elevation, w3.elevation)


def test_autumn_chromatic_palette_compliance() -> None:
    """All 8 primary Sonbahar hex colors from Section 4 of README.md must exist in the 16-color LUT."""
    required_hex = {
        "1A1118",  # Deep Void / Shadow
        "3B2123",  # Withered Bark
        "6B2D26",  # Crimson Decay
        "9E472A",  # Rust / Terracotta
        "C86D2B",  # Burnt Amber
        "E09F3E",  # Harvest Gold
        "F5D67B",  # Sunlit Birch
        "D4C8BE",  # Autumn Mist
    }
    assert len(AUTUMN_16_PALETTE) == 16
    assert required_hex.issubset(set(AUTUMN_16_HEX))
    assert quantize_rgb((25, 18, 25)) == (26, 17, 24)


def test_headless_engine_and_debug_overlays() -> None:
    """Verifies full game loop, asset generation, and [F1]-[F4] debug overlays headlessly."""
    from src.main import AutumnProcGenGame
    from src.rendering.renderer import (
        DEBUG_NONE,
        DEBUG_NOISE_BIOME,
        DEBUG_BITMASK_GRID,
        DEBUG_PATHFINDING,
    )

    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=True, headless=True)
    initial_seed_u64 = game.world.seed_uint64

    # Cycle through all debug overlays and actions
    for mode in (DEBUG_NONE, DEBUG_NOISE_BIOME, DEBUG_BITMASK_GRID, DEBUG_PATHFINDING):
        game.debug_mode = mode
        game.update(1.0 / 60.0)
        game.render()

    # Test Solar Ember attack, Gust Dash, and Instant Re-Seed ([F3])
    game._perform_ember_attack()
    game._perform_gust_dash()
    game.instant_reseed()
    assert game.world.seed_uint64 != initial_seed_u64

    game.update(1.0 / 60.0)
    game.render()

    # Verify generated assets on disk
    assert (REPO_ROOT / "assets" / "palettes" / "autumn_16.hex").exists()
    assert (REPO_ROOT / "assets" / "palettes" / "autumn_lut.png").exists()
    assert (REPO_ROOT / "assets" / "sprites" / "autotile_47.png").exists()
    assert (REPO_ROOT / "assets" / "sprites" / "foliage_sheet.png").exists()
    assert (REPO_ROOT / "assets" / "sprites" / "player_sheet.png").exists()
    assert (REPO_ROOT / "assets" / "sprites" / "entities_sheet.png").exists()
    assert (REPO_ROOT / "assets" / "shaders" / "palette_quantize.glsl").exists()
    assert (REPO_ROOT / "assets" / "shaders" / "wind_sway.glsl").exists()
    assert (REPO_ROOT / "assets" / "audio" / "leaf_crunch_1.wav").exists()

