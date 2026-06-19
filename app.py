#!/usr/bin/env python3
"""
app.py - A cover-flow style app launcher for a Raspberry Pi Zero W with a
2.13" e-Paper (V4) display and a KY-040 rotary encoder.

Three slots are shown at once: the focused app sits large in a card in the
middle, its neighbors peek in smaller on the sides, and a slot is simply left
empty when there's no app there (so with two apps one side is blank). Turning
the knob moves the focus; pressing it selects the focused app (for now, logs).

Layout on the Pi:
    app.py
    assets/album.png       (grayscale master icon)
    assets/settings.png    (grayscale master icon)
"""

from __future__ import annotations

import logging
import signal
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image, ImageDraw, ImageFont
from gpiozero import RotaryEncoder, Button
from waveshare_epd import epd2in13_V4

log = logging.getLogger("launcher")

# --------------------------------------------------------------------------
# Configuration - everything you'd reasonably tweak lives here.
# --------------------------------------------------------------------------

# KY-040 wiring (BCM pin numbers).
CLK_PIN = 5
DT_PIN = 27
SW_PIN = 22

# Panel size in landscape orientation (pixels).
SCREEN_W, SCREEN_H = 250, 122

# Where the grayscale master icons live, relative to this file.
ASSET_DIR = Path(__file__).resolve().parent / "assets"

# Fonts.
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NAME_FONT_SIZE = 15

# Carousel layout (all in pixels).
ICON_CENTER_Y = 46     # vertical center line that all icons share
CENTER_ICON = 52       # size of the focused (middle) icon
SIDE_ICON = 32         # size of the peeking neighbor icons
SIDE_OFFSET = 68       # horizontal distance from center to a side icon
CARD_PAD = 6           # gap between the focused icon and its card border
CARD_RADIUS = 8        # corner radius of the focused card
CARD_LINE_WIDTH = 2    # line thickness of the focused card
LABEL_GAP = 3          # gap between the card and the name
ICON_THRESHOLD = 160   # grayscale < this becomes black when sizing icons

# Page dots.
DOT_RADIUS = 2
DOT_GAP = 9            # horizontal spacing between dot centers
DOT_TOP_GAP = 5        # gap between the name and the dots

# Behaviour.
WRAP_SELECTION = False  # True = wrap around at the ends; False = stop at ends

# How often a slow full refresh runs to clear e-ink "ghosting". Every Nth
# screen update is a full refresh; the rest are fast partial refreshes.
FULL_REFRESH_EVERY = 15


# --------------------------------------------------------------------------
# Domain model
# --------------------------------------------------------------------------

@dataclass
class App:
    """One launchable app: a name, a master icon, and a select action.

    The icon file is a high-resolution grayscale "master"; `icon(size)`
    produces a crisp 1-bit version at any requested size and caches it.
    """

    name: str
    icon_path: Path
    on_select: Callable[["App"], None] | None = None
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
                lambda p: 0 if p < ICON_THRESHOLD else 255, mode="1")
        return self._cache[size]

    def select(self) -> None:
        if self.on_select is not None:
            self.on_select(self)


# --------------------------------------------------------------------------
# Rendering - pure, hardware-free, easy to unit test.
# --------------------------------------------------------------------------

class HomeScreen:
    """Renders the cover-flow home screen to a PIL image."""

    def __init__(self, apps: Sequence[App], width: int, height: int) -> None:
        self.apps = apps
        self.width = width
        self.height = height
        self.font = ImageFont.truetype(FONT_PATH, NAME_FONT_SIZE)
        self._cx = width // 2
        self._card_half = CENTER_ICON // 2 + CARD_PAD

    def render(self, selected: int) -> Image.Image:
        image = Image.new("1", (self.width, self.height), 255)  # white
        draw = ImageDraw.Draw(image)
        # Neighbors first so the center card always sits visually on top.
        self._draw_neighbor(image, selected - 1, self._cx - SIDE_OFFSET)
        self._draw_neighbor(image, selected + 1, self._cx + SIDE_OFFSET)
        self._draw_center(image, draw, selected)
        self._draw_dots(draw, selected)
        return image

    @staticmethod
    def _paste_centered(image: Image.Image, icon: Image.Image, cx: int, cy: int) -> None:
        image.paste(icon, (cx - icon.width // 2, cy - icon.height // 2))

    def _draw_neighbor(self, image: Image.Image, index: int, cx: int) -> None:
        """Draw a small side icon, or nothing if that slot is off the ends."""
        if 0 <= index < len(self.apps):
            self._paste_centered(image, self.apps[index].icon(SIDE_ICON),
                                 cx, ICON_CENTER_Y)

    def _draw_center(self, image: Image.Image, draw: ImageDraw.ImageDraw,
                     selected: int) -> None:
        cx, half = self._cx, self._card_half
        draw.rounded_rectangle(
            (cx - half, ICON_CENTER_Y - half, cx + half, ICON_CENTER_Y + half),
            radius=CARD_RADIUS, outline=0, width=CARD_LINE_WIDTH)
        self._paste_centered(image, self.apps[selected].icon(CENTER_ICON),
                             cx, ICON_CENTER_Y)

        name = self.apps[selected].name
        bbox = draw.textbbox((0, 0), name, font=self.font)
        text_w = bbox[2] - bbox[0]
        draw.text((cx - text_w // 2 - bbox[0], ICON_CENTER_Y + half + LABEL_GAP),
                  name, font=self.font, fill=0)

    def _draw_dots(self, draw: ImageDraw.ImageDraw, selected: int) -> None:
        count = len(self.apps)
        if count < 2:
            return
        cx = self._cx
        span = (count - 1) * DOT_GAP
        y = ICON_CENTER_Y + self._card_half + LABEL_GAP + NAME_FONT_SIZE + DOT_TOP_GAP
        for i in range(count):
            x = cx - span // 2 + i * DOT_GAP
            box = (x - DOT_RADIUS, y - DOT_RADIUS, x + DOT_RADIUS, y + DOT_RADIUS)
            draw.ellipse(box, fill=0) if i == selected else draw.ellipse(box, outline=0)


# --------------------------------------------------------------------------
# Display controller - owns the panel and serializes all refreshes.
# --------------------------------------------------------------------------

class EInkDisplay:
    """
    Wraps the e-Paper panel behind a simple `show(image)` call.

    A single background thread performs the (slow) refreshes so the input
    callbacks never block. If several updates arrive while one is drawing,
    only the most recent image is kept - so fast knob spins don't pile up.
    """

    def __init__(self) -> None:
        self._epd = epd2in13_V4.EPD()
        self._latest: Image.Image | None = None
        self._wake = threading.Event()
        self._running = True
        self._refresh_count = 0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._epd.init()
        self._epd.Clear(0xFF)
        self._thread.start()

    def show(self, image: Image.Image) -> None:
        """Request that `image` be displayed. Returns immediately."""
        self._latest = image
        self._wake.set()

    def _run(self) -> None:
        while self._running:
            self._wake.wait()
            self._wake.clear()
            image = self._latest
            if image is not None:
                self._draw(image)

    def _draw(self, image: Image.Image) -> None:
        buffer = self._epd.getbuffer(image)
        # Periodically (and on the very first draw) do a full refresh to keep
        # ghosting from building up; otherwise use the fast partial path.
        if self._refresh_count % FULL_REFRESH_EVERY == 0:
            self._epd.display(buffer)
            self._epd.displayPartBaseImage(buffer)  # reset partial baseline
        else:
            self._epd.displayPartial(buffer)
        self._refresh_count += 1

    def close(self) -> None:
        self._running = False
        self._wake.set()  # unblock the worker so it can exit
        self._thread.join(timeout=2)
        self._epd.sleep()
        epd2in13_V4.epdconfig.module_exit(cleanup=True)


# --------------------------------------------------------------------------
# Launcher - wires hardware input to selection state and redraws.
# --------------------------------------------------------------------------

class Launcher:
    def __init__(self, apps: Sequence[App], display: EInkDisplay) -> None:
        self.apps = apps
        self.display = display
        self.home = HomeScreen(apps, SCREEN_W, SCREEN_H)
        self.selected = 0
        self._lock = threading.Lock()

        self._encoder = RotaryEncoder(CLK_PIN, DT_PIN, max_steps=0)
        self._button = Button(SW_PIN, pull_up=True, bounce_time=0.05)
        # If left/right feel reversed, swap these two bindings.
        self._encoder.when_rotated_clockwise = lambda: self._move(+1)
        self._encoder.when_rotated_counter_clockwise = lambda: self._move(-1)
        self._button.when_pressed = self._select

    def start(self) -> None:
        self._redraw()  # draw the initial home screen (Album focused)

    def _move(self, delta: int) -> None:
        with self._lock:
            new = self.selected + delta
            if WRAP_SELECTION:
                new %= len(self.apps)
            else:
                new = max(0, min(new, len(self.apps) - 1))
            if new == self.selected:
                return  # already at the end (no wrap) - nothing to redraw
            self.selected = new
        self._redraw()

    def _select(self) -> None:
        app = self.apps[self.selected]
        log.info("Selected app: %s", app.name)
        app.select()

    def _redraw(self) -> None:
        self.display.show(self.home.render(self.selected))


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def build_apps() -> list[App]:
    return [
        App("Album", ASSET_DIR / "album.png"),
        App("Uploader", ASSET_DIR / "uploader.png"),
        App("Settings", ASSET_DIR / "settings.png"),
    ]


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    display = EInkDisplay()
    display.start()
    try:
        launcher = Launcher(build_apps(), display)
        launcher.start()
        log.info("Launcher ready. Turn to move, press to select. Ctrl+C to quit.")
        signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Shutting down.")
        display.close()


if __name__ == "__main__":
    main()
