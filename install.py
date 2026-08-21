"""
install.py — Fokiz installer for systemd --user timer and shell hooks.
Copyright (C) Alenia Studios — GNU GPL v3

Run once to register the episodic monitor:
    python3 install.py

This script:
1. Installs fokiz.timer and fokiz.service in ~/.config/systemd/user/
2. Enables and starts fokiz.timer
3. Prints shell hook instructions for .bashrc / .zshrc
"""

import sys
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent

import sys
from pathlib import Path
SCRIPT_DIR_TMP = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR_TMP / 'src'))
from app.i18n import _  # type: ignore

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"

PYTHON = shutil.which("python3") or sys.executable
MONITOR_PATH = SCRIPT_DIR / "src" / "monitor.py"

# ---------------------------------------------------------------------------
# Unit templates
# ---------------------------------------------------------------------------

SERVICE_UNIT = dedent(f"""\
    [Unit]
    Description=Fokiz — Monitor episódico del Contrato de Ulises
    Documentation=https://github.com/aleniastudios/fokiz
    After=network.target

    [Service]
    Type=oneshot
    ExecStart={PYTHON} {MONITOR_PATH}
    WorkingDirectory={SCRIPT_DIR}
    Environment=PYTHONUNBUFFERED=1
    StandardOutput=journal
    StandardError=journal
""")

TIMER_UNIT = dedent("""\
    [Unit]
    Description=Fokiz — Timer episódico (60s)
    After=graphical-session.target

    [Timer]
    OnBootSec=60s
    OnUnitActiveSec=60s
    Persistent=true
    AccuracySec=10s

    [Install]
    WantedBy=timers.target
""")

# ---------------------------------------------------------------------------
# Shell hook
# ---------------------------------------------------------------------------

HOOK_COMMENT = "# Fokiz shell hook"
HOOK_BLOCK = dedent("""\
    # Fokiz shell hook
    fokiz_check() {
        command -v fokiz >/dev/null 2>&1 && fokiz status 2>/dev/null
    }
    fokiz_check
""")


def _run(cmd: list[str]) -> int:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(_(f"  ⚠ Error: {result.stderr.strip()}"), file=sys.stderr)
    return result.returncode


def install_systemd() -> bool:
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)

    service_path = SYSTEMD_USER_DIR / "fokiz.service"
    timer_path = SYSTEMD_USER_DIR / "fokiz.timer"

    print(_("Instalando fokiz.service → {path}", path=service_path))
    service_path.write_text(SERVICE_UNIT, encoding="utf-8")

    print(_("Instalando fokiz.timer   → {path}", path=timer_path))
    timer_path.write_text(TIMER_UNIT, encoding="utf-8")

    # Check if systemd --user is running
    if _run(["systemctl", "--user", "is-system-running", "--quiet"]) not in (0, 1):
        print(_("⚠ systemd --user no parece estar en ejecución. Las unidades se instalaron pero no se activarán."))
        return False

    print(_("Recargando daemon de systemd --user…"))
    _run(["systemctl", "--user", "daemon-reload"])

    print(_("Habilitando fokiz.timer…"))
    _run(["systemctl", "--user", "enable", "fokiz.timer"])

    print(_("Iniciando fokiz.timer…"))
    rc = _run(["systemctl", "--user", "start", "fokiz.timer"])

    if rc == 0:
        print(_("✓ fokiz.timer activo."))
    else:
        print(_("⚠ No se pudo iniciar fokiz.timer. Revisa: journalctl --user -u fokiz.timer"))
        return False
    return True


def print_shell_hook_instructions() -> None:
    print()
    print("─" * 60)
    print(_("Integración de shell (opcional pero recomendada)"))
    print("─" * 60)
    print(_("Agrega el siguiente bloque a tu ~/.bashrc o ~/.zshrc:"))
    print()
    print(HOOK_BLOCK)
    print("─" * 60)
    print(_("Esto mostrará el banner de Fokiz al abrir un terminal."))


def install_cli_entrypoint() -> None:
    """Create a fokiz wrapper in ~/.local/bin if not already present."""
    local_bin = Path.home() / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)

    script = local_bin / "fokiz"
    content = dedent(f"""\
        #!/usr/bin/env bash
        export PYTHONPATH="{SCRIPT_DIR}/src:$PYTHONPATH"
        exec {PYTHON} -m app.cli "$@"
    """)

    script.write_text(content, encoding="utf-8")
    script.chmod(0o755)
    print(_("✓ Wrapper configurado: {path}", path=script))
    if not script.exists(): # just in case
        print(_("  Asegúrate de que {path} esté en tu $PATH.", path=local_bin))


def main() -> int:
    print("═" * 60)
    print(_("  Fokiz — Instalador"))
    print("═" * 60)

    ok = install_systemd()
    install_cli_entrypoint()
    print_shell_hook_instructions()

    if ok:
        print()
        print(_("✓ Instalación completa."))
        print(_("  Comprueba el estado con: systemctl --user status fokiz.timer"))
    else:
        print()
        print(_("⚠ Instalación parcial. Revisa los mensajes anteriores."))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
