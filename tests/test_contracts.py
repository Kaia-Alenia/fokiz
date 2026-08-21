"""
tests/test_contracts.py — Contract construction and validation tests.
Copyright (C) Alenia Studios — GNU GPL v3
"""

import sys
import pathlib
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from app.contracts import build_contract, validate_phase_days_sum
from app.errors import ValidationError
from app import db
import tempfile
import secrets
import os


def _base_inputs(total_phases: int = 2, total_days: int = 10):
    return [
        {"title": f"Phase {i}", "instructions": f"Do step {i}", "days": total_days // total_phases}
        for i in range(1, total_phases + 1)
    ]


class TestContractValidation(unittest.TestCase):
    def test_valid_contract(self):
        contract = build_contract(
            title="Valid Project",
            objective="Complete this valid project properly",
            total_days=10,
            total_phases=2,
            phase_inputs=_base_inputs(2, 10),
        )
        self.assertEqual(contract.title, "Valid Project")
        self.assertEqual(contract.total_phases, 2)
        self.assertEqual(len(contract.phases), 2)

    def test_title_too_short(self):
        with self.assertRaises(ValidationError):
            build_contract("ab", "Objective long enough to pass", 10, 1,
                           [{"title": "P1", "instructions": "Do it", "days": 10}])

    def test_title_too_long(self):
        with self.assertRaises(ValidationError):
            build_contract("A" * 81, "Objective long enough to pass", 10, 1,
                           [{"title": "P1", "instructions": "Do it", "days": 10}])

    def test_objective_too_short(self):
        with self.assertRaises(ValidationError):
            build_contract("Valid Title", "Short", 10, 1,
                           [{"title": "P1", "instructions": "Do it", "days": 10}])

    def test_days_must_be_positive(self):
        with self.assertRaises(ValidationError):
            build_contract("Valid Title", "Valid objective long enough", 0, 1,
                           [{"title": "P1", "instructions": "Do it", "days": 0}])

    def test_phases_must_sum_to_total_days(self):
        with self.assertRaises(ValidationError):
            build_contract(
                "Valid Title", "Valid objective long enough", 10, 2,
                [
                    {"title": "P1", "instructions": "Do step 1", "days": 3},
                    {"title": "P2", "instructions": "Do step 2", "days": 8},  # 3+8=11 ≠ 10
                ],
            )

    def test_phase_deadlines_are_fixed(self):
        """Phase deadlines must not shift based on when previous phases were completed."""
        t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        contract = build_contract(
            title="Fixed Deadline Test",
            objective="Test that deadlines are fixed from T0",
            total_days=10,
            total_phases=2,
            phase_inputs=[
                {"title": "Phase 1", "instructions": "Do first half", "days": 5},
                {"title": "Phase 2", "instructions": "Do second half", "days": 5},
            ],
            created_at=t0,
        )
        self.assertEqual(contract.phases[0].target_deadline, "2025-01-06 00:00:00")
        self.assertEqual(contract.phases[1].target_deadline, "2025-01-11 00:00:00")
        self.assertEqual(contract.deadline, "2025-01-11 00:00:00")

    def test_max_phases_is_8(self):
        with self.assertRaises(ValidationError):
            build_contract(
                "Valid Title", "Valid objective long enough", 9, 9,
                [{"title": f"P{i}", "instructions": f"Do {i}", "days": 1} for i in range(1, 10)],
            )

    def test_min_phases_is_1(self):
        contract = build_contract(
            "Valid Title", "Valid objective long enough", 5, 1,
            [{"title": "Only Phase", "instructions": "Complete everything", "days": 5}],
        )
        self.assertEqual(len(contract.phases), 1)

    def test_phase_count_mismatch(self):
        with self.assertRaises(ValidationError):
            build_contract(
                "Valid Title", "Valid objective long enough", 10, 2,
                [{"title": "P1", "instructions": "Do it", "days": 10}],  # only 1 phase for 2
            )


class TestPhaseDaysSum(unittest.TestCase):
    def test_exact_match(self):
        validate_phase_days_sum([3, 7], 10)  # Should not raise

    def test_mismatch_raises(self):
        with self.assertRaises(ValidationError):
            validate_phase_days_sum([3, 8], 10)


class TestPhaseSchedulingInvariant(unittest.TestCase):
    """
    Criterio §31.8: terminar tarde una fase no debe mover la deadline
    contractual de la siguiente fase. Las ventanas temporales son fijas
    desde la creación (spec §13.2), independientes de cuándo se
    complete cada fase en la práctica.
    """

    def setUp(self):
        tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp_db.close()
        self.db_path = pathlib.Path(tmp_db.name)
        db.create_schema(self.db_path)
        
        tmp_secret = tempfile.NamedTemporaryFile(suffix=".secret", delete=False)
        tmp_secret.close()
        self.secret_path = pathlib.Path(tmp_secret.name)
        self.secret_path.write_bytes(secrets.token_bytes(32))

        self.t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        # 1. Crear el contrato lógico
        contract = build_contract(
            title="Tarea de prueba de scheduling",
            objective="Verificar que las deadlines de fase no se desplazan",
            total_days=5,
            total_phases=2,
            phase_inputs=[
                {"title": "Fase 1", "instructions": "Hacer A", "days": 2},
                {"title": "Fase 2", "instructions": "Hacer B", "days": 3},
            ],
            created_at=self.t0,
        )
        
        # 2. Persistir en DB como hace commands.py
        integrity_hash = "dummy_hash"
        
        self.task_id = db.insert_task(
            title=contract.title,
            objective=contract.objective,
            total_days=contract.total_days,
            total_phases=contract.total_phases,
            deadline=contract.deadline,
            created_at=contract.created_at,
            integrity_hash=integrity_hash,
            path=self.db_path
        )
        
        phase_dicts = [
            {
                "phase_number": ph.phase_number,
                "title": ph.title,
                "instructions": ph.instructions,
                "target_deadline": ph.target_deadline
            }
            for ph in contract.phases
        ]
        db.insert_phases(self.task_id, phase_dicts, path=self.db_path)
        
        # Deadline esperada de fase 2, calculada SOLO a partir de T0
        # T0 (2025-01-01) + 2 días (Fase 1) + 3 días (Fase 2) = 2025-01-06
        self.expected_phase_2_deadline = "2025-01-06 00:00:00"
        self.expected_task_deadline = "2025-01-06 00:00:00"

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()
        if self.secret_path.exists():
            self.secret_path.unlink()

    def test_late_completion_does_not_shift_next_phase_deadline(self):
        # Deadline original de fase 2, leída ANTES de completar fase 1
        phases_before = db.get_phases(self.task_id, path=self.db_path)
        phase_2_before = next(p for p in phases_before if p["phase_number"] == 2)
        deadline_before = phase_2_before["target_deadline"]
        
        self.assertEqual(
            deadline_before,
            self.expected_phase_2_deadline,
            "La deadline de fase 2 al crear el contrato no coincide con T0 + D1 + D2 según spec §13.2"
        )
        
        # Completar fase 1 DELIBERADAMENTE TARDE:
        # T0 + 10 días = 2025-01-11 00:00:00
        late_completion_time = "2025-01-11 00:00:00"
        
        db.complete_phase(
            task_id=self.task_id,
            phase_number=1,
            log="Log de evidencia suficientemente largo y relacionado con las instrucciones.",
            completed_at=late_completion_time,
            path=self.db_path
        )
        
        # Releer fase 2 DESPUÉS de la finalización tardía de fase 1
        phases_after = db.get_phases(self.task_id, path=self.db_path)
        phase_2_after = next(p for p in phases_after if p["phase_number"] == 2)
        deadline_after = phase_2_after["target_deadline"]
        
        self.assertEqual(
            deadline_after,
            self.expected_phase_2_deadline,
            "BUG: la deadline de fase 2 se movió tras completar fase 1 tarde. Las ventanas temporales deben ser fijas."
        )
        
        # Además: la tarea completa (task.deadline) tampoco debe moverse
        task_row = db.get_task(self.task_id, path=self.db_path)
        self.assertEqual(
            task_row["deadline"],
            self.expected_task_deadline,
            "BUG: task.deadline se desplazó por una finalización tardía de fase."
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
