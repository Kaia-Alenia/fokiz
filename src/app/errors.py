"""
errors.py — Fokiz exceptions and error codes.
Copyright (C) Alenia Studios — GNU GPL v3
"""
from .i18n import _

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class FokizError(Exception):
    """Base class for all Fokiz errors."""
    code: str = "FOKIZ_ERROR"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


# ---------------------------------------------------------------------------
# Integrity errors
# ---------------------------------------------------------------------------

class IntegrityKeyMissingError(FokizError):
    """Raised when .secret is missing and a DB exists."""
    code = "INTEGRITY_KEY_MISSING"

    def __init__(self) -> None:
        super().__init__(_("error.integrity_key_missing"))


class ContractTamperedError(FokizError):
    """Raised when HMAC verification fails."""
    code = "TAMPERED"

    def __init__(self, task_id: int | None = None) -> None:
        msg = _("error.tampered")
        if task_id is not None:
            msg += f" (task_id={task_id})"
        super().__init__(msg)


class ContractImmutableError(FokizError):
    """Raised when an attempt to modify immutable fields is made."""
    code = "CONTRACT_IMMUTABLE"

    def __init__(self, field: str = "") -> None:
        msg = _("error.immutable")
        if field:
            msg += f" ({field})"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# State errors
# ---------------------------------------------------------------------------

class InvalidTransitionError(FokizError):
    """Raised on an illegal state transition."""
    code = "INVALID_TRANSITION"

    def __init__(self, from_state: str, to_state: str) -> None:
        super().__init__(_("error.invalid_transition", f=from_state, t=to_state))


class TaskNotFoundError(FokizError):
    """Raised when a task_id does not exist."""
    code = "TASK_NOT_FOUND"

    def __init__(self, task_id: int) -> None:
        super().__init__(_("error.task_not_found", tid=task_id))


class NoActivePhaseError(FokizError):
    """Raised when no PENDING phase exists."""
    code = "NO_ACTIVE_PHASE"

    def __init__(self, task_id: int) -> None:
        super().__init__(_("error.no_active_phase", tid=task_id))


class MaxSlotsError(FokizError):
    """Raised when active slot limit is reached."""
    code = "MAX_SLOTS"

    def __init__(self, limit: int) -> None:
        super().__init__(_("error.max_slots", limit=limit))


class DatabaseMissingError(FokizError):
    """Raised when data.db is missing."""
    code = "DATABASE_MISSING"

    def __init__(self) -> None:
        super().__init__(_("error.database_missing"))


class NotInitializedError(FokizError):
    """Raised when Fokiz has not been initialized."""
    code = "NOT_INITIALIZED"

    def __init__(self) -> None:
        super().__init__(_("error.not_initialized"))


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class ValidationError(FokizError):
    """Raised on user input validation failures."""
    code = "VALIDATION_ERROR"


class AntiCheatError(FokizError):
    """Raised when anti-cheat heuristics detect suspicious input."""
    code = "ANTI_CHEAT"

    def __init__(self, reason: str) -> None:
        super().__init__(_("error.anti_cheat", reason=reason))


class EarlyCompletionError(FokizError):
    """Raised when user tries to close a phase too early without confirmation."""
    code = "EARLY_COMPLETION"

    def __init__(self) -> None:
        super().__init__(_("error.early_completion"))


# ---------------------------------------------------------------------------
# System / dependency errors
# ---------------------------------------------------------------------------

class DependencyMissingError(FokizError):
    """Raised when a required system dependency is missing."""
    code = "DEPENDENCY_MISSING"

    def __init__(self, dep: str) -> None:
        super().__init__(_("error.dependency_missing", dep=dep))


class PresenceDetectionError(FokizError):
    """Raised when idle time cannot be determined."""
    code = "PRESENCE_DETECTION_FAILED"

    def __init__(self, detail: str = "") -> None:
        msg = _("error.presence_detection")
        if detail:
            msg += f" {detail}"
        super().__init__(msg)
