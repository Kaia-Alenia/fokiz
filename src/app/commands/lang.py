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


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

def _require_initialized() -> None:
    if not DB_PATH.exists() or not SECRET_PATH.exists():
        raise NotInitializedError()

# ---------------------------------------------------------------------------
# cmd_lang
# ---------------------------------------------------------------------------

def cmd_lang(lang_arg: str | None = None) -> int:
    """fokiz lang [en|es] — change the language."""
    _require_initialized()
    conf = load_config()
    data = dict(conf._data)
    
    if not lang_arg:
        current_lang = data.get('language', 'en')
        print(_("lang.current", current_lang=current_lang))
        choice = ui.prompt(_("lang.select_prompt"))
        if choice.lower() in ("es", "en"):
            lang_arg = choice.lower()
        else:
            ui.print_error(_("lang.invalid"))
            return 1

    if lang_arg not in ("es", "en"):
        ui.print_error(_("lang.invalid"))
        return 1

    data["language"] = lang_arg
    save_config(data)
    set_language(lang_arg)
    ui.print_success(_("lang.changed", lang_arg=lang_arg))
    return 0
