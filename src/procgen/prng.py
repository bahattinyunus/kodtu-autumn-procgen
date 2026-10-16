"""
Deterministic Pseudo-Random Number Generators (PRNG) & 64-Bit Seed Serialization.

Implements:
- FNV-1a + SplitMix64 string-to-64-bit seed serialization
- Xoshiro256** (Blackman & Vigna) all-purpose deterministic 64-bit PRNG
- Mulberry32 fast 32-bit coordinate hash PRNG
"""

from __future__ import annotations
from typing import Sequence, TypeVar, List, Union

T = TypeVar("T")

MASK64 = 0xFFFFFFFFFFFFFFFF
MASK32 = 0xFFFFFFFF


def _rotl64(x: int, k: int) -> int:
    """64-bit bitwise left rotation."""
    return ((x << k) & MASK64) | (x >> (64 - k))


def splitmix64(x: int) -> int:
    """
    SplitMix64 bijective hash function.
    Used both to avalanche seed strings and to initialize Xoshiro256** state.
    """
    z = (x + 0x9E3779B97F4A7C15) & MASK64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return (z ^ (z >> 31)) & MASK64


def seed_to_uint64(seed: Union[str, int]) -> int:
    """
    Deterministically serializes any arbitrary string (e.g. 'KODTU2026',
    'KODTU-8492-FALL') or integer into a 64-bit unsigned integer.
    """
    if isinstance(seed, int):
        return splitmix64(seed & MASK64)
    seed_str = str(seed).strip()
    if not seed_str:
        seed_str = "KODTU2026"
    # FNV-1a 64-bit hash followed by SplitMix64 avalanche
    h = 0xCBF29CE484222325
    for byte in seed_str.encode("utf-8"):
        h ^= byte
        h = (h * 0x100000001B3) & MASK64
    return splitmix64(h)


def format_seed_code(seed_uint64: int) -> str:
    """Formats a 64-bit seed integer into a human-shareable KODTU seed code."""
    short_num = (seed_uint64 % 9000) + 1000
    suffixes = ["FALL", "LEAF", "BARK", "MIST", "GOLD", "RUST", "PINE", "MOSS"]
    suffix = suffixes[(seed_uint64 >> 16) & 7]
    return f"KODTU-{short_num}-{suffix}"


class Mulberry32:
    """Fast 32-bit PRNG for tile-coordinate micro-variations."""

    __slots__ = ("state",)

    def __init__(self, seed: int) -> None:
        self.state = seed & MASK32

    def next_uint32(self) -> int:
        self.state = (self.state + 0x6D2B79F5) & MASK32
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & MASK32
        t = (t ^ (t + (((t ^ (t >> 7)) * (t | 61)) & MASK32))) & MASK32
        return (t ^ (t >> 14)) & MASK32

    def random(self) -> float:
        return self.next_uint32() / 4294967296.0


def hash_coords_2d(x: int, y: int, seed: int) -> float:
    """
    O(1) spatial hash returning a deterministic float in [0.0, 1.0)
    for grid coordinates (x, y) and a given seed.
    """
    h = ((x * 374761393) + (y * 668265263) ^ (seed & MASK32)) & MASK32
    h = ((h ^ (h >> 13)) * 1274126177) & MASK32
    h = (h ^ (h >> 16)) & MASK32
    return h / 4294967296.0


class Xoshiro256StarStar:
    """
    Xoshiro256** 64-bit deterministic pseudo-random number generator.
    Period: 2^256 - 1. Zero reliance on Python's global random module.
    """

    __slots__ = ("s0", "s1", "s2", "s3", "seed_str", "seed_uint64")

    def __init__(self, seed: Union[str, int] = "KODTU2026") -> None:
        self.seed_str = str(seed)
        self.seed_uint64 = seed_to_uint64(seed)
        sm = self.seed_uint64
        self.s0 = splitmix64(sm)
        self.s1 = splitmix64(self.s0)
        self.s2 = splitmix64(self.s1)
        self.s3 = splitmix64(self.s2)
        if (self.s0 | self.s1 | self.s2 | self.s3) == 0:
            self.s0 = 1

    def next_uint64(self) -> int:
        """Generates the next 64-bit unsigned integer."""
        result = (_rotl64((self.s1 * 5) & MASK64, 7) * 9) & MASK64
        t = (self.s1 << 17) & MASK64

        self.s2 ^= self.s0
        self.s3 ^= self.s1
        self.s1 ^= self.s2
        self.s0 ^= self.s3

        self.s2 ^= t
        self.s3 = _rotl64(self.s3, 45)
        return result

    def random(self) -> float:
        """Returns a deterministic float in [0.0, 1.0) with 53-bit precision."""
        return (self.next_uint64() >> 11) * (1.0 / (1 << 53))

    def uniform(self, a: float, b: float) -> float:
        """Returns a deterministic float in [a, b)."""
        return a + (b - a) * self.random()

    def randint(self, low: int, high: int) -> int:
        """Returns a deterministic integer in [low, high] inclusive."""
        if high <= low:
            return low
        span = (high - low) + 1
        return low + (self.next_uint64() % span)

    def choice(self, seq: Sequence[T]) -> T:
        """Deterministically chooses an element from a non-empty sequence."""
        if not seq:
            raise ValueError("Cannot choose from an empty sequence")
        idx = self.next_uint64() % len(seq)
        return seq[idx]

    def shuffle(self, seq: List[T]) -> None:
        """In-place deterministic Fisher-Yates shuffle."""
        n = len(seq)
        for i in range(n - 1, 0, -1):
            j = self.next_uint64() % (i + 1)
            seq[i], seq[j] = seq[j], seq[i]

    def fork(self, subsystem_salt: str) -> "Xoshiro256StarStar":
        """
        Creates an independent child PRNG seeded from the current seed + salt.
        Ensures subsystem isolation (e.g. changing particle counts never alters terrain).
        """
        combined = self.seed_uint64 ^ seed_to_uint64(subsystem_salt)
        child = Xoshiro256StarStar(combined)
        child.seed_str = f"{self.seed_str}:{subsystem_salt}"
        return child
