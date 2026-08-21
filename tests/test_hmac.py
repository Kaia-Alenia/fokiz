"""
tests/test_hmac.py — Tests for HMAC integrity verification.
Copyright (C) Alenia Studios — GNU GPL v3
"""

import sys
import pathlib
import tempfile
import unittest
import secrets as _secrets

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from app.integrity import (
    build_canonical_payload,
    compute_hmac,
    verify_hmac,
    IntegrityStatus,
    check_contract_integrity,
    generate_secret,
)
from app.errors import IntegrityKeyMissingError


def _make_secret(path: pathlib.Path) -> None:
    generate_secret(path)


def _sample_task():
    """Return a mock sqlite3.Row-like dict."""
    class FakeRow(dict):
        def __getitem__(self, key):
            return super().__getitem__(key)
    return FakeRow({
        "id": 1,
        "title": "Test Task",
        "objective": "Complete the test",
        "total_days": 10,
        "total_phases": 2,
        "created_at": "2025-01-01 00:00:00",
        "deadline": "2025-01-11 00:00:00",
        "integrity_hash": None,  # filled in test
    })


def _sample_phases():
    class FakeRow(dict):
        def __getitem__(self, key):
            return super().__getitem__(key)
    return [
        FakeRow({
            "phase_number": 1,
            "title": "Phase One",
            "instructions": "Do step one",
            "target_deadline": "2025-01-06 00:00:00",
        }),
        FakeRow({
            "phase_number": 2,
            "title": "Phase Two",
            "instructions": "Do step two",
            "target_deadline": "2025-01-11 00:00:00",
        }),
    ]


class TestHMACComputation(unittest.TestCase):
    def setUp(self):
        self.secret_file = pathlib.Path(tempfile.mktemp(suffix=".secret"))
        _make_secret(self.secret_file)

    def tearDown(self):
        self.secret_file.unlink(missing_ok=True)

    def _build_payload(self, task=None, phases=None):
        t = task or _sample_task()
        p = phases or _sample_phases()
        phase_dicts = [
            {
                "phase_number": ph["phase_number"],
                "title": ph["title"],
                "instructions": ph["instructions"],
                "target_deadline": ph["target_deadline"],
            }
            for ph in p
        ]
        return build_canonical_payload(
            task_id=t["id"],
            title=t["title"],
            objective=t["objective"],
            total_days=t["total_days"],
            total_phases=t["total_phases"],
            created_at=t["created_at"],
            deadline=t["deadline"],
            phases=phase_dicts,
        )

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
        self.assertFalse(verify_hmac(payload, "deadbeef" * 8, self.secret_file))

    def test_title_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)

        task = _sample_task()
        task["title"] = "Hacked Title"
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_objective_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)

        task = _sample_task()
        task["objective"] = "Hacked objective"
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_deadline_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)

        task = _sample_task()
        task["deadline"] = "2099-01-01 00:00:00"
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_phase_title_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)

        phases = _sample_phases()
        phases[0]["title"] = "Hacked Phase Title"
        payload_tampered = self._build_payload(phases=phases)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_phase_instructions_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)

        phases = _sample_phases()
        phases[0]["instructions"] = "Hacked instructions — easier than before"
        payload_tampered = self._build_payload(phases=phases)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_phase_deadline_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)

        phases = _sample_phases()
        phases[0]["target_deadline"] = "2099-01-01 00:00:00"
        payload_tampered = self._build_payload(phases=phases)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))

    def test_total_days_change_detected(self):
        payload_original = self._build_payload()
        h = compute_hmac(payload_original, self.secret_file)

        task = _sample_task()
        task["total_days"] = 999
        payload_tampered = self._build_payload(task=task)
        self.assertFalse(verify_hmac(payload_tampered, h, self.secret_file))


class TestSecretMissing(unittest.TestCase):
    def test_raises_when_secret_missing(self):
        nonexistent = pathlib.Path(tempfile.mktemp(suffix=".secret"))
        payload = b"some payload"
        with self.assertRaises(IntegrityKeyMissingError):
            compute_hmac(payload, nonexistent)

    def test_verify_raises_when_secret_missing(self):
        nonexistent = pathlib.Path(tempfile.mktemp(suffix=".secret"))
        payload = b"some payload"
        with self.assertRaises(IntegrityKeyMissingError):
            verify_hmac(payload, "abc", nonexistent)

    def test_generate_secret_does_not_overwrite(self):
        secret_file = pathlib.Path(tempfile.mktemp(suffix=".secret"))
        generate_secret(secret_file)
        original = secret_file.read_bytes()
        generate_secret(secret_file)  # should be no-op
        self.assertEqual(original, secret_file.read_bytes())
        secret_file.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
