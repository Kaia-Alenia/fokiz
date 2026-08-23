"""
db.py — Single SQLite access layer for Fokiz.
Copyright (C) Alenia Studios — GNU GPL v3

RULES (enforced here):
- Only this module opens SQLite connections.
- All user data is passed as parameters — never interpolated.
- Critical mutations use BEGIN IMMEDIATE.
- The schema is applied once via schema.sql.
"""

import sqlite3
import pathlib
import shutil
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Any

from .time_utils import _utcnow_iso
from .constants import DB_PATH, PERM_DB
from .constants import MAX_ACTIVE_SLOTS
from .errors import (
    DatabaseMissingError,
    NotInitializedError,
    InvalidTransitionError,
    TaskNotFoundError,
    NoActivePhaseError,
    ContractImmutableError,
    MaxSlotsError,
    ImmutableTaskDeletionError,
    ImmutablePhaseDeletionError,
    ImmutableTaskFieldError,
    ImmutablePhaseFieldError,
    InvalidTaskTransitionTriggerError,
    InvalidPhaseTransitionTriggerError,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_schema_path() -> pathlib.Path:
    """Locate schema.sql relative to this package."""
    here = pathlib.Path(__file__).parent.parent
    return here / "schema.sql"


def _connect(path: pathlib.Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _handle_sqlite_error(e: sqlite3.Error) -> None:
    msg = str(e)
    if "immutable task deletion" in msg:
        raise ImmutableTaskDeletionError() from e
    if "immutable phase deletion" in msg:
        raise ImmutablePhaseDeletionError() from e
    if "immutable task contract field" in msg:
        raise ImmutableTaskFieldError() from e
    if "immutable phase contract field" in msg:
        raise ImmutablePhaseFieldError() from e
    if "invalid task state transition" in msg:
        raise InvalidTaskTransitionTriggerError() from e
    if "invalid phase state transition" in msg:
        raise InvalidPhaseTransitionTriggerError() from e
    raise e


@contextmanager
def get_connection(path: pathlib.Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Yield an open connection; caller owns transaction lifecycle."""
    if not path.exists():
        raise DatabaseMissingError()
    conn = _connect(path)
    try:
        yield conn
    except sqlite3.Error as e:
        _handle_sqlite_error(e)
    finally:
        conn.close()


@contextmanager
def immediate_transaction(path: pathlib.Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Yield a connection inside BEGIN IMMEDIATE. Commits on exit, rolls back on error."""
    if not path.exists():
        raise DatabaseMissingError()
    conn = _connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield conn
        conn.execute("COMMIT;")
    except sqlite3.Error as e:
        conn.execute("ROLLBACK;")
        _handle_sqlite_error(e)
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

def create_schema(path: pathlib.Path = DB_PATH) -> None:
    """Create tables and triggers. Safe to run multiple times (IF NOT EXISTS)."""
    schema_path = _get_schema_path()
    sql = schema_path.read_text(encoding="utf-8")

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(path)
    try:
        conn.executescript(sql)
    finally:
        conn.close()

    # Restrict file permissions
    try:
        path.chmod(PERM_DB)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# user_config
# ---------------------------------------------------------------------------

def upsert_user_config(
    nickname: str,
    timezone: str,
    max_active_slots: int = 3,
    path: pathlib.Path = DB_PATH,
) -> None:
    with immediate_transaction(path) as conn:
        conn.execute(
            """
            INSERT INTO user_config (id, nickname, timezone, max_active_slots)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nickname = excluded.nickname,
                timezone = excluded.timezone,
                max_active_slots = excluded.max_active_slots
            """,
            (nickname, timezone, max_active_slots),
        )


def get_user_config(path: pathlib.Path = DB_PATH) -> sqlite3.Row | None:
    with get_connection(path) as conn:
        return conn.execute("SELECT * FROM user_config WHERE id = 1").fetchone()


# ---------------------------------------------------------------------------
# Tasks — read
# ---------------------------------------------------------------------------

def get_task(task_id: int, path: pathlib.Path = DB_PATH) -> sqlite3.Row:
    with get_connection(path) as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise TaskNotFoundError(task_id)
    return row


def get_active_tasks(path: pathlib.Path = DB_PATH) -> list[sqlite3.Row]:
    with get_connection(path) as conn:
        return conn.execute(
            "SELECT * FROM tasks WHERE status = 'ACTIVE' ORDER BY created_at"
        ).fetchall()


def get_all_tasks(path: pathlib.Path = DB_PATH) -> list[sqlite3.Row]:
    with get_connection(path) as conn:
        return conn.execute(
            "SELECT * FROM tasks ORDER BY created_at"
        ).fetchall()


def get_surrendered_tasks(path: pathlib.Path = DB_PATH) -> list[sqlite3.Row]:
    with get_connection(path) as conn:
        return conn.execute(
            "SELECT * FROM tasks WHERE status = 'SURRENDERED' ORDER BY created_at"
        ).fetchall()


def count_surrendered_tasks(path: pathlib.Path = DB_PATH) -> int:
    with get_connection(path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE status = 'SURRENDERED'"
        ).fetchone()
    return row["c"] if row else 0


def count_active_tasks(path: pathlib.Path = DB_PATH) -> int:
    with get_connection(path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE status = 'ACTIVE'"
        ).fetchone()
    return row["c"] if row else 0


# ---------------------------------------------------------------------------
# Tasks — write
# ---------------------------------------------------------------------------

def insert_task(
    title: str,
    objective: str,
    total_days: int,
    total_phases: int,
    deadline: str,
    created_at: str,
    integrity_hash: str,
    path: pathlib.Path = DB_PATH,
) -> int:
    """Insert a new ACTIVE task. Returns the new task_id."""
    with immediate_transaction(path) as conn:
        # Enforce slot limit
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM tasks WHERE status = 'ACTIVE'"
        ).fetchone()
        if row["c"] >= MAX_ACTIVE_SLOTS:
            raise MaxSlotsError(MAX_ACTIVE_SLOTS)

        cursor = conn.execute(
            """
            INSERT INTO tasks (
                title, objective, total_days, total_phases,
                status, created_at, deadline, integrity_hash
            ) VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
            """,
            (title, objective, total_days, total_phases,
             created_at, deadline, integrity_hash),
        )
    return cursor.lastrowid


def finalize_task_hmac(
    task_id: int,
    integrity_hash: str,
    path: pathlib.Path = DB_PATH,
) -> None:
    """
    Update integrity_hash for a newly created task.
    """
    with immediate_transaction(path) as conn:
        conn.execute(
            "UPDATE tasks SET integrity_hash = ? WHERE id = ?",
            (integrity_hash, task_id),
        )

def complete_task(task_id: int, completed_at: str, new_integrity_hash: str, path: pathlib.Path = DB_PATH) -> None:
    with immediate_transaction(path) as conn:
        row = conn.execute(
            "SELECT status FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise TaskNotFoundError(task_id)
        if row["status"] != "ACTIVE":
            raise InvalidTransitionError(row["status"], "COMPLETED")
        conn.execute(
            "UPDATE tasks SET status = 'COMPLETED', completed_at = ?, integrity_hash = ? WHERE id = ?",
            (completed_at, new_integrity_hash, task_id),
        )


def surrender_task(
    task_id: int,
    reason: str,
    completed_at: str,
    path: pathlib.Path = DB_PATH,
) -> None:
    from .integrity import recompute_hmac
    with immediate_transaction(path) as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise TaskNotFoundError(task_id)
        if row["status"] != "ACTIVE":
            raise InvalidTransitionError(row["status"], "SURRENDERED")
            
        phases = conn.execute(
            "SELECT * FROM task_phases WHERE task_id = ? ORDER BY phase_number",
            (task_id,),
        ).fetchall()
        
        task_overrides = {
            "status": "SURRENDERED",
            "completed_at": completed_at,
            "surrender_reason": reason,
        }
        new_integrity_hash = recompute_hmac(row, phases, task_overrides, None)

        conn.execute(
            """
            UPDATE tasks
            SET status = 'SURRENDERED', completed_at = ?, surrender_reason = ?, integrity_hash = ?
            WHERE id = ?
            """,
            (completed_at, reason, new_integrity_hash, task_id),
        )


# ---------------------------------------------------------------------------
# Phases — read
# ---------------------------------------------------------------------------

def get_phases(task_id: int, path: pathlib.Path = DB_PATH) -> list[sqlite3.Row]:
    with get_connection(path) as conn:
        return conn.execute(
            "SELECT * FROM task_phases WHERE task_id = ? ORDER BY phase_number",
            (task_id,),
        ).fetchall()


def get_active_phase(task_id: int, path: pathlib.Path = DB_PATH) -> sqlite3.Row:
    """Return the first PENDING phase ordered by phase_number."""
    with get_connection(path) as conn:
        row = conn.execute(
            """
            SELECT * FROM task_phases
            WHERE task_id = ? AND status = 'PENDING'
            ORDER BY phase_number
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()
    if row is None:
        raise NoActivePhaseError(task_id)
    return row


# ---------------------------------------------------------------------------
# Phases — write
# ---------------------------------------------------------------------------

def insert_phases(
    task_id: int,
    phases: list[dict],
    path: pathlib.Path = DB_PATH,
) -> None:
    """Insert multiple phases for a task (within an existing transaction scope)."""
    with immediate_transaction(path) as conn:
        for ph in phases:
            conn.execute(
                """
                INSERT INTO task_phases (
                    task_id, phase_number, title, instructions, target_deadline
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    ph["phase_number"],
                    ph["title"],
                    ph["instructions"],
                    ph["target_deadline"],
                ),
            )


def complete_phase(
    task_id: int,
    phase_number: int,
    log: str,
    completed_at: str,
    path: pathlib.Path = DB_PATH,
) -> None:
    from .integrity import recompute_hmac
    with immediate_transaction(path) as conn:
        row_task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row_task is None:
            raise TaskNotFoundError(task_id)
        if row_task["status"] != "ACTIVE":
            raise InvalidTransitionError(row_task["status"], "COMPLETED")

        phases = conn.execute(
            "SELECT * FROM task_phases WHERE task_id = ? ORDER BY phase_number",
            (task_id,),
        ).fetchall()
        
        target_phase = None
        for ph in phases:
            if ph["phase_number"] == phase_number:
                target_phase = ph
                break
                
        if target_phase is None:
            raise NoActivePhaseError(task_id)
        if target_phase["status"] != "PENDING":
            raise InvalidTransitionError(target_phase["status"], "COMPLETED")

        phase_overrides = {
            phase_number: {
                "status": "COMPLETED",
                "completed_at": completed_at,
                "completion_log": log,
            }
        }
        new_integrity_hash = recompute_hmac(row_task, phases, None, phase_overrides)

        conn.execute(
            """
            UPDATE task_phases
            SET status = 'COMPLETED', completed_at = ?, completion_log = ?
            WHERE task_id = ? AND phase_number = ?
            """,
            (completed_at, log, task_id, phase_number),
        )
        conn.execute(
            "UPDATE tasks SET integrity_hash = ? WHERE id = ?",
            (new_integrity_hash, task_id),
        )


def complete_phase_and_task(
    task_id: int,
    phase_number: int,
    log: str,
    completed_at: str,
    path: pathlib.Path = DB_PATH,
) -> None:
    from .integrity import recompute_hmac
    with immediate_transaction(path) as conn:
        row_task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row_task is None:
            raise TaskNotFoundError(task_id)
        if row_task["status"] != "ACTIVE":
            raise InvalidTransitionError(row_task["status"], "COMPLETED")

        phases = conn.execute(
            "SELECT * FROM task_phases WHERE task_id = ? ORDER BY phase_number",
            (task_id,),
        ).fetchall()
        
        target_phase = None
        for ph in phases:
            if ph["phase_number"] == phase_number:
                target_phase = ph
                break
                
        if target_phase is None:
            raise NoActivePhaseError(task_id)
        if target_phase["status"] != "PENDING":
            raise InvalidTransitionError(target_phase["status"], "COMPLETED")

        task_overrides = {
            "status": "COMPLETED",
            "completed_at": completed_at,
        }
        phase_overrides = {
            phase_number: {
                "status": "COMPLETED",
                "completed_at": completed_at,
                "completion_log": log,
            }
        }
        new_integrity_hash = recompute_hmac(row_task, phases, task_overrides, phase_overrides)

        conn.execute(
            """
            UPDATE task_phases
            SET status = 'COMPLETED', completed_at = ?, completion_log = ?
            WHERE task_id = ? AND phase_number = ?
            """,
            (completed_at, log, task_id, phase_number),
        )

        conn.execute(
            """
            UPDATE tasks 
            SET status = 'COMPLETED', completed_at = ?, integrity_hash = ? 
            WHERE id = ?
            """,
            (completed_at, new_integrity_hash, task_id),
        )

# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def insert_notification(
    task_id: int,
    urgency_level: str,
    message_sent: str,
    dispatched_at: str,
    path: pathlib.Path = DB_PATH,
) -> None:
    with immediate_transaction(path) as conn:
        conn.execute(
            """
            INSERT INTO notification_history (task_id, urgency_level, message_sent, dispatched_at)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, urgency_level, message_sent, dispatched_at),
        )


def get_last_notification(
    task_id: int,
    path: pathlib.Path = DB_PATH,
) -> sqlite3.Row | None:
    with get_connection(path) as conn:
        return conn.execute(
            """
            SELECT * FROM notification_history
            WHERE task_id = ?
            ORDER BY dispatched_at DESC
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()


# ---------------------------------------------------------------------------
# Integrity log
# ---------------------------------------------------------------------------

def log_integrity_event(
    event_type: str,
    task_id: int | None = None,
    detail: str | None = None,
    path: pathlib.Path = DB_PATH,
) -> None:
    """Write a tamper/anomaly event to the integrity log."""
    now = _utcnow_iso()
    try:
        with immediate_transaction(path) as conn:
            conn.execute(
                """
                INSERT INTO integrity_log (event_type, task_id, detail, recorded_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, task_id, detail, now),
            )
    except Exception:
        # Integrity log failures must never crash the monitor
        pass



def db_exists(path: pathlib.Path = DB_PATH) -> bool:
    return path.exists()
