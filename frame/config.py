"""Central configuration - every value you'd reasonably tweak lives here.

Nothing in this module imports hardware, so it's safe to read from anywhere.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Paths (everything is resolved relative to the repo root, which is the
# parent of this `frame/` package).
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = BASE_DIR / "assets"
SETTINGS_PATH = BASE_DIR / "settings.json"

# --------------------------------------------------------------------------
# Hardware
# --------------------------------------------------------------------------
# KY-040 rotary encoder wiring (BCM pin numbers).
CLK_PIN = 5
DT_PIN = 27
SW_PIN = 22

# Panel size in landscape orientation (pixels).
SCREEN_W, SCREEN_H = 250, 122

# In-screen updates (knob spins, counter ticks) use fast partial refreshes,
# which never flash but leave faint "ghosting". The only flash is a full
# refresh, and it happens solely on screen transitions (see Navigator) - a
# deliberate moment where a brief flash reads as "new screen" and also scrubs
# any ghosting the previous screen left behind.

# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NAME_FONT_SIZE = 15

# --------------------------------------------------------------------------
# Home carousel layout (pixels)
# --------------------------------------------------------------------------
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
DOT_TOP_GAP = 5       # gap between the name and the dots

# --------------------------------------------------------------------------
# Behaviour
# --------------------------------------------------------------------------
WRAP_SELECTION = False     # True = wrap around at the ends; False = stop
DEFAULT_APP_INDEX = 1      # carousel starts focused on this app (Uploader)

# --------------------------------------------------------------------------
# Settings screen layout (pixels)
# --------------------------------------------------------------------------
SETTINGS_TITLE = "Settings"
SETTINGS_TITLE_FONT_SIZE = 15
SETTINGS_ROW_FONT_SIZE = 16

SETTINGS_TITLE_Y = 5
SETTINGS_DIVIDER_Y = 26
SETTINGS_ROWS_TOP = 34      # y where the first row slot begins
SETTINGS_ROW_HEIGHT = 38    # height of each row slot
SETTINGS_LEFT_MARGIN = 18
SETTINGS_RIGHT_MARGIN = 18

# Highlight (navigate mode): underline beneath the label.
SETTINGS_UNDERLINE_GAP = 2
SETTINGS_UNDERLINE_WIDTH = 2

# Focus (edit mode): rounded border around the whole row.
SETTINGS_BORDER_RADIUS = 6
SETTINGS_BORDER_WIDTH = 2
SETTINGS_BORDER_PAD_X = 8
SETTINGS_BORDER_PAD_Y = 4

# Delay value row.
DELAY_KEY = "delay"
DELAY_MIN = 0
DELAY_STEP = 1
DELAY_SUFFIX = "s"     # shown after the number, e.g. "12s"
