"""
monitor.py — Fokiz episodic monitor. Orchestrates per-tick evaluation.
Copyright (C) Alenia Studios — GNU GPL v3

Called by systemd every 60 seconds. Terminates immediately after evaluation.
Contains NO duplicate logic — delegates to app modules.

RULES:
- Does not remain resident.
- Logs errors to stderr (captured by systemd journal).
- A failing notification must never crash the monitor.
- Integrity check is mandatory before any dispatch.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the app package is importable when invoked directly
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from app import db
from app.constants import DB_PATH, SECRET_PATH
from app.errors import (
    DatabaseMissingError,
    IntegrityKeyMissingError,
    FokizError,
)
from app.integrity import IntegrityStatus, check_contract_integrity
from app import db as _db
from app.scheduler import compute_task_metrics, decide_dispatches, is_wakeup_burst
from app.presence import get_presence
from app.notifier import dispatch
from app.math_engine import zone_urgency

logging.basicConfig(
    level=logging.WARNING,
    format="fokiz-monitor %(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("monitor")

# ---------------------------------------------------------------------------
# State file for previous idle (used for Wake-up Burst detection)
# ---------------------------------------------------------------------------

_STATE_FILE = _HERE / ".monitor_state"


def _load_prev_idle() -> float | None:
    try:
        val = _STATE_FILE.read_text(encoding="utf-8").strip()
        return float(val)
    except (FileNotFoundError, ValueError, OSError):
        return None


def _save_prev_idle(idle_s: float | None) -> None:
    try:
        _STATE_FILE.write_text(
            "" if idle_s is None else str(idle_s),
            encoding="utf-8",
        )
    except OSError as e:
        log.debug("Could not save idle state: %s", e)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run() -> None:
    now = datetime.now(timezone.utc)

    # ---- Sanity checks ----
    if not DB_PATH.exists():
        log.warning("data.db not found. Skipping monitor tick.")
        return

    if not SECRET_PATH.exists():
        log.error("INTEGRITY_KEY_MISSING: .secret not found.")
        return

    # ---- Active tasks ----
    try:
        active_tasks = db.get_active_tasks()
    except DatabaseMissingError:
        log.warning("Database missing during monitor tick.")
        return
    except FokizError as e:
        log.error("Error fetching active tasks: %s", e)
        return

    if not active_tasks:
        log.debug("No active tasks.")
        return

    # ---- Presence ----
    presence = get_presence()
    if not presence.detected:
        log.warning("Presence detection failed: %s", presence.error)
        db.log_integrity_event("PRESENCE_DETECTION_FAILED", detail=presence.error)
        # Respect fail-closed for presence: skip dispatch
        _save_prev_idle(None)
        return

    prev_idle = _load_prev_idle()
    current_idle = presence.idle_seconds
    wakeup = is_wakeup_burst(prev_idle, current_idle)
    _save_prev_idle(current_idle)

    # ---- Compute metrics per task ----
    metrics_list = []
    for task in active_tasks:
        try:
            phases = db.get_phases(task["id"])
        except FokizError as e:
            log.error("Error loading phases for task %d: %s", task["id"], e)
            continue

        # Integrity check
        integrity_status = check_contract_integrity(task, phases)
        if integrity_status == IntegrityStatus.TAMPERED:
            log.error("TAMPERED contract detected: task_id=%d", task["id"])
            db.log_integrity_event("TAMPERED", task_id=task["id"], detail="monitor check")
            # Still notify about tamper (fail-closed: keep notifying)
            try:
                dispatch(
                    title="⚠ Fokiz — Contrato Manipulado",
                    body=f"Tarea #{task['id']} tiene integridad comprometida. "
                         "Operaciones contractuales bloqueadas.",
                    urgency="critical",
                    play_sound=False,
                )
            except Exception:
                pass
            continue

        if integrity_status == IntegrityStatus.KEY_MISSING:
            log.error("INTEGRITY_KEY_MISSING during monitor tick.")
            return

        try:
            m = compute_task_metrics(task, phases, now)
            if m is not None:
                metrics_list.append(m)
        except Exception as e:
            log.error("Error computing metrics for task %d: %s", task["id"], e)

    if not metrics_list:
        log.debug("No metrics to dispatch.")
        return

    # ---- Scheduling decisions ----
    decisions = decide_dispatches(
        metrics_list=metrics_list,
        presence=presence,
        now=now,
        previous_idle_s=prev_idle,
        wakeup_burst=wakeup,
    )

    # ---- Dispatch ----
    for decision in decisions:
        if not decision.should_dispatch:
            continue
        # Find the matching task title
        task_title = next(
            (m.title for m in metrics_list if m.task_id == decision.task_id),
            f"Tarea #{decision.task_id}",
        )
        try:
            result = dispatch(
                title=f"Fokiz — {task_title}",
                body=decision.message,
                urgency=decision.urgency,
                play_sound=decision.play_audio,
            )
            if result.get("notification_sent"):
                now_iso = now.strftime("%Y-%m-%d %H:%M:%S")
                db.insert_notification(
                    task_id=decision.task_id,
                    urgency_level=decision.urgency.upper(),
                    message_sent=decision.message,
                    dispatched_at=now_iso,
                )
        except Exception as e:
            log.error("Dispatch error for task %d: %s", decision.task_id, e)
            db.log_integrity_event(
                "DISPATCH_ERROR",
                task_id=decision.task_id,
                detail=str(e),
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log.critical("Unhandled exception in monitor: %s", e, exc_info=True)
        sys.exit(1)
    sys.exit(0)
