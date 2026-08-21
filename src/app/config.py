"""
config.py — Fokiz global configuration loader.
Copyright (C) Alenia Studios — GNU GPL v3
"""

import json
import pathlib
from typing import Any

from .constants import FOKIZ_DATA_DIR, DEFAULT_TIMEZONE


_CONFIG_FILE = FOKIZ_DATA_DIR / "config.json"

# Defaults applied when config.json is absent or a key is missing
_DEFAULTS: dict[str, Any] = {
    "timezone": DEFAULT_TIMEZONE,
    "max_active_slots": 3,
    "presence_fallback": "skip",   # "skip" | "assume_active"
    "audio_enabled": True,
    "notification_enabled": True,
}


class Config:
    """Read-only configuration object loaded once per process."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data


_loaded: Config | None = None


def load_config() -> Config:
    """Return the singleton Config. Reads from disk on first call."""
    global _loaded
    if _loaded is not None:
        return _loaded

    data: dict[str, Any] = dict(_DEFAULTS)

    if _CONFIG_FILE.exists():
        try:
            raw = _CONFIG_FILE.read_text(encoding="utf-8")
            user_data = json.loads(raw)
            if isinstance(user_data, dict):
                data.update(user_data)
        except (json.JSONDecodeError, OSError):
            # Non-fatal: fall back to defaults
            pass

    _loaded = Config(data)
    return _loaded


def save_config(data: dict[str, Any]) -> None:
    """Persist configuration to disk."""
    FOKIZ_DATA_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Invalidate cache
    global _loaded
    _loaded = None
