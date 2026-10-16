"""
Crisp Pixel-Art Bitmap Font & Micro-Number Renderer.

Ensures 100% non-antialiased pixel text rendering on the 320x180 internal canvas
using Deep Void (#1A1118) 1-pixel drop shadows and Sunlit Birch (#F5D67B) / Autumn Mist (#D4C8BE)
glyphs.
"""

from __future__ import annotations
from typing import Dict, Tuple
import pygame

from src.core.palette import DEEP_VOID, SUNLIT_BIRCH

# 3x5 micro-pixel bitmap glyphs for numbers & hex/debug indices on 16x16 tiles
_MICRO_DIGITS: Dict[str, Tuple[int, ...]] = {
    "0": (0b111, 0b101, 0b101, 0b101, 0b111),
    "1": (0b010, 0b110, 0b010, 0b010, 0b111),
    "2": (0b111, 0b001, 0b111, 0b100, 0b111),
    "3": (0b111, 0b001, 0b111, 0b001, 0b111),
    "4": (0b101, 0b101, 0b111, 0b001, 0b001),
    "5": (0b111, 0b100, 0b111, 0b001, 0b111),
    "6": (0b111, 0b100, 0b111, 0b101, 0b111),
    "7": (0b111, 0b001, 0b010, 0b010, 0b010),
    "8": (0b111, 0b101, 0b111, 0b101, 0b111),
    "9": (0b111, 0b101, 0b111, 0b001, 0b111),
}


def draw_micro_number(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    color: Tuple[int, int, int] = SUNLIT_BIRCH,
    shadow: Tuple[int, int, int] = DEEP_VOID,
) -> None:
    """
    Draws a 3x5 micro-bitmap number string at integer coordinates (x, y).
    Ideal for rendering 47-tile blob bitmask indices (0..46) inside 16x16 tiles in [F2] mode.
    """
    cursor_x = int(x)
    base_y = int(y)
    w, h = surface.get_size()
    for ch in text:
        rows = _MICRO_DIGITS.get(ch)
        if rows is None:
            cursor_x += 3
            continue
        for ry, row_bits in enumerate(rows):
            for rx in range(3):
                if (row_bits >> (2 - rx)) & 1:
                    px = cursor_x + rx
                    py = base_y + ry
                    if 0 <= px + 1 < w and 0 <= py + 1 < h:
                        surface.set_at((px + 1, py + 1), shadow)
                    if 0 <= px < w and 0 <= py < h:
                        surface.set_at((px, py), color)
        cursor_x += 4


class PixelFontRenderer:
    """
    Renders non-antialiased pixel-art UI text with 1px Deep Void outline/shadow.
    """

    def __init__(self) -> None:
        pygame.font.init()
        self.font_sm = pygame.font.SysFont("consolas,couriernew,monospace", 9, bold=True)
        self.font_md = pygame.font.SysFont("consolas,couriernew,monospace", 11, bold=True)
        self._cache: Dict[Tuple[str, Tuple[int, int, int], bool], pygame.Surface] = {}

    def draw_text(
        self,
        surface: pygame.Surface,
        text: str,
        x: int,
        y: int,
        color: Tuple[int, int, int] = SUNLIT_BIRCH,
        shadow_color: Tuple[int, int, int] = DEEP_VOID,
        medium: bool = False,
        align_right: bool = False,
        align_center: bool = False,
    ) -> int:
        """
        Draws crisp non-antialiased text onto `surface` at integer pixel coordinates.
        Returns rendered width in pixels.
        """
        key = (text, color, medium)
        cached = self._cache.get(key)
        if cached is None:
            fnt = self.font_md if medium else self.font_sm
            fg_surf = fnt.render(text, False, color)
            sh_surf = fnt.render(text, False, shadow_color)
            tw, th = fg_surf.get_size()
            combined = pygame.Surface((tw + 1, th + 1), pygame.SRCALPHA)
            combined.blit(sh_surf, (1, 1))
            combined.blit(fg_surf, (0, 0))
            if len(self._cache) > 512:
                self._cache.clear()
            self._cache[key] = combined
            cached = combined

        tw = cached.get_width()
        draw_x = int(x)
        if align_right:
            draw_x -= tw
        elif align_center:
            draw_x -= tw // 2
        surface.blit(cached, (draw_x, int(y)))
        return tw
