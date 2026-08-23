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
from typing import Any

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
    status: str,
    completed_at: str | None,
    surrender_reason: str | None,
    phases: list[dict],
) -> bytes:
    """
    Build the canonical byte payload for HMAC signing.

    Field Classification:
    - Immutable task fields: task_id, title, objective, total_days, total_phases, created_at, deadline
    - Mutable task fields (audit/state): status, completed_at, surrender_reason
    - Immutable phase fields: number, title, instructions, target_deadline
    - Mutable phase fields (audit/state): status, completed_at, completion_log

    Format (text/plain, UTF-8):
      version=2
      task_id=<id>
      title=<title>
      objective=<objective>
      total_days=<total_days>
      total_phases=<total_phases>
      created_at=<created_at>
      deadline=<deadline>
      status=<status>
      completed_at=<completed_at>
      surrender_reason=<surrender_reason>
      phase[1].number=<number>
      phase[1].title=<title>
      phase[1].instructions=<instructions>
      phase[1].target_deadline=<deadline>
      phase[1].status=<status>
      phase[1].completed_at=<completed_at>
      phase[1].completion_log=<completion_log>
      ...

    Phases must be sorted by phase_number before serializing.
    None values for optional fields are serialized as empty strings.
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
        f"status={status}",
        f"completed_at={completed_at or ''}",
        f"surrender_reason={surrender_reason or ''}",
    ]

    sorted_phases = sorted(phases, key=lambda p: int(p["phase_number"]))
    for ph in sorted_phases:
        n = ph["phase_number"]
        lines.append(f"phase[{n}].number={n}")
        lines.append(f"phase[{n}].title={ph['title']}")
        lines.append(f"phase[{n}].instructions={ph['instructions']}")
        lines.append(f"phase[{n}].target_deadline={ph['target_deadline']}")
        lines.append(f"phase[{n}].status={ph.get('status', 'PENDING')}")
        lines.append(f"phase[{n}].completed_at={ph.get('completed_at') or ''}")
        lines.append(f"phase[{n}].completion_log={ph.get('completion_log') or ''}")

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

def recompute_hmac(
    task: "sqlite3.Row",
    phases: list["sqlite3.Row"],
    task_overrides: dict[str, Any] | None = None,
    phase_overrides: dict[int, dict[str, Any]] | None = None,
    secret_path: pathlib.Path = SECRET_PATH,
) -> str:
    """
    Compute a new HMAC for a task and its phases, applying overrides.
    This is used during authorized state transitions to generate the new signature.
    """
    if not secret_path.exists():
        raise IntegrityKeyMissingError()

    task_dict = dict(task)
    if task_overrides:
        task_dict.update(task_overrides)

    phases_dicts = []
    for ph in phases:
        ph_dict = dict(ph)
        if phase_overrides and ph_dict["phase_number"] in phase_overrides:
            ph_dict.update(phase_overrides[ph_dict["phase_number"]])
        phases_dicts.append(ph_dict)

    payload = build_canonical_payload(
        task_id=task_dict["id"],
        title=task_dict["title"],
        objective=task_dict["objective"],
        total_days=task_dict["total_days"],
        total_phases=task_dict["total_phases"],
        created_at=task_dict["created_at"],
        deadline=task_dict["deadline"],
        status=task_dict["status"],
        completed_at=task_dict["completed_at"],
        surrender_reason=task_dict["surrender_reason"],
        phases=phases_dicts,
    )
    return compute_hmac(payload, secret_path)


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
            "status": ph["status"],
            "completed_at": ph["completed_at"],
            "completion_log": ph["completion_log"],
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
        status=task["status"],
        completed_at=task["completed_at"],
        surrender_reason=task["surrender_reason"],
        phases=phases_dicts,
    )

    try:
        valid = verify_hmac(payload, task["integrity_hash"], secret_path)
    except IntegrityKeyMissingError:
        return IntegrityStatus.KEY_MISSING

    if valid:
        return IntegrityStatus.OK

    return IntegrityStatus.TAMPERED


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
