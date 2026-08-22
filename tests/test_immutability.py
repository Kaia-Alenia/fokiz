import sys
import pathlib
import sqlite3
import tempfile
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))
from app import db
from app.constants import MAX_ACTIVE_SLOTS
from app.errors import (
    ImmutableTaskFieldError,
    ImmutablePhaseFieldError,
    ImmutableTaskDeletionError,
    ImmutablePhaseDeletionError,
    InvalidTaskTransitionTriggerError,
    InvalidPhaseTransitionTriggerError
)

def _make_temp_db() -> pathlib.Path:
    tmp = tempfile.mktemp(suffix='.db')
    path = pathlib.Path(tmp)
    db.create_schema(path)
    return path

def _insert_task(path: pathlib.Path, task_num: int=1) -> int:
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.execute('PRAGMA foreign_keys = ON;')
    conn.execute('BEGIN;')
    cursor = conn.execute("\n        INSERT INTO tasks (title, objective, total_days, total_phases,\n            status, created_at, deadline, integrity_hash)\n        VALUES (?, ?, ?, ?, 'ACTIVE', '2025-01-01 00:00:00', '2025-01-10 00:00:00', 'abc123')\n        ", (f'Task {task_num}', f'Objective {task_num}', 10, 2))
    task_id = cursor.lastrowid
    conn.execute('COMMIT;')
    conn.close()
    return task_id

def _insert_phase(path: pathlib.Path, task_id: int, phase_num: int=1) -> None:
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.execute('PRAGMA foreign_keys = ON;')
    conn.execute('BEGIN;')
    conn.execute('\n        INSERT INTO task_phases (task_id, phase_number, title, instructions, target_deadline)\n        VALUES (?, ?, ?, ?, ?)\n        ', (task_id, phase_num, f'Phase {phase_num}', 'Do the thing', '2025-01-05 00:00:00'))
    conn.execute('COMMIT;')
    conn.close()
_SQLITE_TRIGGER_ERRORS = (sqlite3.IntegrityError, sqlite3.OperationalError)

class TestTaskImmutability(unittest.TestCase):

    def setUp(self):
        self.path = _make_temp_db()
        self.task_id = _insert_task(self.path)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def _raw_update(self, field: str, value) -> None:
        with db.immediate_transaction(self.path) as conn:
            conn.execute(f'UPDATE tasks SET {field} = ? WHERE id = ?', (value, self.task_id))

    def test_cannot_update_title(self):
        with self.assertRaises(ImmutableTaskFieldError):
            self._raw_update('title', 'Modified Title')

    def test_cannot_update_objective(self):
        with self.assertRaises(ImmutableTaskFieldError):
            self._raw_update('objective', 'Modified Objective')

    def test_cannot_update_deadline(self):
        with self.assertRaises(ImmutableTaskFieldError):
            self._raw_update('deadline', '2099-01-01 00:00:00')

    def test_cannot_update_created_at(self):
        with self.assertRaises(ImmutableTaskFieldError):
            self._raw_update('created_at', '2000-01-01 00:00:00')

    def test_cannot_update_total_days(self):
        with self.assertRaises(ImmutableTaskFieldError):
            self._raw_update('total_days', 999)

    def test_cannot_update_total_phases(self):
        with self.assertRaises(ImmutableTaskFieldError):
            self._raw_update('total_phases', 8)


    def test_cannot_delete_task(self):
        with self.assertRaises(ImmutableTaskDeletionError):
            with db.immediate_transaction(self.path) as conn:
                conn.execute('DELETE FROM tasks WHERE id = ?', (self.task_id,))

    def test_can_update_status_active_to_completed(self):
        with db.immediate_transaction(self.path) as conn:
            conn.execute("UPDATE tasks SET status = 'COMPLETED', completed_at = '2025-01-10 00:00:00' WHERE id = ?", (self.task_id,))
        with db.get_connection(self.path) as conn:
            row = conn.execute('SELECT status FROM tasks WHERE id = ?', (self.task_id,)).fetchone()
        self.assertEqual(row[0], 'COMPLETED')

    def test_cannot_reopen_completed_task(self):
        with db.immediate_transaction(self.path) as conn:
            conn.execute("UPDATE tasks SET status = 'COMPLETED', completed_at = '2025-01-10 00:00:00' WHERE id = ?", (self.task_id,))
        with self.assertRaises(InvalidTaskTransitionTriggerError):
            with db.immediate_transaction(self.path) as conn:
                conn.execute("UPDATE tasks SET status = 'ACTIVE' WHERE id = ?", (self.task_id,))

    def test_cannot_transition_completed_to_surrendered(self):
        with db.immediate_transaction(self.path) as conn:
            conn.execute("UPDATE tasks SET status = 'COMPLETED', completed_at = '2025-01-10 00:00:00' WHERE id = ?", (self.task_id,))
        with self.assertRaises(InvalidTaskTransitionTriggerError):
            with db.immediate_transaction(self.path) as conn:
                conn.execute("UPDATE tasks SET status = 'SURRENDERED' WHERE id = ?", (self.task_id,))

class TestPhaseImmutability(unittest.TestCase):

    def setUp(self):
        self.path = _make_temp_db()
        self.task_id = _insert_task(self.path)
        _insert_phase(self.path, self.task_id, 1)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def _raw_update_phase(self, field: str, value) -> None:
        with db.immediate_transaction(self.path) as conn:
            conn.execute(f'UPDATE task_phases SET {field} = ? WHERE task_id = ? AND phase_number = 1', (value, self.task_id))

    def test_cannot_update_phase_title(self):
        with self.assertRaises(ImmutablePhaseFieldError):
            self._raw_update_phase('title', 'Hacked Phase')

    def test_cannot_update_instructions(self):
        with self.assertRaises(ImmutablePhaseFieldError):
            self._raw_update_phase('instructions', 'Hacked instructions')

    def test_cannot_update_target_deadline(self):
        with self.assertRaises(ImmutablePhaseFieldError):
            self._raw_update_phase('target_deadline', '2099-01-01 00:00:00')

    def test_cannot_update_phase_number(self):
        with self.assertRaises(ImmutablePhaseFieldError):
            self._raw_update_phase('phase_number', 99)

    def test_cannot_delete_phase(self):
        with self.assertRaises(ImmutablePhaseDeletionError):
            with db.immediate_transaction(self.path) as conn:
                conn.execute('DELETE FROM task_phases WHERE task_id = ?', (self.task_id,))

    def test_can_complete_phase(self):
        with db.immediate_transaction(self.path) as conn:
            conn.execute("\n            UPDATE task_phases SET status = 'COMPLETED',\n            completed_at = '2025-01-05 00:00:00',\n            completion_log = 'Done the thing'\n            WHERE task_id = ? AND phase_number = 1\n            ", (self.task_id,))
        with db.get_connection(self.path) as conn:
            row = conn.execute('SELECT status FROM task_phases WHERE task_id = ? AND phase_number = 1', (self.task_id,)).fetchone()
        self.assertEqual(row[0], 'COMPLETED')

    def test_cannot_reopen_phase(self):
        with db.immediate_transaction(self.path) as conn:
            conn.execute("UPDATE task_phases SET status = 'COMPLETED' WHERE task_id = ? AND phase_number = 1", (self.task_id,))
        with self.assertRaises(InvalidPhaseTransitionTriggerError):
            with db.immediate_transaction(self.path) as conn:
                conn.execute("UPDATE task_phases SET status = 'PENDING' WHERE task_id = ? AND phase_number = 1", (self.task_id,))

class TestAtomicCompletion(unittest.TestCase):

    def setUp(self):
        self.path = _make_temp_db()
        self.task_id = _insert_task(self.path)
        _insert_phase(self.path, self.task_id, 1)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_atomic_rollback_on_final_completion_failure(self):
        # 1. Force a failure during the UPDATE of the task (which happens AFTER the phase update)
        # by creating a temporary trigger that throws an error.
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON;')
        conn.execute("""
            CREATE TRIGGER force_fail_task_update
            BEFORE UPDATE OF status ON tasks
            BEGIN
                SELECT RAISE(ABORT, 'Simulated failure during atomic task update');
            END;
        """)
        
        # Save original state
        task_row_before = conn.execute("SELECT status, completed_at, integrity_hash FROM tasks WHERE id = ?", (self.task_id,)).fetchone()
        phase_row_before = conn.execute("SELECT status, completed_at, completion_log FROM task_phases WHERE task_id = ? AND phase_number = 1", (self.task_id,)).fetchone()
        conn.close()
        
        # 2. Try to complete the phase and task atomically
        with self.assertRaises(sqlite3.IntegrityError):
            db.complete_phase_and_task(
                self.task_id,
                1,
                "Log",
                "2025-01-10 00:00:00",
                path=self.path
            )
            
        # 3. Verify that the phase and task were NOT completed (they rolled back)
        conn = sqlite3.connect(str(self.path), isolation_level=None)
        conn.row_factory = sqlite3.Row
        task_row_after = conn.execute("SELECT status, completed_at, integrity_hash FROM tasks WHERE id = ?", (self.task_id,)).fetchone()
        phase_row_after = conn.execute("SELECT status, completed_at, completion_log FROM task_phases WHERE task_id = ? AND phase_number = 1", (self.task_id,)).fetchone()
        
        self.assertEqual(phase_row_after['status'], 'PENDING', "Phase status changed even though task update failed!")
        self.assertEqual(phase_row_after['completed_at'], phase_row_before['completed_at'])
        self.assertEqual(phase_row_after['completion_log'], phase_row_before['completion_log'])
        
        self.assertEqual(task_row_after['status'], 'ACTIVE', "Task status changed!")
        self.assertEqual(task_row_after['completed_at'], task_row_before['completed_at'])
        self.assertEqual(task_row_after['integrity_hash'], task_row_before['integrity_hash'])
        conn.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
