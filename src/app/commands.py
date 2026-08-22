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
from .i18n import _, set_language

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

from .anti_cheat import validate_completion_log
from .config import load_config, save_config
from .constants import (
    FOKIZ_DATA_DIR,
    FOKIZ_BIN_DIR,
    SYSTEMD_USER_DIR,
    DB_PATH,
    SECRET_PATH,
    APP_DIR,
    SURRENDER_REASON_MIN,
    MAX_ACTIVE_SLOTS,
)
from .contracts import build_contract, contract_to_phase_dicts
from . import db
from .errors import (
    FokizError,
    IntegrityKeyMissingError,
    ContractTamperedError,
    DatabaseMissingError,
    NotInitializedError,
    MaxSlotsError,
    ValidationError,
)
from .integrity import (
    IntegrityStatus,
    build_canonical_payload,
    check_contract_integrity,
    compute_hmac,
    generate_secret,
    assert_contract_ok,
)
from .math_engine import (
    Zone,
    compute_delta,
    compute_i_spam,
    compute_iu,
    compute_tau,
    classify_delta,
    classify_zone,
)
from . import ui
from .messages import get_delta_label, pick_message, urgency_label

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SYSTEMD UNIT TEMPLATES
# ---------------------------------------------------------------------------

_SERVICE_TEMPLATE = """\
[Unit]
Description=Fokiz Task Monitor and Procrastination Engine
After=graphical-session.target

[Service]
Type=oneshot
ExecStart={monitor_path}
StandardOutput=null
StandardError=journal
"""

_TIMER_TEMPLATE = """\
[Unit]
Description=Fokiz 1-Minute Evaluation Timer

[Timer]
OnBootSec=1m
OnUnitActiveSec=1m
Persistent=true

[Install]
WantedBy=timers.target
"""

_FOKIZ_WRAPPER = """\
#!/usr/bin/env bash
# Fokiz CLI wrapper
FOKIZ_APP="{app_dir}"
exec python3 "$FOKIZ_APP/cli.py" "$@"
"""

_MONITOR_WRAPPER = """\
#!/usr/bin/env bash
# Fokiz monitor wrapper
FOKIZ_APP="{app_dir}"
exec python3 "{monitor_path}" "$@"
"""


# ---------------------------------------------------------------------------
# Helper: parse UTC iso string → datetime
# ---------------------------------------------------------------------------

def _parse_utc(iso: str) -> datetime:
    return datetime.strptime(iso, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


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
    from .constants import DEFAULT_TIMEZONE
    while True:
        tz_input = ui.prompt(
            _("init.timezone_prompt"),
            default=DEFAULT_TIMEZONE,
        )
        try:
            ZoneInfo(tz_input)
            return tz_input
        except Exception:
            ui.print_error(
                f"'{tz_input}' is not a valid IANA identifier. "
                "Examples: America/Mexico_City, Europe/Madrid, Asia/Tokyo."
            )


# ---------------------------------------------------------------------------
# cmd_init
# ---------------------------------------------------------------------------

def cmd_init() -> int:
    """fokiz init — install Fokiz on this system."""
    print(ui.render_banner(size="LARGE"))
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
        "notify-send": "desktop notifications",
        "xprintidle": "presence detection (optional)",
    }
    for dep, desc in deps.items():
        if shutil.which(dep):
            ui.print_success(f"{dep} — {desc}")
        else:
            ui.print_warning(f"{dep} not found — {desc}")

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
    src_app = Path(__file__).parent

    fokiz_bin = FOKIZ_BIN_DIR / "fokiz"
    fokiz_monitor_bin = FOKIZ_BIN_DIR / "fokiz-monitor"
    monitor_py = FOKIZ_DATA_DIR / "monitor.py"

    fokiz_bin.write_text(
        _FOKIZ_WRAPPER.format(app_dir=str(src_app)),
        encoding="utf-8",
    )
    fokiz_bin.chmod(0o755)

    fokiz_monitor_bin.write_text(
        _MONITOR_WRAPPER.format(
            app_dir=str(src_app),
            monitor_path=str(monitor_py),
        ),
        encoding="utf-8",
    )
    fokiz_monitor_bin.chmod(0o755)
    ui.print_success(_("installer.wrappers_installed"))


def _install_systemd() -> None:
    monitor_bin = FOKIZ_BIN_DIR / "fokiz-monitor"
    service_content = _SERVICE_TEMPLATE.format(monitor_path=str(monitor_bin))

    service_path = SYSTEMD_USER_DIR / "fokiz-monitor.service"
    timer_path = SYSTEMD_USER_DIR / "fokiz-monitor.timer"

    service_path.write_text(service_content, encoding="utf-8")
    timer_path.write_text(_TIMER_TEMPLATE, encoding="utf-8")
    ui.print_success(_("init.systemd_units_installed"))


def _install_shell_hook() -> None:
    hook_line = "# Fokiz Terminal Hook\n[[ $- == *i* ]] && fokiz status --banner 2>/dev/null\n"
    for rc_file in (Path.home() / ".bashrc", Path.home() / ".zshrc"):
        if rc_file.exists():
            content = rc_file.read_text(encoding="utf-8")
            if "# Fokiz Terminal Hook" not in content:
                with rc_file.open("a", encoding="utf-8") as f:
                    f.write(f"\n{hook_line}")
                ui.print_success(f"Hook installed in {rc_file.name}")
            else:
                ui.print_info(f"Hook already present in {rc_file.name}")


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
        ui.print_success("systemd timer activated.")
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
            ui.print_warning(f"{name} — not found")


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
    print(f"  Created   : {contract.created_at}")
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
        ui.print_error(f"Immediate HMAC verification failed: {status.value}")
        return 1

    ui.print_success(_("contract.created", task_id=task_id))
    ui.print_success(_("init.hmac_verified"))
    return 0



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
            print(f"  Local time : {now_local.strftime('%d/%m/%Y %H:%M')}")
            print(f"  {_('status.timezone')}     : {tz_str}")
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
    print(f"  Instructions : {active_phase['instructions']}")
    print(f"  Deadline     : {active_phase['target_deadline']}")

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
    try:
        db.complete_phase(task_id, active_phase["phase_number"], log_text, now_iso)
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    ui.print_success(_("done.phase_completed", phase_number=active_phase['phase_number']))

    # Check if all phases are done
    updated_phases = db.get_phases(task_id)
    all_done = all(ph["status"] == "COMPLETED" for ph in updated_phases)
    if all_done:
        try:
            db.complete_task(task_id, now_iso)
        except FokizError as e:
            ui.print_error(str(e))
            return 1
        ui.print_success(_("done.project_completed", task_id=task_id))
    else:
        remaining = [ph for ph in updated_phases if ph["status"] == "PENDING"]
        ui.print_info(_("done.next_phase", phase_number=remaining[0]['phase_number'], title=remaining[0]['title']))

    return 0


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

    try:
        db.surrender_task(task_id, reason)
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
# cmd_board
# ---------------------------------------------------------------------------

def cmd_board() -> int:
    """fokiz board — display active and completed tasks side-by-side."""
    _require_initialized()

    tasks = db.get_all_tasks()
    
    active_tasks = []
    completed_tasks = []
    now = datetime.now(timezone.utc)
    
    for task in tasks:
        phases = db.get_phases(task["id"])
        
        # Integrity check
        status_integrity = check_contract_integrity(task, phases)
        if status_integrity == IntegrityStatus.KEY_MISSING:
            ui.print_key_missing_warning()
        elif status_integrity == IntegrityStatus.TAMPERED:
            # We skip tampered tasks or just mark them
            continue
            
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
        
        if task["status"] == "COMPLETED":
            completed_tasks.append(card)
        else:
            active_tasks.append(card)
            
    print(ui.render_board(active_tasks, completed_tasks))
    return 0

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
