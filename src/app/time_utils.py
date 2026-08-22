"""
time_utils.py — Shared time utilities for Fokiz.
Copyright (C) Alenia Studios — GNU GPL v3
"""

from datetime import datetime, timezone


def _parse_utc(iso: str) -> datetime:
    return datetime.strptime(iso, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
