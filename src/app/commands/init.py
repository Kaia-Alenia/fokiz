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
from .. math_engine import (
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
from ..templates import (
    SERVICE_TEMPLATE,
    TIMER_TEMPLATE,
    FOKIZ_WRAPPER_TEMPLATE,
    MONITOR_WRAPPER_TEMPLATE,
)

log = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Timezone helpers for fokiz init
# ---------------------------------------------------------------------------

def _detect_system_timezone() -> str | None:
    """
    Attempt to detect the system's IANA timezone identifier.

    Strategy (in order of preference):
    1. Read /etc/localtime symlink and extract the IANA name.
    2. Read /etc/timezone file (Debian/Ubuntu style).
    3. Parse `timedatectl show` output.

    Returns an IANA timezone string (e.g. "America/Mexico_City") or None
    if detection fails.  Never returns a GMT/UTC offset string.
    """
    import os as _os

    # Strategy 1: /etc/localtime symlink
    try:
        link = _os.readlink("/etc/localtime")
        # Typical path: /usr/share/zoneinfo/America/Mexico_City
        if "zoneinfo/" in link:
            tz_name = link.split("zoneinfo/", 1)[1]
            ZoneInfo(tz_name)  # validate
            return tz_name
    except (OSError, Exception):
        pass

    # Strategy 2: /etc/timezone file
    try:
        tz_name = Path("/etc/timezone").read_text(encoding="utf-8").strip()
        if tz_name:
            ZoneInfo(tz_name)  # validate
            return tz_name
    except Exception:
        pass

    # Strategy 3: timedatectl
    try:
        result = subprocess.run(
            ["timedatectl", "show", "--property=Timezone", "--value"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            tz_name = result.stdout.strip()
            if tz_name:
                ZoneInfo(tz_name)  # validate
                return tz_name
    except Exception:
        pass

    return None


def _prompt_iana_timezone() -> str:
    """
    Interactively prompt the user for a valid IANA timezone identifier.

    Keeps asking until the user provides a string accepted by ZoneInfo.
    Returns the validated IANA string.
    """
    while True:
        tz_input = ui.prompt(
            _("init.timezone_prompt")
        )
        try:
            ZoneInfo(tz_input)
            return tz_input
        except Exception:
            ui.print_error(_("init.timezone_invalid", tz=tz_input))


# ---------------------------------------------------------------------------
# cmd_init
# ---------------------------------------------------------------------------

def cmd_init() -> int:
    """fokiz init — install Fokiz on this system."""
    print(ui.render_banner())
    ui.print_section(_("init.title"))

    # 1. Platform check
    if sys.platform != "linux":
        ui.print_error(_("init.linux_required"))
        return 1

    # 2. Python version
    if sys.version_info < (3, 8):
        ui.print_error(_("init.python_required"))
        return 1

    # 3. systemd --user
    result = subprocess.run(
        ["systemctl", "--user", "status"],
        capture_output=True,
        timeout=10,
    )
    if result.returncode not in (0, 1, 3):
        ui.print_warning(_("init.systemd_not_running"))

    # 4. Dependencies
    deps = {
        "notify-send": _("init.dep_notifications"),
        "xprintidle": _("init.dep_presence"),
    }
    for dep, desc in deps.items():
        if shutil.which(dep):
            ui.print_success(_("init.dep_found", dep=dep, desc=desc))
        else:
            ui.print_warning(_("init.dep_missing", dep=dep, desc=desc))

    # 4.5. XFCE Notification logging fix
    if shutil.which("xfconf-query"):
        try:
            # Check and fix log level
            xfce_check = subprocess.run(
                ["xfconf-query", "-c", "xfce4-notifyd", "-p", "/log-level"],
                capture_output=True, text=True, timeout=5
            )
            if xfce_check.returncode == 0 and xfce_check.stdout.strip() != "0":
                subprocess.run(
                    ["xfconf-query", "-c", "xfce4-notifyd", "-p", "/log-level", "-s", "0"],
                    capture_output=True, timeout=5
                )
                ui.print_success(_("init.xfce_notifications_updated"))
            
            # Disable Do Not Disturb (permanently prevent muting)
            subprocess.run(
                ["xfconf-query", "-c", "xfce4-notifyd", "-p", "/do-not-disturb", "-s", "false"],
                capture_output=True, timeout=5
            )
        except Exception as e:
            log.debug(f"Failed to configure xfce4-notifyd: {e}")

    # 5. Nickname
    nickname = ui.prompt(_("init.nickname_prompt"))
    if not nickname:
        ui.print_error(_("init.name_empty"))
        return 1

    # 6. Timezone — detect system IANA timezone, confirm or let user set it
    detected_tz = _detect_system_timezone()
    if detected_tz:
        print()
        print(_("init.timezone_detected"))
        print(f"  {detected_tz}")
        use_detected = ui.confirm(_("init.timezone_use_detected"))
        if use_detected:
            tz = detected_tz
        else:
            tz = _prompt_iana_timezone()
    else:
        ui.print_warning(_("init.timezone_detection_failed"))
        tz = _prompt_iana_timezone()

    # 7. Create directories
    FOKIZ_DATA_DIR.mkdir(parents=True, exist_ok=True)
    FOKIZ_BIN_DIR.mkdir(parents=True, exist_ok=True)
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    ui.print_success(_("init.directories_created"))

    # 8. Generate .secret if not exists
    if SECRET_PATH.exists():
        ui.print_info(_("init.secret_preserved"))
    elif DB_PATH.exists():
        # DB exists but no secret — dangerous, block
        ui.print_error(_("init.secret_integrity_broken"))
        return 1
    else:
        generate_secret(SECRET_PATH)
        ui.print_success(_("init.secret_generated"))

    # 9. Create SQLite + schema (idempotent)
    db.create_schema(DB_PATH)
    ui.print_success(_("init.db_initialized"))

    # 10. User config
    db.upsert_user_config(nickname=nickname, timezone=tz)
    save_config({"timezone": tz, "max_active_slots": MAX_ACTIVE_SLOTS})
    ui.print_success(_("init.config_saved", nickname=nickname, tz=tz))

    # 11. Install wrappers
    _install_wrappers()

    # 12. Install systemd units
    _install_systemd()

    # 13. Install terminal hook
    _install_shell_hook()

    # 14. Activate timer
    _activate_systemd_timer()

    # 15. Diagnostic run
    _run_diagnostic()

    ui.print_section(_("init.complete"))
    ui.print_success(_("init.ready"))
    return 0


def _install_wrappers() -> None:
    src_app = Path(__file__).resolve().parents[3]
    python_exec = shutil.which("python3") or sys.executable

    fokiz_bin = FOKIZ_BIN_DIR / "fokiz"
    fokiz_monitor_bin = FOKIZ_BIN_DIR / "fokiz-monitor"
    monitor_py = src_app / "src" / "monitor.py"

    fokiz_bin.write_text(
        FOKIZ_WRAPPER_TEMPLATE.format(
            app_dir=str(src_app),
            script_dir=str(src_app),
            python_exec=python_exec
        ),
        encoding="utf-8",
    )
    fokiz_bin.chmod(0o755)

    fokiz_monitor_bin.write_text(
        MONITOR_WRAPPER_TEMPLATE.format(
            app_dir=str(src_app),
            script_dir=str(src_app),
            python_exec=python_exec,
            monitor_py_path=str(monitor_py),
        ),
        encoding="utf-8",
    )
    fokiz_monitor_bin.chmod(0o755)
    ui.print_success(_("installer.wrappers_installed"))


def _install_systemd() -> None:
    src_app = Path(__file__).resolve().parents[3]
    monitor_bin = FOKIZ_BIN_DIR / "fokiz-monitor"
    service_content = SERVICE_TEMPLATE.format(
        monitor_path=str(monitor_bin),
        script_dir=str(src_app)
    )

    service_path = SYSTEMD_USER_DIR / "fokiz-monitor.service"
    timer_path = SYSTEMD_USER_DIR / "fokiz-monitor.timer"

    service_path.write_text(service_content, encoding="utf-8")
    timer_path.write_text(TIMER_TEMPLATE, encoding="utf-8")
    ui.print_success(_("init.systemd_units_installed"))


def _install_shell_hook() -> None:
    hook_line = "# Fokiz Terminal Hook\n[[ $- == *i* ]] && fokiz status --banner 2>/dev/null\n"
    for rc_file in (Path.home() / ".bashrc", Path.home() / ".zshrc"):
        if rc_file.exists():
            content = rc_file.read_text(encoding="utf-8")
            if "# Fokiz Terminal Hook" not in content:
                with rc_file.open("a", encoding="utf-8") as f:
                    f.write(f"\n{hook_line}")
                ui.print_success(_("init.hook_installed", file=rc_file.name))
            else:
                ui.print_info(_("init.hook_already_present", file=rc_file.name))


def _activate_systemd_timer() -> None:
    try:
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True, timeout=15,
        )
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", "fokiz-monitor.timer"],
            capture_output=True, timeout=15,
        )
        ui.print_success(_("init.systemd_timer_activated"))
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        ui.print_warning(_("init.systemd_timer_failed"))


def _run_diagnostic() -> None:
    ui.print_section(_("status.title"))
    checks = {
        "data.db": DB_PATH.exists(),
        ".secret": SECRET_PATH.exists(),
        "fokiz wrapper": (FOKIZ_BIN_DIR / "fokiz").exists(),
        "fokiz-monitor wrapper": (FOKIZ_BIN_DIR / "fokiz-monitor").exists(),
        "systemd service": (SYSTEMD_USER_DIR / "fokiz-monitor.service").exists(),
        "systemd timer": (SYSTEMD_USER_DIR / "fokiz-monitor.timer").exists(),
    }
    for name, ok in checks.items():
        if ok:
            ui.print_success(name)
        else:
            ui.print_warning(_("init.diag_not_found", name=name))


