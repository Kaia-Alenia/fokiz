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
from app.templates import (
    SERVICE_TEMPLATE,
    TIMER_TEMPLATE,
    FOKIZ_WRAPPER_TEMPLATE,
    MONITOR_WRAPPER_TEMPLATE,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"

PYTHON = shutil.which("python3") or sys.executable

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
        print(_("installer.error", err=result.stderr.strip()), file=sys.stderr)
    return result.returncode


def install_systemd() -> bool:
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)

    service_path = SYSTEMD_USER_DIR / "fokiz-monitor.service"
    timer_path = SYSTEMD_USER_DIR / "fokiz-monitor.timer"

    local_bin = Path.home() / ".local" / "bin"
    monitor_bin = local_bin / "fokiz-monitor"
    
    print(_("installer.service_path", path=service_path))
    service_content = SERVICE_TEMPLATE.format(
        monitor_path=str(monitor_bin),
        script_dir=str(SCRIPT_DIR)
    )
    service_path.write_text(service_content, encoding="utf-8")

    print(_("installer.timer_path", path=timer_path))
    timer_path.write_text(TIMER_TEMPLATE, encoding="utf-8")

    # Check if systemd --user is running
    if _run(["systemctl", "--user", "is-system-running", "--quiet"]) not in (0, 1):
        print(_("installer.systemd_not_running"))
        return False

    print(_("init.systemd_daemon_reload"))
    _run(["systemctl", "--user", "daemon-reload"])

    print(_("init.systemd_enabling"))
    _run(["systemctl", "--user", "enable", "fokiz-monitor.timer"])

    print(_("init.systemd_starting"))
    rc = _run(["systemctl", "--user", "start", "fokiz-monitor.timer"])

    if rc == 0:
        print(_("init.systemd_active"))
    else:
        print(_("installer.timer_failed"))
        return False
    return True


def print_shell_hook_instructions() -> None:
    print()
    print("─" * 60)
    print(_("installer.shell_integration_title"))
    print("─" * 60)
    print(_("installer.shell_integration_hint"))
    print()
    print(HOOK_BLOCK)
    print("─" * 60)
    print(_("installer.shell_integration_effect"))


def install_cli_entrypoint() -> None:
    """Create a fokiz wrapper and fokiz-monitor wrapper in ~/.local/bin if not already present."""
    local_bin = Path.home() / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)

    # 1. fokiz CLI wrapper
    script = local_bin / "fokiz"
    content = FOKIZ_WRAPPER_TEMPLATE.format(
        app_dir=str(SCRIPT_DIR),
        script_dir=str(SCRIPT_DIR),
        python_exec=PYTHON
    )
    script.write_text(content, encoding="utf-8")
    script.chmod(0o755)
    print(_("installer.wrapper_ok", path=script))
    
    # 2. fokiz-monitor wrapper
    monitor_script = local_bin / "fokiz-monitor"
    monitor_py = SCRIPT_DIR / "src" / "monitor.py"
    monitor_content = MONITOR_WRAPPER_TEMPLATE.format(
        app_dir=str(SCRIPT_DIR),
        script_dir=str(SCRIPT_DIR),
        python_exec=PYTHON,
        monitor_py_path=str(monitor_py)
    )
    monitor_script.write_text(monitor_content, encoding="utf-8")
    monitor_script.chmod(0o755)
    print(_("installer.wrapper_ok", path=monitor_script))

    if not script.exists():  # just in case
        print(_("installer.path_hint", path=local_bin))


def main() -> int:
    print("═" * 60)
    print(_("installer.title"))
    print("═" * 60)

    ok = install_systemd()
    install_cli_entrypoint()
    print_shell_hook_instructions()

    if ok:
        print()
        print(_("installer.complete"))
        print(_("installer.check_status"))
    else:
        print()
        print(_("installer.partial"))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
