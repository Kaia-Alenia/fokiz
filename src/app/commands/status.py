"""
commands.py — Fokiz CLI use cases: init, add, status, done, surrender.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- Orchestrates modules; contains no SQL, no math, no ANSI rendering duplicated.
- All DB access via db.py only.
- All integrity via integrity.py only.
- All rendering via ui.py only.
"""

from __future__ import annotations
from ..i18n import _, set_language

import logging
import os
import shutil
import stat
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..anti_cheat import validate_completion_log
from ..config import load_config, save_config
from ..constants import (
    FOKIZ_DATA_DIR,
    FOKIZ_BIN_DIR,
    SYSTEMD_USER_DIR,
    DB_PATH,
    SECRET_PATH,
    APP_DIR,
    SURRENDER_REASON_MIN,
    MAX_ACTIVE_SLOTS,
)
from ..contracts import build_contract, contract_to_phase_dicts
from .. import db
from ..errors import (
    FokizError,
    IntegrityKeyMissingError,
    ContractTamperedError,
    DatabaseMissingError,
    NotInitializedError,
    MaxSlotsError,
    ValidationError,
)
from ..integrity import (
    IntegrityStatus,
    build_canonical_payload,
    check_contract_integrity,
    compute_hmac,
    generate_secret,
    assert_contract_ok,
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
from ..messages import get_delta_label, pick_message, urgency_label

log = logging.getLogger(__name__)


def cmd_status(show_banner: bool = False, show_completed: bool = False) -> int:
    """fokiz status — display tasks (active or completed depending on flag)."""
    if not DB_PATH.exists():
        ui.print_error(_("error.not_initialized"))
        return 1

    if show_banner:
        print(ui.render_banner(size="LARGE"))

        user_config = db.get_user_config()
        if user_config:
            tz_str = user_config["timezone"] if "timezone" in user_config.keys() else "America/Mexico_City"
            try:
                tz = ZoneInfo(tz_str)
            except Exception:
                tz = ZoneInfo("UTC")
            now_local = datetime.now(timezone.utc).astimezone(tz)
            print(_("status.local_time", time=now_local.strftime('%d/%m/%Y %H:%M')))
            print(_("status.timezone_field", tz=tz_str))
            print()

    tasks = db.get_all_tasks()
    
    if not show_completed:
        tasks = [t for t in tasks if t["status"] != "COMPLETED"]
    else:
        tasks = [t for t in tasks if t["status"] == "COMPLETED"]
        
    if not tasks:
        msg = _("status.no_tasks") if show_completed else _("status.no_active")
        ui.print_info(msg)
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
            db.log_integrity_event("TAMPERED", task_id=task["id"], detail="status check")
            continue

        # Metrics
        phases_done = sum(1 for ph in phases if ph["status"] == "COMPLETED")
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

            tau = compute_tau(now, t_start, t_phase_dl)
            delta = compute_delta(phases_done, task["total_phases"], now, t_created, t_task_dl)
            delta_status = classify_delta(delta)
            iu = compute_iu(tau, now, t_phase_dl)
            zone = classify_zone(tau)
            i_spam = compute_i_spam(tau)
            phase_label = f"#{active_phase['phase_number']} — {active_phase['title']}"
            time_remaining = ui.format_time_remaining(t_phase_dl, now)
        else:
            tau = 0.0
            delta = 0.0
            delta_status = classify_delta(delta)
            iu = 0.0
            zone = Zone.GREEN
            i_spam = compute_i_spam(tau)
            phase_label = _("board.all_phases_done")
            time_remaining = "—"

        print()
        card = ui.render_task_card(
            task_id=task["id"],
            title=task["title"],
            status=task["status"],
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
        )
        print(card)

    try:
        from .updater import check_for_updates
        latest_version = check_for_updates()
        if latest_version:
            print(_("status.new_version", latest_version=latest_version))
            print("    curl -sSL https://raw.githubusercontent.com/Kaia-Alenia/fokiz/main/install.sh | bash\n")
    except Exception:
        pass

    return 0


