"""
from .i18n import _
ui.py — ANSI terminal rendering for Fokiz.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- No DB access, no math, no subprocess.
- Pure terminal rendering.
"""

import sys
from datetime import datetime, timezone
from typing import Any

from .constants import BANNER_WIDTH, PROGRESS_BAR_WIDTH
from .math_engine import Zone, DeltaStatus


# ---------------------------------------------------------------------------
# ANSI color codes
# ---------------------------------------------------------------------------

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    GREEN   = "\033[92m"
    ORANGE  = "\033[33m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"


def _zone_color(zone: Zone) -> str:
    return {
        Zone.GREEN:   C.GREEN,
        Zone.YELLOW:  C.YELLOW,
        Zone.ORANGE:  C.ORANGE,
        Zone.RED:     C.RED,
        Zone.EXPIRED: C.RED,
    }[zone]


def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(code: str) -> str:
    return code if _supports_color() else ""


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------

def render_progress_bar(ratio: float, width: int = PROGRESS_BAR_WIDTH, zone: Zone = Zone.GREEN) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = int(ratio * width)
    empty = width - filled
    color = _c(_zone_color(zone))
    reset = _c(C.RESET)
    bar = f"[{color}{'█' * filled}{reset}{'░' * empty}]"
    return f"{bar} {ratio * 100:.1f}%"


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def render_banner(size: str = "LARGE") -> str:
    if size == "NONE":
        return ""
        
    c_orange = _c(C.ORANGE)
    c_dark = _c(C.GRAY)
    reset = _c(C.RESET)
    bold = _c(C.BOLD)
    cyan = _c(C.CYAN)
    
    try:
        import os
        art_path = os.path.join(os.path.dirname(__file__), "fokiz_art.txt")
        with open(art_path, "r", encoding="utf-8") as f:
            logo_large = f.read()
    except Exception:
        logo_large = ""
    
    logo_small = """
      ⢀⣴⣾⣿⣿⣶⣶⣿⣿⣷⣦⡀
      ⠘⢿⣿⡿⢋⣼⣧⡙⢿⣿⡿⠃
         ⠈⠉⠁⠛⠛⠈⠉⠁
"""

    logo = logo_large if size == "LARGE" else logo_small

    top = "┌" + "─" * (BANNER_WIDTH - 2) + "┐"
    mid = f"│{bold}{cyan}{'FOKIZ':^{BANNER_WIDTH - 2}}{reset}│"
    bot = "└" + "─" * (BANNER_WIDTH - 2) + "┘"
    return f"{logo.strip('\n')}\n{top}\n{mid}\n{bot}"


# ---------------------------------------------------------------------------
# Status panel
# ---------------------------------------------------------------------------

def render_task_card(
    task_id: int,
    title: str,
    status: str,
    phase_label: str,
    tau: float,
    delta: float,
    delta_status: DeltaStatus,
    iu: float,
    zone: Zone,
    i_spam_min: float,
    phases_done: int,
    total_phases: int,
    deadline: str,
    time_remaining: str,
) -> str:
    color = _c(_zone_color(zone))
    reset = _c(C.RESET)
    bold = _c(C.BOLD)
    dim = _c(C.DIM)
    cyan = _c(C.CYAN)

    bar = render_progress_bar(tau if tau <= 1.0 else 1.0, zone=zone)

    lines = [
        f"{bold}{cyan}Tarea #{task_id} — {title}{reset}",
        f"  Estado    : {status}",
        f"  Fase      : {phase_label}",
        f"  Progreso  : {phases_done}/{total_phases} fases completadas",
        f"  τ         : {tau:.4f}  {bar}",
        f"  Δ         : {delta:+.4f}  ({delta_status.value})",
        f"  IU        : {iu:.4f}",
        f"  Zona      : {color}{zone.value}{reset}",
        f"  Intervalo : {i_spam_min:.1f} min",
        f"  Deadline  : {deadline}",
        f"  Restante  : {time_remaining}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Simple print helpers
# ---------------------------------------------------------------------------

def print_success(msg: str) -> None:
    print(f"{_c(C.GREEN)}✓{_c(C.RESET)} {msg}")


def print_error(msg: str) -> None:
    print(f"{_c(C.RED)}✗{_c(C.RESET)} {msg}", file=sys.stderr)


def print_warning(msg: str) -> None:
    print(f"{_c(C.YELLOW)}⚠{_c(C.RESET)} {msg}")


def print_info(msg: str) -> None:
    print(f"{_c(C.CYAN)}ℹ{_c(C.RESET)} {msg}")


def print_section(title: str) -> None:
    width = BANNER_WIDTH
    print(f"\n{_c(C.BOLD)}{title}{_c(C.RESET)}")
    print("─" * min(len(title) + 4, width))


def print_tampered_warning(task_id: int) -> None:
    print(
        f"\n{_c(C.RED)}{_c(C.BOLD)}"
        f"⚠ INTEGRIDAD COMPROMETIDA — Tarea #{task_id}"
        f"{_c(C.RESET)}\n"
        "  El HMAC no coincide. El contrato ha sido manipulado externamente.\n"
        "  Operaciones contractuales bloqueadas hasta recuperación explícita.\n"
    )


def print_key_missing_warning() -> None:
    print(
        f"\n{_c(C.RED)}{_c(C.BOLD)}"
        "⚠ INTEGRITY_KEY_MISSING"
        f"{_c(C.RESET)}\n"
        "  .secret no encontrado. No se puede verificar la integridad de los contratos.\n"
        "  Ejecuta 'fokiz init' para recuperar o reinicializar.\n"
    )


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return value if value else default


def prompt_int(text: str, minimum: int = 1, maximum: int | None = None) -> int:
    while True:
        raw = prompt(text)
        try:
            value = int(raw)
        except ValueError:
            print_error(f"Ingresa un número entero (mínimo {minimum}).")
            continue
        if value < minimum:
            print_error(f"El valor debe ser >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print_error(f"El valor debe ser <= {maximum}.")
            continue
        return value


def confirm(text: str) -> bool:
    answer = prompt(f"{text} [s/N]").lower()
    return answer in ("s", "si", "sí", "y", "yes")


def prompt_multiline(text: str) -> str:
    """Prompt for multi-line input (empty line to finish)."""
    print(f"{text} (línea vacía para terminar):")
    lines = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        lines.append(line)
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Time formatting
# ---------------------------------------------------------------------------

def format_time_remaining(target_dt: datetime, now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    diff = target_dt - now
    total_seconds = diff.total_seconds()
    if total_seconds <= 0:
        secs = abs(int(total_seconds))
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        return f"-{h:02d}h {m:02d}m {s:02d}s (VENCIDO)"
    secs = int(total_seconds)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days > 0:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    return f"{hours:02d}h {minutes:02d}m"


# ---------------------------------------------------------------------------
# Board rendering
# ---------------------------------------------------------------------------

def render_board(active_tasks: list[str], completed_tasks: list[str]) -> str:
    """Render a dual-column board with active and completed tasks."""
    c_orange = _c(C.ORANGE)
    c_green = _c(C.GREEN)
    c_bold = _c(C.BOLD)
    c_reset = _c(C.RESET)
    
    # ANSI-aware width padding
    def _strip_ansi(text: str) -> str:
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)
        
    def _pad(text: str, width: int) -> str:
        visible_len = len(_strip_ansi(text))
        padding = max(0, width - visible_len)
        return text + " " * padding
        
    COL_WIDTH = 55
    out = []
    out.append(render_banner(size="LARGE"))
    out.append(f"{c_bold}{c_orange}{'EN PROGRESO':^{COL_WIDTH}}{c_reset}│{c_bold}{c_green}{'COMPLETADO':^{COL_WIDTH}}{c_reset}")
    out.append("─" * COL_WIDTH + "┼" + "─" * COL_WIDTH)
    
    # Split task cards into lines
    active_lines = [card.split("\n") for card in active_tasks]
    completed_lines = [card.split("\n") for card in completed_tasks]
    
    # Display tasks side-by-side
    max_idx = max(len(active_lines), len(completed_lines))
    
    for i in range(max_idx):
        active_card = active_lines[i] if i < len(active_lines) else []
        completed_card = completed_lines[i] if i < len(completed_lines) else []
        
        max_lines = max(len(active_card), len(completed_card))
        for j in range(max_lines):
            l_act = active_card[j] if j < len(active_card) else ""
            l_cmp = completed_card[j] if j < len(completed_card) else ""
            
            out.append(f"{_pad(l_act, COL_WIDTH)}│{_pad(l_cmp, COL_WIDTH)}")
            
        out.append(" " * COL_WIDTH + "│" + " " * COL_WIDTH)
        
    return "\n".join(out)

