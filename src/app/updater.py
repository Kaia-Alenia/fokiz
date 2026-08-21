"""
updater.py — Checks for new Fokiz versions on GitHub via API.
Copyright (C) Alenia Studios — GNU GPL v3
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

from .constants import FOKIZ_DATA_DIR, FOKIZ_VERSION
from .i18n import _

# Cache file to avoid hitting GitHub API on every `fokiz status`
UPDATE_CACHE_FILE = FOKIZ_DATA_DIR / ".update_check"
CACHE_DURATION_SECONDS = 86400  # 24 hours
GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/Kaia-Alenia/fokiz/releases/latest"

def _parse_version(version_str: str) -> tuple:
    """Parses a version string (e.g. 'v0.2.0' or '0.2.0') into a tuple of ints."""
    clean = version_str.lstrip("vV")
    try:
        return tuple(int(part) for part in clean.split("."))
    except ValueError:
        return (0, 0, 0)

def check_for_updates() -> str | None:
    """
    Checks if a newer version of Fokiz is available.
    Returns a notification message if an update is found, otherwise None.
    Uses a 24-hour local cache.
    """
    now = time.time()
    
    # 1. Read from cache if it exists and is fresh
    if UPDATE_CACHE_FILE.exists():
        try:
            cache_data = json.loads(UPDATE_CACHE_FILE.read_text(encoding="utf-8"))
            last_check = cache_data.get("timestamp", 0)
            latest_version = cache_data.get("latest_version", "0.0.0")
            
            if now - last_check < CACHE_DURATION_SECONDS:
                # Cache is valid
                if _parse_version(latest_version) > _parse_version(FOKIZ_VERSION):
                    return latest_version
                return None
        except Exception:
            pass # Invalid cache, ignore and fetch

    # 2. Fetch from GitHub API
    try:
        req = urllib.request.Request(
            GITHUB_LATEST_RELEASE_URL, 
            headers={"User-Agent": "Fokiz-CLI-Updater"}
        )
        # Timeout of 2 seconds to avoid blocking the CLI if offline
        with urllib.request.urlopen(req, timeout=2.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                latest_version = data.get("tag_name", "0.0.0")
                
                # Update cache
                UPDATE_CACHE_FILE.write_text(
                    json.dumps({"timestamp": now, "latest_version": latest_version}),
                    encoding="utf-8"
                )
                
                if _parse_version(latest_version) > _parse_version(FOKIZ_VERSION):
                    return latest_version
                return None
    except Exception:
        # Ignore all errors (no internet, API limits, timeouts, etc.)
        pass
    
    return None
