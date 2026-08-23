"""
_guards.py — Shared pre-condition guards for Fokiz commands.
Copyright (C) Alenia Studios — GNU GPL v3
"""
from __future__ import annotations
from ..constants import DB_PATH, SECRET_PATH
from ..errors import NotInitializedError


def _require_initialized() -> None:
    """Raise NotInitializedError if Fokiz has not been initialized."""
    if not DB_PATH.exists() or not SECRET_PATH.exists():
        raise NotInitializedError()
