"""Navigator - a stack of screens plus input routing.

Hardware-free: it only talks to the display and the current screen, so it can
be unit-tested with fakes. Input arrives via `handle_rotate`/`handle_press`
(wired up to RotaryInput in app.py).
"""

from __future__ import annotations

from .display import EInkDisplay
from .screens.base import Screen


class Navigator:
    def __init__(self, display: EInkDisplay) -> None:
        self._display = display
        self._stack: list[Screen] = []

    @property
    def top(self) -> Screen:
        return self._stack[-1]

    # Stack management --------------------------------------------------
    def push(self, screen: Screen) -> None:
        screen.nav = self
        self._stack.append(screen)
        self._render(full=True)  # big layout change -> full refresh

    def pop(self) -> None:
        if len(self._stack) > 1:        # never pop the root (home) screen
            self._stack.pop()
            self._render(full=True)

    # Input routing -----------------------------------------------------
    def handle_rotate(self, delta: int) -> None:
        if self.top.on_rotate(delta):
            self._render()

    def handle_press(self) -> None:
        if self.top.on_press():
            self._render()

    # Internal ----------------------------------------------------------
    def _render(self, full: bool = False) -> None:
        self._display.show(self.top.render(), full=full)
