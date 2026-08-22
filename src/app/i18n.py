"""
i18n.py — Fokiz internationalization layer.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- All keys are stable English identifiers (dot-namespaced).
- Values in ES_STRINGS and EN_STRINGS are the ONLY place where
  human-readable text in a specific language may appear.
- Source code (commands.py, ui.py, etc.) MUST only use keys.
- No Spanish phrase may exist anywhere outside the values in ES_STRINGS.
"""

from __future__ import annotations

import json
import os

# ---------------------------------------------------------------------------
# Language resolution
# ---------------------------------------------------------------------------

_lang_file = os.path.join(
    os.path.expanduser("~"), ".local", "share", "fokiz", "config.json"
)

CURRENT_LANG: str = "en"  # safe default

try:
    if os.path.exists(_lang_file):
        with open(_lang_file, "r", encoding="utf-8") as _f:
            _data = json.load(_f)
            if isinstance(_data, dict) and _data.get("language") in ("en", "es"):
                CURRENT_LANG = _data["language"]
except Exception:
    pass


def set_language(lang: str) -> None:
    global CURRENT_LANG
    if lang in ("es", "en"):
        CURRENT_LANG = lang


# ---------------------------------------------------------------------------
# Spanish strings
# ---------------------------------------------------------------------------

ES_STRINGS: dict[str, str] = {
    # --- Contract / add ---
    "contract.title_prompt": "Título del proyecto (5–80 caracteres)",
    "contract.objective_prompt": "Objetivo (10–200 caracteres)",
    "contract.days_prompt": "Días totales para el proyecto",
    "contract.phases_prompt": "Número de fases (1–8)",
    "contract.phase_section": "Fase {i} de {total_phases}",
    "contract.phase_title_prompt": "Título de la fase {i}",
    "contract.phase_instructions_prompt": "Instrucciones de la fase {i}",
    "contract.phase_days_prompt": "Días asignados a la fase {i} (quedan {remaining_days} para {rem_phases} fases)",
    "contract.phase_days_auto": "Días asignados a la fase {i}: {ph_days} (resto automático)",
    "contract.warning": "⚠ Este contrato es irreversible. Una vez confirmado, no podrás modificar el plazo.",
    "contract.confirm_prompt": "\n¿Confirmas este contrato? No hay vuelta atrás",
    "contract.cancelled": "Contrato cancelado.",
    "contract.signed": "¡Contrato firmado en sangre! Tu enfoque comienza ahora.",
    "contract.created": "Contrato creado. ID de tarea: #{task_id}",
    "contract.summary_title": "NUEVO CONTRATO DE ULISES",
    "contract.summary_header": "RESUMEN DEL CONTRATO",
    "contract.field_title": "  Título    : {title}",
    "contract.field_objective": "  Objetivo  : {objective}",
    "contract.field_days": "  Días      : {days}",
    "contract.field_phases": "  Fases     : {phases}",
    "contract.field_deadline": "  Deadline  : {deadline}",
    "contract.phase_row": "  Fase {phase_number}: {title} → {target_deadline} ({days}d)",
    "contract.slots_full": "Slots activos llenos ({active_count}/{max_slots}). Completa o ríndete primero.",

    # --- Done ---
    "done.phase_section": "Fase #{phase_number} — {title}",
    "done.log_prompt": "Bitácora de la fase — ¿qué hiciste exactamente?",
    "done.confirm_prompt": "¿Confirmas la fase #{phase_number} como COMPLETADA?",
    "done.phase_completed": "Fase #{phase_number} completada.",
    "done.project_completed": "¡Proyecto #{task_id} COMPLETADO! El contrato queda cerrado.",
    "done.next_phase": "Siguiente fase: #{phase_number} — {title}",
    "done.tampered_block": "No se puede completar una fase con contrato manipulado.",

    # --- Surrender ---
    "surrender.section": "RENDICIÓN — Tarea #{task_id}: {title}",
    "surrender.warning": "Esto marcará la tarea como SURRENDERED permanentemente. El registro histórico se conserva.",
    "surrender.confirm_prompt": "¿Confirmas la rendición?",
    "surrender.reason_prompt": "Motivo de la rendición (mínimo {min_chars} caracteres)",
    "surrender.reason_too_short": "El motivo debe tener al menos {min_chars} caracteres.",
    "surrender.marked": "Tarea #{task_id} marcada como SURRENDERED.",
    "surrender.recorded": "El contrato y la rendición quedan registrados permanentemente.",
    "surrender.tampered_block": "No se puede rendir con contrato manipulado. La rendición no borra la evidencia de manipulación.",

    # --- Init ---
    "init.title": "FOKIZ INIT",
    "init.nickname_prompt": "Ingresa tu nombre o apodo",
    "init.name_empty": "El nombre no puede estar vacío.",
    "init.timezone_prompt": "Zona horaria IANA (ej. America/Mexico_City)",
    "init.timezone_detected": "Zona horaria detectada:",
    "init.timezone_use_detected": "¿Usar esta zona horaria?",
    "init.timezone_detection_failed": "No se pudo detectar la zona horaria del sistema.",
    "init.xfce_notifications_updated": "Configuración de notificaciones de XFCE actualizada (historial activado).",
    "init.directories_created": "Directorios creados.",
    "init.secret_generated": ".secret generado.",
    "init.secret_preserved": ".secret ya existe — preservado.",
    "init.secret_integrity_broken": ".secret no encontrado pero data.db existe. Integridad comprometida. Recupera manualmente.",
    "init.db_initialized": "Base de datos SQLite inicializada.",
    "init.config_saved": "Configuración guardada (nick: {nickname}, tz: {tz}).",
    "init.complete": "Instalación completa",
    "init.ready": "Fokiz está listo. Usa 'fokiz add' para crear tu primer contrato.",
    "init.linux_required": "Fokiz requiere Linux.",
    "init.python_required": "Se requiere Python >= 3.8.",
    "init.systemd_daemon_reload": "Recargando daemon de systemd --user…",
    "init.systemd_enabling": "Habilitando fokiz.timer…",
    "init.systemd_starting": "Iniciando fokiz.timer…",
    "init.systemd_active": "✓ fokiz.timer activo.",
    "init.systemd_units_installed": "Unidades systemd instaladas.",
    "init.systemd_not_running": "systemd --user no disponible. Las notificaciones automáticas no funcionarán.",
    "init.systemd_timer_failed": "⚠ No se pudo iniciar fokiz.timer. Revisa: journalctl --user -u fokiz.timer",
    "init.systemd_not_activated": "⚠ systemd --user no parece estar en ejecución. Las unidades se instalaron pero no se activarán.",
    "init.partial": "⚠ Instalación parcial. Revisa los mensajes anteriores.",
    "init.success": "¡Fokiz inicializado correctamente! Estructuras de inmutabilidad creadas.",
    "init.already_initialized": "Fokiz ya está inicializado.",
    "init.hmac_verified": "HMAC verificado correctamente.",
    "init.hash_correction": "⚠ Realizando corrección interna de hash...",

    # --- Status ---
    "status.title": "Diagnóstico",
    "status.timezone": "Zona horaria",
    "status.no_active": "No hay ningún contrato activo en este momento.",
    "status.no_tasks": "No hay tareas registradas.",
    "status.new_version": "\n\033[93m[i] Nueva versión de Fokiz disponible ({latest_version}).\033[0m",
    "status.task_not_active": "La tarea #{task_id} no está activa (estado: {status}).",

    # --- Lang ---
    "lang.current": "Idioma actual: {current_lang}",
    "lang.select_prompt": "Selecciona idioma (es / en)",
    "lang.changed": "Idioma cambiado a: {lang_arg}",
    "lang.invalid": "Idioma no válido.",

    # --- Board ---
    "board.in_progress": "EN PROGRESO",
    "board.completed": "COMPLETADO",
    "board.all_phases_done": "Todas completadas",

    # --- Card labels ---
    "card.task": "Tarea",
    "card.status": "Estado",
    "card.phase": "Fase",
    "card.progress": "Progreso",
    "card.phases_completed": "fases completadas",
    "card.zone": "Zona",
    "card.interval": "Intervalo",
    "card.remaining": "Restante",
    "card.deadline": "Deadline",

    # --- Delta labels ---
    "delta.ahead": "ADELANTADO — Zona de tregua",
    "delta.on_track": "AL DÍA — Mantén el ritmo",
    "delta.behind": "ATRASADO — Hostigamiento activo",

    # --- Time ---
    "time.min": "min",
    "time.sec": "s",
    "time.expired": "VENCIDO",

    # --- Integrity ---
    "integrity.tampered_header": "⚠ INTEGRIDAD COMPROMETIDA — Tarea #{task_id}",
    "integrity.hmac_mismatch": "El HMAC no coincide. El contrato ha sido manipulado externamente.",
    "integrity.blocked": "Operaciones contractuales bloqueadas hasta recuperación explícita.",
    "integrity.key_missing": ".secret no encontrado. No se puede verificar la integridad de los contratos.",
    "integrity.recover": "Ejecuta 'fokiz init' para recuperar o reinicializar.",

    # --- Errors ---
    "error.not_initialized": "Fokiz no está inicializado. Ejecuta 'fokiz init'.",
    "error.already_initialized": "Fokiz ya está inicializado.",
    "error.active_contract": "Ya existe un contrato activo.",
    "error.cooldown": "No puedes crear un nuevo contrato durante el período de enfriamiento.",
    "error.database": "Error de base de datos.",
    "error.integrity": "Error de Integridad: La base de datos de Fokiz ha sido manipulada o corrompida.",
    "error.integrity_key_missing": "Clave de integridad faltante. El archivo .secret no existe.",
    "error.tampered": "Integridad comprometida. El contrato ha sido manipulado.",
    "error.immutable": "Error de Fokiz: Contrato inmutable.",
    "error.invalid_transition": "Transición de estado inválida: {f} → {t}",
    "error.task_not_found": "Tarea #{tid} no encontrada.",
    "error.no_active_phase": "No hay fase activa para la tarea #{tid}.",
    "error.max_slots": "Límite de {limit} contratos activos alcanzado.",
    "error.database_missing": "Base de datos no encontrada.",
    "error.anti_cheat": "Verificación anti-trampa fallida: {reason}",
    "error.early_completion": "Completaste esta fase demasiado pronto. Confirma explícitamente que realmente la terminaste.",
    "error.dependency_missing": "Dependencia faltante: {dep}",
    "error.presence_detection": "No se pudo detectar la presencia del usuario.",

    # --- UI prompts ---
    "ui.int_minimum": "Ingresa un número entero (mínimo {minimum}).",
    "ui.value_gte": "El valor debe ser >= {minimum}.",
    "ui.value_lte": "El valor debe ser <= {maximum}.",
    "ui.multiline_hint": "{text} (línea vacía para terminar):",
    "ui.confirm_yes_no": "[s/N]",
    "ui.yes_values": "s,si,sí,y,yes",
    "ui.cancelled": "Operación cancelada.",

    # --- CLI ---
    "cli.usage": (
        "Fokiz — Contrato de Ulises\n\n"
        "Uso:\n"
        "  fokiz init                  Instalar Fokiz en este sistema\n"
        "  fokiz add                   Crear un nuevo contrato\n"
        "  fokiz status                Ver tareas en progreso\n"
        "  fokiz status --complete     Ver tareas completadas\n"
        "  fokiz status --banner       Ver estado con banner\n"
        "  fokiz board                 Ver tablero (En progreso / Completado)\n"
        "  fokiz lang [es|en]          Cambiar el idioma de la interfaz\n"
        "  fokiz done <task_id>        Completar la fase activa de una tarea\n"
        "  fokiz surrender <task_id>   Rendirse en una tarea\n"
        "  fokiz help                  Mostrar esta ayuda\n"
    ),
    "cli.usage_done": "Uso: fokiz done <task_id>",
    "cli.usage_surrender": "Uso: fokiz surrender <task_id>",
    "cli.invalid_task_id": "task_id inválido: {task_id}",
    "cli.unknown_cmd": "Comando desconocido: {cmd}",
    "cli.cancelled": "Cancelado.",

    # --- Installer ---
    "installer.title": "  Fokiz — Instalador",
    "installer.shell_integration_title": "Integración de shell (opcional pero recomendada)",
    "installer.shell_integration_hint": "Agrega el siguiente bloque a tu ~/.bashrc o ~/.zshrc:",
    "installer.shell_integration_effect": "Esto mostrará el banner de Fokiz al abrir un terminal.",
    "installer.complete": "✓ Instalación completa.",
    "installer.check_status": "  Comprueba el estado con: systemctl --user status fokiz.timer",
    "installer.service_path": "Instalando fokiz.service → {path}",
    "installer.timer_path": "Instalando fokiz.timer   → {path}",
    "installer.wrapper_ok": "✓ Wrapper configurado: {path}",
    "installer.path_hint": "  Asegúrate de que {path} esté en tu $PATH.",
    "installer.wrappers_installed": "Wrappers instalados en ~/.local/bin/",
    "installer.error": "  ⚠ Error: {err}",
    "installer.systemd_not_running": "⚠ systemd --user no parece estar en ejecución. Las unidades se instalaron pero no se activarán.",
    "installer.timer_failed": "⚠ No se pudo iniciar fokiz.timer. Revisa: journalctl --user -u fokiz.timer",
    "installer.partial": "⚠ Instalación parcial. Revisa los mensajes anteriores.",

    # --- Abandon (legacy compat) ---
    "abandon.aborted": "Abortado. El contrato sigue activo.",
    "abandon.success": "Contrato abandonado. Se ha registrado como fallo.",
    # --- Messages ---
    "msg.green.1": "Vas bien. No te duermas.",
    "msg.green.2": "Todavía hay tiempo. No lo desperdicies.",
    "msg.green.3": "El plazo sigue ahí, esperándote.",
    "msg.green.4": "Buen ritmo. Mantén el paso.",
    "msg.green.5": "El contrato recuerda lo que prometiste.",
    "msg.yellow.1": "El tiempo corre. ¿Estás avanzando?",
    "msg.yellow.2": "La mitad del camino ya pasó. ¿Dónde está tu progreso?",
    "msg.yellow.3": "¿Ya olvidaste lo que te comprometiste a hacer?",
    "msg.yellow.4": "El reloj no se detiene aunque tú sí.",
    "msg.yellow.5": "Zona amarilla. No es señal de ceder.",
    "msg.yellow.6": "Medio tiempo. Las excusas no cuentan como progreso.",
    "msg.orange.1": "El tiempo se acaba. Espabila.",
    "msg.orange.2": "¿Todavía en esto? El plazo no es opcional.",
    "msg.orange.3": "Zona naranja. Cada minuto desperdiciado es tuyo.",
    "msg.orange.4": "Urgencia real. No simulada. Muévete.",
    "msg.orange.5": "El contrato no va a renegociarse solo porque no avanzaste.",
    "msg.orange.6": "¿Sabías que la procrastinación también tiene plazos?",
    "msg.red.1": "ÚLTIMA OPORTUNIDAD. ¿Qué estás esperando?",
    "msg.red.2": "Ya casi no hay margen. Este es el momento.",
    "msg.red.3": "El deadline está ahí. Tú también. Haz algo.",
    "msg.red.4": "El contrato vence pronto. Sin excepciones.",
    "msg.red.5": "Zona roja. No hay tiempo para distracciones.",
    "msg.expired.1": "VENCIDO. El plazo pasó. Registra tu falla o ríndete.",
    "msg.expired.2": "El contrato ya expiró. El registro queda permanente.",
    "msg.expired.3": "Fase vencida. Fokiz sigue. El contrato sigue.",
    "msg.expired.4": "Ya era tarde antes. Ahora es peor.",
    "msg.expired.5": "Sin excusas. La fecha límite no espera.",
    "msg.wakeup.1": "¡Bienvenido de vuelta! El contrato no tomó un descanso.",
    "msg.wakeup.2": "Volviste. El plazo tampoco se fue.",
    "msg.wakeup.3": "Fin del descanso. El trabajo sigue esperando.",
    "msg.wakeup.4": "Reanudaste la sesión. El contrato también reanuda el cargo.",
    "msg.wakeup.5": "¿Descansado? El deadline no lo está.",
    "msg.surrender.1": "Rendición registrada. La historia queda intacta.",
    "msg.surrender.2": "El contrato permanece. La rendición también.",
    "msg.surrender.3": "Fokiz registra todo. Esta decisión también.",
    "msg.madrugada.1": "Es de madrugada, {nickname}. El contrato no duerme, tú tampoco deberías si estás atrasado.",
    "msg.madrugada.2": "Trabajando tarde, {nickname}. Aprovecha el silencio para avanzar.",
    "msg.madrugada.3": "La noche es larga, pero el deadline se acerca, {nickname}.",
    "urgency.low": "BAJA",
    "urgency.medium": "MEDIA",
    "urgency.high": "ALTA",
    "urgency.critical": "CRÍTICA",
}

# ---------------------------------------------------------------------------
# English strings
# ---------------------------------------------------------------------------

EN_STRINGS: dict[str, str] = {
    # --- Contract / add ---
    "contract.title_prompt": "Project title (5–80 characters)",
    "contract.objective_prompt": "Objective (10–200 characters)",
    "contract.days_prompt": "Total days for the project",
    "contract.phases_prompt": "Number of phases (1–8)",
    "contract.phase_section": "Phase {i} of {total_phases}",
    "contract.phase_title_prompt": "Phase {i} title",
    "contract.phase_instructions_prompt": "Phase {i} instructions",
    "contract.phase_days_prompt": "Days for phase {i} ({remaining_days} remaining for {rem_phases} phases)",
    "contract.phase_days_auto": "Phase {i} days: {ph_days} (auto remainder)",
    "contract.warning": "⚠ This contract is irreversible. Once confirmed, you cannot modify the deadline.",
    "contract.confirm_prompt": "\nConfirm this contract? There is no going back",
    "contract.cancelled": "Contract cancelled.",
    "contract.signed": "Contract signed in blood! Your focus begins now.",
    "contract.created": "Contract created. Task ID: #{task_id}",
    "contract.summary_title": "NEW ULYSSES CONTRACT",
    "contract.summary_header": "CONTRACT SUMMARY",
    "contract.field_title": "  Title     : {title}",
    "contract.field_objective": "  Objective : {objective}",
    "contract.field_days": "  Days      : {days}",
    "contract.field_phases": "  Phases    : {phases}",
    "contract.field_deadline": "  Deadline  : {deadline}",
    "contract.phase_row": "  Phase {phase_number}: {title} → {target_deadline} ({days}d)",
    "contract.slots_full": "Active slots full ({active_count}/{max_slots}). Complete or surrender first.",

    # --- Done ---
    "done.phase_section": "Phase #{phase_number} — {title}",
    "done.log_prompt": "Phase log — what did you do exactly?",
    "done.confirm_prompt": "Confirm phase #{phase_number} as COMPLETED?",
    "done.phase_completed": "Phase #{phase_number} completed.",
    "done.project_completed": "Project #{task_id} COMPLETED! The contract is now closed.",
    "done.next_phase": "Next phase: #{phase_number} — {title}",
    "done.tampered_block": "Cannot complete a phase with a tampered contract.",

    # --- Surrender ---
    "surrender.section": "SURRENDER — Task #{task_id}: {title}",
    "surrender.warning": "This will permanently mark the task as SURRENDERED. The historical record is kept.",
    "surrender.confirm_prompt": "Confirm surrender?",
    "surrender.reason_prompt": "Reason for surrender (minimum {min_chars} characters)",
    "surrender.reason_too_short": "The reason must be at least {min_chars} characters.",
    "surrender.marked": "Task #{task_id} marked as SURRENDERED.",
    "surrender.recorded": "The contract and surrender are permanently recorded.",
    "surrender.tampered_block": "Cannot surrender with a tampered contract. Surrendering does not erase evidence of tampering.",

    # --- Init ---
    "init.title": "FOKIZ INIT",
    "init.nickname_prompt": "Enter your name or nickname",
    "init.name_empty": "Name cannot be empty.",
    "init.timezone_prompt": "IANA timezone (e.g. America/Mexico_City)",
    "init.timezone_detected": "Detected timezone:",
    "init.timezone_use_detected": "Use this timezone?",
    "init.timezone_detection_failed": "Could not detect system timezone.",
    "init.xfce_notifications_updated": "XFCE notifications config updated (history enabled).",
    "init.directories_created": "Directories created.",
    "init.secret_generated": ".secret generated.",
    "init.secret_preserved": ".secret already exists — preserved.",
    "init.secret_integrity_broken": ".secret not found but data.db exists. Integrity compromised. Recover manually.",
    "init.db_initialized": "SQLite database initialized.",
    "init.config_saved": "Configuration saved (nick: {nickname}, tz: {tz}).",
    "init.complete": "Installation complete",
    "init.ready": "Fokiz is ready. Use 'fokiz add' to create your first contract.",
    "init.linux_required": "Fokiz requires Linux.",
    "init.python_required": "Python >= 3.8 required.",
    "init.systemd_daemon_reload": "Reloading systemd --user daemon...",
    "init.systemd_enabling": "Enabling fokiz.timer...",
    "init.systemd_starting": "Starting fokiz.timer...",
    "init.systemd_active": "✓ fokiz.timer active.",
    "init.systemd_units_installed": "systemd units installed.",
    "init.systemd_not_running": "systemd --user unavailable. Automatic notifications will not work.",
    "init.systemd_timer_failed": "⚠ Could not start fokiz.timer. Check: journalctl --user -u fokiz.timer",
    "init.systemd_not_activated": "⚠ systemd --user does not seem to be running. Units installed but won't be activated.",
    "init.partial": "⚠ Partial installation. Check the messages above.",
    "init.success": "Fokiz initialized successfully! Immutability structures created.",
    "init.already_initialized": "Fokiz is already initialized.",
    "init.hmac_verified": "HMAC verified successfully.",
    "init.hash_correction": "⚠ Performing internal hash correction...",

    # --- Status ---
    "status.title": "Diagnostics",
    "status.timezone": "Timezone",
    "status.no_active": "No active contract at this time.",
    "status.no_tasks": "No tasks registered.",
    "status.new_version": "\n\033[93m[i] New Fokiz version available ({latest_version}).\033[0m",
    "status.task_not_active": "Task #{task_id} is not active (status: {status}).",

    # --- Lang ---
    "lang.current": "Current language: {current_lang}",
    "lang.select_prompt": "Select language (es / en)",
    "lang.changed": "Language changed to: {lang_arg}",
    "lang.invalid": "Invalid language.",

    # --- Board ---
    "board.in_progress": "IN PROGRESS",
    "board.completed": "COMPLETED",
    "board.all_phases_done": "All phases completed",

    # --- Card labels ---
    "card.task": "Task",
    "card.status": "Status",
    "card.phase": "Phase",
    "card.progress": "Progress",
    "card.phases_completed": "phases completed",
    "card.zone": "Zone",
    "card.interval": "Interval",
    "card.remaining": "Remaining",
    "card.deadline": "Deadline",

    # --- Delta labels ---
    "delta.ahead": "AHEAD — Truce zone",
    "delta.on_track": "ON TRACK — Keep the pace",
    "delta.behind": "BEHIND — Active harassment",

    # --- Time ---
    "time.min": "min",
    "time.sec": "s",
    "time.expired": "EXPIRED",

    # --- Integrity ---
    "integrity.tampered_header": "⚠ INTEGRITY COMPROMISED — Task #{task_id}",
    "integrity.hmac_mismatch": "HMAC mismatch. The contract has been externally tampered.",
    "integrity.blocked": "Contract operations blocked until explicit recovery.",
    "integrity.key_missing": ".secret not found. Cannot verify contract integrity.",
    "integrity.recover": "Run 'fokiz init' to recover or reinitialize.",

    # --- Errors ---
    "error.not_initialized": "Fokiz is not initialized. Run 'fokiz init'.",
    "error.already_initialized": "Fokiz is already initialized.",
    "error.active_contract": "There is already an active contract.",
    "error.cooldown": "You cannot create a new contract during the cooldown period.",
    "error.database": "Database error.",
    "error.integrity": "Integrity Error: Fokiz database has been manipulated or corrupted.",
    "error.integrity_key_missing": "Integrity key missing. The .secret file does not exist.",
    "error.tampered": "Integrity compromised. The contract has been tampered.",
    "error.immutable": "Fokiz Error: Immutable contract.",
    "error.invalid_transition": "Invalid state transition: {f} → {t}",
    "error.task_not_found": "Task #{tid} not found.",
    "error.no_active_phase": "No active phase for task #{tid}.",
    "error.max_slots": "Active contract limit of {limit} reached.",
    "error.database_missing": "Database not found.",
    "error.anti_cheat": "Anti-cheat verification failed: {reason}",
    "error.early_completion": "You completed this phase too early. Confirm explicitly that you actually finished it.",
    "error.dependency_missing": "Missing dependency: {dep}",
    "error.presence_detection": "Could not detect user presence.",

    # --- UI prompts ---
    "ui.int_minimum": "Enter an integer (minimum {minimum}).",
    "ui.value_gte": "Value must be >= {minimum}.",
    "ui.value_lte": "Value must be <= {maximum}.",
    "ui.multiline_hint": "{text} (empty line to finish):",
    "ui.confirm_yes_no": "[y/N]",
    "ui.yes_values": "y,yes",
    "ui.cancelled": "Operation cancelled.",

    # --- CLI ---
    "cli.usage": (
        "Fokiz — Ulysses Pact\n\n"
        "Usage:\n"
        "  fokiz init                  Install Fokiz on this system\n"
        "  fokiz add                   Create a new contract\n"
        "  fokiz status                View in-progress tasks\n"
        "  fokiz status --complete     View completed tasks\n"
        "  fokiz status --banner       View status with banner\n"
        "  fokiz board                 View task board (In-progress / Completed)\n"
        "  fokiz lang [es|en]          Change interface language\n"
        "  fokiz done <task_id>        Complete the active phase of a task\n"
        "  fokiz surrender <task_id>   Surrender a task\n"
        "  fokiz help                  Show this help\n"
    ),
    "cli.usage_done": "Usage: fokiz done <task_id>",
    "cli.usage_surrender": "Usage: fokiz surrender <task_id>",
    "cli.invalid_task_id": "Invalid task_id: {task_id}",
    "cli.unknown_cmd": "Unknown command: {cmd}",
    "cli.cancelled": "Cancelled.",

    # --- Installer ---
    "installer.title": "  Fokiz — Installer",
    "installer.shell_integration_title": "Shell integration (optional but recommended)",
    "installer.shell_integration_hint": "Add the following block to your ~/.bashrc or ~/.zshrc:",
    "installer.shell_integration_effect": "This will show the Fokiz banner when opening a terminal.",
    "installer.complete": "✓ Installation complete.",
    "installer.check_status": "  Check status with: systemctl --user status fokiz.timer",
    "installer.service_path": "Installing fokiz.service → {path}",
    "installer.timer_path": "Installing fokiz.timer   → {path}",
    "installer.wrapper_ok": "✓ Wrapper configured: {path}",
    "installer.path_hint": "  Make sure that {path} is in your $PATH.",
    "installer.wrappers_installed": "Wrappers installed in ~/.local/bin/",
    "installer.error": "  ⚠ Error: {err}",
    "installer.systemd_not_running": "⚠ systemd --user does not seem to be running. Units installed but won't be activated.",
    "installer.timer_failed": "⚠ Could not start fokiz.timer. Check: journalctl --user -u fokiz.timer",
    "installer.partial": "⚠ Partial installation. Check the messages above.",

    # --- Abandon (legacy compat) ---
    "abandon.aborted": "Aborted. The contract remains active.",
    "abandon.success": "Contract abandoned. Registered as failure.",
    # --- Messages ---
    "msg.green.1": "You're doing well. Don't fall asleep.",
    "msg.green.2": "There's still time. Don't waste it.",
    "msg.green.3": "The deadline is still there, waiting for you.",
    "msg.green.4": "Good pace. Keep it up.",
    "msg.green.5": "The contract remembers what you promised.",
    "msg.yellow.1": "Time is ticking. Are you making progress?",
    "msg.yellow.2": "Half the time is gone. Where is your progress?",
    "msg.yellow.3": "Did you forget what you committed to?",
    "msg.yellow.4": "The clock doesn't stop even if you do.",
    "msg.yellow.5": "Yellow zone. Not a signal to yield.",
    "msg.yellow.6": "Halftime. Excuses don't count as progress.",
    "msg.orange.1": "Time is running out. Wake up.",
    "msg.orange.2": "Still on this? The deadline is not optional.",
    "msg.orange.3": "Orange zone. Every wasted minute is yours.",
    "msg.orange.4": "Real urgency. Not simulated. Move.",
    "msg.orange.5": "The contract won't renegotiate just because you didn't advance.",
    "msg.orange.6": "Did you know procrastination has deadlines too?",
    "msg.red.1": "LAST CHANCE. What are you waiting for?",
    "msg.red.2": "Almost no margin left. This is the moment.",
    "msg.red.3": "The deadline is there. You too. Do something.",
    "msg.red.4": "The contract expires soon. No exceptions.",
    "msg.red.5": "Red zone. No time for distractions.",
    "msg.expired.1": "EXPIRED. The time has passed. Register your failure or surrender.",
    "msg.expired.2": "The contract has expired. The record is permanent.",
    "msg.expired.3": "Expired phase. Fokiz continues. The contract continues.",
    "msg.expired.4": "It was late before. Now it's worse.",
    "msg.expired.5": "No excuses. The deadline waits for no one.",
    "msg.wakeup.1": "Welcome back! The contract didn't take a break.",
    "msg.wakeup.2": "You're back. The deadline hasn't left either.",
    "msg.wakeup.3": "End of the break. The work is still waiting.",
    "msg.wakeup.4": "Session resumed. The contract resumes charge as well.",
    "msg.wakeup.5": "Rested? The deadline isn't.",
    "msg.surrender.1": "Surrender registered. History remains intact.",
    "msg.surrender.2": "The contract remains. So does the surrender.",
    "msg.surrender.3": "Fokiz records everything. This decision too.",
    "msg.madrugada.1": "It's late at night, {nickname}. The contract doesn't sleep, and neither should you if you're behind.",
    "msg.madrugada.2": "Working late, {nickname}. Use the silence to make progress.",
    "msg.madrugada.3": "The night is long, but the deadline is getting closer, {nickname}.",
    "urgency.low": "LOW",
    "urgency.medium": "MEDIUM",
    "urgency.high": "HIGH",
    "urgency.critical": "CRITICAL",
}


# ---------------------------------------------------------------------------
# Translation function
# ---------------------------------------------------------------------------

def _(key: str, **kwargs: object) -> str:
    """
    Translate a dot-namespaced key to the current locale string.

    Falls back to English if the key is missing in the active locale.
    Returns the key itself if not found in any locale (never returns Spanish
    when locale is English).

    Args:
        key:    dot-namespaced stable English identifier.
        kwargs: format placeholders.

    Returns:
        Localized string.
    """
    if CURRENT_LANG == "en":
        text = EN_STRINGS.get(key, key)
    else:
        text = ES_STRINGS.get(key, EN_STRINGS.get(key, key))

    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
