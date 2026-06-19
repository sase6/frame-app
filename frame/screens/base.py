"""The Screen interface every view implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:  # only for type hints; no import cycle at runtime
    from ..navigator import Navigator


class Screen(ABC):
    """One full-screen view.

    The navigator sets `nav` when the screen is pushed, giving the screen a
    handle to push or pop other screens. `on_rotate`/`on_press` return True
    iff something changed and the screen needs redrawing - so a no-op (e.g.
    turning past the end of a list) never triggers a slow e-ink refresh.
    """

    nav: "Navigator"

    @abstractmethod
    def render(self) -> Image.Image:
        """Draw the whole screen and return a 1-bit PIL image."""

    def on_rotate(self, delta: int) -> bool:
        """Handle a knob turn (+1 right / -1 left). Return True if changed."""
        return False

    def on_press(self) -> bool:
        """Handle a button press. Return True if changed."""
        return False
