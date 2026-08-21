"""
integrity.py — HMAC-SHA256 secret management and contract verification.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- Only this module reads/writes .secret.
- .secret is never printed, logged, or stored in DB.
- If .secret is missing and DB exists → INTEGRITY_KEY_MISSING.
- New .secret is never generated silently over an existing DB.
"""

import hashlib
import hmac
import os
import pathlib
import secrets
from enum import Enum

from .constants import SECRET_PATH, SECRET_SIZE_BYTES, HMAC_VERSION, PERM_SECRET
from .errors import IntegrityKeyMissingError, ContractTamperedError


# ---------------------------------------------------------------------------
# Integrity status
# ---------------------------------------------------------------------------

class IntegrityStatus(Enum):
    OK = "OK"
    TAMPERED = "TAMPERED"
    KEY_MISSING = "INTEGRITY_KEY_MISSING"
    NO_CONTRACT = "NO_CONTRACT"


# ---------------------------------------------------------------------------
# Secret management
# ---------------------------------------------------------------------------

def generate_secret(path: pathlib.Path = SECRET_PATH) -> None:
    """Generate and persist a new secret. Raises if one already exists."""
    if path.exists():
        # Never overwrite silently
        return
    raw = secrets.token_bytes(SECRET_SIZE_BYTES)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    try:
        path.chmod(PERM_SECRET)
    except OSError:
        pass


def _load_secret(path: pathlib.Path = SECRET_PATH) -> bytes:
    """Load raw secret bytes. Raises IntegrityKeyMissingError if absent."""
    if not path.exists():
        raise IntegrityKeyMissingError()
    return path.read_bytes()


# ---------------------------------------------------------------------------
# Canonical payload
# ---------------------------------------------------------------------------

def build_canonical_payload(
    task_id: int,
    title: str,
    objective: str,
    total_days: int,
    total_phases: int,
    created_at: str,
    deadline: str,
    phases: list[dict],
) -> bytes:
    """
    Build the canonical byte payload for HMAC signing.

    Format (text/plain, UTF-8):
      version=1
      task_id=<id>
      title=<title>
      objective=<objective>
      total_days=<total_days>
      total_phases=<total_phases>
      created_at=<created_at>
      deadline=<deadline>
      phase[1].number=<number>
      phase[1].title=<title>
      phase[1].instructions=<instructions>
      phase[1].target_deadline=<deadline>
      ...

    Phases must be sorted by phase_number before serializing.
    """
    lines: list[str] = [
        f"version={HMAC_VERSION}",
        f"task_id={task_id}",
        f"title={title}",
        f"objective={objective}",
        f"total_days={total_days}",
        f"total_phases={total_phases}",
        f"created_at={created_at}",
        f"deadline={deadline}",
    ]

    sorted_phases = sorted(phases, key=lambda p: int(p["phase_number"]))
    for ph in sorted_phases:
        n = ph["phase_number"]
        lines.append(f"phase[{n}].number={n}")
        lines.append(f"phase[{n}].title={ph['title']}")
        lines.append(f"phase[{n}].instructions={ph['instructions']}")
        lines.append(f"phase[{n}].target_deadline={ph['target_deadline']}")

    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# HMAC computation
# ---------------------------------------------------------------------------

def compute_hmac(payload: bytes, secret_path: pathlib.Path = SECRET_PATH) -> str:
    """Return hex-encoded HMAC-SHA256 of payload using the stored secret."""
    key = _load_secret(secret_path)
    mac = hmac.new(key, payload, hashlib.sha256)
    return mac.hexdigest()


def verify_hmac(
    payload: bytes,
    stored_hash: str,
    secret_path: pathlib.Path = SECRET_PATH,
) -> bool:
    """Return True iff HMAC matches using constant-time comparison."""
    key = _load_secret(secret_path)
    mac = hmac.new(key, payload, hashlib.sha256)
    expected = mac.hexdigest()
    return hmac.compare_digest(expected, stored_hash)


# ---------------------------------------------------------------------------
# High-level contract verification
# ---------------------------------------------------------------------------

def check_contract_integrity(
    task: "sqlite3.Row",
    phases: list["sqlite3.Row"],
    secret_path: pathlib.Path = SECRET_PATH,
) -> IntegrityStatus:
    """
    Verify a complete task+phases contract.
    Returns IntegrityStatus without raising — caller decides action.
    """
    if not secret_path.exists():
        return IntegrityStatus.KEY_MISSING

    phases_dicts = [
        {
            "phase_number": ph["phase_number"],
            "title": ph["title"],
            "instructions": ph["instructions"],
            "target_deadline": ph["target_deadline"],
        }
        for ph in phases
    ]

    payload = build_canonical_payload(
        task_id=task["id"],
        title=task["title"],
        objective=task["objective"],
        total_days=task["total_days"],
        total_phases=task["total_phases"],
        created_at=task["created_at"],
        deadline=task["deadline"],
        phases=phases_dicts,
    )

    try:
        valid = verify_hmac(payload, task["integrity_hash"], secret_path)
    except IntegrityKeyMissingError:
        return IntegrityStatus.KEY_MISSING

    return IntegrityStatus.OK if valid else IntegrityStatus.TAMPERED


def assert_contract_ok(
    task: "sqlite3.Row",
    phases: list["sqlite3.Row"],
    secret_path: pathlib.Path = SECRET_PATH,
) -> None:
    """
    Raise ContractTamperedError or IntegrityKeyMissingError if contract is not OK.
    Use this before any write operation that depends on contract integrity.
    """
    status = check_contract_integrity(task, phases, secret_path)
    if status == IntegrityStatus.KEY_MISSING:
        raise IntegrityKeyMissingError()
    if status == IntegrityStatus.TAMPERED:
        raise ContractTamperedError(task_id=task["id"])
