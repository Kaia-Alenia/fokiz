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
from ._guards import _require_initialized

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

from ..time_utils import _parse_utc, _utcnow_iso
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
    recompute_hmac,
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


# ---------------------------------------------------------------------------
# cmd_done
# ---------------------------------------------------------------------------

def cmd_done(task_id: int) -> int:
    """fokiz done <task_id> — complete the active phase of a task."""
    _require_initialized()
    
    try:
        task = db.get_task(task_id)
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    if task["status"] != "ACTIVE":
        ui.print_error(_("status.task_not_active", task_id=task_id, status=task['status']))
        return 1

    phases = db.get_phases(task_id)

    # Integrity check — TAMPERED blocks done
    status_integrity = check_contract_integrity(task, phases)
    if status_integrity == IntegrityStatus.KEY_MISSING:
        ui.print_key_missing_warning()
        return 1
    if status_integrity == IntegrityStatus.TAMPERED:
        ui.print_tampered_warning(task_id)
        db.log_integrity_event("TAMPERED_BLOCKED_DONE", task_id=task_id)
        ui.print_error(_("done.tampered_block"))
        return 1

    # Active phase
    try:
        active_phase = db.get_active_phase(task_id)
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    # Show instructions
    ui.print_section(_("done.phase_section", phase_number=active_phase['phase_number'], title=active_phase['title']))
    print(_("done.field_instructions", instructions=active_phase['instructions']))
    print(_("done.field_deadline", deadline=active_phase['target_deadline']))

    # Compute τ for anti-cheat
    now = datetime.now(timezone.utc)
    phases_done = sum(1 for ph in phases if ph["status"] == "COMPLETED")
    prev_deadline_str = task["created_at"]
    for ph in sorted(phases, key=lambda p: p["phase_number"]):
        if ph["phase_number"] < active_phase["phase_number"]:
            prev_deadline_str = ph["target_deadline"]
    t_start = _parse_utc(prev_deadline_str)
    t_phase_dl = _parse_utc(active_phase["target_deadline"])
    tau = compute_tau(now, t_start, t_phase_dl)

    # Request journal log
    print()
    log_text = ui.prompt_multiline(_("done.log_prompt"))

    # Anti-cheat validation
    try:
        validate_completion_log(
            log=log_text,
            instructions=active_phase["instructions"],
            tau=tau,
        )
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    # Confirmation
    if not ui.confirm(_("done.confirm_prompt", phase_number=active_phase['phase_number'])):
        ui.print_info(_("ui.cancelled"))
        return 0

    # Complete phase
    now_iso = _utcnow_iso()
    phase_overrides = {
        active_phase["phase_number"]: {
            "status": "COMPLETED",
            "completed_at": now_iso,
            "completion_log": log_text,
        }
    }
    
    # Check if all phases are done
    updated_phases = [dict(ph) for ph in phases]
    for ph in updated_phases:
        if ph["phase_number"] == active_phase["phase_number"]:
            ph["status"] = "COMPLETED"
            ph["completed_at"] = now_iso
            ph["completion_log"] = log_text

    all_done = all(ph["status"] == "COMPLETED" for ph in updated_phases)
    
    task_overrides = {}
    if all_done:
        task_overrides["status"] = "COMPLETED"
        task_overrides["completed_at"] = now_iso

    try:
        if all_done:
            db.complete_phase_and_task(task_id, active_phase["phase_number"], log_text, now_iso)
        else:
            db.complete_phase(task_id, active_phase["phase_number"], log_text, now_iso)
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    ui.print_success(_("done.phase_completed", phase_number=active_phase['phase_number']))

    if all_done:
        ui.print_success(_("done.project_completed", task_id=task_id))
    else:
        remaining = [ph for ph in updated_phases if ph["status"] == "PENDING"]
        ui.print_info(_("done.next_phase", phase_number=remaining[0]['phase_number'], title=remaining[0]['title']))

    return 0


