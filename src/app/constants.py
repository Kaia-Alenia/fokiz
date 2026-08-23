"""
constants.py — Fokiz technical constants and limits.
Copyright (C) Alenia Studios — GNU GPL v3
"""

import os
import pathlib

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HOME = pathlib.Path.home()
FOKIZ_DATA_DIR = HOME / ".local" / "share" / "fokiz"
FOKIZ_BIN_DIR = HOME / ".local" / "bin"
SYSTEMD_USER_DIR = HOME / ".config" / "systemd" / "user"

FOKIZ_VERSION = "1.0.2"

APP_DIR = FOKIZ_DATA_DIR / "app"
DB_PATH = FOKIZ_DATA_DIR / "data.db"
SECRET_PATH = FOKIZ_DATA_DIR / ".secret"
SCHEMA_PATH = FOKIZ_DATA_DIR / "schema.sql"

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
ICON_PATH = PROJECT_ROOT / "fokiz.svg"

MONITOR_WRAPPER = FOKIZ_BIN_DIR / "fokiz-monitor"
FOKIZ_WRAPPER = FOKIZ_BIN_DIR / "fokiz"

SYSTEMD_SERVICE = SYSTEMD_USER_DIR / "fokiz-monitor.service"
SYSTEMD_TIMER = SYSTEMD_USER_DIR / "fokiz-monitor.timer"

# ---------------------------------------------------------------------------
# Slots
# ---------------------------------------------------------------------------

MAX_ACTIVE_SLOTS: int = 3

# ---------------------------------------------------------------------------
# Task field limits
# ---------------------------------------------------------------------------

TITLE_MIN: int = 5
TITLE_MAX: int = 80
OBJECTIVE_MIN: int = 10
OBJECTIVE_MAX: int = 200

PHASES_MIN: int = 1
PHASES_MAX: int = 8

DAYS_MIN: int = 1

SURRENDER_REASON_MIN: int = 30

# ---------------------------------------------------------------------------
# Idle thresholds (seconds)
# ---------------------------------------------------------------------------

IDLE_ACTIVE_THRESHOLD_S: int = 300      # user is "active" if idle < 300 s
IDLE_WAKEUP_THRESHOLD_S: int = 1800     # trigger wake-up burst after 30 min
IDLE_WAKEUP_CURRENT_MAX_S: int = 10     # current idle must be < 10 s to burst

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

MONITOR_TICK_S: int = 60                # systemd fires every 60 s
I_SPAM_EXPIRED_MIN: int = 5             # fixed interval when τ >= 1 (minutes)
I_SPAM_COEFF_A: float = 10.0           # I_spam = A + B*(1-τ)^2
I_SPAM_COEFF_B: float = 350.0

# τ zone thresholds
TAU_YELLOW: float = 0.40
TAU_ORANGE: float = 0.75
TAU_RED: float = 0.95

# Δ thresholds
DELTA_AHEAD: float = 0.20
DELTA_BEHIND: float = -0.10

# IU denominator minimum (hours)
IU_DENOM_MIN_H: float = 0.1

# Notification budget ratio
BUDGET_PRIMARY: float = 0.80
BUDGET_SECONDARY: float = 0.20

# ---------------------------------------------------------------------------
# Anti-cheat
# ---------------------------------------------------------------------------

LOG_EARLY_TAU_THRESHOLD: float = 0.10  # if τ < this, require confirmation

ENTROPY_MIN: float = 1.5               # bits; below this → rejected
LOG_MIN_CHARS: int = 20                # minimum meaningful log length
LOG_TOKENS_OVERLAP_MIN: int = 1        # at least 1 token from instructions

# ---------------------------------------------------------------------------
# HMAC
# ---------------------------------------------------------------------------

HMAC_VERSION: str = "2"
SECRET_SIZE_BYTES: int = 32

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

BANNER_WIDTH: int = 60
PROGRESS_BAR_WIDTH: int = 30

# ---------------------------------------------------------------------------
# File permissions
# ---------------------------------------------------------------------------

PERM_SECRET = 0o600
PERM_DB = 0o600
