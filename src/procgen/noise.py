"""
Multi-Octave Simplex / Gradient Noise & Fractional Brownian Motion (fBm) Synthesizer.

Implements:
- Deterministic 2D Simplex & Perlin Gradient Noise seeded via Xoshiro256**
- Multi-Octave Fractional Brownian Motion (fBm):
    H(x, y) = sum_{i=0}^{n-1} persistence^i * Noise(lacunarity^i * x, lacunarity^i * y)
- Biome synthesis matrices:
    1. Elevation Map (cliffs, forest floor, basins)
    2. Moisture & Decay Map (wet crimson fungal soil vs. dry golden leaf corridors)
    3. 2D Wind Vector Field (curl-like aerodynamic flow for Verlet leaf particles)
"""

from __future__ import annotations
import math
from typing import Tuple, Union
import numpy as np
from src.procgen.prng import Xoshiro256StarStar

# 12-direction 2D gradient vectors on the unit circle
_GRAD2 = np.array(
    [
        [1.0, 1.0],
        [-1.0, 1.0],
        [1.0, -1.0],
        [-1.0, -1.0],
        [1.0, 0.0],
        [-1.0, 0.0],
        [0.0, 1.0],
        [0.0, -1.0],
        [0.8660254, 0.5],
        [-0.8660254, 0.5],
        [0.8660254, -0.5],
        [-0.8660254, -0.5],
    ],
    dtype=np.float64,
)

# 2D Simplex skew constants
_F2 = 0.5 * (math.sqrt(3.0) - 1.0)
_G2 = (3.0 - math.sqrt(3.0)) / 6.0


class SimplexNoise2D:
    """
    Deterministic 2D Simplex & Gradient Noise synthesizer.
    Provides both fast NumPy grid evaluation and scalar continuous evaluation.
    """

    def __init__(self, prng: Union[Xoshiro256StarStar, str, int]) -> None:
        if not isinstance(prng, Xoshiro256StarStar):
            prng = Xoshiro256StarStar(prng)
        base_perm = list(range(256))
        prng.shuffle(base_perm)
        self.perm = np.array(base_perm + base_perm, dtype=np.int32)
        self.perm_mod12 = (self.perm % 12).astype(np.int32)

    def sample(self, x: float, y: float) -> float:
        """
        Evaluates 2D Simplex noise at scalar coordinates (x, y).
        Returns value in [-1.0, 1.0].
        """
        s = (x + y) * _F2
        i = math.floor(x + s)
        j = math.floor(y + s)
        t = (i + j) * _G2
        X0 = i - t
        Y0 = j - t
        x0 = x - X0
        y0 = y - Y0

        if x0 > y0:
            i1, j1 = 1, 0
        else:
            i1, j1 = 0, 1

        x1 = x0 - i1 + _G2
        y1 = y0 - j1 + _G2
        x2 = x0 - 1.0 + 2.0 * _G2
        y2 = y0 - 1.0 + 2.0 * _G2

        ii = i & 255
        jj = j & 255

        gi0 = self.perm_mod12[ii + self.perm[jj]]
        gi1 = self.perm_mod12[ii + i1 + self.perm[jj + j1]]
        gi2 = self.perm_mod12[ii + 1 + self.perm[jj + 1]]

        n0 = 0.0
        t0 = 0.5 - x0 * x0 - y0 * y0
        if t0 >= 0.0:
            t0 *= t0
            g0 = _GRAD2[gi0]
            n0 = t0 * t0 * (g0[0] * x0 + g0[1] * y0)

        n1 = 0.0
        t1 = 0.5 - x1 * x1 - y1 * y1
        if t1 >= 0.0:
            t1 *= t1
            g1 = _GRAD2[gi1]
            n1 = t1 * t1 * (g1[0] * x1 + g1[1] * y1)

        n2 = 0.0
        t2 = 0.5 - x2 * x2 - y2 * y2
        if t2 >= 0.0:
            t2 *= t2
            g2 = _GRAD2[gi2]
            n2 = t2 * t2 * (g2[0] * x2 + g2[1] * y2)

        return float(70.0 * (n0 + n1 + n2))

    def sample_grid(
        self, width: int, height: int, scale: float = 0.06, offset_x: float = 0.0, offset_y: float = 0.0
    ) -> np.ndarray:
        """
        Vectorized 2D Simplex noise over a (height, width) grid.
        Returns a float64 ndarray with values in [-1.0, 1.0].
        """
        xs = (np.arange(width, dtype=np.float64) + offset_x) * scale
        ys = (np.arange(height, dtype=np.float64) + offset_y) * scale
        x, y = np.meshgrid(xs, ys)

        s = (x + y) * _F2
        i = np.floor(x + s).astype(np.int32)
        j = np.floor(y + s).astype(np.int32)
        t = (i + j) * _G2
        x0 = x - (i - t)
        y0 = y - (j - t)

        i1 = (x0 > y0).astype(np.int32)
        j1 = 1 - i1

        x1 = x0 - i1 + _G2
        y1 = y0 - j1 + _G2
        x2 = x0 - 1.0 + 2.0 * _G2
        y2 = y0 - 1.0 + 2.0 * _G2

        ii = i & 255
        jj = j & 255

        gi0 = self.perm_mod12[ii + self.perm[jj]]
        gi1 = self.perm_mod12[ii + i1 + self.perm[jj + j1]]
        gi2 = self.perm_mod12[ii + 1 + self.perm[jj + 1]]

        t0 = np.maximum(0.0, 0.5 - x0 * x0 - y0 * y0)
        t0_4 = (t0 * t0) * (t0 * t0)
        n0 = t0_4 * (_GRAD2[gi0, 0] * x0 + _GRAD2[gi0, 1] * y0)

        t1 = np.maximum(0.0, 0.5 - x1 * x1 - y1 * y1)
        t1_4 = (t1 * t1) * (t1 * t1)
        n1 = t1_4 * (_GRAD2[gi1, 0] * x1 + _GRAD2[gi1, 1] * y1)

        t2 = np.maximum(0.0, 0.5 - x2 * x2 - y2 * y2)
        t2_4 = (t2 * t2) * (t2 * t2)
        n2 = t2_4 * (_GRAD2[gi2, 0] * x2 + _GRAD2[gi2, 1] * y2)

        return np.clip(70.0 * (n0 + n1 + n2), -1.0, 1.0)

    def fbm_scalar(
        self,
        x: float,
        y: float,
        octaves: int = 4,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        scale: float = 0.05,
    ) -> float:
        """
        Evaluates multi-octave Fractional Brownian Motion (fBm) at scalar (x, y).
        Normalized to [0.0, 1.0].
        """
        total = 0.0
        amplitude = 1.0
        frequency = scale
        max_amp = 0.0
        for _ in range(octaves):
            total += amplitude * self.sample(x * frequency, y * frequency)
            max_amp += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        norm = (total / max_amp) * 0.5 + 0.5
        return max(0.0, min(1.0, norm))

    def fbm_grid(
        self,
        width: int,
        height: int,
        octaves: int = 4,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        scale: float = 0.055,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
    ) -> np.ndarray:
        """
        Synthesizes a 2D Fractional Brownian Motion (fBm) matrix:
            H(x, y) = sum_{i=0}^{n-1} persistence^i * Noise(lacunarity^i * x, lacunarity^i * y)
        Normalized to [0.0, 1.0].
        """
        accum = np.zeros((height, width), dtype=np.float64)
        amplitude = 1.0
        freq = scale
        max_amp = 0.0

        for octave_idx in range(octaves):
            # Offset each octave slightly to eliminate axial alignment artifacts
            ox = offset_x + octave_idx * 37.17
            oy = offset_y + octave_idx * 73.91
            layer = self.sample_grid(width, height, scale=freq, offset_x=ox, offset_y=oy)
            accum += amplitude * layer
            max_amp += amplitude
            amplitude *= persistence
            freq *= lacunarity

        # Normalize from [-max_amp, max_amp] into [0.0, 1.0]
        res = (accum / max_amp) * 0.5 + 0.5
        return np.clip(res, 0.0, 1.0)


# Biome classification constants
BIOME_CLIFF_VOID = 0       # High elevation impassable ancient stone / dense canopy wall
BIOME_DAMP_DECAY = 1       # High moisture: muddy soil, crimson maple leaves, spore mushrooms
BIOME_AMBER_GROVE = 2      # Balanced moisture: classic burnt amber & rust autumn floor
BIOME_CRISP_GOLDEN = 3     # Dry corridor: crunchy golden birch leaves, wind trails & speed boost


def classify_autumn_biomes(
    elevation: np.ndarray,
    moisture: np.ndarray,
    walkable_mask: np.ndarray,
) -> np.ndarray:
    """
    Combines Elevation, Moisture/Decay, and Topological Walkable Mask into
    a discrete autumn biome matrix.
    """
    height, width = elevation.shape
    biomes = np.full((height, width), BIOME_CLIFF_VOID, dtype=np.int32)

    is_floor = walkable_mask == 0
    # Damp decay where moisture >= 0.60
    damp_mask = is_floor & (moisture >= 0.60)
    # Crisp golden leaf corridor where moisture <= 0.40
    dry_mask = is_floor & (moisture <= 0.40)
    # Balanced burnt amber grove in between
    amber_mask = is_floor & (~damp_mask) & (~dry_mask)

    biomes[damp_mask] = BIOME_DAMP_DECAY
    biomes[amber_mask] = BIOME_AMBER_GROVE
    biomes[dry_mask] = BIOME_CRISP_GOLDEN
    return biomes


def compute_wind_vector_field(
    noise_gen: SimplexNoise2D,
    width: int,
    height: int,
    time_sec: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes a 2D Wind Vector Field (vx, vy) across the map grid.
    Prevailing autumn wind blows towards the East-Southeast with turbulent eddies.
    """
    angle_field = noise_gen.fbm_grid(
        width,
        height,
        octaves=2,
        persistence=0.5,
        lacunarity=2.0,
        scale=0.07,
        offset_x=time_sec * 1.8,
        offset_y=time_sec * 0.9,
    )
    # Map [0, 1] to angle around prevailing autumn breeze (~20 degrees)
    theta = (angle_field - 0.5) * (math.pi * 0.85) + 0.32
    speed = 0.65 + 0.65 * angle_field
    vx = np.cos(theta) * speed
    vy = np.sin(theta) * speed * 0.6 + 0.25
    return vx, vy
