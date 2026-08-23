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


# ---------------------------------------------------------------------------
# cmd_add
# ---------------------------------------------------------------------------

def cmd_add() -> int:
    """fokiz add — create a new Ulysses contract interactively."""
    _require_initialized()

    ui.print_section(_("contract.summary_title"))
    ui.print_warning(_("contract.warning"))

    # Slot check
    active_count = db.count_active_tasks()
    if active_count >= MAX_ACTIVE_SLOTS:
        ui.print_error(_("contract.slots_full", active_count=active_count, max_slots=MAX_ACTIVE_SLOTS))
        return 1

    # Collect inputs
    title = ui.prompt(_("contract.title_prompt"))
    objective = ui.prompt(_("contract.objective_prompt"))

    total_days = ui.prompt_int(_("contract.days_prompt"), minimum=1)
    total_phases = ui.prompt_int(_("contract.phases_prompt"), minimum=1, maximum=8)

    phase_inputs = []
    remaining_days = total_days
    for i in range(1, total_phases + 1):
        ui.print_section(_("contract.phase_section", i=i, total_phases=total_phases))
        ph_title = ui.prompt(_("contract.phase_title_prompt", i=i))
        ph_instructions = ui.prompt(_("contract.phase_instructions_prompt", i=i))
        if i < total_phases:
            ph_days = ui.prompt_int(
                _("contract.phase_days_prompt", i=i, remaining_days=remaining_days, rem_phases=total_phases - i + 1),
                minimum=1,
                maximum=remaining_days - (total_phases - i),
            )
        else:
            ph_days = remaining_days
            ui.print_info(_("contract.phase_days_auto", i=i, ph_days=ph_days))
        remaining_days -= ph_days
        phase_inputs.append({
            "title": ph_title,
            "instructions": ph_instructions,
            "days": ph_days,
        })

    # Build and validate contract
    # Load user timezone from config
    cfg = load_config()
    user_tz = cfg.get("timezone", None)
    try:
        contract = build_contract(
            title=title,
            objective=objective,
            total_days=total_days,
            total_phases=total_phases,
            phase_inputs=phase_inputs,
            user_timezone=user_tz,
        )
    except ValidationError as e:
        ui.print_error(str(e))
        return 1

    # Show summary
    ui.print_section(_("contract.summary_header"))
    print(_("contract.field_title", title=contract.title))
    print(_("contract.field_objective", objective=contract.objective))
    print(_("contract.field_days", days=contract.total_days))
    print(_("contract.field_phases", phases=contract.total_phases))
    print(_("contract.field_created", created_at=contract.created_at))
    print(_("contract.field_deadline", deadline=contract.deadline))
    for ph in contract.phases:
        print(_("contract.phase_row", phase_number=ph.phase_number, title=ph.title, target_deadline=ph.target_deadline, days=ph.days))

    if not ui.confirm(_("contract.confirm_prompt")):
        ui.print_info(_("contract.cancelled"))
        return 0

    # Insert task
    try:
        task_id = db.insert_task(
            title=contract.title,
            objective=contract.objective,
            total_days=contract.total_days,
            total_phases=contract.total_phases,
            deadline=contract.deadline,
            created_at=contract.created_at,
            integrity_hash="PENDING",  # placeholder
        )
    except (MaxSlotsError, FokizError) as e:
        ui.print_error(str(e))
        return 1

    # Insert phases
    phase_dicts = [
        {
            "phase_number": ph.phase_number,
            "title": ph.title,
            "instructions": ph.instructions,
            "target_deadline": ph.target_deadline,
        }
        for ph in contract.phases
    ]
    try:
        db.insert_phases(task_id=task_id, phases=phase_dicts)
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    # Compute and store HMAC
    payload = build_canonical_payload(
        task_id=task_id,
        title=contract.title,
        objective=contract.objective,
        total_days=contract.total_days,
        total_phases=contract.total_phases,
        created_at=contract.created_at,
        deadline=contract.deadline,
        phases=contract_to_phase_dicts(contract),
    )
    try:
        integrity_hash = compute_hmac(payload)
    except IntegrityKeyMissingError as e:
        ui.print_error(str(e))
        return 1

    # Update integrity_hash (allowed because task was just created with placeholder)
    db.finalize_task_hmac(task_id, integrity_hash)

    # Immediate verification
    task_row = db.get_task(task_id)
    phases_rows = db.get_phases(task_id)
    status = check_contract_integrity(task_row, phases_rows)
    if status != IntegrityStatus.OK:
        ui.print_error(_("contract.hmac_verification_failed", status=status.value))
        return 1

    ui.print_success(_("contract.created", task_id=task_id))
    ui.print_success(_("init.hmac_verified"))
    return 0



