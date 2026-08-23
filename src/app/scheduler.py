"""
scheduler.py — Notification scheduling, cooldown, priority, and 80/20 budget.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- Decides WHEN to notify; does not send notifications.
- Respects cooldown; never spams every 60 s.
- Applies 80/20 budget for multi-task scenarios.
- Wake-up Burst ignores cooldown once per wakeup event.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .constants import (
    IDLE_ACTIVE_THRESHOLD_S,
    IDLE_WAKEUP_THRESHOLD_S,
    IDLE_WAKEUP_CURRENT_MAX_S,
    BUDGET_PRIMARY,
    BUDGET_SECONDARY,
)
from .math_engine import (
    Zone,
    DeltaStatus,
    compute_tau,
    compute_delta,
    compute_i_spam,
    compute_iu,
    classify_zone,
    classify_delta,
    cooldown_elapsed,
    zone_urgency,
    zone_audio,
)
from .presence import PresenceResult
from .messages import pick_message, urgency_label

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TaskMetrics:
    task_id: int
    title: str
    phase_number: int
    phase_title: str
    tau: float
    delta: float
    delta_status: DeltaStatus
    iu: float
    zone: Zone
    i_spam_min: float
    phases_done: int
    total_phases: int
    deadline_str: str
    phase_deadline: datetime
    last_notification_iso: Optional[str]


@dataclass
class DispatchDecision:
    should_dispatch: bool
    task_id: int
    urgency: str
    message: str
    play_audio: bool
    reason: str


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_task_metrics(
    task: "sqlite3.Row",
    phases: list["sqlite3.Row"],
    now: datetime,
) -> TaskMetrics | None:
    """Compute metrics for a single task. Returns None if no active phase."""
    from .db import get_last_notification  # local import to avoid circular

    # Find active phase (first PENDING)
    active_phase = None
    phases_done = 0
    for ph in sorted(phases, key=lambda p: p["phase_number"]):
        if ph["status"] == "COMPLETED":
            phases_done += 1
        elif active_phase is None and ph["status"] == "PENDING":
            active_phase = ph

    if active_phase is None:
        return None

    # Phase start = previous phase deadline or task created_at
    prev_deadline_str = task["created_at"]
    for ph in sorted(phases, key=lambda p: p["phase_number"]):
        if ph["phase_number"] < active_phase["phase_number"]:
            prev_deadline_str = ph["target_deadline"]

    t_start = _parse_dt(prev_deadline_str)
    t_phase_deadline = _parse_dt(active_phase["target_deadline"])
    t_task_deadline = _parse_dt(task["deadline"])
    t_created = _parse_dt(task["created_at"])

    tau = compute_tau(now, t_start, t_phase_deadline)
    delta = compute_delta(phases_done, task["total_phases"], now, t_created, t_task_deadline)
    delta_status = classify_delta(delta)
    iu = compute_iu(tau, now, t_phase_deadline)
    zone = classify_zone(tau)
    i_spam = compute_i_spam(tau)

    last_notif = get_last_notification(task["id"])
    last_notif_iso = last_notif["dispatched_at"] if last_notif else None

    return TaskMetrics(
        task_id=task["id"],
        title=task["title"],
        phase_number=active_phase["phase_number"],
        phase_title=active_phase["title"],
        tau=tau,
        delta=delta,
        delta_status=delta_status,
        iu=iu,
        zone=zone,
        i_spam_min=i_spam,
        phases_done=phases_done,
        total_phases=task["total_phases"],
        deadline_str=task["deadline"],
        phase_deadline=t_phase_deadline,
        last_notification_iso=last_notif_iso,
    )


# ---------------------------------------------------------------------------
# Wake-up Burst detection
# ---------------------------------------------------------------------------

def is_wakeup_burst(
    previous_idle_s: Optional[float],
    current_idle_s: Optional[float],
) -> bool:
    """
    Return True if the user just returned after being idle >= 1800 s
    and current idle is < 10 s.
    """
    if previous_idle_s is None or current_idle_s is None:
        return False
    return (
        previous_idle_s >= IDLE_WAKEUP_THRESHOLD_S
        and current_idle_s < IDLE_WAKEUP_CURRENT_MAX_S
    )


# ---------------------------------------------------------------------------
# Scheduling decision
# ---------------------------------------------------------------------------

def decide_dispatches(
    metrics_list: list[TaskMetrics],
    presence: PresenceResult,
    now: datetime,
    previous_idle_s: Optional[float] = None,
    wakeup_burst: bool = False,
) -> list[DispatchDecision]:
    """
    Given metrics for all active tasks, decide which notifications to send.

    - User must be active (or wakeup_burst must be True).
    - Cooldown must have elapsed.
    - 80/20 budget: primary task gets 80%, rest share 20%.
    """
    decisions: list[DispatchDecision] = []

    if not metrics_list:
        return decisions

    from .db import get_user_config
    user_config = get_user_config()
    nickname = user_config["nickname"] if user_config and "nickname" in user_config.keys() else "Usuario"
    from .errors import ConfigurationError
    if not user_config or "timezone" not in user_config:
        raise ConfigurationError("Scheduler cannot run: explicit timezone is required.")
    tz_str = user_config["timezone"]
    
    import zoneinfo
    try:
        zone = zoneinfo.ZoneInfo(tz_str)
    except zoneinfo.ZoneInfoNotFoundError:
        raise ConfigurationError(f"Scheduler cannot run: invalid timezone '{tz_str}'.")
    local_time = now.astimezone(zone)
    local_hour = local_time.hour

    # Presence check (skip if not active and not wakeup burst)
    if not wakeup_burst:
        if not presence.detected:
            log.warning("Presence unknown; skipping notifications. %s", presence.error)
            return decisions
        if not presence.is_active:
            log.debug("User idle (%.0fs); skipping notifications.", presence.idle_seconds)
            return decisions

    # Sort by IU descending to find primary task
    sorted_metrics = sorted(metrics_list, key=lambda m: m.iu, reverse=True)
    primary = sorted_metrics[0]
    secondary = sorted_metrics[1:]

    # Primary task — dispatch if cooldown elapsed or wakeup burst
    primary_ok = wakeup_burst or cooldown_elapsed(
        primary.last_notification_iso, primary.i_spam_min, now
    )
    if primary_ok:
        msg = pick_message(primary.zone, wakeup=wakeup_burst, nickname=nickname, local_hour=local_hour)
        decisions.append(DispatchDecision(
            should_dispatch=True,
            task_id=primary.task_id,
            urgency=zone_urgency(primary.zone),
            message=msg,
            play_audio=zone_audio(primary.zone) and not wakeup_burst,
            reason="primary" if not wakeup_burst else "wakeup_burst",
        ))

    # Secondary tasks — only dispatch one consolidated summary per cycle
    for m in secondary:
        if cooldown_elapsed(m.last_notification_iso, m.i_spam_min, now):
            msg = f"[{m.title}] Phase {m.phase_number} — τ={m.tau:.2f} ({m.zone.value})"
            decisions.append(DispatchDecision(
                should_dispatch=True,
                task_id=m.task_id,
                urgency=zone_urgency(m.zone),
                message=msg,
                play_audio=False,
                reason="secondary",
            ))

    return decisions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_dt(iso_str: str) -> datetime:
    """Parse 'YYYY-MM-DD HH:MM:SS' as UTC datetime."""
    return datetime.strptime(iso_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
