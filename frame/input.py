"""Rotary-encoder + push-button input, wired to plain callbacks.

This is the only place that touches gpiozero, so the navigator and screens
stay hardware-free and testable.
"""

from __future__ import annotations

from typing import Callable

from gpiozero import Button, RotaryEncoder

from . import config


class RotaryInput:
    """Binds a KY-040 encoder to `on_rotate(delta)` and `on_press()`.

    `delta` is +1 for a clockwise (right) detent and -1 for counter-clockwise
    (left). If left/right ever feel reversed, swap CLK_PIN and DT_PIN in
    config. Keep a reference to the instance alive for as long as you want
    input to work (gpiozero closes devices when they're garbage-collected).
    """

    def __init__(self, on_rotate: Callable[[int], None],
                 on_press: Callable[[], None]) -> None:
        self._encoder = RotaryEncoder(config.CLK_PIN, config.DT_PIN, max_steps=0)
        self._button = Button(config.SW_PIN, pull_up=True, bounce_time=0.05)
        self._encoder.when_rotated_clockwise = lambda: on_rotate(+1)
        self._encoder.when_rotated_counter_clockwise = lambda: on_rotate(-1)
        self._button.when_pressed = on_press
