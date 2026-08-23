"""
shame.py — Fokiz CLI use case: shame.
Copyright (C) Alenia Studios — GNU GPL v3
"""

from __future__ import annotations
from ..i18n import _

import sys
from datetime import datetime, timezone
from pathlib import Path

from ..time_utils import _parse_utc
from ..constants import DB_PATH
from .. import db
from ..errors import NotInitializedError
from ..integrity import (
    IntegrityStatus,
    check_contract_integrity,
)
from ..math_engine import (
    Zone,
    compute_delta,
    compute_i_spam,
    compute_iu,
    compute_tau,
    classify_delta,
    classify_zone,
)
from .. import ui


def cmd_shame() -> int:
    """fokiz shame — display surrendered tasks in the Muro de la Vergüenza."""
    if not DB_PATH.exists():
        ui.print_error(_("error.not_initialized"))
        return 1

    tasks = db.get_surrendered_tasks()
    
    # Print custom banner
    ui.print_section("Muro de la Vergüenza")
    
    if not tasks:
        ui.print_info("No hay tareas perdidas.")
        return 0

    now = datetime.now(timezone.utc)

    for task in tasks:
        phases = db.get_phases(task["id"])

        # Integrity check
        status_integrity = check_contract_integrity(task, phases)
        if status_integrity == IntegrityStatus.KEY_MISSING:
            ui.print_key_missing_warning()
        elif status_integrity == IntegrityStatus.TAMPERED:
            ui.print_tampered_warning(task["id"])
            db.log_integrity_event("TAMPERED", task_id=task["id"], detail="shame check")
            continue

        phases_done = sum(1 for ph in phases if ph["status"] == "COMPLETED")
        
        # Determine the phase it was surrendered on. Usually it's the first PENDING.
        active_phase = next(
            (ph for ph in sorted(phases, key=lambda p: p["phase_number"])
             if ph["status"] == "PENDING"),
            None,
        )

        if active_phase:
            prev_deadline_str = task["created_at"]
            for ph in sorted(phases, key=lambda p: p["phase_number"]):
                if ph["phase_number"] < active_phase["phase_number"]:
                    prev_deadline_str = ph["target_deadline"]

            t_start = _parse_utc(prev_deadline_str)
            t_phase_dl = _parse_utc(active_phase["target_deadline"])
            t_task_dl = _parse_utc(task["deadline"])
            t_created = _parse_utc(task["created_at"])

            # Use completed_at instead of now to show metrics at the time of surrender
            t_completed = _parse_utc(task["completed_at"]) if task["completed_at"] else now

            tau = compute_tau(t_completed, t_start, t_phase_dl)
            delta = compute_delta(phases_done, task["total_phases"], t_completed, t_created, t_task_dl)
            delta_status = classify_delta(delta)
            iu = compute_iu(tau, t_completed, t_phase_dl)
            zone = classify_zone(tau)
            i_spam = compute_i_spam(tau)
            phase_label = f"#{active_phase['phase_number']} — {active_phase['title']}"
            time_remaining = "—"
        else:
            tau = 0.0
            delta = 0.0
            delta_status = classify_delta(delta)
            iu = 0.0
            zone = Zone.EXPIRED
            i_spam = 0.0
            phase_label = _("board.all_phases_done")
            time_remaining = "—"

        print()
        card = ui.render_task_card(
            task_id=task["id"],
            title=task["title"],
            status="SURRENDERED",
            phase_label=phase_label,
            tau=tau,
            delta=delta,
            delta_status=delta_status,
            iu=iu,
            zone=zone,
            i_spam_min=i_spam,
            phases_done=phases_done,
            total_phases=task["total_phases"],
            deadline=task["deadline"],
            time_remaining=time_remaining,
            is_shame=True,
        )
        print(card)

    return 0
