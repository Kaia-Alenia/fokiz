import os
import locale

def get_system_locale() -> str:
    """Detect the system language."""
    # Check LANG environment variable first
    lang = os.environ.get("LANG")
    if lang:
        if lang.startswith("es"):
            return "es"
        elif lang.startswith("en"):
            return "en"
    
    # Fallback to python's locale module
    try:
        loc, _ = locale.getdefaultlocale()
        if loc:
            if loc.startswith("es"):
                return "es"
            elif loc.startswith("en"):
                return "en"
    except Exception:
        pass
    
    # Default to Spanish if undetermined
    return "es"

CURRENT_LANG = get_system_locale()

# Translation dictionaries
ES_STRINGS = {
    # Contract / Add
    "abort_contract_msg": "Operación cancelada. El contrato NO se ha firmado.",
    "contract_signed": "¡Contrato firmado en sangre! Tu enfoque comienza ahora.",
    "contract_active": "Ya tienes un contrato activo.",
    "title_prompt": "Título del proyecto (5–80 caracteres)",
    "duration_prompt": "Duración en minutos (10-180)",
    "new_contract_header": "NUEVO CONTRATO DE ULISES",
    "contract_warning": "⚠ Este contrato es irreversible. Una vez confirmado, no podrás modificar el plazo.",
    "accept_prompt": "¿Aceptas las condiciones y firmas el contrato?",

    # Status / UI
    "status_active": "En progreso",
    "status_completed": "Completado",
    "status_failed": "Fallido (Procrastinación)",
    "status_cooldown": "En Descanso",
    "status_none": "Sin Contrato",
    
    "ui_no_active": "No hay ningún contrato activo en este momento.",
    "ui_active_title": "CONTRATO ACTIVO",
    "ui_cooldown": "En periodo de descanso. Disponible de nuevo en",
    "ui_time_left": "Tiempo restante",
    "ui_progress": "Progreso",
    
    # Abandon
    "abandon_success": "Contrato abandonado. Se ha registrado como fallo.",
    "abandon_confirm": "⚠ Estás a punto de romper el contrato. Esto quedará registrado permanentemente como un fallo. ¿Estás seguro?",
    "abandon_aborted": "Abortado. El contrato sigue activo.",
    
    # Errors
    "err_immutable": "Fokiz Error: El contrato es inmutable.",
    "err_not_initialized": "Fokiz no está inicializado. Ejecuta 'fokiz init'.",
    "err_already_initialized": "Fokiz ya está inicializado.",
    "err_active_contract": "Ya existe un contrato activo.",
    "err_cooldown": "No puedes crear un contrato nuevo durante el periodo de descanso.",
    "err_database": "Error en la base de datos.",
    "err_integrity": "Error de Integridad: La base de datos de Fokiz ha sido manipulada o corrompida.",
    
    # Init
    "init_success": "¡Fokiz inicializado correctamente! Estructuras de inmutabilidad creadas.",
    
    # General
    "time_min": "min",
    "time_sec": "s",
    
    # CLI
    "cli_usage": "Fokiz — Contrato de Ulises\n\nUso:\n  fokiz init                  Instalar Fokiz en este sistema\n  fokiz add                   Crear un nuevo contrato\n  fokiz status                Ver tareas en progreso\n  fokiz status --complete     Ver tareas completadas\n  fokiz status --banner       Ver estado con banner\n  fokiz board                 Ver tablero (En progreso / Completado)\n  fokiz done <task_id>        Completar la fase activa de una tarea\n  fokiz surrender <task_id>   Rendirse en una tarea\n  fokiz help                  Mostrar esta ayuda\n",
    "cli_usage_done": "Uso: fokiz done <task_id>",
    "cli_usage_surrender": "Uso: fokiz surrender <task_id>",
    "cli_invalid_task_id": "task_id inválido: {task_id}",
    "cli_unknown_cmd": "Comando desconocido: {cmd}",
    "cli_cancelled": "Operación cancelada por el usuario.",
}

EN_STRINGS = {
    # Contract / Add
    "abort_contract_msg": "Operation cancelled. The contract was NOT signed.",
    "contract_signed": "Contract signed in blood! Your focus begins now.",
    "contract_active": "You already have an active contract.",
    "title_prompt": "Project title (5-80 characters)",
    "duration_prompt": "Duration in minutes (10-180)",
    "new_contract_header": "NEW ULYSSES PACT",
    "contract_warning": "⚠ This contract is irreversible. Once confirmed, you cannot modify the duration.",
    "accept_prompt": "Do you accept the conditions and sign the contract?",

    # Status / UI
    "status_active": "In progress",
    "status_completed": "Completed",
    "status_failed": "Failed (Procrastination)",
    "status_cooldown": "In Cooldown",
    "status_none": "No Contract",
    
    "ui_no_active": "There is no active contract at the moment.",
    "ui_active_title": "ACTIVE CONTRACT",
    "ui_cooldown": "In cooldown period. Available again in",
    "ui_time_left": "Time remaining",
    "ui_progress": "Progress",
    
    # Abandon
    "abandon_success": "Contract abandoned. It has been recorded as a failure.",
    "abandon_confirm": "⚠ You are about to break the contract. This will be permanently recorded as a failure. Are you sure?",
    "abandon_aborted": "Aborted. The contract remains active.",
    
    # Errors
    "err_immutable": "Fokiz Error: Immutable contract.",
    "err_not_initialized": "Fokiz is not initialized. Run 'fokiz init'.",
    "err_already_initialized": "Fokiz is already initialized.",
    "err_active_contract": "There is already an active contract.",
    "err_cooldown": "You cannot create a new contract during the cooldown period.",
    "err_database": "Database error.",
    "err_integrity": "Integrity Error: Fokiz database has been manipulated or corrupted.",
    
    # Init
    "init_success": "Fokiz initialized successfully! Immutability structures created.",
    
    # General
    "time_min": "min",
    "time_sec": "s",
    
    # CLI
    "cli_usage": "Fokiz — Ulysses Pact\n\nUsage:\n  fokiz init                  Install Fokiz on this system\n  fokiz add                   Create a new contract\n  fokiz status                View in-progress tasks\n  fokiz status --complete     View completed tasks\n  fokiz status --banner       View status with banner\n  fokiz board                 View task board (In-progress / Completed)\n  fokiz done <task_id>        Complete the active phase of a task\n  fokiz surrender <task_id>   Surrender a task\n  fokiz help                  Show this help\n",
    "cli_usage_done": "Usage: fokiz done <task_id>",
    "cli_usage_surrender": "Usage: fokiz surrender <task_id>",
    "cli_invalid_task_id": "Invalid task_id: {task_id}",
    "cli_unknown_cmd": "Unknown command: {cmd}",
    "cli_cancelled": "Cancelled.",
    '  Comprueba el estado con: systemctl --user status fokiz.timer': '  Check status with: systemctl --user status fokiz.timer',
    '.secret generado.': '.secret generated.',
    '.secret no encontrado pero data.db existe. "\\n            "Integridad comprometida. Recupera manualmente.': '.secret not found but data.db exists. "\\n            "Integrity compromised. Recover manually.',
    '.secret ya existe — preservado.': '.secret already exists — preserved.',
    'Base de datos SQLite inicializada.': 'SQLite database initialized.',
    'Bitácora de la fase — ¿qué hiciste exactamente?': 'Phase log — what did you do exactly?',
    'Configuración de notificaciones de XFCE actualizada (historial activado).': 'XFCE notifications config updated (history enabled).',
    'Contrato cancelado.': 'Contract cancelled.',
    'Diagnóstico': 'Diagnostics',
    'Directorios creados.': 'Directories created.',
    'Días totales para el proyecto': 'Total days for the project',
    'El contrato y la rendición quedan registrados permanentemente.': 'The contract and surrender are permanently recorded.',
    'El nombre no puede estar vacío.': 'Name cannot be empty.',
    'Este contrato es irreversible. Una vez confirmado, no podrás modificar el plazo.': 'This contract is irreversible. Once confirmed, you cannot modify the deadline.',
    'Esto marcará la tarea como SURRENDERED permanentemente. "\\n        "El registro histórico se conserva.': 'This will permanently mark the task as SURRENDERED. "\\n        "The historical record is kept.',
    'FOKIZ INIT': 'FOKIZ INIT',
    "Fokiz está listo. Usa 'fokiz add' para crear tu primer contrato.": "Fokiz is ready. Use 'fokiz add' to create your first contract.",
    "Fokiz no está inicializado. Ejecuta 'fokiz init'.": "Fokiz is not initialized. Run 'fokiz init'.",
    'Fokiz requiere Linux.': 'Fokiz requires Linux.',
    'HMAC verificado correctamente.': 'HMAC verified successfully.',
    'Habilitando fokiz.timer…': 'Enabling fokiz.timer...',
    'Ingresa tu nombre o apodo': 'Enter your name or nickname',
    'Iniciando fokiz.timer…': 'Starting fokiz.timer...',
    'Instalación completa': 'Installation complete',
    'NUEVO CONTRATO DE ULISES': 'NEW ULYSSES CONTRACT',
    'No hay tareas registradas.': 'No tasks registered.',
    'No se pudo activar el timer systemd. Actívalo manualmente.': 'Could not activate systemd timer. Activate it manually.',
    'No se puede completar una fase con contrato manipulado.': 'Cannot complete a phase with a tampered contract.',
    'No se puede rendir con contrato manipulado. "\\n            "La rendición no borra la evidencia de manipulación.': 'Cannot surrender with a tampered contract. "\\n            "Surrendering does not erase evidence of tampering.',
    'Número de fases (1–8)': 'Number of phases (1-8)',
    'Objetivo (10–200 caracteres)': 'Objective (10-200 characters)',
    'Operación cancelada.': 'Operation cancelled.',
    'RESUMEN DEL CONTRATO': 'CONTRACT SUMMARY',
    'Recargando daemon de systemd --user…': 'Reloading systemd --user daemon...',
    'Se requiere Python >= 3.8.': 'Python >= 3.8 required.',
    'Timer systemd activado.': 'systemd timer activated.',
    'Título del proyecto (5–80 caracteres)': 'Project title (5-80 characters)',
    'Unidades systemd instaladas.': 'systemd units installed.',
    'Wrappers instalados en ~/.local/bin/': 'Wrappers installed in ~/.local/bin/',
    'Zona horaria': 'Timezone',
    '\\n¿Confirmas este contrato? No hay vuelta atrás': '\\nConfirm this contract? There is no going back',
    'systemd --user no disponible. Las notificaciones automáticas no funcionarán.': 'systemd --user unavailable. Automatic notifications will not work.',
    '¿Confirmas la rendición?': 'Confirm surrender?',
    '⚠ Instalación parcial. Revisa los mensajes anteriores.': '⚠ Partial installation. Check the messages above.',
    '⚠ No se pudo iniciar fokiz.timer. Revisa: journalctl --user -u fokiz.timer': '⚠ Could not start fokiz.timer. Check: journalctl --user -u fokiz.timer',
    '⚠ Realizando corrección interna de hash...': '⚠ Performing internal hash correction...',
    '⚠ systemd --user no parece estar en ejecución. Las unidades se instalaron pero no se activarán.': "⚠ systemd --user does not seem to be running. Units installed but won't be activated.",
    '✓ fokiz.timer activo.': '✓ fokiz.timer active.',
    
    # Installer additions
    "Integración de shell (opcional pero recomendada)": "Shell integration (optional but recommended)",
    "Agrega el siguiente bloque a tu ~/.bashrc o ~/.zshrc:": "Add the following block to your ~/.bashrc or ~/.zshrc:",
    "Esto mostrará el banner de Fokiz al abrir un terminal.": "This will show the Fokiz banner when opening a terminal.",
    "  Fokiz — Instalador": "  Fokiz — Installer",
    "✓ Instalación completa.": "✓ Installation complete.",
    "Instalando fokiz.service → {path}": "Installing fokiz.service → {path}",
    "Instalando fokiz.timer   → {path}": "Installing fokiz.timer   → {path}",
    "✓ Wrapper configurado: {path}": "✓ Wrapper configured: {path}",
    "  Asegúrate de que {path} esté en tu $PATH.": "  Make sure that {path} is in your $PATH.",
}

def _(key: str, **kwargs) -> str:
    """
    Translate a string based on the current locale.
    Falls back to Spanish if key is not found in English,
    and returns the key itself if not found in any dictionary.
    """
    if CURRENT_LANG == "en":
        text = EN_STRINGS.get(key, ES_STRINGS.get(key, key))
    else:
        text = ES_STRINGS.get(key, key)
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
