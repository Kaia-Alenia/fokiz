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

CURRENT_LANG: str = "en"  # safe default


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
    "contract.field_created": "  Creado    : {created_at}",
    "contract.field_deadline": "  Deadline  : {deadline}",
    "contract.phase_row": "  Fase {phase_number}: {title} → {target_deadline} ({days}d)",
    "contract.val_title_len": "El título debe tener entre {min_len} y {max_len} caracteres (tiene {actual}).",
    "contract.val_obj_len": "El objetivo debe tener entre {min_len} y {max_len} caracteres (tiene {actual}).",
    "contract.val_days_min": "Los días totales deben ser >= {min_days}.",
    "contract.val_phases_range": "El número de fases debe estar entre {min_phases} y {max_phases}.",
    "contract.val_phase_days_min": "Los días de la fase {phase} deben ser > 0.",
    "contract.val_phase_days_sum": "La suma de los días de las fases ({sum_days}) debe ser igual a los días totales ({total}).",
    "contract.val_tz_unknown": "Zona horaria '{tz}' no reconocida. Usa un identificador IANA válido como 'America/Mexico_City', 'Europe/Madrid', 'Asia/Tokyo', etc.",
    "contract.val_phases_expected": "Se esperaban {expected} fases, se recibieron {actual}.",
    "contract.val_phase_title_empty": "El título de la fase {i} no puede estar vacío.",
    "contract.val_phase_instructions_empty": "Las instrucciones de la fase {i} no pueden estar vacías.",
    "contract.slots_full": "Slots activos llenos ({active_count}/{max_slots}). Completa o ríndete primero.",
    "contract.hmac_verification_failed": "Verificación HMAC inmediata falló: {status}",

    # --- Done ---
    "done.phase_section": "Fase #{phase_number} — {title}",
    "done.field_instructions": "  Instrucciones: {instructions}",
    "done.field_deadline": "  Deadline     : {deadline}",
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
    "init.name_empty": "El nickname no puede estar vacío.",
    "init.timezone_prompt": "Fallo al detectar IANA timezone automáticamente.\nIngresa un timezone válido (ej. America/Mexico_City): ",
    "init.timezone_invalid": "'{tz}' no es un identificador IANA válido. Ejemplos: America/Mexico_City, Europe/Madrid, Asia/Tokyo.",
    "init.timezone_detected": "Timezone detectado: {tz}",
    "init.timezone_use_detected": "¿Usar este timezone?",
    "init.timezone_detection_failed": "No se pudo detectar el timezone automáticamente.",
    "init.xfce_notifications_updated": "Configuración de notificaciones XFCE actualizada para modo estricto.",
    "init.directories_created": "Directorios base creados.",
    "init.secret_generated": "Nuevo secreto maestro generado.",
    "init.secret_preserved": "Secreto maestro detectado y preservado.",
    "init.secret_integrity_broken": "Fallo de integridad: no se pudo leer o escribir el archivo secreto (verificar permisos).",
    "init.db_initialized": "Base de datos SQLite inicializada.",
    "init.config_saved": "Configuración guardada (Nickname: {nickname} | TZ: {tz}).",
    "init.complete": "Instalación Completada",
    "init.ready": "Fokiz está listo. Usa 'fokiz add' para crear un nuevo contrato.",
    "init.linux_required": "Fokiz actualmente sólo soporta Linux.",
    "init.python_required": "Fokiz requiere Python 3.10 o superior.",
    "init.systemd_daemon_reload": "Recargando daemon de systemd --user…",
    "init.systemd_enabling": "Habilitando fokiz.timer…",
    "init.systemd_starting": "Iniciando fokiz.timer…",
    "init.systemd_active": "✓ fokiz.timer activo.",
    "init.systemd_units_installed": "Unidades de Systemd (service, timer) generadas.",
    "init.systemd_not_running": "systemd daemon no está corriendo. El demonio de Fokiz no podrá autoiniciarse.",
    "init.systemd_timer_failed": "Fallo al activar el timer systemd. El daemon no se iniciará automáticamente.",
    "init.systemd_not_activated": "⚠ systemd --user no parece estar en ejecución. Las unidades se instalaron pero no se activarán.",
    "init.partial": "⚠ Instalación parcial. Revisa los mensajes anteriores.",
    "init.success": "¡Fokiz inicializado correctamente! Estructuras de inmutabilidad creadas.",
    "init.already_initialized": "Fokiz ya está inicializado.",
    "init.hmac_verified": "Firma de contrato verificada y preservada.",
    "init.hash_correction": "⚠ Realizando corrección interna de hash...",
    "init.hook_installed": "Hook inyectado en {file}.",
    "init.hook_already_present": "Hook de Fokiz ya detectado en {file}.",
    "init.systemd_timer_activated": "Systemd timer activado (fokiz-monitor.timer).",
    "init.diag_not_found": "{name} — no encontrado",
    "init.dep_notifications": "notificaciones de escritorio",
    "init.dep_presence": "detección de presencia (opcional)",
    "init.dep_found": "{dep} — {desc}",
    "init.dep_missing": "{dep} no encontrado — {desc}",

    # --- Status ---
    "status.title": "Diagnóstico",
    "status.timezone": "Zona horaria",
    "status.local_time": "  Hora local : {time}",
    "status.timezone_field": "  Zona horaria: {tz}",
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
    "error.immutable_deletion_task": "Prohibido borrar tareas. Termina o ríndete.",
    "error.immutable_deletion_phase": "Prohibido borrar fases.",
    "error.immutable_task_field": "La tarea contractual es inmutable.",
    "error.immutable_phase_field": "La fase contractual es inmutable.",
    "error.invalid_task_transition": "Transición de estado de tarea inválida.",
    "error.invalid_phase_transition": "Transición de estado de fase inválida.",
    "error.invalid_transition": "Transición de estado inválida: {f} → {t}",
    "error.task_not_found": "Tarea #{tid} no encontrada.",
    "error.no_active_phase": "No hay fase activa para la tarea #{tid}.",
    "error.max_slots": "Límite de {limit} contratos activos alcanzado.",
    "error.database_missing": "Base de datos no encontrada.",
    "error.anti_cheat": "Verificación anti-trampa fallida: {reason}",
    "error.early_completion": "Completaste esta fase demasiado pronto. Confirma explícitamente que realmente la terminaste.",
    "error.dependency_missing": "Dependencia faltante: {dep}",
    "error.presence_detection": "No se pudo detectar la presencia del usuario.",

    # --- Anti-cheat ---
    "anti_cheat.garbage": "Contenido de relleno detectado.",
    "anti_cheat.keyboard_pattern": "Patrón de teclado detectado.",
    "anti_cheat.low_entropy": "Entropía demasiado baja ({entropy:.2f} bits). El texto parece repetitivo o sin información.",
    "anti_cheat.too_short": "Bitácora muy corta ({length} caracteres). Mínimo requerido: {min_chars}.",
    "anti_cheat.no_overlap": "La bitácora no parece relacionada con las instrucciones de la fase. Incluye al menos un término del trabajo realizado.",
    "anti_cheat.early_confirm_phrase": "confirmo que termine antes de tiempo",

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
    "contract.field_created": "  Created   : {created_at}",
    "contract.field_deadline": "  Deadline  : {deadline}",
    "contract.phase_row": "  Phase {phase_number}: {title} → {target_deadline} ({days}d)",
    "contract.val_title_len": "Title must be between {min_len} and {max_len} characters (got {actual}).",
    "contract.val_obj_len": "Objective must be between {min_len} and {max_len} characters (got {actual}).",
    "contract.val_days_min": "Total days must be >= {min_days}.",
    "contract.val_phases_range": "Phase count must be between {min_phases} and {max_phases}.",
    "contract.val_phase_days_min": "Phase {phase} days must be > 0.",
    "contract.val_phase_days_sum": "Sum of phase days ({sum_days}) must equal total_days ({total}).",
    "contract.val_tz_unknown": "Timezone '{tz}' not recognized. Use a valid IANA identifier like 'America/Mexico_City', 'Europe/Madrid', 'Asia/Tokyo', etc.",
    "contract.val_phases_expected": "Expected {expected} phases, got {actual}.",
    "contract.val_phase_title_empty": "Phase {i} title cannot be empty.",
    "contract.val_phase_instructions_empty": "Phase {i} instructions cannot be empty.",
    "contract.slots_full": "Active slots full ({active_count}/{max_slots}). Complete or surrender first.",
    "contract.hmac_verification_failed": "Immediate HMAC verification failed: {status}",

    # --- Done ---
    "done.phase_section": "Phase #{phase_number} — {title}",
    "done.field_instructions": "  Instructions : {instructions}",
    "done.field_deadline": "  Deadline     : {deadline}",
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
    "init.name_empty": "Nickname cannot be empty.",
    "init.timezone_prompt": "Failed to auto-detect IANA timezone.\nEnter a valid timezone (e.g. America/New_York): ",
    "init.timezone_invalid": "'{tz}' is not a valid IANA identifier. Examples: America/New_York, Europe/London, Asia/Tokyo.",
    "init.timezone_detected": "Detected timezone: {tz}",
    "init.timezone_use_detected": "Use this timezone?",
    "init.timezone_detection_failed": "Could not auto-detect timezone.",
    "init.xfce_notifications_updated": "XFCE notification configuration updated for strict mode.",
    "init.directories_created": "Base directories created.",
    "init.secret_generated": "New master secret generated.",
    "init.secret_preserved": "Master secret detected and preserved.",
    "init.secret_integrity_broken": "Integrity failure: could not read or write secret file (check permissions).",
    "init.db_initialized": "SQLite database initialized.",
    "init.config_saved": "Configuration saved (Nickname: {nickname} | TZ: {tz}).",
    "init.complete": "Installation Complete",
    "init.ready": "Fokiz is ready. Use 'fokiz add' to create a new contract.",
    "init.linux_required": "Fokiz currently only supports Linux.",
    "init.python_required": "Fokiz requires Python 3.10 or higher.",
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
    "init.hook_installed": "Hook installed in {file}",
    "init.hook_already_present": "Hook already present in {file}",
    "init.systemd_timer_activated": "systemd timer activated.",
    "init.diag_not_found": "{name} — not found",

    # --- Status ---
    "status.title": "Diagnostics",
    "status.timezone": "Timezone",
    "status.local_time": "  Local time : {time}",
    "status.timezone_field": "  Timezone   : {tz}",
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
    "error.immutable_deletion_task": "Task deletion is forbidden. Complete it or surrender.",
    "error.immutable_deletion_phase": "Phase deletion is forbidden.",
    "error.immutable_task_field": "The task contract is immutable.",
    "error.immutable_phase_field": "The phase contract is immutable.",
    "error.invalid_task_transition": "Invalid task state transition.",
    "error.invalid_phase_transition": "Invalid phase state transition.",
    "error.invalid_transition": "Invalid state transition: {f} → {t}",
    "error.task_not_found": "Task #{tid} not found.",
    "error.no_active_phase": "No active phase for task #{tid}.",
    "error.max_slots": "Active contract limit of {limit} reached.",
    "error.database_missing": "Database not found.",
    "error.anti_cheat": "Anti-cheat verification failed: {reason}",
    "error.early_completion": "You completed this phase too early. Confirm explicitly that you actually finished it.",
    "error.dependency_missing": "Missing dependency: {dep}",
    "error.presence_detection": "Could not detect user presence.",

    # --- Anti-cheat ---
    "anti_cheat.garbage": "Garbage content detected.",
    "anti_cheat.keyboard_pattern": "Keyboard pattern detected.",
    "anti_cheat.low_entropy": "Entropy too low ({entropy:.2f} bits). The text seems repetitive or lacks information.",
    "anti_cheat.too_short": "Log too short ({length} characters). Minimum required: {min_chars}.",
    "anti_cheat.no_overlap": "The log doesn't seem related to the phase instructions. Include at least one term from the completed work.",
    "anti_cheat.early_confirm_phrase": "i confirm i finished early",

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
