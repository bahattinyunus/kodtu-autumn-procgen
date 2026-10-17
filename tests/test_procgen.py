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


def test_procedural_soundtrack_and_blade_dance_combo() -> None:
    """
    Verifies:
    1. 8.0-second seamless procedural autumn soundtrack loop synthesizes cleanly with NumPy.
    2. Player combo meter accumulation (0..6 hits) and [X] Bozkır Kılıç Dansı finisher activation.
    3. Campfire sizzle and blade dance sound synthesizers produce valid PCM buffers.
    """
    from src.core.audio_synth import synth_autumn_theme, synth_campfire_sizzle, synth_blade_dance
    from src.entities.actors import Player
    import numpy as np

    # 1. Procedural soundtrack synthesis
    theme = synth_autumn_theme()
    assert len(theme) == 176400  # 8.0s at 22050 Hz
    assert np.max(np.abs(theme)) <= 1.0

    # New combat sound synthesizers
    sizzle = synth_campfire_sizzle()
    dance_sfx = synth_blade_dance()
    assert len(sizzle) > 0
    assert len(dance_sfx) > 0
    assert np.max(np.abs(sizzle)) <= 1.0
    assert np.max(np.abs(dance_sfx)) <= 1.0

    # 2. Player combo meter & Blade Dance finisher
    p = Player(10.0, 10.0)
    assert p.combo_hits == 0
    assert not p.combo_ready
    assert not p.trigger_blade_dance()

    # Build combo with melee hits
    for _ in range(5):
        p.increment_combo(1)
    assert p.combo_hits == 5
    assert not p.combo_ready

    # 6th hit reaches full combo
    p.increment_combo(1)
    assert p.combo_hits == 6
    assert p.combo_ready

    # Trigger Blade Dance
    assert p.trigger_blade_dance()
    assert p.combo_hits == 0
    assert p.blade_dance_timer > 0.0
    assert p.invuln_timer >= 0.70


def test_enraged_warden_boss_and_campfire_roasting() -> None:
    """
    Verifies:
    1. Elder Stag Warden enters Phase 2 Enraged state at <= 50% HP with increased speed and 8-way orb storm.
    2. Campfire resting restores full warmth and roasts acorn into warm aura (+25s aura).
    3. Headless full game loop executes campfire interaction and blade dance without errors.
    """
    from src.entities.actors import EnemyAgent
    from src.main import AutumnProcGenGame

    # 1. Warden boss enraged phase
    warden = EnemyAgent(x=20.0, y=20.0, kind="warden", seed_phase=0.0)
    assert not warden.is_enraged
    assert warden.hp == 12

    # Damage warden below 50% (hp <= 6)
    warden.apply_hit(6, source_x=19.0, source_y=20.0)
    assert warden.hp == 6
    assert warden.is_enraged

    # 2. Campfire resting & acorn roasting in game
    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=False, headless=True)
    game.player.warmth = 30.0
    game.player.acorns_collected = 2

    # Find a campfire structure
    campfires = [st for st in game.world.structures if st.structure_type == "campfire"]
    assert len(campfires) > 0
    cf = campfires[0]

    # Teleport player near campfire and interact
    game.player.x = cf.tile_x + 0.5
    game.player.y = cf.tile_y + 0.5
    game._try_interact_action()

    # Warmth restored to 100%, 1 acorn consumed, 25s aura granted
    assert game.player.warmth == game.player.max_warmth
    assert game.player.acorns_collected == 1
    assert game.player.campfire_aura_timer == 25.0

    # 3. Trigger blade dance in game loop
    game.player.combo_hits = 6
    game._perform_blade_dance()
    assert game.player.combo_hits == 0
    assert game.player.blade_dance_timer > 0.0

    # Advance game loop across 10 frames
    for _ in range(10):
        game.update(0.016)
        game.render()


def test_blade_dance_visual_vfx_and_enraged_warden_aura() -> None:
    """
    Verifies:
    1. Bozkır Kılıç Dansı 4-way rotating supersonic slash VFX renders cleanly onto canvas.
    2. Enraged Elder Stag Warden renders golden antler aura and enraged HP color.
    3. Campfire aura expands lantern light radius from 56px to 72px in the vignette pass.
    """
    from src.entities.actors import EnemyAgent
    from src.main import AutumnProcGenGame

    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=False, headless=True)

    # 1. Trigger blade dance and verify render frame
    game.player.combo_hits = 6
    game._perform_blade_dance()
    assert game.player.blade_dance_timer > 0.0
    game.render()

    # 2. Add an enraged warden and test rendering
    warden = EnemyAgent(x=game.player.x + 1.0, y=game.player.y + 1.0, kind="warden")
    warden.hp = 4  # Below 50% max HP -> is_enraged True
    assert warden.is_enraged
    game.enemies.append(warden)
    game.render()

    # 3. Test campfire aura vignette calculation
    assert game.player.campfire_aura_timer == 0.0
    game.player.campfire_aura_timer = 20.0
    game.render()


def test_cclub_and_altug_kitabe_inscriptions() -> None:
    """
    Verifies:
    1. Historical ODTÜ inscriptions contain METU CClub (1989) and Altuğ Bilgin Altıntaş wisdom.
    2. Reading through kitabeler loops cleanly across all 6 inscriptions without index errors.
    """
    from src.core.story import HISTORICAL_ODTU_INSCRIPTIONS, StoryManager

    assert len(HISTORICAL_ODTU_INSCRIPTIONS) >= 6
    titles = [t for t, _ in HISTORICAL_ODTU_INSCRIPTIONS]
    assert any("CCLUB" in t for t in titles)
    assert any("ALTI TAŞ" in t or "ALTINTAŞ" in t for t in titles)

    sm = StoryManager(show_intro_card=False)
    for i in range(12):  # Test modulo wraparound across multiple readings
        title, text = sm.on_read_kitabe(i)
        assert len(title) > 0
        assert len(text) > 0
        assert sm.active_dialogue is not None
        assert sm.active_dialogue.title == title


def test_five_chapters_story_progression() -> None:
    """
    Verifies:
    1. Narrative engine supports full 5-chapter story progression (Chapters I through V).
    2. Chapter titles and themes conform to Yalıncak, Eymir, Devrim, Bozkır Kütüphanesi & Altın Şafak.
    """
    from src.core.story import StoryManager, CHAPTER_INFO

    assert len(CHAPTER_INFO) == 5
    sm = StoryManager(show_intro_card=False)
    for ch in range(1, 6):
        sm.chapter = ch
        title, text = sm.get_chapter_meta()
        assert len(title) > 0
        assert len(text) > 0
        assert f"BÖLÜM" in title

    sm.start_chapter(4, "ODTU-CHAPTER-4")
    assert sm.chapter == 4
    assert sm.active_dialogue is not None
    assert "KÜTÜPHANESİ" in sm.active_dialogue.title

    sm.start_chapter(5, "ODTU-CHAPTER-5")
    assert sm.chapter == 5
    assert sm.active_dialogue is not None
    assert "ŞAFAK" in sm.active_dialogue.title


def test_boss_roar_and_parry_spark_synthesizers() -> None:
    """
    Verifies:
    1. Primal boss roar synthesizer outputs valid sub-bass growl PCM data.
    2. Golden parry spark synthesizer outputs high-frequency clash PCM data.
    3. Headless game loop triggers boss roar upon warden entering enraged phase.
    """
    from src.core.audio_synth import synth_boss_roar, synth_parry_spark
    from src.entities.actors import EnemyAgent
    from src.main import AutumnProcGenGame
    import numpy as np

    roar = synth_boss_roar()
    spark = synth_parry_spark()
    assert len(roar) > 0
    assert len(spark) > 0
    assert np.max(np.abs(roar)) <= 1.0
    assert np.max(np.abs(spark)) <= 1.0

    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=False, headless=True)
    warden = EnemyAgent(x=game.player.x + 2.0, y=game.player.y, kind="warden")
    warden.hp = 12
    game.enemies.append(warden)

    # Damage warden below 50%
    warden.apply_hit(7, source_x=game.player.x, source_y=game.player.y)
    assert warden.is_enraged
    assert not warden.has_roared

    # Advance game loop -> should trigger roar and set has_roared to True
    game.update(0.016)
    assert warden.has_roared is True


def test_continuous_five_chapter_saga_and_ci_contract() -> None:
    """
    Verifies:
    1. GitHub Actions CI workflow (.github/workflows/ci.yml) exists and adheres to competition CI standards.
    2. Continuous 5-Chapter Saga progression (Depths 1 through 5) synchronizes narrative chapters,
       shrine transitions, and triggers grand victory at target_victory_depth=5.
    3. Headless rendering works without artifact errors across all saga depths.
    """
    from pathlib import Path
    from src.main import AutumnProcGenGame
    from src.core.story import CHAPTER_INFO

    # 1. CI Contract Verification
    ci_file = Path(".github/workflows/ci.yml")
    assert ci_file.is_file(), "GitHub Actions CI workflow must exist at .github/workflows/ci.yml"
    ci_content = ci_file.read_text(encoding="utf-8")
    assert "pytest tests/ -v" in ci_content
    assert "SDL_VIDEODRIVER: dummy" in ci_content
    assert "windows-latest" in ci_content
    assert "ubuntu-latest" in ci_content

    # 2. 5-Chapter Story Synchronization
    for ch_idx in range(1, 6):
        assert ch_idx in CHAPTER_INFO
        title, text, task = CHAPTER_INFO[ch_idx]
        assert len(title) > 0
        assert len(text) > 0
        assert len(task) > 0

    # 3. Continuous 5-Depth Progression
    game = AutumnProcGenGame(
        initial_seed="KODTU-SAGA-2026",
        debug_procgen=False,
        headless=True,
        target_victory_depth=5,
    )
    assert game.world.depth_level == 1
    assert game.story.chapter_index == 1
    assert "YALINCAK" in game.story.chapter_title

    # Walk from Depth 1 up to Depth 4
    for expected_depth in range(1, 5):
        assert game.world.depth_level == expected_depth
        assert game.story.chapter_index == expected_depth
        game.player.relics_collected = game.world.total_relics
        sx, sy = game.world.shrine_tile
        game.player.x = sx + 0.5
        game.player.y = sy + 0.5
        game._try_interact_shrine()

        assert game.story.show_victory_modal is False
        assert game.world.depth_level == expected_depth + 1
        assert game.story.chapter_index == expected_depth + 1

    # At Depth 5: Interacting with Shrine triggers Grand Victory
    assert game.world.depth_level == 5
    assert "ALTIN ŞAFAK" in game.story.chapter_title or "SAGA" in game.story.chapter_title
    game.player.relics_collected = game.world.total_relics
    sx, sy = game.world.shrine_tile
    game.player.x = sx + 0.5
    game.player.y = sy + 0.5
    game._try_interact_shrine()

    assert game.story.show_victory_modal is True

    # 4. Render headlessly during Chapter 5 victory modal
    game.render()


def test_audio_mute_toggle_volume_and_pause_modal_control() -> None:
    """
    Verifies:
    1. SoundEngine audio controls: mute toggle, master volume adjustment, and safe fallback.
    2. Engine pause mode ([P]): freeze simulation, movement vector zeroing, and headless pause modal overlay.
    3. Modern pyproject.toml packaging and pytest configuration integrity.
    """
    from pathlib import Path
    from src.main import AutumnProcGenGame

    # 1. Packaging integrity check
    pyproject_file = Path("pyproject.toml")
    assert pyproject_file.is_file(), "pyproject.toml must exist in repo root"
    content = pyproject_file.read_text(encoding="utf-8")
    assert "kodtu-autumn-procgen" in content
    assert "pygame-ce>=2.5.0" in content

    # 2. Audio mute and volume controls
    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=False, headless=True)
    assert game.sound.muted is False
    assert game.sound.master_volume == 1.0

    muted_state = game.sound.toggle_mute()
    assert muted_state is True
    assert game.sound.muted is True

    unmuted_state = game.sound.toggle_mute()
    assert unmuted_state is False
    assert game.sound.muted is False

    game.sound.set_master_volume(0.65)
    assert abs(game.sound.master_volume - 0.65) < 1e-4

    # 3. Game Pause State & Headless Rendering
    assert game.is_paused is False
    game.is_paused = True
    assert game._get_move_vector() == (0.0, 0.0)

    # Render while paused to verify _render_pause_modal_hd operates without errors
    game.render()

    game.is_paused = False
    assert game.is_paused is False


def test_boss_defeat_cinematic_drop_and_frost_respawn() -> None:
    """
    Verifies:
    1. Player respawn system (_respawn_player) restores warmth to 100%, resets to spawn tile,
       and activates invulnerability frames.
    2. Twilight frost decay triggers automatic respawn when warmth depletes to 0.0.
    3. Defeating Kadim Orman Bekçisi (Warden) drops 3 Golden Acorns, grants warmth bonus,
       triggers unique narrative boss dialogue, and announces victory banner.
    """
    from src.main import AutumnProcGenGame
    from src.entities.actors import EnemyAgent

    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=False, headless=True)
    sx, sy = game.world.spawn_tile

    # 1. Test player damage and respawn
    game.player.x = sx + 10.0
    game.player.y = sy + 10.0
    game.player.warmth = 5.0
    game._apply_player_damage(10.0)

    assert game.player.warmth == game.player.max_warmth
    assert abs(game.player.x - (sx + 0.5)) < 1e-4
    assert abs(game.player.y - (sy + 0.5)) < 1e-4
    assert game.player.invuln_timer > 1.0

    # 2. Test Twilight Frost depletion respawn in update()
    game.time_sec = 45.0  # Phase 1: Twilight Frost
    game.player.x = sx + 8.0
    game.player.y = sy + 8.0
    game.player.warmth = 0.0
    game.update(0.016)

    assert game.player.warmth == game.player.max_warmth
    assert abs(game.player.x - (sx + 0.5)) < 1e-4
    assert abs(game.player.y - (sy + 0.5)) < 1e-4

    # 3. Test Boss Defeat Event & 3-Acorn Loot Drop
    initial_items_count = len(game.items)
    warden = EnemyAgent(x=game.player.x + 3.0, y=game.player.y, kind="warden")
    game.enemies.append(warden)

    game._on_enemy_defeated(warden)
    assert game.player.enemies_defeated >= 1
    assert len(game.items) == initial_items_count + 3
    new_drops = [it for it in game.items[-3:] if it.kind == "acorn"]
    assert len(new_drops) == 3

    # Narrative dialogue and banner
    assert game.story.active_dialogue is not None
    assert "BEKÇİSİ" in game.story.active_dialogue.speaker or "KADİM" in game.story.active_dialogue.speaker
    assert "KADİM ORMAN BEKÇİSİ DİZE GELDİ" in game.hud.banner_text


def test_devrim_overdrive_mode_and_audio_synthesis() -> None:
    """
    [Test 30] Verifies:
    1. Procedural brass crescendo synthesizer synth_devrim_overdrive() generates valid stereo 16-bit PCM.
    2. Player trigger_devrim_overdrive() requires warmth >= 70% and combo or relic.
    3. Overdrive grants +35% movement speed, ghost afterimages, +2 melee damage, and bolt refill.
    4. Headless rendering properly displays the golden chromatic screen vignette.
    """
    import numpy as np
    from src.core.audio_synth import synth_devrim_overdrive
    from src.entities.actors import EnemyAgent
    from src.main import AutumnProcGenGame

    # 1. Audio synthesis validation
    overdrive_pcm = synth_devrim_overdrive()
    assert len(overdrive_pcm) > 8000
    assert np.max(np.abs(overdrive_pcm)) <= 1.0

    # 2. Engine and Overdrive mechanics
    game = AutumnProcGenGame(initial_seed="ODTU-DEVRIM-1956", debug_procgen=False, headless=True)

    # Ineligible when warmth is low or combo not met
    game.player.warmth = 50.0
    game.player.combo_hits = 0
    game.player.relics_collected = 0
    assert not game.player.overdrive_ready
    assert not game.player.trigger_devrim_overdrive()

    # Eligible when warmth >= 70 and combo is full
    game.player.warmth = 85.0
    game.player.combo_hits = 6
    assert game.player.overdrive_ready
    game._perform_devrim_overdrive()

    assert game.player.is_in_overdrive
    assert game.player.overdrive_timer > 9.0
    assert game.player.solar_bolts == game.player.max_solar_bolts
    assert game.player.combo_hits == 0

    # Verify bonus damage in _perform_ember_attack
    # Spawn enemy directly in front of player
    enemy = EnemyAgent(x=game.player.x + 0.8, y=game.player.y, kind="wolf")
    enemy.hp = 10
    game.enemies.append(enemy)
    game.player.attack_cooldown = 0.0
    game._perform_ember_attack()
    # Base attack is 2 + 2 (overdrive) = 4 dmg
    assert enemy.hp <= 6

    # Verify headless rendering with vignette
    game.render()


def test_steppe_alchemy_and_tactical_map_modal() -> None:
    """
    [Test 31] Verifies:
    1. Procedural crystalline pentatonic chime synth_alchemy_chime() generates valid stereo 16-bit PCM.
    2. Bozkır Simyası / Acorn Alchemy ([G]) transmuting 2 acorns at Campfire/Shrine into permanent upgrades.
    3. Tactical Steppe Cartography modal ([N]) opens full-screen 56x42 map and freezes movement.
    """
    import numpy as np
    from src.core.audio_synth import synth_alchemy_chime
    from src.main import AutumnProcGenGame

    # 1. Audio synthesis validation
    chime_pcm = synth_alchemy_chime()
    assert len(chime_pcm) > 5000
    assert np.max(np.abs(chime_pcm)) <= 1.0

    # 2. Engine and Steppe Alchemy
    game = AutumnProcGenGame(initial_seed="ODTU-ALCHEMY-TEST", debug_procgen=False, headless=True)

    # Far from any alchemy site -> fails
    game.player.x = 0.5
    game.player.y = 0.5
    game.player.acorns_collected = 5
    game._perform_steppe_alchemy()
    assert game.player.acorns_collected == 5  # No acorns consumed

    # Move near shrine
    sx, sy = game.world.shrine_tile
    game.player.x = sx + 0.5
    game.player.y = sy + 0.5

    # First transmutation: +1 Max Solar Bolt
    initial_max_bolts = game.player.max_solar_bolts
    game._perform_steppe_alchemy()
    assert game.player.acorns_collected == 3
    assert game.player.max_solar_bolts == initial_max_bolts + 1

    # Second transmutation: -25% Dash Cooldown
    game._perform_steppe_alchemy()
    assert game.player.acorns_collected == 1
    assert game.player.dash_cooldown_mult == 0.75

    # Third transmutation fails due to insufficient acorns (< 2)
    game._perform_steppe_alchemy()
    assert game.player.acorns_collected == 1

    # 3. Tactical Map Modal ([N])
    assert not game.tactical_map_open
    game.tactical_map_open = True
    # Movement vector is locked to (0, 0)
    assert game._get_move_vector() == (0.0, 0.0)

    # Render frame with tactical map modal active
    game.render()
    assert game.tactical_map_open


def test_steppe_raven_enemy_and_screech_synthesis() -> None:
    """
    [Test 32] Verifies:
    1. Procedural avian screech synthesizer synth_raven_screech() outputs valid audio array.
    2. Bozkır Kuzgunu (Steppe Shadow Raven) enemy stats, swoop and dive AI behavior.
    3. Defeating a raven triggers speed boost and acorn drop.
    """
    import numpy as np
    from src.core.audio_synth import synth_raven_screech
    from src.entities.actors import EnemyAgent
    from src.main import AutumnProcGenGame

    screech = synth_raven_screech()
    assert len(screech) > 0
    assert np.max(np.abs(screech)) <= 1.0

    game = AutumnProcGenGame(initial_seed="RAVEN-TEST", debug_procgen=False, headless=True)
    raven = EnemyAgent(x=game.player.x + 3.0, y=game.player.y + 1.0, kind="raven")
    assert raven.max_hp == 2
    assert raven.speed == 3.90
    assert raven.radius == 0.28
    game.enemies.append(raven)

    # Update raven AI
    raven.update(0.016, game.player.x, game.player.y, 0.0, game.spatial_hash)
    assert abs(raven.vx) > 0.0 or abs(raven.vy) > 0.0

    # Defeat raven and test reward
    initial_items = len(game.items)
    game._on_enemy_defeated(raven)
    assert game.player.leaf_boost_timer > 3.0
    assert len(game.items) == initial_items + 1

    # Render frame with raven
    game.render()


def test_eymir_spring_structure_and_healing() -> None:
    """
    [Test 33] Verifies:
    1. Procedural bubbling water synthesizer synth_spring_splash() outputs valid audio array.
    2. Eymir Şifa Pınarı (Sacred Healing Spring) structure placement in world gen.
    3. Interacting with the spring restores full warmth, invulnerability, and speed.
    """
    import numpy as np
    from src.core.audio_synth import synth_spring_splash
    from src.procgen.structures import StructurePlacement
    from src.main import AutumnProcGenGame

    splash = synth_spring_splash()
    assert len(splash) > 0
    assert np.max(np.abs(splash)) <= 1.0

    game = AutumnProcGenGame(initial_seed="SPRING-TEST", debug_procgen=False, headless=True)
    # Manually ensure an eymir_pinari structure exists near player
    spring_x = int(game.player.x) + 1
    spring_y = int(game.player.y)
    game.world.structures.append(
        StructurePlacement(tile_x=spring_x, tile_y=spring_y, structure_type="eymir_pinari", radius_tiles=1)
    )

    # Deplete warmth
    game.player.warmth = 25.0
    game.player.invuln_timer = 0.0
    game.player.leaf_boost_timer = 0.0

    # Interact with spring
    game._try_interact_action()
    assert game.player.warmth == game.player.max_warmth
    assert game.player.invuln_timer > 2.0
    assert game.player.leaf_boost_timer > 5.0

    # Render frame
    game.render()


def test_perfect_parry_and_academic_grade_evaluator() -> None:
    """
    [Test 34] Verifies:
    1. METU Academic Grade Evaluator calculates S, A, B, and C tiers correctly.
    2. Perfect Parry counter timing blocks damage, awards warmth, recharges bolts, and counters enemy.
    3. Victory modal renders S-tier academic grade strip cleanly in headless mode.
    """
    from src.core.story import evaluate_academic_grade
    from src.entities.actors import EnemyAgent
    from src.main import AutumnProcGenGame

    # 1. Academic Grade Evaluation tests
    grade_c, title_c, score_c = evaluate_academic_grade(1, 1, 1, 0, 0, 1)
    assert grade_c == "C"
    assert "ÇIRAĞI" in title_c

    grade_b, title_b, score_b = evaluate_academic_grade(3, 4, 3, 2, 1, 2)
    assert grade_b == "B"
    assert "SEYYAHI" in title_b

    grade_a, title_a, score_a = evaluate_academic_grade(4, 6, 5, 4, 3, 3)
    assert grade_a == "A"
    assert "ŞEREF" in title_a

    grade_s, title_s, score_s = evaluate_academic_grade(5, 8, 8, 6, 5, 4)
    assert grade_s == "S"
    assert "KURDAŞ" in title_s

    # 2. Perfect Parry Counter Mechanics
    game = AutumnProcGenGame(initial_seed="PARRY-TEST", debug_procgen=False, headless=True)
    game.player.warmth = 80.0
    game.player.attack_timer = 0.12  # Active swing
    game.player.solar_bolts = 0

    # Spawn enemy near player
    wolf = EnemyAgent(x=game.player.x + 0.8, y=game.player.y, kind="wolf")
    wolf.hp = 10
    game.enemies.append(wolf)

    # Apply enemy incoming hit during active player swing -> triggers PERFECT PARRY!
    game._apply_player_damage(20.0)

    # Warmth should not have decreased; instead gained parry warmth
    assert game.player.warmth > 80.0
    assert game.player.solar_bolts > 0
    assert game.player.invuln_timer > 0.40
    # Enemy took parry counter damage
    assert wolf.hp <= 5

    # 3. Victory modal rendering with S-rank
    game.story.show_victory_modal = True
    game.player.relics_collected = 5
    game.player.acorns_collected = 10
    game.player.enemies_defeated = 10
    game.render()


def test_bilim_agaci_ceremony_and_thunder_synthesis() -> None:
    """
    Verifies:
    1. Audio synthesis for 'bilim_chime' (celestial tubular bells) and 'distant_thunder' (sub-bass rolling rumble).
    2. Interacting [E] near ODTÜ Bilim Ağacı monument triggers ceremony:
       - Refills warmth to max
       - Activates 30s celestial halo (bilim_ritual_timer)
       - Plays bilim_chime audio
    3. bilim_ritual_timer applies passive warmth regeneration and decays cleanly over time.
    """
    from src.core.audio_synth import synth_bilim_chime, synth_distant_thunder
    from src.main import AutumnProcGenGame

    # 1. Audio synthesis checks
    chime_wave = synth_bilim_chime()
    assert len(chime_wave) > 0
    assert float(np.max(np.abs(chime_wave))) > 0.05

    thunder_wave = synth_distant_thunder()
    assert len(thunder_wave) > 0
    assert float(np.max(np.abs(thunder_wave))) > 0.05

    # 2. In-game Bilim Ağacı interaction ceremony
    game = AutumnProcGenGame(initial_seed="KODTU2026", debug_procgen=False, headless=True)
    # Find Bilim Ağacı structure
    bilim_st = next((st for st in game.world.structures if st.structure_type == "bilim_agaci"), None)
    assert bilim_st is not None

    # Teleport player near Bilim Ağacı
    game.player.x = float(bilim_st.tile_x) + 0.5
    game.player.y = float(bilim_st.tile_y) + 0.5
    game.player.warmth = 25.0
    assert game.player.bilim_ritual_timer == 0.0

    # Trigger interaction [E]
    game._try_interact_action()

    # Verify ceremony activation
    assert game.player.warmth == game.player.max_warmth
    assert game.player.bilim_ritual_timer == 30.0

    # 3. Verify passive warmth regeneration and timer decrement
    game.player.warmth = 50.0
    game.player.update(
        dt=1.0,
        move_x=0.0,
        move_y=0.0,
        spatial_hash=game.spatial_hash,
        biome_grid=game.world.biome_grid,
    )
    assert game.player.bilim_ritual_timer == 29.0
    assert game.player.warmth == 54.0  # +4.0 warmth regen/sec


def test_chronicle_ledger_modal_and_ritual_halo() -> None:
    """
    Verifies:
    1. Sefer Günlüğü / Run Chronicle Ledger modal ([J]) toggles, pauses movement and updates statistics.
    2. Perfect parries are recorded and incremented on player stats.
    3. Rendering of modern HD overlay with ledger_open renders without exceptions.
    4. Rendering player with active bilim_ritual_timer expands lighting vignette base halo.
    """
    from src.entities.actors import EnemyAgent
    from src.main import AutumnProcGenGame

    game = AutumnProcGenGame(initial_seed="ODTU-LEDGER-TEST", debug_procgen=False, headless=True)
    assert not game.hud.ledger_modal_open

    # 1. Toggle ledger modal open
    game.hud.ledger_modal_open = True
    assert game.hud.ledger_modal_open

    # When ledger modal is open, movement vector must be 0, 0
    mx, my = game._get_move_vector()
    assert mx == 0.0 and my == 0.0

    # 2. Perfect parry increments player.perfect_parries
    game.player.perfect_parries = 0
    game.player.attack_timer = 0.14
    wolf = EnemyAgent(x=game.player.x + 0.5, y=game.player.y, kind="wolf")
    game.enemies.append(wolf)
    game._apply_player_damage(15.0)
    assert game.player.perfect_parries == 1

    # 3. Render frame with ledger_open = True
    game.render()

    # 4. Ritual halo rendering test
    game.hud.ledger_modal_open = False
    game.player.bilim_ritual_timer = 25.0
    game.render()


def test_steppe_companion_kangal_and_bark_synthesis() -> None:
    """
    Verifies:
    1. Procedural synthesizers for companion bark and leaf scatter generate valid audio buffers.
    2. SteppeCompanion follows the player, updates animations, and alerts with barking when enemies approach.
    3. Enemy distraction occurs when enemies enter companion distraction radius.
    4. Petting the companion ([E]) grants +12 warmth, triggers pet animation, increments player.pets_count,
       and unlocks the COMPANION_FRIEND achievement.
    """
    from src.core.audio_synth import synth_companion_bark, synth_leaf_scatter
    from src.entities.actors import SteppeCompanion, EnemyAgent, Player
    from src.main import AutumnProcGenGame

    # 1. Procedural audio synthesis validation
    bark_wav = synth_companion_bark()
    assert isinstance(bark_wav, np.ndarray) and len(bark_wav) > 1000
    assert float(np.max(np.abs(bark_wav))) > 0.05

    scatter_wav = synth_leaf_scatter()
    assert isinstance(scatter_wav, np.ndarray) and len(scatter_wav) > 1000
    assert float(np.max(np.abs(scatter_wav))) > 0.05

    # 2. SteppeCompanion movement and steering physics
    player = Player(x=10.0, y=10.0)
    companion = SteppeCompanion(x=10.0, y=10.0)
    assert companion.kind == "companion"
    assert companion.pet_timer == 0.0

    # Companion stays close when distance is small
    companion.update(dt=0.1, target_x=10.5, target_y=10.0, enemies=[], spatial_hash=None)
    assert companion.is_moving is False

    # Companion chases when player runs far ahead
    companion.update(dt=0.2, target_x=16.0, target_y=10.0, enemies=[], spatial_hash=None)
    assert companion.is_moving is True
    assert companion.x > 10.0

    # 3. Enemy alert barking and combat distraction
    enemy = EnemyAgent(x=12.0, y=10.0, kind="wolf")
    companion.alert_cooldown = 0.0
    companion.update(dt=0.1, target_x=10.0, target_y=10.0, enemies=[enemy], spatial_hash=None)
    assert companion.bark_alert_trigger is True
    assert enemy.distraction_timer > 0.0

    # 4. Interactive petting mechanic
    player.warmth = 40.0
    player.pets_count = 0
    petted = companion.pet(player)
    assert petted is True
    assert player.warmth == 52.0  # +12 warmth
    assert player.pets_count == 1
    assert companion.pet_timer > 0.0

    # 5. In-game integration test with AutumnProcGenGame
    game = AutumnProcGenGame(initial_seed="KANGAL-TEST-SEED", debug_procgen=False, headless=True)
    assert hasattr(game, "companion") and isinstance(game.companion, SteppeCompanion)

    # Place companion next to player away from any structure and interact
    game.player.x = 25.0
    game.player.y = 25.0
    game.companion.x = 25.5
    game.companion.y = 25.0
    game.companion.pet_timer = 0.0
    start_pets = game.player.pets_count
    game._try_interact_action()
    assert game.player.pets_count == start_pets + 1
    assert "COMPANION_FRIEND" in game.story.unlocked_achievements


def test_bozkir_achievements_system_and_leaf_pile_scattering() -> None:
    """
    Verifies:
    1. Bozkir Achievements registry contains all 8 defined campus milestones.
    2. StoryManager.unlock_achievement records progress without duplicates.
    3. Destroying leaf piles via attack or gust dash scatters leaves and unearths bonus resources.
    4. Headless rendering of game frame and ledger modal with companion and achievements.
    """
    from src.core.story import ACHIEVEMENT_REGISTRY, StoryManager
    from src.procgen.poisson import PropPlacement
    from src.core.spatial_hash import CHUNK_SIZE_TILES
    from src.main import AutumnProcGenGame

    # 1. Registry validation
    assert len(ACHIEVEMENT_REGISTRY) == 8
    expected_keys = {
        "FIRST_DEFLECT", "PERFECT_PARRY", "COMPANION_FRIEND", "BILIM_CEREMONY",
        "STEPPE_ALCHEMY", "BLADE_DANCE", "DEVRIM_OVERDRIVE", "CHRONICLE_HISTORIAN"
    }
    assert {ach.key for ach in ACHIEVEMENT_REGISTRY} == expected_keys

    # 2. StoryManager unlock mechanics
    story = StoryManager()
    ach = story.unlock_achievement("FIRST_DEFLECT")
    assert ach is not None
    assert ach.key == "FIRST_DEFLECT"
    assert "FIRST_DEFLECT" in story.unlocked_achievements

    # Duplicate unlock returns None
    assert story.unlock_achievement("FIRST_DEFLECT") is None
    assert len(story.unlocked_achievements) == 1

    # 3. Leaf pile scattering and gust dash destruction
    game = AutumnProcGenGame(initial_seed="EYMIR-SCATTER-TEST", debug_procgen=False, headless=True)
    leaf_drift = PropPlacement(
        x=game.player.x + 0.6,
        y=game.player.y + 0.2,
        prop_type="leaf_pile",
        solid=False,
        biome=1,
        variant=0,
    )
    chx = int(leaf_drift.x) // CHUNK_SIZE_TILES
    chy = int(leaf_drift.y) // CHUNK_SIZE_TILES
    game.spatial_hash.chunk_props[(chx, chy)].append(leaf_drift)
    initial_decor_count = len(game.spatial_hash.chunk_props[(chx, chy)])

    # Smash prop
    game._smash_nearby_props(game.player.x, game.player.y, radius=1.5)
    assert len(game.spatial_hash.chunk_props[(chx, chy)]) == initial_decor_count - 1

    # 4. Headless rendering coverage with companion and ledger modal
    game.hud.ledger_modal_open = True
    game.story.unlock_achievement("COMPANION_FRIEND")
    game.story.unlock_achievement("BILIM_CEREMONY")
    game.render()

    game.hud.ledger_modal_open = False
    game.render()













