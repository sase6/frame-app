"""Domain models shared across screens."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PIL import Image

from . import config

if TYPE_CHECKING:  # avoid an import cycle; only needed for type hints
    from .screens.base import Screen


@dataclass
class App:
    """One launchable app shown in the carousel.

    `icon_path` points at a grayscale master image; `icon(size)` produces a
    crisp 1-bit version at any size and caches it. `build_screen`, if set, is
    a factory the navigator calls to open the app's screen when selected;
    apps without one simply log on select (for now).
    """

    name: str
    icon_path: Path
    build_screen: Callable[[], "Screen"] | None = None
    _master: Image.Image | None = field(default=None, init=False, repr=False)
    _cache: dict[int, Image.Image] = field(default_factory=dict, init=False, repr=False)

    @property
    def master(self) -> Image.Image:
        if self._master is None:
            self._master = Image.open(self.icon_path).convert("L")
        return self._master

    def icon(self, size: int) -> Image.Image:
        if size not in self._cache:
            scaled = self.master.resize((size, size), Image.LANCZOS)
            self._cache[size] = scaled.point(
                lambda p: 0 if p < config.ICON_THRESHOLD else 255, mode="1")
        return self._cache[size]
