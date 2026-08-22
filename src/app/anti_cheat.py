"""
anti_cheat.py — Anti-cheat heuristics for phase completion logs.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- These are heuristics, not cryptographic proof of work.
- They add friction, not certainty.
- Never reject based solely on length if the content is valid.
"""

import math
import re
from collections import Counter

from .constants import (
    ENTROPY_MIN,
    LOG_MIN_CHARS,
    LOG_TOKENS_OVERLAP_MIN,
    LOG_EARLY_TAU_THRESHOLD,
)
from .errors import AntiCheatError, EarlyCompletionError
from .i18n import _


# ---------------------------------------------------------------------------
# Known garbage patterns
# ---------------------------------------------------------------------------

_GARBAGE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(.)\1{4,}$"),          # aaaaaaaa
    re.compile(r"^(asdf|qwer|zxcv|wasd)", re.IGNORECASE),  # keyboard rows
    re.compile(r"^[0-9]+$"),              # pure numbers
    re.compile(r"^qwerty", re.IGNORECASE),
    re.compile(r"^123456"),
    re.compile(r"^\s*$"),                  # blank
]

_KEYBOARD_ROWS = {
    "asdfghjkl", "qwertyuiop", "zxcvbnm",
    "asdfjkl", "qwerty", "asdf", "zxcv",
}


# ---------------------------------------------------------------------------
# Shannon entropy
# ---------------------------------------------------------------------------

def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    length = len(text)
    return -sum(
        (c / length) * math.log2(c / length)
        for c in counts.values()
    )


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"\b[a-záéíóúüñ\w]{3,}\b", text.lower())
    return set(tokens)


# ---------------------------------------------------------------------------
# Core checks
# ---------------------------------------------------------------------------

def _check_garbage(log: str) -> None:
    stripped = log.strip()
    for pattern in _GARBAGE_PATTERNS:
        if pattern.match(stripped):
            raise AntiCheatError(_("anti_cheat.garbage"))
    lowered = stripped.lower().replace(" ", "")
    if lowered in _KEYBOARD_ROWS:
        raise AntiCheatError(_("anti_cheat.keyboard_pattern"))


def _check_entropy(log: str) -> None:
    entropy = _shannon_entropy(log.strip())
    if entropy < ENTROPY_MIN:
        raise AntiCheatError(_("anti_cheat.low_entropy", entropy=entropy))


def _check_length(log: str) -> None:
    if len(log.strip()) < LOG_MIN_CHARS:
        raise AntiCheatError(
            _("anti_cheat.too_short", length=len(log.strip()), min_chars=LOG_MIN_CHARS)
        )


def _check_lexical_overlap(log: str, instructions: str) -> None:
    log_tokens = _tokenize(log)
    instr_tokens = _tokenize(instructions)
    if not instr_tokens:
        return  # No instructions to compare against
    overlap = log_tokens & instr_tokens
    if len(overlap) < LOG_TOKENS_OVERLAP_MIN:
        raise AntiCheatError(_("anti_cheat.no_overlap"))


def _normalize_phrase(text: str) -> str:
    return " ".join(text.strip().lower().split())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_completion_log(
    log: str,
    instructions: str,
    tau: float,
) -> None:
    """
    Run all anti-cheat heuristics on a completion log.
    Raises AntiCheatError or EarlyCompletionError on failure.

    Parameters:
        log: User-supplied completion log text.
        instructions: Phase instructions (used for lexical comparison).
        tau: Current τ value for temporal sanity check.
    """
    _check_garbage(log)
    _check_length(log)
    _check_entropy(log)
    _check_lexical_overlap(log, instructions)
    _check_early_completion(log, tau)


def _check_early_completion(log: str, tau: float) -> None:
    """
    If τ < LOG_EARLY_TAU_THRESHOLD, the user must type the exact confirmation phrase.
    """
    if tau >= LOG_EARLY_TAU_THRESHOLD:
        return
    normalized_log = _normalize_phrase(log)
    normalized_phrase = _normalize_phrase(_("anti_cheat.early_confirm_phrase"))
    # The log must contain the phrase (it may have more text after)
    if normalized_phrase not in normalized_log:
        raise EarlyCompletionError()


def validate_early_confirm_phrase(text: str) -> bool:
    """Utility: return True if the text contains the required early-confirm phrase."""
    return _normalize_phrase(_("anti_cheat.early_confirm_phrase")) in _normalize_phrase(text)
