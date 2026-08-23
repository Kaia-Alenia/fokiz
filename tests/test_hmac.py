import sys
import pathlib
import tempfile
import unittest
import secrets as _secrets
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))
from app.integrity import build_canonical_payload, compute_hmac, verify_hmac, IntegrityStatus, check_contract_integrity, generate_secret
from app.errors import IntegrityKeyMissingError

def _make_secret(path: pathlib.Path) -> None:
    generate_secret(path)

def _sample_task():

    class FakeRow(dict):

        def __getitem__(self, key):
            return super().__getitem__(key)
    return FakeRow({'id': 1, 'title': 'Test Task', 'objective': 'Complete the test', 'total_days': 10, 'total_phases': 2, 'created_at': '2025-01-01 00:00:00', 'deadline': '2025-01-11 00:00:00', 'status': 'ACTIVE', 'completed_at': None, 'surrender_reason': None, 'integrity_hash': None})

def _sample_phases():

    class FakeRow(dict):

        def __getitem__(self, key):
            return super().__getitem__(key)
    return [FakeRow({'phase_number': 1, 'title': 'Phase One', 'instructions': 'Do step one', 'target_deadline': '2025-01-06 00:00:00', 'status': 'PENDING', 'completed_at': None, 'completion_log': None}), FakeRow({'phase_number': 2, 'title': 'Phase Two', 'instructions': 'Do step two', 'target_deadline': '2025-01-11 00:00:00', 'status': 'PENDING', 'completed_at': None, 'completion_log': None})]

class TestHMACComputation(unittest.TestCase):

    def setUp(self):
        self.secret_file = pathlib.Path(tempfile.mktemp(suffix='.secret'))
        _make_secret(self.secret_file)

    def tearDown(self):
        self.secret_file.unlink(missing_ok=True)

    def _build_payload(self, task=None, phases=None):
        t = task or _sample_task()
        p = phases or _sample_phases()
        phase_dicts = [{'phase_number': ph['phase_number'], 'title': ph['title'], 'instructions': ph['instructions'], 'target_deadline': ph['target_deadline'], 'status': ph.get('status', 'PENDING'), 'completed_at': ph.get('completed_at'), 'completion_log': ph.get('completion_log')} for ph in p]
        return build_canonical_payload(task_id=t['id'], title=t['title'], objective=t['objective'], total_days=t['total_days'], total_phases=t['total_phases'], created_at=t['created_at'], deadline=t['deadline'], status=t.get('status', 'ACTIVE'), completed_at=t.get('completed_at'), surrender_reason=t.get('surrender_reason'), phases=phase_dicts)

    def test_hmac_is_deterministic(self):
        payload = self._build_payload()
        h1 = compute_hmac(payload, self.secret_file)
        h2 = compute_hmac(payload, self.secret_file)
        self.assertEqual(h1, h2)

    def test_verify_correct(self):
        payload = self._build_payload()
        h = compute_hmac(payload, self.secret_file)
        self.assertTrue(verify_hmac(payload, h, self.secret_file))

    def test_verify_wrong_hash(self):
        payload = self._build_payload()
        self.assertFalse(verify_hmac(payload, 'deadbeef' * 8, self.secret_file))

    def test_title_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        task = _sample_task()
        task['title'] = 'Hacked Title'
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_objective_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        task = _sample_task()
        task['objective'] = 'Hacked objective'
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_deadline_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        task = _sample_task()
        task['deadline'] = '2099-01-01 00:00:00'
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_phase_title_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        phases = _sample_phases()
        phases[0]['title'] = 'Hacked Phase Title'
        payload_tampered = self._build_payload(phases=phases)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_phase_instructions_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        phases = _sample_phases()
        phases[0]['instructions'] = 'Hacked instructions — easier than before'
        payload_tampered = self._build_payload(phases=phases)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_phase_deadline_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        phases = _sample_phases()
        phases[0]['target_deadline'] = '2099-01-01 00:00:00'
        payload_tampered = self._build_payload(phases=phases)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_total_days_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        task = _sample_task()
        task['total_days'] = 999
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_task_status_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        task = _sample_task()
        task['status'] = 'COMPLETED'
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_task_completed_at_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        task = _sample_task()
        task['completed_at'] = '2025-01-11 12:00:00'
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_surrender_reason_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        task = _sample_task()
        task['surrender_reason'] = 'Too hard'
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_phase_status_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        phases = _sample_phases()
        phases[0]['status'] = 'COMPLETED'
        payload_tampered = self._build_payload(phases=phases)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_phase_completed_at_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        phases = _sample_phases()
        phases[0]['completed_at'] = '2025-01-06 12:00:00'
        payload_tampered = self._build_payload(phases=phases)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_phase_completion_log_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)
        phases = _sample_phases()
        phases[0]['completion_log'] = 'Did it'
        payload_tampered = self._build_payload(phases=phases)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

class TestSecretMissing(unittest.TestCase):

    def test_raises_when_secret_missing(self):
        nonexistent = pathlib.Path(tempfile.mktemp(suffix='.secret'))
        payload = b'some payload'
        with self.assertRaises(IntegrityKeyMissingError):
            compute_hmac(payload, nonexistent)

    def test_verify_raises_when_secret_missing(self):
        nonexistent = pathlib.Path(tempfile.mktemp(suffix='.secret'))
        payload = b'some payload'
        with self.assertRaises(IntegrityKeyMissingError):
            verify_hmac(payload, 'abc', nonexistent)

    def test_generate_secret_does_not_overwrite(self):
        secret_file = pathlib.Path(tempfile.mktemp(suffix='.secret'))
        generate_secret(secret_file)
        original = secret_file.read_bytes()
        generate_secret(secret_file)
        self.assertEqual(original, secret_file.read_bytes())
        secret_file.unlink(missing_ok=True)

class TestIntegrationHMAC(unittest.TestCase):
    def setUp(self):
        from app import db
        self.db_path = pathlib.Path(tempfile.mktemp(suffix='.db'))
        self.secret_path = pathlib.Path(tempfile.mktemp(suffix='.secret'))
        db.create_schema(self.db_path)
        _make_secret(self.secret_path)

        # Insert a valid task and phase
        self.task_id = db.insert_task(
            title="Test", objective="Obj", total_days=10, total_phases=1,
            deadline="2025-01-10 00:00:00", created_at="2025-01-01 00:00:00",
            integrity_hash="dummy", path=self.db_path
        )
        db.insert_phases(self.task_id, [{"phase_number": 1, "title": "P1", "instructions": "I1", "target_deadline": "2025-01-05 00:00:00"}], path=self.db_path)
        
        # Calculate real HMAC
        import sqlite3
        conn = sqlite3.connect(str(self.db_path), isolation_level=None)
        conn.row_factory = sqlite3.Row
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (self.task_id,)).fetchone()
        phases = conn.execute("SELECT * FROM task_phases WHERE task_id = ?", (self.task_id,)).fetchall()
        
        from app.integrity import recompute_hmac
        real_hash = recompute_hmac(task, phases, None, None, secret_path=self.secret_path)
        conn.execute("UPDATE tasks SET integrity_hash = ? WHERE id = ?", (real_hash, self.task_id))
        conn.close()

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)
        self.secret_path.unlink(missing_ok=True)

    def _tamper_and_check(self, query, params):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path), isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(query, params)
        
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (self.task_id,)).fetchone()
        phases = conn.execute("SELECT * FROM task_phases WHERE task_id = ?", (self.task_id,)).fetchall()
        conn.close()
        
        status = check_contract_integrity(task, phases, secret_path=self.secret_path)
        self.assertEqual(status, IntegrityStatus.TAMPERED)

    def test_direct_sql_status_mutation(self):
        self._tamper_and_check("UPDATE tasks SET status = 'COMPLETED' WHERE id = ?", (self.task_id,))

    def test_direct_sql_completed_at_mutation(self):
        self._tamper_and_check("UPDATE tasks SET completed_at = '2025-01-10 00:00:00' WHERE id = ?", (self.task_id,))

    def test_direct_sql_completion_log_mutation(self):
        self._tamper_and_check("UPDATE task_phases SET completion_log = 'Tampered' WHERE task_id = ? AND phase_number = 1", (self.task_id,))

    def test_direct_sql_surrender_reason_mutation(self):
        self._tamper_and_check("UPDATE tasks SET surrender_reason = 'Tampered' WHERE id = ?", (self.task_id,))
        
    def test_direct_sql_phase_status_mutation(self):
        self._tamper_and_check("UPDATE task_phases SET status = 'COMPLETED' WHERE task_id = ? AND phase_number = 1", (self.task_id,))



if __name__ == '__main__':
    unittest.main(verbosity=2)
