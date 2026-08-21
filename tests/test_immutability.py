"""
tests/test_immutability.py — Tests for SQLite immutability triggers.
Copyright (C) Alenia Studios — GNU GPL v3
"""

import sys
import pathlib
import sqlite3
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from app import db
from app.constants import MAX_ACTIVE_SLOTS


def _make_temp_db() -> pathlib.Path:
    tmp = tempfile.mktemp(suffix=".db")
    path = pathlib.Path(tmp)
    db.create_schema(path)
    return path


def _insert_task(path: pathlib.Path, task_num: int = 1) -> int:
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("BEGIN;")
    cursor = conn.execute(
        """
        INSERT INTO tasks (title, objective, total_days, total_phases,
            status, created_at, deadline, integrity_hash)
        VALUES (?, ?, ?, ?, 'ACTIVE', '2025-01-01 00:00:00', '2025-01-10 00:00:00', 'abc123')
        """,
        (f"Task {task_num}", f"Objective {task_num}", 10, 2),
    )
    task_id = cursor.lastrowid
    conn.execute("COMMIT;")
    conn.close()
    return task_id


def _insert_phase(path: pathlib.Path, task_id: int, phase_num: int = 1) -> None:
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("BEGIN;")
    conn.execute(
        """
        INSERT INTO task_phases (task_id, phase_number, title, instructions, target_deadline)
        VALUES (?, ?, ?, ?, ?)
        """,
        (task_id, phase_num, f"Phase {phase_num}", "Do the thing", "2025-01-05 00:00:00"),
    )
    conn.execute("COMMIT;")
    conn.close()


# SQLite RAISE(ABORT, ...) raises IntegrityError in Python 3.x.
# We accept both to be robust.
_SQLITE_TRIGGER_ERRORS = (sqlite3.IntegrityError, sqlite3.OperationalError)


class TestTaskImmutability(unittest.TestCase):
    def setUp(self):
        self.path = _make_temp_db()
        self.task_id = _insert_task(self.path)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def _raw_update(self, field: str, value) -> None:
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            f"UPDATE tasks SET {field} = ? WHERE id = ?",
            (value, self.task_id),
        )
        conn.close()

    def test_cannot_update_title(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update("title", "Modified Title")

    def test_cannot_update_objective(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update("objective", "Modified Objective")

    def test_cannot_update_deadline(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update("deadline", "2099-01-01 00:00:00")

    def test_cannot_update_created_at(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update("created_at", "2000-01-01 00:00:00")

    def test_cannot_update_total_days(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update("total_days", 999)

    def test_cannot_update_total_phases(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update("total_phases", 8)

    def test_cannot_update_integrity_hash(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update("integrity_hash", "fakedhash")

    def test_cannot_delete_task(self):
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON;")
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            conn.execute("DELETE FROM tasks WHERE id = ?", (self.task_id,))
        conn.close()

    def test_can_update_status_active_to_completed(self):
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            "UPDATE tasks SET status = 'COMPLETED', completed_at = '2025-01-10 00:00:00' WHERE id = ?",
            (self.task_id,),
        )
        row = conn.execute("SELECT status FROM tasks WHERE id = ?", (self.task_id,)).fetchone()
        self.assertEqual(row[0], "COMPLETED")
        conn.close()

    def test_cannot_reopen_completed_task(self):
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            "UPDATE tasks SET status = 'COMPLETED', completed_at = '2025-01-10 00:00:00' WHERE id = ?",
            (self.task_id,),
        )
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            conn.execute(
                "UPDATE tasks SET status = 'ACTIVE' WHERE id = ?",
                (self.task_id,),
            )
        conn.close()

    def test_cannot_transition_completed_to_surrendered(self):
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            "UPDATE tasks SET status = 'COMPLETED', completed_at = '2025-01-10 00:00:00' WHERE id = ?",
            (self.task_id,),
        )
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            conn.execute(
                "UPDATE tasks SET status = 'SURRENDERED' WHERE id = ?",
                (self.task_id,),
            )
        conn.close()


class TestPhaseImmutability(unittest.TestCase):
    def setUp(self):
        self.path = _make_temp_db()
        self.task_id = _insert_task(self.path)
        _insert_phase(self.path, self.task_id, 1)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def _raw_update_phase(self, field: str, value) -> None:
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            f"UPDATE task_phases SET {field} = ? WHERE task_id = ? AND phase_number = 1",
            (value, self.task_id),
        )
        conn.close()

    def test_cannot_update_phase_title(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update_phase("title", "Hacked Phase")

    def test_cannot_update_instructions(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update_phase("instructions", "Hacked instructions")

    def test_cannot_update_target_deadline(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update_phase("target_deadline", "2099-01-01 00:00:00")

    def test_cannot_update_phase_number(self):
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            self._raw_update_phase("phase_number", 99)

    def test_cannot_delete_phase(self):
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON;")
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            conn.execute(
                "DELETE FROM task_phases WHERE task_id = ?",
                (self.task_id,),
            )
        conn.close()

    def test_can_complete_phase(self):
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            """
            UPDATE task_phases SET status = 'COMPLETED',
            completed_at = '2025-01-05 00:00:00',
            completion_log = 'Done the thing'
            WHERE task_id = ? AND phase_number = 1
            """,
            (self.task_id,),
        )
        row = conn.execute(
            "SELECT status FROM task_phases WHERE task_id = ? AND phase_number = 1",
            (self.task_id,),
        ).fetchone()
        self.assertEqual(row[0], "COMPLETED")
        conn.close()

    def test_cannot_reopen_phase(self):
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            "UPDATE task_phases SET status = 'COMPLETED' WHERE task_id = ? AND phase_number = 1",
            (self.task_id,),
        )
        with self.assertRaises(_SQLITE_TRIGGER_ERRORS):
            conn.execute(
                "UPDATE task_phases SET status = 'PENDING' WHERE task_id = ? AND phase_number = 1",
                (self.task_id,),
            )
        conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
