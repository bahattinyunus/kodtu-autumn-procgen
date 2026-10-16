"""
Pixel-Perfect Integer-Scaled Viewport & Camera Matrix.

Enforces Section 1 & Section 4 of README.md:
- Native internal viewport resolution: 320x180 (16:9 aspect ratio, 20x11.25 tiles at 16x16)
- Zero sub-pixel jitter: Camera translation and entity rendering coordinates are rounded
  to exact integers (`round(pos.x), round(pos.y)`).
- Strict Nearest-Neighbor Integer Scaling to window dimensions.
"""

from __future__ import annotations
import math
from typing import Tuple

NATIVE_WIDTH = 320
NATIVE_HEIGHT = 180
TILE_SIZE = 16


class PixelCamera:
    """
    2D Pixel-Perfect Camera with smooth exponential damping, map boundary clamping,
    trauma-based directional screen shake, and frustum culling bounds.
    """

    def __init__(self, viewport_w: int = NATIVE_WIDTH, viewport_h: int = NATIVE_HEIGHT) -> None:
        self.viewport_w = viewport_w
        self.viewport_h = viewport_h
        self.true_x = 0.0
        self.true_y = 0.0
        self.x = 0
        self.y = 0
        self.trauma = 0.0
        self.shake_timer = 0.0

    def snap_to(self, target_px_x: float, target_px_y: float, world_px_w: int, world_px_h: int) -> None:
        """Immediately centers the camera on (target_px_x, target_px_y) in pixel space."""
        cx = target_px_x - self.viewport_w * 0.5
        cy = target_px_y - self.viewport_h * 0.5
        self.true_x = max(0.0, min(float(max(0, world_px_w - self.viewport_w)), cx))
        self.true_y = max(0.0, min(float(max(0, world_px_h - self.viewport_h)), cy))
        self.x = int(round(self.true_x))
        self.y = int(round(self.true_y))

    def add_trauma(self, amount: float) -> None:
        """Adds trauma in [0.0, 1.0] for pixel-snapped screen shake."""
        self.trauma = min(1.0, self.trauma + amount)

    def update(
        self,
        dt: float,
        target_px_x: float,
        target_px_y: float,
        world_px_w: int,
        world_px_h: int,
    ) -> None:
        """Updates smooth tracking and rounds final camera coordinates to global pixel grid."""
        desired_x = target_px_x - self.viewport_w * 0.5
        desired_y = target_px_y - self.viewport_h * 0.5

        max_x = float(max(0, world_px_w - self.viewport_w))
        max_y = float(max(0, world_px_h - self.viewport_h))
        desired_x = max(0.0, min(max_x, desired_x))
        desired_y = max(0.0, min(max_y, desired_y))

        # Frame-rate independent damping
        alpha = 1.0 - math.exp(-10.0 * dt)
        self.true_x += (desired_x - self.true_x) * alpha
        self.true_y += (desired_y - self.true_y) * alpha

        shake_ox = 0.0
        shake_oy = 0.0
        if self.trauma > 0.01:
            self.shake_timer += dt * 45.0
            mag = (self.trauma * self.trauma) * 4.0
            shake_ox = math.sin(self.shake_timer * 1.7) * mag
            shake_oy = math.cos(self.shake_timer * 2.3) * mag
            self.trauma = max(0.0, self.trauma - dt * 2.4)
        else:
            self.trauma = 0.0

        # Strict integer rounding to prevent sub-pixel swimming
        self.x = int(round(self.true_x + shake_ox))
        self.y = int(round(self.true_y + shake_oy))
        self.x = max(0, min(int(max_x), self.x))
        self.y = max(0, min(int(max_y), self.y))

    def world_to_screen(self, world_px_x: float, world_px_y: float) -> Tuple[int, int]:
        """Converts world pixel coordinates to integer-snapped screen coordinates."""
        return (int(round(world_px_x)) - self.x, int(round(world_px_y)) - self.y)

    def get_visible_tile_bounds(self, map_w: int, map_h: int, margin_tiles: int = 2) -> Tuple[int, int, int, int]:
        """
        Computes the frustum-culled tile index bounds (x0, y0, x1, y1) overlapping the viewport.
        Used by the tile batch renderer and particle culling.
        """
        x0 = max(0, (self.x // TILE_SIZE) - margin_tiles)
        y0 = max(0, (self.y // TILE_SIZE) - margin_tiles)
        x1 = min(map_w, ((self.x + self.viewport_w) // TILE_SIZE) + 1 + margin_tiles)
        y1 = min(map_h, ((self.y + self.viewport_h) // TILE_SIZE) + 1 + margin_tiles)
        return x0, y0, x1, y1

    @staticmethod
    def compute_integer_viewport_rect(window_w: int, window_h: int) -> Tuple[int, int, int, int, int]:
        """
        Computes the largest integer scale factor for NATIVE_WIDTH x NATIVE_HEIGHT
        inside (window_w, window_h) along with centered letterbox offsets.
        Returns (scale, offset_x, offset_y, scaled_w, scaled_h).
        """
        scale_x = max(1, window_w // NATIVE_WIDTH)
        scale_y = max(1, window_h // NATIVE_HEIGHT)
        scale = max(1, min(scale_x, scale_y))
        scaled_w = NATIVE_WIDTH * scale
        scaled_h = NATIVE_HEIGHT * scale
        offset_x = (window_w - scaled_w) // 2
        offset_y = (window_h - scaled_h) // 2
        return scale, offset_x, offset_y, scaled_w, scaled_h
