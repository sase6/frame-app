"""A tiny JSON-backed settings store (settings.json).

Tolerant of a missing or corrupt file, and writes atomically so a power loss
mid-write can't leave a half-written file on the SD card.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger("launcher.store")


class SettingsStore:
    """A flat key/value store persisted to a JSON object file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            with self._path.open() as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            log.warning("%s is not a JSON object; ignoring it.", self._path.name)
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read %s (%s); starting fresh.", self._path.name, exc)
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a key and persist. No-op (and no write) if unchanged."""
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self._save()

    def _save(self) -> None:
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            with tmp.open("w") as f:
                json.dump(self._data, f, indent=2)
            tmp.replace(self._path)  # atomic on POSIX
        except OSError as exc:
            log.error("Failed to write %s: %s", self._path.name, exc)
