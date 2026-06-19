"""SettingsScreen - navigate rows, focus one to edit its value, persist.

Two-level focus:
  * navigate: the knob moves the highlight between rows (underlined).
  * edit:     pressing a value row focuses it (bordered); now the knob
              changes its value. Pressing again leaves edit mode and saves.
Action rows (e.g. Back) just run their action when pressed.

Adding a setting later is a one-liner: append another Row to `self.rows`.
"""

from __future__ import annotations

import logging
from typing import Callable

from PIL import Image, ImageDraw

from .. import config, ui
from .base import Screen

log = logging.getLogger("launcher.settings")


# --------------------------------------------------------------------------
# Rows
# --------------------------------------------------------------------------

class Row:
    """A line in the settings list. Subclasses define behaviour."""

    label: str
    editable: bool = False

    def value_text(self) -> str | None:
        """Right-aligned text (e.g. a counter), or None for no value."""
        return None

    def activate(self) -> None:
        """Run when a non-editable row is pressed in navigate mode."""

    def adjust(self, delta: int) -> bool:
        """Change the value in edit mode. Return True if it changed."""
        return False

    def commit(self) -> None:
        """Persist the value (called once, on leaving edit mode)."""


class ActionRow(Row):
    """A row that performs an action when pressed (no value, no edit mode)."""

    editable = False

    def __init__(self, label: str, action: Callable[[], None]) -> None:
        self.label = label
        self._action = action

    def activate(self) -> None:
        self._action()


class IntRow(Row):
    """An integer value with a minimum, optional maximum, and step.

    The working value lives in memory while editing; `commit` writes it out,
    so we persist once when you leave the field - not on every detent.
    """

    editable = True

    def __init__(self, label: str, value: int, on_commit: Callable[[int], None],
                 minimum: int = 0, maximum: int | None = None,
                 step: int = 1, suffix: str = "") -> None:
        self.label = label
        self._value = int(value)
        self._on_commit = on_commit
        self._min = minimum
        self._max = maximum
        self._step = step
        self._suffix = suffix

    def value_text(self) -> str:
        return f"{self._value}{self._suffix}"

    def adjust(self, delta: int) -> bool:
        new = self._value + delta * self._step
        new = max(self._min, new)
        if self._max is not None:
            new = min(self._max, new)
        if new == self._value:
            return False
        self._value = new
        return True

    def commit(self) -> None:
        self._on_commit(self._value)


# --------------------------------------------------------------------------
# Screen
# --------------------------------------------------------------------------

class SettingsScreen(Screen):
    def __init__(self, store) -> None:
        self._title_font = ui.font(config.SETTINGS_TITLE_FONT_SIZE)
        self._row_font = ui.font(config.SETTINGS_ROW_FONT_SIZE)
        self.rows: list[Row] = [
            ActionRow("Back", action=self._go_back),
            IntRow("Delay",
                   value=store.get(config.DELAY_KEY, 0),
                   on_commit=lambda v: store.set(config.DELAY_KEY, v),
                   minimum=config.DELAY_MIN,
                   step=config.DELAY_STEP,
                   suffix=config.DELAY_SUFFIX),
        ]
        self.index = 0        # highlighted row (Back on top)
        self.editing = False  # True once a value row is focused/bordered

    def _go_back(self) -> None:
        self.nav.pop()

    # Input -------------------------------------------------------------
    def on_rotate(self, delta: int) -> bool:
        if self.editing:
            return self.rows[self.index].adjust(delta)
        new = max(0, min(self.index + delta, len(self.rows) - 1))  # clamp, no wrap
        if new == self.index:
            return False
        self.index = new
        return True

    def on_press(self) -> bool:
        row = self.rows[self.index]
        if self.editing:
            self.editing = False  # leave edit mode -> back to underline
            row.commit()          # persist now, not mid-spin
            return True
        if row.editable:
            self.editing = True   # enter edit mode -> bordered
            return True
        row.activate()            # action row (Back) pops and redraws itself
        return False

    # Rendering ---------------------------------------------------------
    def render(self) -> Image.Image:
        image = Image.new("1", (config.SCREEN_W, config.SCREEN_H), 255)
        draw = ImageDraw.Draw(image)
        self._draw_header(draw)
        for i, row in enumerate(self.rows):
            self._draw_row(draw, i, row)
        return image

    def _draw_header(self, draw: ImageDraw.ImageDraw) -> None:
        w, _, bbox = ui.text_size(draw, config.SETTINGS_TITLE, self._title_font)
        cx = config.SCREEN_W // 2
        draw.text((cx - w // 2 - bbox[0], config.SETTINGS_TITLE_Y),
                  config.SETTINGS_TITLE, font=self._title_font, fill=0)
        draw.line((config.SETTINGS_LEFT_MARGIN, config.SETTINGS_DIVIDER_Y,
                   config.SCREEN_W - config.SETTINGS_RIGHT_MARGIN, config.SETTINGS_DIVIDER_Y),
                  fill=0, width=1)

    def _draw_row(self, draw: ImageDraw.ImageDraw, i: int, row: Row) -> None:
        top = config.SETTINGS_ROWS_TOP + i * config.SETTINGS_ROW_HEIGHT
        bottom = top + config.SETTINGS_ROW_HEIGHT
        mid = (top + bottom) // 2
        left = config.SETTINGS_LEFT_MARGIN

        # Label (left aligned, vertically centered in the row slot).
        lw, lh, lbbox = ui.text_size(draw, row.label, self._row_font)
        label_y = mid - lh // 2 - lbbox[1]
        draw.text((left, label_y), row.label, font=self._row_font, fill=0)

        # Value (right aligned), if the row has one.
        value = row.value_text()
        if value is not None:
            vw, vh, vbbox = ui.text_size(draw, value, self._row_font)
            vx = config.SCREEN_W - config.SETTINGS_RIGHT_MARGIN - vw - vbbox[0]
            draw.text((vx, mid - vh // 2 - vbbox[1]), value, font=self._row_font, fill=0)

        # Highlight: a full border while editing, otherwise an underline.
        if i != self.index:
            return
        if self.editing:
            draw.rounded_rectangle(
                (left - config.SETTINGS_BORDER_PAD_X, top + config.SETTINGS_BORDER_PAD_Y,
                 config.SCREEN_W - config.SETTINGS_RIGHT_MARGIN + config.SETTINGS_BORDER_PAD_X,
                 bottom - config.SETTINGS_BORDER_PAD_Y),
                radius=config.SETTINGS_BORDER_RADIUS, outline=0,
                width=config.SETTINGS_BORDER_WIDTH)
        else:
            uy = label_y + lh + config.SETTINGS_UNDERLINE_GAP
            draw.line((left, uy, left + lw, uy), fill=0,
                      width=config.SETTINGS_UNDERLINE_WIDTH)
