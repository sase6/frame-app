"""e-Paper display controller - owns the panel and serializes refreshes.

A single background thread performs the (slow) refreshes so input callbacks
never block. If several updates arrive while one is drawing, only the most
recent image is kept, so fast knob spins don't pile up.
"""

from __future__ import annotations

import threading

from PIL import Image
from waveshare_epd import epd2in13_V4

from . import config


class EInkDisplay:
    def __init__(self) -> None:
        self._epd = epd2in13_V4.EPD()
        self._latest: Image.Image | None = None
        self._force_full = False
        self._wake = threading.Event()
        self._running = True
        self._refresh_count = 0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._epd.init()
        self._epd.Clear(0xFF)
        self._thread.start()

    def show(self, image: Image.Image, full: bool = False) -> None:
        """Request that `image` be displayed. Returns immediately.

        `full=True` forces a slow full refresh (use on screen transitions to
        clear ghosting). Only the most recent requested image is ever drawn.
        """
        self._latest = image
        if full:
            self._force_full = True
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
        # Full refresh when forced, on the first draw, or periodically to keep
        # ghosting from building up; otherwise use the fast partial path.
        full = self._force_full or (self._refresh_count % config.FULL_REFRESH_EVERY == 0)
        self._force_full = False
        if full:
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
