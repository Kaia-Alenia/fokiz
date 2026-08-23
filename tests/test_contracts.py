import sys
import os
import pathlib
import unittest
import tempfile
import secrets
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))
from app.contracts import build_contract, compute_calendar_deadline, validate_phase_days_sum, _first_contract_date, _deadline_exclusive
from app.errors import ValidationError
from app import db
MX = ZoneInfo('America/Mexico_City')
NY = ZoneInfo('America/New_York')
MDR = ZoneInfo('Europe/Madrid')

def _utc(y, mo, d, h=0, mi=0, s=0) -> datetime:
    return datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc)

def _local(y, mo, d, h=0, mi=0, s=0, tz=MX) -> datetime:
    return datetime(y, mo, d, h, mi, s, tzinfo=tz).astimezone(timezone.utc)

def _base_inputs(total_phases: int=2, total_days: int=10):
    return [{'title': f'Phase {i}', 'instructions': f'Do step {i}', 'days': total_days // total_phases} for i in range(1, total_phases + 1)]

class TestA_OneDayAt22h(unittest.TestCase):

    def setUp(self):
        self.created = _local(2026, 8, 21, 22, 0, 0, tz=MX)
        self.tz = MX

    def test_first_contract_date(self):
        first = _first_contract_date(self.created, self.tz)
        self.assertEqual(first.year, 2026)
        self.assertEqual(first.month, 8)
        self.assertEqual(first.day, 22)

    def test_deadline_exclusive_utc(self):
        dl = compute_calendar_deadline(self.created, 1, self.tz)
        expected = _local(2026, 8, 23, 0, 0, 0, tz=MX)
        self.assertEqual(dl, expected, f'Got {dl!r}, expected {expected!r}')

    def test_build_contract_deadline(self):
        contract = build_contract(title='Test task A', objective='Verify that the deadline is correct when created at 22h', total_days=1, total_phases=1, phase_inputs=[{'title': 'Single phase', 'instructions': 'Complete the task', 'days': 1}], created_at=self.created, user_timezone='America/Mexico_City')
        expected_utc_str = '2026-08-23 06:00:00'
        self.assertEqual(contract.deadline, expected_utc_str)
        self.assertEqual(contract.phases[0].target_deadline, expected_utc_str)

    def test_deadline_is_not_created_plus_24h(self):
        dl = compute_calendar_deadline(self.created, 1, self.tz)
        wrong_deadline = self.created + timedelta(hours=24)
        self.assertNotEqual(dl, wrong_deadline, 'BUG: deadline was computed as created_at + 24h instead of end of calendar day')

class TestB_OneDayAt0005(unittest.TestCase):

    def setUp(self):
        self.created = _local(2026, 8, 21, 0, 5, 0, tz=MX)
        self.tz = MX

    def test_first_contract_date(self):
        first = _first_contract_date(self.created, self.tz)
        self.assertEqual(first.day, 22)

    def test_deadline_exclusive(self):
        dl = compute_calendar_deadline(self.created, 1, self.tz)
        expected = _local(2026, 8, 23, 0, 0, 0, tz=MX)
        self.assertEqual(dl, expected)

    def test_build_contract_deadline(self):
        contract = build_contract(title='Test task B', objective='Verify deadline at 00:05 of day start', total_days=1, total_phases=1, phase_inputs=[{'title': 'Single phase', 'instructions': 'Complete the task', 'days': 1}], created_at=self.created, user_timezone='America/Mexico_City')
        expected_utc_str = '2026-08-23 06:00:00'
        self.assertEqual(contract.deadline, expected_utc_str)

class TestB2_ExactMidnight(unittest.TestCase):

    def setUp(self):
        self.created = _local(2026, 8, 21, 0, 0, 0, tz=MX)
        self.tz = MX

    def test_first_contract_date_is_same_day(self):
        first = _first_contract_date(self.created, self.tz)
        self.assertEqual(first.day, 21)

    def test_deadline_exclusive(self):
        dl = compute_calendar_deadline(self.created, 1, self.tz)
        expected = _local(2026, 8, 22, 0, 0, 0, tz=MX)
        self.assertEqual(dl, expected)

class TestC_ThreeDaysAt22h(unittest.TestCase):

    def setUp(self):
        self.created = _local(2026, 8, 21, 22, 0, 0, tz=MX)
        self.tz = MX

    def test_deadline_exclusive(self):
        dl = compute_calendar_deadline(self.created, 3, self.tz)
        expected = _local(2026, 8, 25, 0, 0, 0, tz=MX)
        self.assertEqual(dl, expected)

    def test_build_contract_phases(self):
        contract = build_contract(title='5-day project Test C', objective='Verify contractual dates for 5 days starting at 22h', total_days=5, total_phases=3, phase_inputs=[{'title': 'Phase 1', 'instructions': 'Do first part', 'days': 2}, {'title': 'Phase 2', 'instructions': 'Do second part', 'days': 1}, {'title': 'Phase 3', 'instructions': 'Do third part', 'days': 2}], created_at=self.created, user_timezone='America/Mexico_City')
        self.assertEqual(contract.phases[0].target_deadline, '2026-08-24 06:00:00')
        self.assertEqual(contract.phases[1].target_deadline, '2026-08-25 06:00:00')
        self.assertEqual(contract.phases[2].target_deadline, '2026-08-27 06:00:00')
        self.assertEqual(contract.deadline, '2026-08-27 06:00:00')

class TestD_TauIndependentOfEnvTimezone(unittest.TestCase):

    def test_tau_consistent_across_env_timezones(self):
        from app.math_engine import compute_tau
        t_start = _utc(2026, 8, 22, 6, 0, 0)
        t_dl = _utc(2026, 8, 23, 6, 0, 0)
        t_now = _utc(2026, 8, 22, 18, 0, 0)
        tau = compute_tau(t_now, t_start, t_dl)
        self.assertAlmostEqual(tau, 0.5, places=6)
        offset = timedelta(hours=5)
        tau2 = compute_tau(t_now + offset, t_start + offset, t_dl + offset)
        self.assertAlmostEqual(tau2, 0.5, places=6)

class TestE_TimezoneChangeDoesNotMoveDeadlines(unittest.TestCase):

    def setUp(self):
        self.created = _local(2026, 8, 21, 22, 0, 0, tz=MX)

    def test_original_deadline_unchanged_after_zone_switch(self):
        contract_mx = build_contract(title='MX zone task', objective='Verify that the deadline is absolute and immutable', total_days=1, total_phases=1, phase_inputs=[{'title': 'Phase', 'instructions': 'Do something', 'days': 1}], created_at=self.created, user_timezone='America/Mexico_City')
        original_deadline = contract_mx.deadline
        contract_ny = build_contract(title='MX zone task', objective='Verify that the deadline is absolute and immutable', total_days=1, total_phases=1, phase_inputs=[{'title': 'Phase', 'instructions': 'Do something', 'days': 1}], created_at=self.created, user_timezone='America/New_York')
        self.assertEqual(contract_mx.deadline, original_deadline, 'Original contract deadline mutated when building a new contract in different TZ')
        self.assertNotEqual(contract_mx.deadline, contract_ny.deadline, 'Expected different absolute deadlines for different timezones, but got the same')

class TestF_MidnightCrossing(unittest.TestCase):

    def test_before_midnight(self):
        before = _local(2026, 8, 21, 23, 59, 59, tz=MX)
        local_before = before.astimezone(MX)
        self.assertEqual(local_before.day, 21)

    def test_after_midnight(self):
        after = _local(2026, 8, 22, 0, 0, 1, tz=MX)
        local_after = after.astimezone(MX)
        self.assertEqual(local_after.day, 22)

    def test_first_contract_date_changes_at_midnight(self):
        before = _local(2026, 8, 22, 23, 59, 59, tz=MX)
        first_before = _first_contract_date(before, MX)
        self.assertEqual(first_before.day, 23)
        at_midnight = _local(2026, 8, 23, 0, 0, 0, tz=MX)
        first_at = _first_contract_date(at_midnight, MX)
        self.assertEqual(first_at.day, 23)

class TestG_TwoIANAZones(unittest.TestCase):

    def test_different_zones_different_deadlines(self):
        created_utc = _utc(2026, 8, 21, 22, 0, 0)
        dl_mx = compute_calendar_deadline(created_utc, 1, MX)
        dl_mdr = compute_calendar_deadline(created_utc, 1, MDR)
        self.assertNotEqual(dl_mx, dl_mdr, 'Two different timezones produced the same absolute deadline (unexpected)')
        expected_mx = _local(2026, 8, 23, 0, 0, 0, tz=MX)
        self.assertEqual(dl_mx, expected_mx)
        self.assertEqual(dl_mx.tzinfo, timezone.utc)
        self.assertEqual(dl_mdr.tzinfo, timezone.utc)

class TestH_PhaseSchedulingInvariant(unittest.TestCase):

    def setUp(self):
        tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        tmp_db.close()
        self.db_path = pathlib.Path(tmp_db.name)
        db.create_schema(self.db_path)
        tmp_secret = tempfile.NamedTemporaryFile(suffix='.secret', delete=False)
        tmp_secret.close()
        self.secret_path = pathlib.Path(tmp_secret.name)
        self.secret_path.write_bytes(secrets.token_bytes(32))
        self.t0_local = datetime(2025, 1, 1, 0, 0, 0, tzinfo=MX)
        self.t0_utc = self.t0_local.astimezone(timezone.utc)
        contract = build_contract(title='Scheduling test task', objective='Verify that phase deadlines do not shift', total_days=5, total_phases=2, phase_inputs=[{'title': 'Phase 1', 'instructions': 'Do A', 'days': 2}, {'title': 'Phase 2', 'instructions': 'Do B', 'days': 3}], created_at=self.t0_utc, user_timezone='America/Mexico_City')
        self.task_id = db.insert_task(title=contract.title, objective=contract.objective, total_days=contract.total_days, total_phases=contract.total_phases, deadline=contract.deadline, created_at=contract.created_at, integrity_hash='dummy_hash', path=self.db_path)
        phase_dicts = [{'phase_number': ph.phase_number, 'title': ph.title, 'instructions': ph.instructions, 'target_deadline': ph.target_deadline} for ph in contract.phases]
        db.insert_phases(self.task_id, phase_dicts, path=self.db_path)
        self.expected_phase_1_deadline = '2025-01-03 06:00:00'
        self.expected_phase_2_deadline = '2025-01-06 06:00:00'
        self.expected_task_deadline = '2025-01-06 06:00:00'

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()
        if self.secret_path.exists():
            self.secret_path.unlink()

    def test_initial_deadlines_correct(self):
        phases = db.get_phases(self.task_id, path=self.db_path)
        ph1 = next((p for p in phases if p['phase_number'] == 1))
        ph2 = next((p for p in phases if p['phase_number'] == 2))
        self.assertEqual(ph1['target_deadline'], self.expected_phase_1_deadline)
        self.assertEqual(ph2['target_deadline'], self.expected_phase_2_deadline)

    def test_late_completion_does_not_shift_next_phase_deadline(self):
        phases_before = db.get_phases(self.task_id, path=self.db_path)
        phase_2_before = next((p for p in phases_before if p['phase_number'] == 2))
        deadline_before = phase_2_before['target_deadline']
        self.assertEqual(deadline_before, self.expected_phase_2_deadline)
        late_completion_time = '2025-01-11 06:00:00'
        db.complete_phase(task_id=self.task_id, phase_number=1, log='Evidence log sufficiently long and related to the instructions.', completed_at=late_completion_time, path=self.db_path)
        phases_after = db.get_phases(self.task_id, path=self.db_path)
        phase_2_after = next((p for p in phases_after if p['phase_number'] == 2))
        deadline_after = phase_2_after['target_deadline']
        self.assertEqual(deadline_after, self.expected_phase_2_deadline, 'BUG: Phase 2 deadline moved after completing phase 1 late.')
        task_row = db.get_task(self.task_id, path=self.db_path)
        self.assertEqual(task_row['deadline'], self.expected_task_deadline, 'BUG: task.deadline shifted after late phase completion.')

class TestI_ContractValidation(unittest.TestCase):

    def test_valid_contract(self):
        contract = build_contract(title='Valid Project', objective='Complete this valid project properly', total_days=10, total_phases=2, phase_inputs=_base_inputs(2, 10), user_timezone='America/Mexico_City')
        self.assertEqual(contract.title, 'Valid Project')
        self.assertEqual(contract.total_phases, 2)
        self.assertEqual(len(contract.phases), 2)

    def test_title_too_short(self):
        with self.assertRaises(ValidationError):
            build_contract('ab', 'Objective long enough to pass', 10, 1, [{'title': 'P1', 'instructions': 'Do it', 'days': 10}])

    def test_title_too_long(self):
        with self.assertRaises(ValidationError):
            build_contract('A' * 81, 'Objective long enough to pass', 10, 1, [{'title': 'P1', 'instructions': 'Do it', 'days': 10}])

    def test_objective_too_short(self):
        with self.assertRaises(ValidationError):
            build_contract('Valid Title', 'Short', 10, 1, [{'title': 'P1', 'instructions': 'Do it', 'days': 10}])

    def test_days_must_be_positive(self):
        with self.assertRaises(ValidationError):
            build_contract('Valid Title', 'Valid objective long enough', 0, 1, [{'title': 'P1', 'instructions': 'Do it', 'days': 0}])

    def test_phases_must_sum_to_total_days(self):
        with self.assertRaises(ValidationError):
            build_contract('Valid Title', 'Valid objective long enough', 10, 2, [{'title': 'P1', 'instructions': 'Do step 1', 'days': 3}, {'title': 'P2', 'instructions': 'Do step 2', 'days': 8}])

    def test_max_phases_is_8(self):
        with self.assertRaises(ValidationError):
            build_contract('Valid Title', 'Valid objective long enough', 9, 9, [{'title': f'P{i}', 'instructions': f'Do {i}', 'days': 1} for i in range(1, 10)])

    def test_min_phases_is_1(self):
        contract = build_contract('Valid Title', 'Valid objective long enough', 5, 1, [{'title': 'Only Phase', 'instructions': 'Complete everything', 'days': 5}], user_timezone='America/Mexico_City')
        self.assertEqual(len(contract.phases), 1)

    def test_phase_count_mismatch(self):
        with self.assertRaises(ValidationError):
            build_contract('Valid Title', 'Valid objective long enough', 10, 2, [{'title': 'P1', 'instructions': 'Do it', 'days': 10}])

    def test_invalid_iana_timezone(self):
        with self.assertRaises(ValidationError):
            build_contract('Valid Title', 'Valid objective long enough', 5, 1, [{'title': 'Phase', 'instructions': 'Do something', 'days': 5}], user_timezone='GMT-6')

    def test_utc_offset_rejected(self):
        for bad_tz in ('UTC-6', 'GMT+5', 'UTC+0', '-0600'):
            with self.assertRaises(ValidationError, msg=f"Expected rejection of '{bad_tz}'"):
                build_contract('Valid Title', 'Valid objective long enough', 5, 1, [{'title': 'Phase', 'instructions': 'Do something', 'days': 5}], user_timezone=bad_tz)

class TestPhaseDaysSum(unittest.TestCase):

    def test_exact_match(self):
        validate_phase_days_sum([3, 7], 10)

    def test_mismatch_raises(self):
        with self.assertRaises(ValidationError):
            validate_phase_days_sum([3, 8], 10)
if __name__ == '__main__':
    unittest.main(verbosity=2)
