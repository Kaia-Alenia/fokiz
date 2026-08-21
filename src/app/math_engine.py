"""
math_engine.py — Pure mathematical formulas for Fokiz.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- No I/O (no subprocess, no file access, no sqlite).
- No side effects.
- All functions are deterministic given the same inputs.
- This is the single source of truth for τ, Δ, I_spam, IU.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from .constants import (
    I_SPAM_COEFF_A,
    I_SPAM_COEFF_B,
    I_SPAM_EXPIRED_MIN,
    TAU_YELLOW,
    TAU_ORANGE,
    TAU_RED,
    DELTA_AHEAD,
    DELTA_BEHIND,
    IU_DENOM_MIN_H,
)


# ---------------------------------------------------------------------------
# Severity zones
# ---------------------------------------------------------------------------

class Zone(Enum):
    GREEN = "GREEN"         # τ < 0.40
    YELLOW = "YELLOW"       # 0.40 <= τ < 0.75
    ORANGE = "ORANGE"       # 0.75 <= τ < 0.95
    RED = "RED"             # 0.95 <= τ < 1.00
    EXPIRED = "EXPIRED"     # τ >= 1.00


class DeltaStatus(Enum):
    AHEAD = "ADELANTADO"
    ON_TRACK = "AL DÍA"
    BEHIND = "ATRASADO"


# ---------------------------------------------------------------------------
# τ — phase urgency ratio
# ---------------------------------------------------------------------------

def compute_tau(
    t_actual: datetime,
    t_start_phase: datetime,
    t_deadline_phase: datetime,
) -> float:
    """
    τ_i = (t_actual - t_start) / (t_deadline - t_start)

    Clamps to 0 if t_deadline == t_start (degenerate window).
    τ is never clamped upward; values > 1 are valid (expired phase).
    τ is never clamped below 0 (before phase start is abnormal).
    """
    window = (t_deadline_phase - t_start_phase).total_seconds()
    if window <= 0:
        return 0.0
    elapsed = (t_actual - t_start_phase).total_seconds()
    return elapsed / window


# ---------------------------------------------------------------------------
# Δ — overall progress gap
# ---------------------------------------------------------------------------

def compute_delta(
    phases_completed: int,
    total_phases: int,
    t_actual: datetime,
    t_created: datetime,
    t_deadline: datetime,
) -> float:
    """
    Δ = (phases_completed / K) - ((t_actual - created_at) / (deadline - created_at))

    Δ > +0.20  → AHEAD
    -0.10 <= Δ <= +0.20 → ON_TRACK
    Δ < -0.10 → BEHIND
    """
    if total_phases <= 0:
        return 0.0
    task_window = (t_deadline - t_created).total_seconds()
    if task_window <= 0:
        return 0.0
    progress_ratio = phases_completed / total_phases
    time_ratio = (t_actual - t_created).total_seconds() / task_window
    return progress_ratio - time_ratio


def classify_delta(delta: float) -> DeltaStatus:
    if delta > DELTA_AHEAD:
        return DeltaStatus.AHEAD
    if delta < DELTA_BEHIND:
        return DeltaStatus.BEHIND
    return DeltaStatus.ON_TRACK


# ---------------------------------------------------------------------------
# I_spam — notification interval in minutes
# ---------------------------------------------------------------------------

def compute_i_spam(tau: float) -> float:
    """
    I_spam(τ) = 10 + 350 * (1 - τ)²   for 0 <= τ < 1
    I_spam     = 5                       for τ >= 1

    Returns minutes (float).
    """
    if tau >= 1.0:
        return float(I_SPAM_EXPIRED_MIN)
    return I_SPAM_COEFF_A + I_SPAM_COEFF_B * (1.0 - tau) ** 2


# ---------------------------------------------------------------------------
# Zone classification
# ---------------------------------------------------------------------------

def classify_zone(tau: float) -> Zone:
    if tau >= 1.0:
        return Zone.EXPIRED
    if tau >= TAU_RED:
        return Zone.RED
    if tau >= TAU_ORANGE:
        return Zone.ORANGE
    if tau >= TAU_YELLOW:
        return Zone.YELLOW
    return Zone.GREEN


def zone_urgency(zone: Zone) -> str:
    """Return notify-send urgency string for the zone."""
    mapping = {
        Zone.GREEN: "low",
        Zone.YELLOW: "normal",
        Zone.ORANGE: "critical",
        Zone.RED: "critical",
        Zone.EXPIRED: "critical",
    }
    return mapping[zone]


def zone_audio(zone: Zone) -> bool:
    """Return True if audio should be played for this zone."""
    return zone in (Zone.RED, Zone.EXPIRED)


# ---------------------------------------------------------------------------
# IU — urgency index for multi-task scheduling
# ---------------------------------------------------------------------------

def compute_iu(
    tau: float,
    t_actual: datetime,
    t_deadline_phase: datetime,
) -> float:
    """
    IU = τ / max(0.1, hours_remaining_phase)

    hours_remaining_phase = (t_deadline_phase - t_actual) / 3600
    If expired, the denominator is clamped to IU_DENOM_MIN_H.
    """
    hours_remaining = (t_deadline_phase - t_actual).total_seconds() / 3600.0
    denominator = max(IU_DENOM_MIN_H, hours_remaining)
    return tau / denominator


# ---------------------------------------------------------------------------
# Cooldown check
# ---------------------------------------------------------------------------

def cooldown_elapsed(
    last_dispatch_iso: str | None,
    i_spam_minutes: float,
    t_actual: datetime,
) -> bool:
    """
    Return True if enough time has elapsed since last_dispatch to send again.
    If last_dispatch is None, returns True (never dispatched).
    """
    if last_dispatch_iso is None:
        return True
    try:
        last = datetime.strptime(last_dispatch_iso, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return True
    elapsed_minutes = (t_actual - last).total_seconds() / 60.0
    return elapsed_minutes >= i_spam_minutes
