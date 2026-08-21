"""
notifier.py — Desktop notification and audio dispatcher.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- Uses subprocess.run() with argument list — never shell=True with user data.
- Audio failure never crashes the monitor.
- Does not compute priorities (that is scheduler.py's job).
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_silent(args: list[str], timeout: int = 10) -> bool:
    """Run a subprocess silently. Returns True on success."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        log.debug("Command failed %s: %s", args[0], exc)
        return False


def _find_audio_player() -> Optional[str]:
    """Return 'paplay' or 'aplay' if available, else None."""
    for player in ("paplay", "aplay"):
        result = subprocess.run(
            ["which", player],
            capture_output=True,
        )
        if result.returncode == 0:
            return player
    return None


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

def send_notification(
    title: str,
    body: str,
    urgency: str = "critical",
    app_name: str = "Fokiz",
    timeout_ms: int = 10000,
) -> bool:
    """
    Send a desktop notification via notify-send.

    Parameters:
        title: Notification title.
        body: Notification body.
        urgency: 'low' | 'normal' | 'critical'
        app_name: Application name displayed by the notifier.
        timeout_ms: Display duration in milliseconds (-1 for persistent).
    """
    args = [
        "notify-send",
        "--urgency", "critical",
        "--app-name", app_name,
        "--expire-time", str(timeout_ms),
    ]

    # Add icon if it exists
    from .constants import ICON_PATH
    if ICON_PATH.exists():
        args.extend(["--icon", str(ICON_PATH)])

    args.extend([title, body])

    success = _run_silent(args)
    if not success:
        log.warning("notify-send failed. title=%r urgency=%s", title, urgency)
    return success


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

def play_audio(sound_path: Optional[Path] = None) -> bool:
    """
    Play a sound file or a system bell.
    Never crashes; audio failure is logged and ignored.
    """
    player = _find_audio_player()

    if player is None:
        log.debug("No audio player available (paplay/aplay). Skipping audio.")
        return False

    if sound_path and sound_path.exists():
        success = _run_silent([player, str(sound_path)])
    else:
        # System bell via aplay with a generated tone, or just skip
        if player == "aplay":
            # Try to play /dev/urandom as noise-free fallback is unreliable;
            # just emit console bell if terminal
            try:
                print("\a", end="", flush=True)
                success = True
            except Exception:
                success = False
        else:
            log.debug("No sound file provided and paplay has no default. Skipping.")
            success = False

    if not success:
        log.debug("Audio playback failed. Continuing without audio.")
    return success


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------

def dispatch(
    title: str,
    body: str,
    urgency: str = "normal",
    play_sound: bool = False,
    sound_path: Optional[Path] = None,
) -> dict:
    """
    Send a notification and optionally play audio.
    Returns a dict summarizing what was done.
    """
    notif_ok = send_notification(title=title, body=body, urgency=urgency)
    audio_ok = False
    if play_sound:
        audio_ok = play_audio(sound_path)

    return {
        "notification_sent": notif_ok,
        "audio_played": audio_ok,
    }
