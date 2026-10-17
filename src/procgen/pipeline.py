"""
6-Stage Deterministic Procedural Content Generation (PCG) Pipeline.

Pipeline Stages (matching Section 2 of README.md):
1. Topographic Noise Synthesis (Multi-Octave Simplex fBm: Elevation & Moisture/Decay)
2. Topological Sculpting (B678/S345678 Cellular Automata, BFS Flood-Fill & Corridor Carving)
3. Bitmask Autotiling (47-Tile 8-Bit Blob & 4-Directional Transition Masks)
4. Ecological Distribution (Bridson's Fast Poisson Disk Sampling)
5. Dynamic Entity & Threat Budgeting (Dijkstra Distance Field Scaling)
6. Atmospheric Synthesis Setup (2D Wind Vector Field)
"""

from __future__ import annotations
from dataclasses import dataclass, field
import time
from typing import Dict, List, Set, Tuple, Union
import numpy as np

from src.procgen.prng import Xoshiro256StarStar, format_seed_code, seed_to_uint64
from src.procgen.noise import (
    SimplexNoise2D,
    classify_autumn_biomes,
    compute_wind_vector_field,
)
from src.procgen.automata import (
    sculpt_connected_topology,
    compute_dijkstra_distance_field,
)
from src.procgen.autotile import (
    compute_47_blob_grid,
    compute_4dir_mask_grid,
)
from src.procgen.poisson import (
    PropPlacement,
    distribute_ecological_props,
)
from src.procgen.structures import (
    StructurePlacement,
    synthesize_autumn_structures,
    compute_flow_field_vectors,
)


@dataclass(frozen=True)
class EntitySpawn:
    """Deterministic spawn descriptor for enemies and harvest relics."""

    x: float
    y: float
    entity_type: str   # 'relic', 'acorn', 'wisp', 'stalker', 'golem', 'warden'
    threat_cost: int
    dijkstra_norm: float


@dataclass
class WorldData:
    """Complete deterministic output of the 6-stage PCG pipeline."""

    seed_input: str
    seed_uint64: int
    seed_code: str
    width: int
    height: int
    depth_level: int

    # Stage 1: Noise & Biome Matrices
    elevation: np.ndarray        # float64 [0.0, 1.0]
    moisture: np.ndarray         # float64 [0.0, 1.0]
    biome_grid: np.ndarray       # int32 (0=Wall, 1=Damp, 2=Amber, 3=Golden)

    # Stage 2: Topology, Dijkstra Connectivity & Vector Flow-Field
    walkable_grid: np.ndarray    # int32 (0=Walkable floor, 1=Solid cliff/canopy wall)
    corridor_tiles: List[Tuple[int, int]]
    spawn_tile: Tuple[int, int]
    shrine_tile: Tuple[int, int]
    dijkstra_dist: np.ndarray    # int32 step distance (-1 for walls)
    dijkstra_norm: np.ndarray    # float64 [0.0, 1.0] normalized distance
    shortest_path: List[Tuple[int, int]]
    flow_vx: np.ndarray          # float64 downhill geodesic flow X
    flow_vy: np.ndarray          # float64 downhill geodesic flow Y

    # Stage 3: Bitmask Autotiling
    wall_mask_8bit: np.ndarray   # int32 sanitized 8-bit mask
    wall_blob_47: np.ndarray     # int32 47-tile index (0..46)
    biome_mask_4dir: np.ndarray  # int32 4-dir mask (0..15) for golden leaf transitions

    # Stage 4: Poisson Disk Ecological Props & Procedural Micro-Structures
    props: List[PropPlacement]
    structures: List[StructurePlacement]

    # Stage 5: Threat-Budgeted Entities & Relics
    spawns: List[EntitySpawn]
    total_relics: int

    # Stage 6: Wind Field & Noise Generator
    wind_vx: np.ndarray
    wind_vy: np.ndarray
    wind_noise: SimplexNoise2D

    # Telemetry (milliseconds per stage)
    timings_ms: Dict[str, float] = field(default_factory=dict)
    total_gen_ms: float = 0.0


def _select_spawn_tile(walkable_grid: np.ndarray) -> Tuple[int, int]:
    """Finds the walkable tile closest to the geometric center of the map."""
    height, width = walkable_grid.shape
    cx, cy = width // 2, height // 2
    if walkable_grid[cy, cx] == 0:
        return (cx, cy)

    best_tile = (cx, cy)
    best_dist = 10**9
    for y in range(2, height - 2):
        for x in range(2, width - 2):
            if walkable_grid[y, x] == 0:
                d = (x - cx) ** 2 + (y - cy) ** 2
                if d < best_dist:
                    best_dist = d
                    best_tile = (x, y)
    return best_tile


def _budget_entities_and_relics(
    walkable_grid: np.ndarray,
    dijkstra_norm: np.ndarray,
    props: List[PropPlacement],
    spawn_tile: Tuple[int, int],
    shrine_tile: Tuple[int, int],
    prng: Xoshiro256StarStar,
    depth_level: int = 1,
    target_relics: int = 5,
) -> List[EntitySpawn]:
    """
    Stage 5: Dynamic Entity & Threat Budgeting using the Dijkstra Distance Field.
    - Places `target_relics` Harvest Relics across distinct regions at d in [0.22, 0.92].
    - Allocates threat budget proportional to depth_level and geodesic distance from spawn.
    """
    height, width = walkable_grid.shape
    occupied: Set[Tuple[int, int]] = {spawn_tile, shrine_tile}
    for p in props:
        if p.solid:
            occupied.add((int(p.x), int(p.y)))

    # Gather all valid open floor tiles with their normalized Dijkstra distance
    candidates: List[Tuple[int, int, float]] = []
    for y in range(3, height - 3):
        for x in range(3, width - 3):
            if walkable_grid[y, x] == 0 and (x, y) not in occupied:
                d = float(dijkstra_norm[y, x])
                if d > 0.0:
                    candidates.append((x, y, d))

    prng.shuffle(candidates)
    spawns: List[EntitySpawn] = []

    # 1. Place Amber Harvest Relics with spatial separation
    relic_tiles: List[Tuple[int, int]] = []
    relic_candidates = [c for c in candidates if 0.22 <= c[2] <= 0.95]
    if len(relic_candidates) < target_relics:
        relic_candidates = [c for c in candidates if c[2] >= 0.12]

    for min_sep_sq in (64.0, 36.0, 16.0, 4.0):
        for cx, cy, cd in relic_candidates:
            if len(relic_tiles) >= target_relics:
                break
            if (cx, cy) in occupied:
                continue
            if all((cx - rx) ** 2 + (cy - ry) ** 2 >= min_sep_sq for rx, ry in relic_tiles):
                relic_tiles.append((cx, cy))
                occupied.add((cx, cy))
                spawns.append(
                    EntitySpawn(
                        x=float(cx) + 0.5,
                        y=float(cy) + 0.5,
                        entity_type="relic",
                        threat_cost=0,
                        dijkstra_norm=cd,
                    )
                )
        if len(relic_tiles) >= target_relics:
            break

    # 2. Place bonus Golden Acorns (warmth/score pickups)
    acorn_count = 0
    for cx, cy, cd in candidates:
        if acorn_count >= 8:
            break
        if (cx, cy) not in occupied and cd >= 0.15:
            occupied.add((cx, cy))
            acorn_count += 1
            spawns.append(
                EntitySpawn(
                    x=float(cx) + 0.5,
                    y=float(cy) + 0.5,
                    entity_type="acorn",
                    threat_cost=0,
                    dijkstra_norm=cd,
                )
            )

    # 3. Threat Budgeting for Autumn Enemies based on Dijkstra distance
    threat_budget = 16 + depth_level * 5
    enemy_tiles: List[Tuple[int, int]] = []

    for cx, cy, cd in candidates:
        if threat_budget <= 0:
            break
        if (cx, cy) in occupied or cd < 0.20:
            continue
        # Ensure enemies aren't stacked on top of each other
        if any((cx - ex) ** 2 + (cy - ey) ** 2 < 12.0 for ex, ey in enemy_tiles):
            continue

        if cd >= 0.70 and threat_budget >= 3 and prng.random() < 0.35:
            etype = "golem"
            cost = 3
        elif cd >= 0.55 and threat_budget >= 2 and prng.random() < 0.35:
            etype = "lynx"
            cost = 2
        elif cd >= 0.45 and threat_budget >= 2 and prng.random() < 0.40:
            etype = "wolf"
            cost = 2
        elif cd >= 0.38 and threat_budget >= 2 and prng.random() < 0.40:
            etype = "raven"
            cost = 2
        elif cd >= 0.30 and threat_budget >= 2 and prng.random() < 0.60:
            etype = "stalker"
            cost = 2
        else:
            etype = "wisp"
            cost = 1

        occupied.add((cx, cy))
        enemy_tiles.append((cx, cy))
        threat_budget -= cost
        spawns.append(
            EntitySpawn(
                x=float(cx) + 0.5,
                y=float(cy) + 0.5,
                entity_type=etype,
                threat_cost=cost,
                dijkstra_norm=cd,
            )
        )

    # 4. Place an Elder Stag Warden guardian near the Ancient Autumn Shrine
    for cx, cy, cd in candidates:
        if (cx, cy) not in occupied and cd >= 0.78:
            if 4 <= (cx - shrine_tile[0]) ** 2 + (cy - shrine_tile[1]) ** 2 <= 25:
                occupied.add((cx, cy))
                spawns.append(
                    EntitySpawn(
                        x=float(cx) + 0.5,
                        y=float(cy) + 0.5,
                        entity_type="warden",
                        threat_cost=5,
                        dijkstra_norm=cd,
                    )
                )
                break

    return spawns


def generate_autumn_world(
    seed: Union[str, int] = "KODTU2026",
    width: int = 56,
    height: int = 42,
    depth_level: int = 1,
) -> WorldData:
    """
    Executes the complete 6-stage deterministic PCG pipeline for `seed`.
    """
    t_start = time.perf_counter()
    timings: Dict[str, float] = {}

    root_prng = Xoshiro256StarStar(seed)
    seed_uint64 = root_prng.seed_uint64
    seed_code = format_seed_code(seed_uint64)

    # --- STAGE 1: Multi-Octave Simplex fBm Synthesis ---
    t0 = time.perf_counter()
    elev_noise = SimplexNoise2D(root_prng.fork("elevation"))
    moist_noise = SimplexNoise2D(root_prng.fork("moisture"))
    wind_noise = SimplexNoise2D(root_prng.fork("wind"))

    elevation = elev_noise.fbm_grid(
        width, height, octaves=4, persistence=0.52, lacunarity=2.05, scale=0.075
    )
    moisture = moist_noise.fbm_grid(
        width, height, octaves=4, persistence=0.50, lacunarity=2.0, scale=0.065
    )
    timings["1_fbm_noise"] = (time.perf_counter() - t0) * 1000.0

    # --- STAGE 2: Cellular Automata (B678/S345678), Flood-Fill & Flow-Field ---
    t0 = time.perf_counter()
    topo_prng = root_prng.fork("topology")
    walkable_grid, corridor_tiles = sculpt_connected_topology(
        elevation, topo_prng, wall_threshold=0.56, ca_iterations=4, min_clearing_size=16
    )
    spawn_tile = _select_spawn_tile(walkable_grid)
    dijkstra_dist, dijkstra_norm, shrine_tile, shortest_path = compute_dijkstra_distance_field(
        walkable_grid, spawn_tile
    )
    flow_vx, flow_vy = compute_flow_field_vectors(dijkstra_dist)
    biome_grid = classify_autumn_biomes(elevation, moisture, walkable_grid)
    timings["2_automata_bfs"] = (time.perf_counter() - t0) * 1000.0

    # --- STAGE 3: 47-Tile Blob & 4-Dir Bitmask Autotiling ---
    t0 = time.perf_counter()
    wall_mask_8bit, wall_blob_47 = compute_47_blob_grid(walkable_grid, target_value=1)
    biome_mask_4dir = compute_4dir_mask_grid((biome_grid == 3).astype(np.int32), target_value=1)
    timings["3_autotile_47"] = (time.perf_counter() - t0) * 1000.0

    # --- STAGE 4: Bridson's Fast Poisson Disk Sampling & Micro-Structures ---
    t0 = time.perf_counter()
    poisson_prng = root_prng.fork("poisson")
    struct_prng = root_prng.fork("structures")
    structures = synthesize_autumn_structures(
        walkable_grid=walkable_grid,
        dijkstra_norm=dijkstra_norm,
        spawn_tile=spawn_tile,
        shrine_tile=shrine_tile,
        shortest_path=shortest_path,
        prng=struct_prng,
    )
    props = distribute_ecological_props(
        walkable_grid=walkable_grid,
        biome_grid=biome_grid,
        moisture_grid=moisture,
        spawn_tile=spawn_tile,
        shrine_tile=shrine_tile,
        shortest_path=shortest_path,
        prng=poisson_prng,
        min_dist=2.55,
    )
    timings["4_poisson_disk"] = (time.perf_counter() - t0) * 1000.0

    # --- STAGE 5: Threat Budgeting via Dijkstra Distance Field ---
    t0 = time.perf_counter()
    threat_prng = root_prng.fork("threat_budget")
    spawns = _budget_entities_and_relics(
        walkable_grid=walkable_grid,
        dijkstra_norm=dijkstra_norm,
        props=props,
        spawn_tile=spawn_tile,
        shrine_tile=shrine_tile,
        prng=threat_prng,
        depth_level=depth_level,
        target_relics=5,
    )
    total_relics = sum(1 for s in spawns if s.entity_type == "relic")
    timings["5_threat_budget"] = (time.perf_counter() - t0) * 1000.0

    # --- STAGE 6: 2D Wind Vector Field Synthesis ---
    t0 = time.perf_counter()
    wind_vx, wind_vy = compute_wind_vector_field(wind_noise, width, height, time_sec=0.0)
    timings["6_wind_field"] = (time.perf_counter() - t0) * 1000.0

    total_ms = (time.perf_counter() - t_start) * 1000.0

    return WorldData(
        seed_input=str(seed),
        seed_uint64=seed_uint64,
        seed_code=seed_code,
        width=width,
        height=height,
        depth_level=depth_level,
        elevation=elevation,
        moisture=moisture,
        biome_grid=biome_grid,
        walkable_grid=walkable_grid,
        corridor_tiles=corridor_tiles,
        spawn_tile=spawn_tile,
        shrine_tile=shrine_tile,
        dijkstra_dist=dijkstra_dist,
        dijkstra_norm=dijkstra_norm,
        shortest_path=shortest_path,
        flow_vx=flow_vx,
        flow_vy=flow_vy,
        wall_mask_8bit=wall_mask_8bit,
        wall_blob_47=wall_blob_47,
        biome_mask_4dir=biome_mask_4dir,
        props=props,
        structures=structures,
        spawns=spawns,
        total_relics=total_relics,
        wind_vx=wind_vx,
        wind_vy=wind_vy,
        wind_noise=wind_noise,
        timings_ms=timings,
        total_gen_ms=total_ms,
    )
