"""Small, shared drawing helpers and a font cache.

Keeping these in one place means every screen draws text and icons the same
way, and there are no duplicated one-liners scattered across the screens.
"""

from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from . import config


@lru_cache(maxsize=None)
def font(size: int) -> ImageFont.FreeTypeFont:
    """Return a (cached) bold font at the requested pixel size."""
    return ImageFont.truetype(config.FONT_PATH, size)


def text_size(draw: ImageDraw.ImageDraw, text: str,
              fnt: ImageFont.FreeTypeFont) -> tuple[int, int, tuple[int, int, int, int]]:
    """Return (width, height, bbox) of `text`. bbox lets callers correct for
    the font's left/top bearing when positioning precisely."""
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox


def paste_centered(image: Image.Image, icon: Image.Image, cx: int, cy: int) -> None:
    """Paste `icon` so its center sits at (cx, cy)."""
    image.paste(icon, (cx - icon.width // 2, cy - icon.height // 2))
