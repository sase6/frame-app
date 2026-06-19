"""HomeScreen - the cover-flow carousel of apps.

The focused app sits large in a card in the middle; its neighbors peek in
smaller on the sides, and a slot is left empty when there's no app there.
Turning the knob moves the focus; pressing opens the focused app's screen
(or just logs, for apps without one yet).
"""

from __future__ import annotations

import logging
from typing import Sequence

from PIL import Image, ImageDraw

from .. import config, ui
from ..models import App
from .base import Screen

log = logging.getLogger("launcher.home")


class HomeScreen(Screen):
    def __init__(self, apps: Sequence[App]) -> None:
        self.apps = apps
        self.font = ui.font(config.NAME_FONT_SIZE)
        self._cx = config.SCREEN_W // 2
        self._card_half = config.CENTER_ICON // 2 + config.CARD_PAD
        self.selected = (config.DEFAULT_APP_INDEX
                         if len(apps) > config.DEFAULT_APP_INDEX else 0)

    # Input -------------------------------------------------------------
    def on_rotate(self, delta: int) -> bool:
        new = self.selected + delta
        if config.WRAP_SELECTION:
            new %= len(self.apps)
        else:
            new = max(0, min(new, len(self.apps) - 1))
        if new == self.selected:
            return False  # already at the end (no wrap) - nothing to redraw
        self.selected = new
        return True

    def on_press(self) -> bool:
        app = self.apps[self.selected]
        log.info("Selected app: %s", app.name)
        if app.build_screen is not None:
            self.nav.push(app.build_screen())  # push performs its own redraw
        return False

    # Rendering ---------------------------------------------------------
    def render(self) -> Image.Image:
        image = Image.new("1", (config.SCREEN_W, config.SCREEN_H), 255)  # white
        draw = ImageDraw.Draw(image)
        # Neighbors first so the center card always sits visually on top.
        self._draw_neighbor(image, self.selected - 1, self._cx - config.SIDE_OFFSET)
        self._draw_neighbor(image, self.selected + 1, self._cx + config.SIDE_OFFSET)
        self._draw_center(image, draw)
        self._draw_dots(draw)
        return image

    def _draw_neighbor(self, image: Image.Image, index: int, cx: int) -> None:
        if 0 <= index < len(self.apps):
            ui.paste_centered(image, self.apps[index].icon(config.SIDE_ICON),
                              cx, config.ICON_CENTER_Y)

    def _draw_center(self, image: Image.Image, draw: ImageDraw.ImageDraw) -> None:
        cx, half, cy = self._cx, self._card_half, config.ICON_CENTER_Y
        draw.rounded_rectangle(
            (cx - half, cy - half, cx + half, cy + half),
            radius=config.CARD_RADIUS, outline=0, width=config.CARD_LINE_WIDTH)
        ui.paste_centered(image, self.apps[self.selected].icon(config.CENTER_ICON), cx, cy)

        name = self.apps[self.selected].name
        w, _, bbox = ui.text_size(draw, name, self.font)
        draw.text((cx - w // 2 - bbox[0], cy + half + config.LABEL_GAP),
                  name, font=self.font, fill=0)

    def _draw_dots(self, draw: ImageDraw.ImageDraw) -> None:
        count = len(self.apps)
        if count < 2:
            return
        cx = self._cx
        span = (count - 1) * config.DOT_GAP
        y = (config.ICON_CENTER_Y + self._card_half + config.LABEL_GAP
             + config.NAME_FONT_SIZE + config.DOT_TOP_GAP)
        r = config.DOT_RADIUS
        for i in range(count):
            x = cx - span // 2 + i * config.DOT_GAP
            box = (x - r, y - r, x + r, y + r)
            draw.ellipse(box, fill=0) if i == self.selected else draw.ellipse(box, outline=0)
