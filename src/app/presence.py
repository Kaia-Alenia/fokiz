"""
presence.py — Idle time detection via xprintidle or D-Bus fallback.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- If detection fails, log the failure; do NOT assume active silently.
- Return None when idle time cannot be determined.
"""

import subprocess
import logging
from typing import Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# xprintidle
# ---------------------------------------------------------------------------

def _get_idle_xprintidle() -> Optional[float]:
    """Return idle time in seconds via xprintidle, or None on failure."""
    try:
        result = subprocess.run(
            ["xprintidle"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            ms = int(result.stdout.strip())
            return ms / 1000.0
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired, OSError):
        pass
    return None


# ---------------------------------------------------------------------------
# D-Bus fallback
# ---------------------------------------------------------------------------

def _get_idle_dbus() -> Optional[float]:
    """
    Try to get idle time via D-Bus (org.gnome.Mutter.IdleMonitor or
    org.freedesktop.ScreenSaver).
    Returns seconds or None.
    """
    try:
        result = subprocess.run(
            [
                "dbus-send",
                "--print-reply",
                "--dest=org.gnome.Mutter.IdleMonitor",
                "/org/gnome/Mutter/IdleMonitor/Core",
                "org.gnome.Mutter.IdleMonitor.GetIdletime",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for token in result.stdout.split():
                try:
                    ms = int(token)
                    if ms >= 0:
                        return ms / 1000.0
                except ValueError:
                    continue
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Fallback: org.freedesktop.ScreenSaver
    try:
        result = subprocess.run(
            [
                "dbus-send",
                "--print-reply",
                "--dest=org.freedesktop.ScreenSaver",
                "/org/freedesktop/ScreenSaver",
                "org.freedesktop.ScreenSaver.GetSessionIdleTime",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for token in result.stdout.split():
                try:
                    sec = int(token)
                    if sec >= 0:
                        return float(sec)
                except ValueError:
                    continue
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PresenceResult:
    __slots__ = ("idle_seconds", "method", "error")

    def __init__(
        self,
        idle_seconds: Optional[float],
        method: str,
        error: Optional[str] = None,
    ) -> None:
        self.idle_seconds = idle_seconds
        self.method = method
        self.error = error

    @property
    def is_active(self) -> Optional[bool]:
        """True if user is active, False if idle, None if unknown."""
        if self.idle_seconds is None:
            return None
        from .constants import IDLE_ACTIVE_THRESHOLD_S
        return self.idle_seconds < IDLE_ACTIVE_THRESHOLD_S

    @property
    def detected(self) -> bool:
        return self.idle_seconds is not None


def get_presence() -> PresenceResult:
    """
    Attempt to determine user idle time.
    Priority: xprintidle → D-Bus → failure.
    Never assumes active without a successful detection.
    """
    idle = _get_idle_xprintidle()
    if idle is not None:
        return PresenceResult(idle_seconds=idle, method="xprintidle")

    idle = _get_idle_dbus()
    if idle is not None:
        return PresenceResult(idle_seconds=idle, method="dbus")

    error_msg = "No se pudo detectar tiempo de inactividad (xprintidle y D-Bus fallaron)."
    log.warning(error_msg)
    return PresenceResult(idle_seconds=None, method="none", error=error_msg)
