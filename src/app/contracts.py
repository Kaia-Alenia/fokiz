"""
contracts.py — Contract construction and validation for Fokiz tasks.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- Contract fields are validated here before touching the DB.
- Phase deadlines are computed from T0 and are fixed.
- No deadline is ever shifted due to late completion.
"""

from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from .constants import (
    TITLE_MIN, TITLE_MAX,
    OBJECTIVE_MIN, OBJECTIVE_MAX,
    PHASES_MIN, PHASES_MAX,
    DAYS_MIN,
)
from .errors import ValidationError


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class PhaseSpec(NamedTuple):
    phase_number: int
    title: str
    instructions: str
    days: int
    target_deadline: str   # ISO-8601 UTC string


class ContractSpec(NamedTuple):
    title: str
    objective: str
    total_days: int
    total_phases: int
    created_at: str         # ISO-8601 UTC string
    deadline: str           # ISO-8601 UTC string
    phases: list[PhaseSpec]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_title(title: str) -> str:
    title = title.strip()
    if len(title) < TITLE_MIN or len(title) > TITLE_MAX:
        raise ValidationError(
            f"El título debe tener entre {TITLE_MIN} y {TITLE_MAX} caracteres "
            f"(tiene {len(title)})."
        )
    return title


def validate_objective(objective: str) -> str:
    objective = objective.strip()
    if len(objective) < OBJECTIVE_MIN or len(objective) > OBJECTIVE_MAX:
        raise ValidationError(
            f"El objetivo debe tener entre {OBJECTIVE_MIN} y {OBJECTIVE_MAX} caracteres "
            f"(tiene {len(objective)})."
        )
    return objective


def validate_total_days(days: int) -> int:
    if days < DAYS_MIN:
        raise ValidationError(f"Los días totales deben ser >= {DAYS_MIN}.")
    return days


def validate_total_phases(phases: int) -> int:
    if phases < PHASES_MIN or phases > PHASES_MAX:
        raise ValidationError(
            f"El número de fases debe estar entre {PHASES_MIN} y {PHASES_MAX}."
        )
    return phases


def validate_phase_days(days: int, phase_num: int) -> int:
    if days <= 0:
        raise ValidationError(f"Los días de la fase {phase_num} deben ser > 0.")
    return days


def validate_phase_days_sum(phase_days: list[int], total_days: int) -> None:
    total = sum(phase_days)
    if total != total_days:
        raise ValidationError(
            f"La suma de días de las fases ({total}) "
            f"debe ser exactamente igual a los días totales ({total_days})."
        )


# ---------------------------------------------------------------------------
# Contract construction
# ---------------------------------------------------------------------------

def build_contract(
    title: str,
    objective: str,
    total_days: int,
    total_phases: int,
    phase_inputs: list[dict],
    created_at: datetime | None = None,
) -> ContractSpec:
    """
    Build and validate a ContractSpec from raw user inputs.

    phase_inputs: list of dicts with keys: title, instructions, days

    Phase deadlines are computed from T0 (created_at) using fixed windows.
    No deadline is moved due to late completion.
    """
    # Validate scalars
    title = validate_title(title)
    objective = validate_objective(objective)
    total_days = validate_total_days(total_days)
    total_phases = validate_total_phases(total_phases)

    if len(phase_inputs) != total_phases:
        raise ValidationError(
            f"Se esperaban {total_phases} fases, se recibieron {len(phase_inputs)}."
        )

    # Validate phase days
    phase_days = []
    for i, ph in enumerate(phase_inputs, start=1):
        d = validate_phase_days(int(ph["days"]), i)
        phase_days.append(d)
    validate_phase_days_sum(phase_days, total_days)

    # Timestamps
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    created_at = created_at.replace(second=0, microsecond=0)

    created_at_str = _dt_to_iso(created_at)

    # Build phase specs with fixed deadlines
    phases: list[PhaseSpec] = []
    cursor = created_at
    for i, (ph_input, days) in enumerate(zip(phase_inputs, phase_days), start=1):
        ph_title = ph_input["title"].strip()
        ph_instructions = ph_input["instructions"].strip()

        if not ph_title:
            raise ValidationError(f"El título de la fase {i} no puede estar vacío.")
        if not ph_instructions:
            raise ValidationError(f"Las instrucciones de la fase {i} no pueden estar vacías.")

        cursor = cursor + timedelta(days=days)
        phases.append(PhaseSpec(
            phase_number=i,
            title=ph_title,
            instructions=ph_instructions,
            days=days,
            target_deadline=_dt_to_iso(cursor),
        ))

    deadline_str = _dt_to_iso(created_at + timedelta(days=total_days))

    return ContractSpec(
        title=title,
        objective=objective,
        total_days=total_days,
        total_phases=total_phases,
        created_at=created_at_str,
        deadline=deadline_str,
        phases=phases,
    )


# ---------------------------------------------------------------------------
# Serialization for HMAC
# ---------------------------------------------------------------------------

def contract_to_phase_dicts(contract: ContractSpec) -> list[dict]:
    """Convert PhaseSpec list to plain dicts suitable for integrity.py."""
    return [
        {
            "phase_number": ph.phase_number,
            "title": ph.title,
            "instructions": ph.instructions,
            "target_deadline": ph.target_deadline,
        }
        for ph in contract.phases
    ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dt_to_iso(dt: datetime) -> str:
    """Format datetime as 'YYYY-MM-DD HH:MM:SS' (no timezone suffix, UTC assumed)."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")
