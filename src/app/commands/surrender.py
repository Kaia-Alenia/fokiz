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

from ..time_utils import _utcnow_iso
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
# cmd_surrender
# ---------------------------------------------------------------------------

def cmd_surrender(task_id: int) -> int:
    """fokiz surrender <task_id> — formally surrender a task."""
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

    # Integrity — surrender cannot erase tamper evidence
    status_integrity = check_contract_integrity(task, phases)
    if status_integrity == IntegrityStatus.TAMPERED:
        ui.print_tampered_warning(task_id)
        ui.print_error(_("surrender.tampered_block"))
        return 1

    ui.print_section(_("surrender.section", task_id=task_id, title=task['title']))
    ui.print_warning(_("surrender.warning"))

    if not ui.confirm(_("surrender.confirm_prompt")):
        ui.print_info(_("ui.cancelled"))
        return 0

    reason = ui.prompt(_("surrender.reason_prompt", min_chars=SURRENDER_REASON_MIN))
    if len(reason.strip()) < SURRENDER_REASON_MIN:
        ui.print_error(_("surrender.reason_too_short", min_chars=SURRENDER_REASON_MIN))
        return 1

    now_iso = _utcnow_iso()
    try:
        db.surrender_task(task_id, reason, now_iso)
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    ui.print_warning(_("surrender.marked", task_id=task_id))
    ui.print_info(_("surrender.recorded"))
    return 0


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _require_initialized() -> None:
    if not DB_PATH.exists() or not SECRET_PATH.exists():
        raise NotInitializedError()

# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _require_initialized() -> None:
    if not DB_PATH.exists() or not SECRET_PATH.exists():
        raise NotInitializedError()

