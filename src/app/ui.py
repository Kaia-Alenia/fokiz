"""
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
from .i18n import _


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

def render_banner(size: str = "LARGE", width: int = BANNER_WIDTH) -> str:
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

    # Center each line of the logo if a custom width is provided
    logo_lines = []
    for line in logo.strip('\n').split('\n'):
        visible_len = len(line)
        if visible_len < width:
            pad = (width - visible_len) // 2
            logo_lines.append(" " * pad + line)
        else:
            logo_lines.append(line)
    
    centered_logo = "\n".join(logo_lines)

    top = "┌" + "─" * (width - 2) + "┐"
    mid = f"│{bold}{cyan}{'FOKIZ':^{width - 2}}{reset}│"
    bot = "└" + "─" * (width - 2) + "┘"
    return f"{centered_logo}\n{top}\n{mid}\n{bot}"



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
    is_shame: bool = False,
) -> str:
    if is_shame:
        color = _c(C.RED)
        cyan = _c(C.RED)
        bar_zone = Zone.EXPIRED
    else:
        color = _c(_zone_color(zone))
        cyan = _c(C.CYAN)
        bar_zone = zone
        
    reset = _c(C.RESET)
    bold = _c(C.BOLD)
    dim = _c(C.DIM)

    def _truncate(t: str, max_l: int) -> str:
        return t if len(t) <= max_l else t[:max_l-1] + "…"

    t_title = _truncate(title, 35)
    t_phase = _truncate(phase_label, 38)
    # Use progress bar width 26 to fit exactly within 55 columns (22 prefix + 26 bar + ~7 suffix = 55)
    bar = render_progress_bar(tau if tau <= 1.0 else 1.0, width=25, zone=bar_zone)
    
    l_status = _("card.status").ljust(10)
    l_phase = _("card.phase").ljust(10)
    l_prog = _("card.progress").ljust(10)
    l_zone = _("card.zone").ljust(10)
    l_int = _("card.interval").ljust(10)
    l_rest = _("card.remaining").ljust(10)

    from .messages import get_delta_label
    lines = [
        f"{bold}{cyan}{_('card.task')} #{task_id} — {t_title}{reset}",
        f"  {l_status}: {status}",
        f"  {l_phase}: {t_phase}",
        f"  {l_prog}: {phases_done}/{total_phases} {_('card.phases_completed')}",
        f"  τ         : {tau:.4f}  {bar}",
        f"  Δ         : {delta:+.4f}  ({get_delta_label(delta_status)})",
        f"  IU        : {iu:.4f}",
        f"  {l_zone}: {color}{zone.value}{reset}",
        f"  {l_int}: {i_spam_min:.1f} {_('time.min')}",
        f"  {_('card.deadline')}".ljust(12) + f": {deadline}",
        f"  {l_rest}: {time_remaining}",
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
        f"⚠ {_('integrity.tampered_header', task_id=task_id)}"
        f"{_c(C.RESET)}\n"
        f"  {_('integrity.hmac_mismatch')}\n"
        f"  {_('integrity.blocked')}\n"
    )


def print_key_missing_warning() -> None:
    print(
        f"\n{_c(C.RED)}{_c(C.BOLD)}"
        "\u26a0 INTEGRITY_KEY_MISSING"
        f"{_c(C.RESET)}\n"
        f"  {_('integrity.key_missing')}\n"
        f"  {_('integrity.recover')}\n"
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
            print_error(_("ui.int_minimum", minimum=minimum))
            continue
        if value < minimum:
            print_error(_("ui.value_gte", minimum=minimum))
            continue
        if maximum is not None and value > maximum:
            print_error(_("ui.value_lte", maximum=maximum))
            continue
        return value


def confirm(text: str) -> bool:
    yes_vals = set(_("ui.yes_values").split(","))
    answer = prompt(f"{text} {_('ui.confirm_yes_no')}").lower().strip()
    return answer in yes_vals


def prompt_multiline(text: str) -> str:
    """Prompt for multi-line input (empty line to finish)."""
    print(_("ui.multiline_hint", text=text))
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
        return f"-{h:02d}h {m:02d}m {s:02d}s ({_('time.expired')})"
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
    TOTAL_WIDTH = COL_WIDTH * 2 + 1
    
    out = []
    out.append(render_banner(width=TOTAL_WIDTH))
    
    # Center text manually to avoid ANSI escape sequences interfering with format alignments
    hdr_left = _('board.in_progress').center(COL_WIDTH)
    hdr_right = _('board.completed').center(COL_WIDTH)
    out.append(f"{c_bold}{c_orange}{hdr_left}{c_reset}│{c_bold}{c_green}{hdr_right}{c_reset}")
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
            
        if i < max_idx - 1:
            out.append(" " * COL_WIDTH + "│" + " " * COL_WIDTH)
        
    return "\n".join(out)

