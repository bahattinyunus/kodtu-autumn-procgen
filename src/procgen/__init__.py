"""
KODTÜ Autumn ProcGen Core Package.
"""

from src.procgen.prng import Xoshiro256StarStar, Mulberry32, seed_to_uint64, format_seed_code
from src.procgen.noise import SimplexNoise2D, classify_autumn_biomes, compute_wind_vector_field
from src.procgen.automata import (
    step_cellular_automata_b678_s345678,
    sculpt_connected_topology,
    compute_dijkstra_distance_field,
    find_connected_clearings,
)
from src.procgen.autotile import (
    CANONICAL_47_MASKS,
    MASK_TO_47_INDEX,
    RAW_TO_47_LUT,
    compute_47_blob_grid,
    compute_4dir_mask_grid,
)
from src.procgen.poisson import fast_poisson_disk_sampling, distribute_ecological_props, PropPlacement
from src.procgen.structures import (
    StructurePlacement,
    astar_shortest_path,
    compute_flow_field_vectors,
    synthesize_autumn_structures,
)
from src.procgen.pipeline import generate_autumn_world, WorldData, EntitySpawn

__all__ = [
    "Xoshiro256StarStar",
    "Mulberry32",
    "seed_to_uint64",
    "format_seed_code",
    "SimplexNoise2D",
    "classify_autumn_biomes",
    "compute_wind_vector_field",
    "step_cellular_automata_b678_s345678",
    "sculpt_connected_topology",
    "compute_dijkstra_distance_field",
    "find_connected_clearings",
    "CANONICAL_47_MASKS",
    "MASK_TO_47_INDEX",
    "RAW_TO_47_LUT",
    "compute_47_blob_grid",
    "compute_4dir_mask_grid",
    "fast_poisson_disk_sampling",
    "distribute_ecological_props",
    "PropPlacement",
    "StructurePlacement",
    "astar_shortest_path",
    "compute_flow_field_vectors",
    "synthesize_autumn_structures",
    "generate_autumn_world",
    "WorldData",
    "EntitySpawn",
]
