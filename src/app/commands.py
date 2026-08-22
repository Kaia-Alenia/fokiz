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
from .i18n import _

import logging
import os
import shutil
import stat
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

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
# cmd_init
# ---------------------------------------------------------------------------

def cmd_init() -> int:
    """fokiz init — install Fokiz on this system."""
    print(ui.render_banner(size="LARGE"))
    ui.print_section(_("FOKIZ INIT"))

    # 1. Platform check
    if sys.platform != "linux":
        ui.print_error(_("Fokiz requiere Linux."))
        return 1

    # 2. Python version
    if sys.version_info < (3, 8):
        ui.print_error(_("Se requiere Python >= 3.8."))
        return 1

    # 3. systemd --user
    result = subprocess.run(
        ["systemctl", "--user", "status"],
        capture_output=True,
        timeout=10,
    )
    if result.returncode not in (0, 1, 3):
        ui.print_warning(_("systemd --user no disponible. Las notificaciones automáticas no funcionarán."))

    # 4. Dependencies
    deps = {
        "notify-send": "Notificaciones de escritorio",
        "xprintidle": "Detección de presencia (opcional)",
    }
    for dep, desc in deps.items():
        if shutil.which(dep):
            ui.print_success(_(f"{dep} — {desc}"))
        else:
            ui.print_warning(_(f"{dep} no encontrado — {desc}"))

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
                ui.print_success(_("Configuración de notificaciones de XFCE actualizada (historial activado)."))
            
            # Disable Do Not Disturb (permanently prevent muting)
            subprocess.run(
                ["xfconf-query", "-c", "xfce4-notifyd", "-p", "/do-not-disturb", "-s", "false"],
                capture_output=True, timeout=5
            )
        except Exception as e:
            log.debug(f"Fallo al configurar xfce4-notifyd: {e}")

    # 5. Nickname
    nickname = ui.prompt(_("Ingresa tu nombre o apodo"))
    if not nickname:
        ui.print_error(_("El nombre no puede estar vacío."))
        return 1

    # 6. Timezone
    from .constants import DEFAULT_TIMEZONE
    tz = ui.prompt(_("Zona horaria"), default=DEFAULT_TIMEZONE)

    # 7. Create directories
    FOKIZ_DATA_DIR.mkdir(parents=True, exist_ok=True)
    FOKIZ_BIN_DIR.mkdir(parents=True, exist_ok=True)
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    ui.print_success(_("Directorios creados."))

    # 8. Generate .secret if not exists
    if SECRET_PATH.exists():
        ui.print_info(_(".secret ya existe — preservado."))
    elif DB_PATH.exists():
        # DB exists but no secret — dangerous, block
        ui.print_error(_(".secret no encontrado pero data.db existe. "
            "Integridad comprometida. Recupera manualmente.")
        )
        return 1
    else:
        generate_secret(SECRET_PATH)
        ui.print_success(_(".secret generado."))

    # 9. Create SQLite + schema (idempotent)
    db.create_schema(DB_PATH)
    ui.print_success(_("Base de datos SQLite inicializada."))

    # 10. User config
    db.upsert_user_config(nickname=nickname, timezone=tz)
    save_config({"timezone": tz, "max_active_slots": MAX_ACTIVE_SLOTS})
    ui.print_success(_(f"Configuración guardada (nick: {nickname}, tz: {tz})."))

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

    ui.print_section(_("Instalación completa"))
    ui.print_success(_("Fokiz está listo. Usa 'fokiz add' para crear tu primer contrato."))
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
    ui.print_success(_("Wrappers instalados en ~/.local/bin/"))


def _install_systemd() -> None:
    monitor_bin = FOKIZ_BIN_DIR / "fokiz-monitor"
    service_content = _SERVICE_TEMPLATE.format(monitor_path=str(monitor_bin))

    service_path = SYSTEMD_USER_DIR / "fokiz-monitor.service"
    timer_path = SYSTEMD_USER_DIR / "fokiz-monitor.timer"

    service_path.write_text(service_content, encoding="utf-8")
    timer_path.write_text(_TIMER_TEMPLATE, encoding="utf-8")
    ui.print_success(_("Unidades systemd instaladas."))


def _install_shell_hook() -> None:
    hook_line = "# Fokiz Terminal Hook\n[[ $- == *i* ]] && fokiz status --banner 2>/dev/null\n"
    for rc_file in (Path.home() / ".bashrc", Path.home() / ".zshrc"):
        if rc_file.exists():
            content = rc_file.read_text(encoding="utf-8")
            if "# Fokiz Terminal Hook" not in content:
                with rc_file.open("a", encoding="utf-8") as f:
                    f.write(f"\n{hook_line}")
                ui.print_success(_(f"Hook instalado en {rc_file.name}"))
            else:
                ui.print_info(_(f"Hook ya presente en {rc_file.name}"))


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
        ui.print_success(_("Timer systemd activado."))
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        ui.print_warning(_("No se pudo activar el timer systemd. Actívalo manualmente."))


def _run_diagnostic() -> None:
    ui.print_section(_("Diagnóstico"))
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
            ui.print_warning(_(f"{name} — no encontrado"))


# ---------------------------------------------------------------------------
# cmd_add
# ---------------------------------------------------------------------------

def cmd_add() -> int:
    """fokiz add — create a new Ulysses contract interactively."""
    _require_initialized()

    ui.print_section(_("NUEVO CONTRATO DE ULISES"))
    ui.print_warning(_("Este contrato es irreversible. Una vez confirmado, no podrás modificar el plazo."))

    # Slot check
    active_count = db.count_active_tasks()
    if active_count >= MAX_ACTIVE_SLOTS:
        ui.print_error(_(f"Slots activos llenos ({active_count}/{MAX_ACTIVE_SLOTS}). Completa o ríndete primero."))
        return 1

    # Collect inputs
    title = ui.prompt(_("Título del proyecto (5–80 caracteres)"))
    objective = ui.prompt(_("Objetivo (10–200 caracteres)"))

    total_days = ui.prompt_int(_("Días totales para el proyecto"), minimum=1)
    total_phases = ui.prompt_int(_("Número de fases (1–8)"), minimum=1, maximum=8)

    phase_inputs = []
    remaining_days = total_days
    for i in range(1, total_phases + 1):
        ui.print_section(_(f"Fase {i} de {total_phases}"))
        ph_title = ui.prompt(_(f"Título de la fase {i}"))
        ph_instructions = ui.prompt(_(f"Instrucciones/criterios de la fase {i}"))
        if i < total_phases:
            ph_days = ui.prompt_int(_(f"Días asignados a la fase {i} (quedan {remaining_days} para {total_phases - i + 1} fases)"),
                minimum=1,
                maximum=remaining_days - (total_phases - i),
            )
        else:
            ph_days = remaining_days
            ui.print_info(_(f"Días asignados a la fase {i}: {ph_days} (resto automático)"))
        remaining_days -= ph_days
        phase_inputs.append({
            "title": ph_title,
            "instructions": ph_instructions,
            "days": ph_days,
        })

    # Build and validate contract
    try:
        contract = build_contract(
            title=title,
            objective=objective,
            total_days=total_days,
            total_phases=total_phases,
            phase_inputs=phase_inputs,
        )
    except ValidationError as e:
        ui.print_error(str(e))
        return 1

    # Show summary
    ui.print_section(_("RESUMEN DEL CONTRATO"))
    print(f"  Título    : {contract.title}")
    print(f"  Objetivo  : {contract.objective}")
    print(f"  Días      : {contract.total_days}")
    print(f"  Fases     : {contract.total_phases}")
    print(f"  Creado    : {contract.created_at}")
    print(f"  Deadline  : {contract.deadline}")
    for ph in contract.phases:
        print(f"  Fase {ph.phase_number}: {ph.title} → {ph.target_deadline} ({ph.days}d)")

    if not ui.confirm(_("\n¿Confirmas este contrato? No hay vuelta atrás")):
        ui.print_info(_("Contrato cancelado."))
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
        ui.print_error(_(f"Verificación HMAC inmediata falló: {status.value}"))
        return 1

    ui.print_success(_(f"Contrato creado. ID de tarea: #{task_id}"))
    ui.print_success(_("HMAC verificado correctamente."))
    return 0



def cmd_status(show_banner: bool = False, show_completed: bool = False) -> int:
    """fokiz status — display tasks (active or completed depending on flag)."""
    if not DB_PATH.exists():
        ui.print_error(_("Fokiz no está inicializado. Ejecuta 'fokiz init'."))
        return 1

    if show_banner:
        print(ui.render_banner(size="LARGE"))

    tasks = db.get_all_tasks()
    
    if not show_completed:
        tasks = [t for t in tasks if t["status"] != "COMPLETED"]
    else:
        tasks = [t for t in tasks if t["status"] == "COMPLETED"]
        
    if not tasks:
        msg = _("No hay tareas registradas.") if show_completed else _("ui_no_active")
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
            phase_label = "Todas completadas"
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
            print(f"\n\033[93m[i] Nueva versión de Fokiz disponible ({latest_version}).\033[0m")
            print("    Actualiza ejecutando:")
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
        ui.print_error(_(f"La tarea #{task_id} no está activa (estado: {task['status']})."))
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
        ui.print_error(_("No se puede completar una fase con contrato manipulado."))
        return 1

    # Active phase
    try:
        active_phase = db.get_active_phase(task_id)
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    # Show instructions
    ui.print_section(_(f"Fase #{active_phase['phase_number']} — {active_phase['title']}"))
    print(f"  Instrucciones: {active_phase['instructions']}")
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
    log_text = ui.prompt_multiline(_("Bitácora de la fase — ¿qué hiciste exactamente?"))

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
    if not ui.confirm(_(f"¿Confirmas la fase #{active_phase['phase_number']} como COMPLETADA?")):
        ui.print_info(_("Operación cancelada."))
        return 0

    # Complete phase
    now_iso = _utcnow_iso()
    try:
        db.complete_phase(task_id, active_phase["phase_number"], log_text, now_iso)
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    ui.print_success(_(f"Fase #{active_phase['phase_number']} completada."))

    # Check if all phases are done
    updated_phases = db.get_phases(task_id)
    all_done = all(ph["status"] == "COMPLETED" for ph in updated_phases)
    if all_done:
        try:
            db.complete_task(task_id, now_iso)
        except FokizError as e:
            ui.print_error(str(e))
            return 1
        ui.print_success(_(f"¡Proyecto #{task_id} COMPLETADO! El contrato queda cerrado."))
    else:
        remaining = [ph for ph in updated_phases if ph["status"] == "PENDING"]
        ui.print_info(_(f"Siguiente fase: #{remaining[0]['phase_number']} — {remaining[0]['title']}"))

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
        ui.print_error(_(f"La tarea #{task_id} no está activa (estado: {task['status']})."))
        return 1

    phases = db.get_phases(task_id)

    # Integrity — surrender cannot erase tamper evidence
    status_integrity = check_contract_integrity(task, phases)
    if status_integrity == IntegrityStatus.TAMPERED:
        ui.print_tampered_warning(task_id)
        ui.print_error(_("No se puede rendir con contrato manipulado. "
            "La rendición no borra la evidencia de manipulación.")
        )
        return 1

    ui.print_section(_(f"RENDICIÓN — Tarea #{task_id}: {task['title']}"))
    ui.print_warning(_("Esto marcará la tarea como SURRENDERED permanentemente. "
        "El registro histórico se conserva.")
    )

    if not ui.confirm(_("¿Confirmas la rendición?")):
        ui.print_info(_("Operación cancelada."))
        return 0

    reason = ui.prompt(_(f"Motivo de la rendición (mínimo {SURRENDER_REASON_MIN} caracteres)"))
    if len(reason.strip()) < SURRENDER_REASON_MIN:
        ui.print_error(_(f"El motivo debe tener al menos {SURRENDER_REASON_MIN} caracteres."))
        return 1

    try:
        db.surrender_task(task_id, reason)
    except FokizError as e:
        ui.print_error(str(e))
        return 1

    ui.print_warning(_(f"Tarea #{task_id} marcada como SURRENDERED."))
    ui.print_info(_("El contrato y la rendición quedan registrados permanentemente."))
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
            phase_label = "Todas completadas"
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
        current_lang = data.get('lang', 'auto')
        print(f"Idioma actual / Current language: {current_lang}")
        choice = ui.prompt("Selecciona idioma / Select language (es / en)")
        if choice.lower() in ("es", "en"):
            lang_arg = choice.lower()
        else:
            ui.print_error("Idioma no válido / Invalid language.")
            return 1
            
    if lang_arg not in ("es", "en"):
        ui.print_error("Idioma no válido / Invalid language.")
        return 1
        
    data["lang"] = lang_arg
    save_config(data)
    ui.print_success(f"Idioma cambiado a / Language changed to: {lang_arg}")
    return 0
