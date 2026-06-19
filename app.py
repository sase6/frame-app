#!/usr/bin/env python3
"""Cover-flow app launcher for a Raspberry Pi Zero W with a 2.13" e-Paper
(V4) display and a KY-040 rotary encoder.

Run on the Pi:
    python3 app.py

The pieces live in the `frame` package:
    frame/config.py     - everything you'd tweak
    frame/display.py    - the e-Paper panel
    frame/input.py      - the rotary encoder
    frame/navigator.py  - the screen stack
    frame/screens/      - home carousel, settings, ...
"""

from __future__ import annotations

import logging
import signal

from frame import config
from frame.display import EInkDisplay
from frame.input import RotaryInput
from frame.models import App
from frame.navigator import Navigator
from frame.screens.home import HomeScreen
from frame.screens.settings import SettingsScreen
from frame.store import SettingsStore

log = logging.getLogger("launcher")


def build_apps(store: SettingsStore) -> list[App]:
    """The carousel, in order. Settings opens its own screen on select."""
    return [
        App("Album", config.ASSET_DIR / "album.png"),
        App("Uploader", config.ASSET_DIR / "uploader.png"),
        App("Settings", config.ASSET_DIR / "settings.png",
            build_screen=lambda: SettingsScreen(store)),
    ]


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    store = SettingsStore(config.SETTINGS_PATH)
    display = EInkDisplay()
    display.start()
    try:
        nav = Navigator(display)
        nav.push(HomeScreen(build_apps(store)))  # draws the initial home screen
        # `controller` must stay referenced for the life of the program, or
        # gpiozero will garbage-collect and close the encoder/button. The
        # local lives until main() returns (after signal.pause unblocks).
        controller = RotaryInput(on_rotate=nav.handle_rotate,  # noqa: F841
                                 on_press=nav.handle_press)
        log.info("Launcher ready. Turn to move, press to select. Ctrl+C to quit.")
        signal.pause()
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Shutting down.")
        display.close()


if __name__ == "__main__":
    main()
