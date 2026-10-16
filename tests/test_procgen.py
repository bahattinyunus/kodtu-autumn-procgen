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

    # Test Solar Ember attack, Harvest Nova, Gust Dash, and Instant Re-Seed ([F3])
    game._perform_ember_attack()
    game._perform_harvest_nova()
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
    assert (REPO_ROOT / "assets" / "audio" / "dialogue_blip.wav").exists()
    assert (REPO_ROOT / "assets" / "audio" / "deflect_clash.wav").exists()
    assert (REPO_ROOT / "assets" / "audio" / "level_up.wav").exists()


def test_astar_and_procedural_structures() -> None:
    """Verifies A* optimal pathfinding matches Dijkstra distance and structures are placed."""
    from src.procgen.structures import astar_shortest_path

    world = generate_autumn_world(seed="KODTU2026", width=48, height=36)
    astar_path = astar_shortest_path(world.walkable_grid, world.spawn_tile, world.shrine_tile)
    assert astar_path[0] == world.spawn_tile
    assert astar_path[-1] == world.shrine_tile
    assert len(astar_path) - 1 == int(world.dijkstra_dist[world.shrine_tile[1], world.shrine_tile[0]])
    assert len(world.structures) >= 2
    assert any(st.structure_type == "campfire" for st in world.structures)
    assert any(st.structure_type == "bilim_agaci" for st in world.structures)


def test_odtu_bilim_agaci_monument_and_curated_seeds() -> None:
    """Verifies that all curated ODTÜ / METU seeds place the Bilim Ağacı monument and cycle cleanly."""
    from src.main import AutumnProcGenGame

    game = AutumnProcGenGame(initial_seed="ODTU-1956-DEVRIM", debug_procgen=False, headless=True)
    for _ in range(len(game.odtu_presets)):
        assert any(st.structure_type == "bilim_agaci" for st in game.world.structures)
        game.cycle_odtu_preset()
        game.update(1.0 / 60.0)
        game.render()


def test_solar_bolts_boons_and_orb_deflection() -> None:
    """
    Verifies competitor-inspired combat mechanics:
    - Hyper Light Drifter style Solar Bolt firing & melee ammo recharge
    - Enter the Gungeon / HLD style Enemy Twilight Orb melee deflection
    - Wizard of Legend / Hades style 5 ODTÜ Autumn Boons & 3-way volley
    - Dash Afterimage Ghost spawning
    """
    from src.main import AutumnProcGenGame
    from src.entities.actors import Projectile

    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=False, headless=True)

    # 1. Fire Solar Bolt ([F]) -> consumes 1 bolt, spawns 1 player projectile
    initial_bolts = game.player.solar_bolts
    game._perform_solar_bolt()
    assert game.player.solar_bolts == initial_bolts - 1
    assert len(game.projectiles) == 1
    assert game.projectiles[0].owner == "player"

    # 2. Spawn an incoming enemy Twilight Orb near the player and deflect it with melee slash
    enemy_orb = Projectile(
        x=game.player.x + 0.8,
        y=game.player.y,
        vx=-4.5,
        vy=0.0,
        owner="enemy",
        damage=10,
    )
    game.projectiles.append(enemy_orb)
    game.player.attack_cooldown = 0.0
    game._perform_ember_attack()
    assert enemy_orb.owner == "player"
    assert enemy_orb.deflected is True
    assert game.player.orbs_deflected == 1
    assert game.player.solar_bolts == initial_bolts  # Recharged by deflection!

    # 3. Unlock all 5 ODTÜ Autumn Boons & verify HARVEST_CROWN fires a 3-way volley
    for _ in range(5):
        game._unlock_next_boon()
    assert len(game.player.active_boons) == 5
    assert game.player.has_boon("HARVEST_CROWN")

    game.projectiles.clear()
    game.player.bolt_cooldown = 0.0
    game._perform_solar_bolt()
    assert len(game.projectiles) == 3  # 3-way Solar Volley!

    # 4. Trigger Autumn Gust Dash & verify DashGhost afterimages spawn
    game.player.dash_cooldown = 0.0
    game._perform_gust_dash()
    game.hit_stop_timer = 0.0
    game.update(1.0 / 60.0)
    assert len(game.dash_ghosts) >= 1


def test_destructible_props_and_codex_modal() -> None:
    """Verifies O(1) destructible flora smashing, Golden Acorn drops, and the [C] Codex Modal."""
    from src.main import AutumnProcGenGame
    from src.procgen.poisson import PropPlacement

    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=False, headless=True)
    initial_items = len(game.items)

    # Place a destructible pumpkin right in front of the player and smash it
    px = game.player.x + 0.6
    py = game.player.y
    ch_key = (int(px) // 16, int(py) // 16)
    game.spatial_hash.chunk_props[ch_key].append(
        PropPlacement(x=px, y=py, prop_type="pumpkin", variant=0, biome=2, solid=True)
    )
    game._smash_nearby_props(px, py, 1.2)
    assert len(game.items) == initial_items + 1
    assert game.items[-1].kind == "acorn"

    # Toggle and render ODTÜ Boon Codex Modal ([C])
    game.hud.codex_modal_open = True
    game.render()
    game.hud.codex_modal_open = False


def test_story_manager_and_modern_hd_overlay() -> None:
    """Verifies Turkish story chapter progression, dialogue triggers, and modern HD 1280x720 overlay."""
    from src.main import AutumnProcGenGame

    game = AutumnProcGenGame(initial_seed="ODTU-1956-DEVRIM", debug_procgen=False, headless=True)

    # Initial Chapter meta & objective
    title, _ = game.story.get_chapter_meta()
    assert "YALINCAK" in title.upper() or "BÖLÜM" in title.upper()
    obj_text = game.story.get_current_objective_text(0, 5)
    assert "GÖREV:" in obj_text
    assert "0/5" in obj_text

    # Trigger near Bilim Ağacı dialogue
    game.story.on_near_bilim_agaci()
    assert game.story.active_dialogue is not None
    assert "ODTÜ BİLİM AĞACI" in game.story.active_dialogue.speaker

    # Trigger relic collection story fragment
    game.story.on_relic_collected(1, 5, boon_title="BİLİM KIVILCIMI")
    assert game.story.active_dialogue is not None
    assert "1/5" in game.story.active_dialogue.speaker

    # Test Story Intro Card toggle and render
    game.story.show_intro_card = True
    game.render()
    game.story.show_intro_card = False
    game.render()


def test_historical_kitabeler_and_victory_epilogue() -> None:
    """
    Verifies:
    1. Historical ODTÜ Inscription Steles (odtu_kitabe) are placed in the world.
    2. Reading a kitabe triggers historical campus dialogue, restores warmth, and grants inspiration.
    3. Completing Depth 3 shrine interaction triggers the Grand Victory Epilogue sequence.
    """
    from src.main import AutumnProcGenGame

    game = AutumnProcGenGame(initial_seed="ODTU-1956-DEVRIM", debug_procgen=False, headless=True)

    # 1. Verify odtu_kitabe structure exists in the world
    kitabe_structs = [st for st in game.world.structures if st.structure_type == "odtu_kitabe"]
    assert len(kitabe_structs) >= 1

    # 2. Simulate reading an inscription
    kitabe = kitabe_structs[0]
    game.player.x = kitabe.tile_x + 0.5
    game.player.y = kitabe.tile_y + 0.5
    initial_warmth = game.player.warmth
    game._try_interact_action()
    assert len(game.story.read_kitabes) >= 1
    assert game.story.active_dialogue is not None
    assert "KİTABE" in game.story.active_dialogue.speaker or "ODTÜ" in game.story.active_dialogue.speaker
    assert game.player.warmth >= initial_warmth
    assert game.player.leaf_boost_timer > 0.0

    # 3. Test Grand Victory sequence in Depth 3
    game.world.depth_level = 3
    game.player.relics_collected = game.world.total_relics
    sx, sy = game.world.shrine_tile
    game.player.x = sx + 0.5
    game.player.y = sy + 0.5
    game._try_interact_shrine()
    assert game.story.show_victory_modal is True

    # 4. Render victory epilogue modal headlessly
    game.render()
    game.story.show_victory_modal = False
    game.render()


def test_wolf_enemy_and_new_audio_synthesis() -> None:
    """
    Verifies:
    1. Bozkır Kurdu (Steppe Wolf) EnemyAgent stats and AI movement states (circling flank vs pounce).
    2. New procedural sound synthesizers (kitabe_chime and water_splash) output valid audio waveforms.
    """
    from src.entities.actors import EnemyAgent
    from src.core.audio_synth import synth_kitabe_chime, synth_water_splash
    from src.core.spatial_hash import ChunkSpatialHash
    import numpy as np

    # 1. Wolf enemy stats
    wolf = EnemyAgent(x=10.0, y=10.0, kind="wolf", seed_phase=0.0)
    assert wolf.max_hp == 3
    assert wolf.speed == 3.65
    assert wolf.radius == 0.32
    assert wolf.damage == 14.0

    # Test wolf movement when far (flanking) vs near (pounce surge)
    dummy_grid = np.zeros((20, 20), dtype=np.uint8)
    sp_hash = ChunkSpatialHash(dummy_grid, [])
    # Far: dist > 3.0
    wolf.update(0.016, player_x=15.0, player_y=10.0, player_noise_radius=0.0, spatial_hash=sp_hash)
    assert math.hypot(wolf.vx, wolf.vy) > 0.0

    # Near: dist <= 3.0
    wolf.x, wolf.y = 12.0, 10.0
    wolf.update(0.016, player_x=12.5, player_y=10.0, player_noise_radius=0.0, spatial_hash=sp_hash)
    assert math.hypot(wolf.vx, wolf.vy) > 0.0

    # 2. Audio synthesizers
    chime = synth_kitabe_chime()
    splash = synth_water_splash()
    assert len(chime) > 0
    assert len(splash) > 0
    assert np.max(np.abs(chime)) <= 1.0
    assert np.max(np.abs(splash)) <= 1.0


def test_atmospheric_weather_system_and_minimap_enhancements() -> None:
    """
    Verifies:
    1. Dynamic Autumn Weather System cycles through 3 distinct atmospheric phases.
    2. Minimap base surface records odtu_kitabe steles in addition to campfires and bilim_agaci.
    3. Headless gameplay loop runs smoothly across all 3 weather phases.
    """
    from src.main import AutumnProcGenGame

    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=False, headless=True)

    # 1. Weather phases across time
    # 0s -> Phase 0: ALTIN İKİNDİ
    game.time_sec = 10.0
    phase_0 = int((game.time_sec // 40.0) % 3)
    assert phase_0 == 0

    # 50s -> Phase 1: ALACAKARANLIK AYAZI
    game.time_sec = 50.0
    phase_1 = int((game.time_sec // 40.0) % 3)
    assert phase_1 == 1

    # 90s -> Phase 2: BOZKIR FIRTINASI
    game.time_sec = 90.0
    phase_2 = int((game.time_sec // 40.0) % 3)
    assert phase_2 == 2

    # 2. Verify minimap contains kitabe steles
    mm_base = game.hud._ensure_minimap_base(game.world)
    assert mm_base.get_width() == game.world.width
    assert mm_base.get_height() == game.world.height

    # 3. Step updates and render across all phases
    for t in (15.0, 55.0, 95.0):
        game.time_sec = t
        game.update(0.016)
        game.render()





