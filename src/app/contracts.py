"""
contracts.py — Contract construction and validation for Fokiz tasks.
Copyright (C) Alenia Studios — GNU GPL v3

RULES:
- Contract fields are validated here before touching the DB.
- Phase deadlines are computed from T0 and are fixed.
- No deadline is ever shifted due to late completion.

GOLDEN RULE — CALENDAR DAYS:
  Fokiz does NOT count "24 hours since you created the task" when the
  user specifies days.  Fokiz counts real calendar days in the user's
  configured IANA timezone and converts the boundary of those calendar
  days to an absolute, immutable timestamp.

  1 day ≠ "created_at + 24 h"
  1 day = the NEXT calendar date boundary in the user's local timezone.

  Internally we store deadlines as the exclusive start of the *following*
  day (midnight of day+1) so that:
      remaining = deadline_exclusive - now
  can be computed without floating-point rounding on "23:59:59.999…".

  Example:
      timezone = America/Mexico_City
      created_at_local = 2026-08-21 22:00
      total_days = 1
      → first_contract_date = 2026-08-22   (creation was mid-day → next date)
      → deadline_exclusive  = 2026-08-23 00:00:00 Mexico_City
      → stored UTC string   = 2026-08-23 06:00:00  (Mexico_City is UTC-6)
"""

from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import NamedTuple

from .constants import (
    TITLE_MIN, TITLE_MAX,
    OBJECTIVE_MIN, OBJECTIVE_MAX,
    PHASES_MIN, PHASES_MAX,
    DAYS_MIN,
    DEFAULT_TIMEZONE,
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
    target_deadline: str   # ISO-8601 UTC string  "YYYY-MM-DD HH:MM:SS"


class ContractSpec(NamedTuple):
    title: str
    objective: str
    total_days: int
    total_phases: int
    created_at: str         # ISO-8601 UTC string
    deadline: str           # ISO-8601 UTC string  (exclusive next-day midnight)
    phases: list[PhaseSpec]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_title(title: str) -> str:
    title = title.strip()
    if len(title) < TITLE_MIN or len(title) > TITLE_MAX:
        raise ValidationError(
            f"Title must be between {TITLE_MIN} and {TITLE_MAX} characters "
            f"(got {len(title)})."
        )
    return title


def validate_objective(objective: str) -> str:
    objective = objective.strip()
    if len(objective) < OBJECTIVE_MIN or len(objective) > OBJECTIVE_MAX:
        raise ValidationError(
            f"Objective must be between {OBJECTIVE_MIN} and {OBJECTIVE_MAX} characters "
            f"(got {len(objective)})."
        )
    return objective


def validate_total_days(days: int) -> int:
    if days < DAYS_MIN:
        raise ValidationError(f"Total days must be >= {DAYS_MIN}.")
    return days


def validate_total_phases(phases: int) -> int:
    if phases < PHASES_MIN or phases > PHASES_MAX:
        raise ValidationError(
            f"Phase count must be between {PHASES_MIN} and {PHASES_MAX}."
        )
    return phases


def validate_phase_days(days: int, phase_num: int) -> int:
    if days <= 0:
        raise ValidationError(f"Phase {phase_num} days must be > 0.")
    return days


def validate_phase_days_sum(phase_days: list[int], total_days: int) -> None:
    total = sum(phase_days)
    if total != total_days:
        raise ValidationError(
            f"Sum of phase days ({total}) must equal total_days ({total_days})."
        )


# ---------------------------------------------------------------------------
# Calendar helpers — the core of the timezone-aware day system
# ---------------------------------------------------------------------------

def _first_contract_date(created_at_utc: datetime, tz: ZoneInfo) -> date:
    """
    Determine the first contractual calendar date.

    Rule:
    - If the task is created exactly at midnight (00:00:00) local, that
      same calendar day IS the first contractual day.
    - If the task is created at any other time during the day (i.e. after
      midnight has already started), the NEXT calendar date is the first
      contractual day.  A partial day at creation does not consume a full
      contractual day.

    Args:
        created_at_utc: timezone-aware UTC datetime of task creation.
        tz: IANA ZoneInfo object for the user's local timezone.

    Returns:
        A date object representing the first contractual calendar day.
    """
    local_dt = created_at_utc.astimezone(tz)
    local_date = local_dt.date()
    midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    if local_dt == midnight:
        # Created exactly at midnight → this date is the first contract day
        return local_date
    else:
        # Created mid-day → next calendar date is the first contract day
        return local_date + timedelta(days=1)


def _deadline_exclusive(contract_date: date, tz: ZoneInfo) -> datetime:
    """
    Convert a calendar date to the exclusive deadline timestamp (UTC).

    The exclusive deadline is midnight at the START of the day AFTER
    contract_date.  This means the contractual day contract_date runs
    from 00:00:00 up to (but not including) 00:00:00 of the next day.

    Example:
        contract_date = 2026-08-22, tz = America/Mexico_City (UTC-6)
        → exclusive deadline local = 2026-08-23 00:00:00 Mexico_City
        → exclusive deadline UTC   = 2026-08-23 06:00:00 UTC

    Args:
        contract_date: the last calendar day of the contractual window.
        tz: IANA ZoneInfo object.

    Returns:
        A timezone-aware UTC datetime representing the exclusive deadline.
    """
    next_day = contract_date + timedelta(days=1)
    # Midnight at start of next_day in local timezone
    local_midnight = datetime(next_day.year, next_day.month, next_day.day,
                              0, 0, 0, tzinfo=tz)
    return local_midnight.astimezone(timezone.utc)


def compute_calendar_deadline(
    created_at_utc: datetime,
    calendar_days: int,
    tz: ZoneInfo,
) -> datetime:
    """
    Compute an exclusive UTC deadline for `calendar_days` contractual days.

    Steps:
    1. Find first_contract_date from created_at_utc and tz.
    2. last_contract_date = first_contract_date + (calendar_days - 1) days.
    3. deadline_exclusive = midnight at start of (last_contract_date + 1 day).

    Args:
        created_at_utc:  timezone-aware UTC creation timestamp.
        calendar_days:   number of contractual calendar days (>= 1).
        tz:              IANA ZoneInfo object.

    Returns:
        timezone-aware UTC datetime (exclusive, midnight of the following day).
    """
    first = _first_contract_date(created_at_utc, tz)
    last = first + timedelta(days=calendar_days - 1)
    return _deadline_exclusive(last, tz)


# ---------------------------------------------------------------------------
# IANA timezone validation
# ---------------------------------------------------------------------------

def validate_iana_timezone(tz_str: str) -> ZoneInfo:
    """
    Validate and return a ZoneInfo object for an IANA timezone identifier.

    Raises ValidationError if the identifier is not recognised by the system's
    tzdata (via the stdlib zoneinfo module).

    Args:
        tz_str: IANA timezone string, e.g. "America/Mexico_City".

    Returns:
        ZoneInfo instance for tz_str.
    """
    try:
        return ZoneInfo(tz_str)
    except (ZoneInfoNotFoundError, KeyError):
        raise ValidationError(
            f"Timezone '{tz_str}' not recognized. "
            "Use a valid IANA identifier like 'America/Mexico_City', "
            "'Europe/Madrid', 'Asia/Tokyo', etc."
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
    user_timezone: str | None = None,
) -> ContractSpec:
    """
    Build and validate a ContractSpec from raw user inputs.

    Calendar-day semantics (GOLDEN RULE):
    - `total_days` means calendar days in the user's IANA timezone, NOT
      multiples of 24 hours from created_at.
    - Phase deadlines are exclusive UTC timestamps (midnight of the day
      AFTER the last contractual day of each phase).
    - No deadline is ever moved due to late completion.

    Args:
        title:          project title.
        objective:      project objective text.
        total_days:     total contractual calendar days.
        total_phases:   number of phases.
        phase_inputs:   list of dicts with keys: title, instructions, days.
        created_at:     optional UTC datetime of creation (default: now).
        user_timezone:  optional IANA timezone string (default: DEFAULT_TIMEZONE).

    Returns:
        A fully validated ContractSpec with absolute UTC deadlines.
    """
    # Validate scalars
    title = validate_title(title)
    objective = validate_objective(objective)
    total_days = validate_total_days(total_days)
    total_phases = validate_total_phases(total_phases)

    if len(phase_inputs) != total_phases:
        raise ValidationError(
            f"Expected {total_phases} phases, got {len(phase_inputs)}."
        )

    # Validate phase days
    phase_days = []
    for i, ph in enumerate(phase_inputs, start=1):
        d = validate_phase_days(int(ph["days"]), i)
        phase_days.append(d)
    validate_phase_days_sum(phase_days, total_days)

    # Timezone
    tz_name = user_timezone or DEFAULT_TIMEZONE
    tz = validate_iana_timezone(tz_name)

    # Creation timestamp (UTC, aware)
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    # Ensure the datetime is timezone-aware UTC
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    else:
        created_at = created_at.astimezone(timezone.utc)
    # Strip sub-minute precision to keep stored strings clean
    created_at = created_at.replace(second=0, microsecond=0)

    created_at_str = _dt_to_iso(created_at)

    # Determine first contractual calendar date once
    first_date = _first_contract_date(created_at, tz)

    # Build phase specs with calendar-day deadlines
    phases: list[PhaseSpec] = []
    phase_cursor_date = first_date  # tracks start of next phase window
    for i, (ph_input, days) in enumerate(zip(phase_inputs, phase_days), start=1):
        ph_title = ph_input["title"].strip()
        ph_instructions = ph_input["instructions"].strip()

        if not ph_title:
            raise ValidationError(f"Phase {i} title cannot be empty.")
        if not ph_instructions:
            raise ValidationError(f"Phase {i} instructions cannot be empty.")

        # Last calendar day of this phase
        last_day_of_phase = phase_cursor_date + timedelta(days=days - 1)
        phase_dl_utc = _deadline_exclusive(last_day_of_phase, tz)

        phases.append(PhaseSpec(
            phase_number=i,
            title=ph_title,
            instructions=ph_instructions,
            days=days,
            target_deadline=_dt_to_iso(phase_dl_utc),
        ))

        # Next phase starts on the day after this phase's last day
        phase_cursor_date = last_day_of_phase + timedelta(days=1)

    # Overall contract deadline = deadline of the last phase
    overall_deadline_utc = compute_calendar_deadline(created_at, total_days, tz)
    deadline_str = _dt_to_iso(overall_deadline_utc)

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
    """Format a UTC-aware datetime as 'YYYY-MM-DD HH:MM:SS' (UTC, no suffix)."""
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%d %H:%M:%S")
