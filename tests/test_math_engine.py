import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))
import unittest
from datetime import datetime, timedelta, timezone
from app.math_engine import compute_tau, compute_delta, compute_i_spam, compute_iu, classify_zone, classify_delta, cooldown_elapsed, Zone, DeltaStatus

def _dt(days_offset: float=0.0) -> datetime:
    base = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(days=days_offset)

class TestTau(unittest.TestCase):

    def test_tau_at_start(self):
        t_start = _dt(0)
        t_deadline = _dt(10)
        tau = compute_tau(t_start, t_start, t_deadline)
        self.assertAlmostEqual(tau, 0.0)

    def test_tau_at_midpoint(self):
        t_start = _dt(0)
        t_deadline = _dt(10)
        t_now = _dt(5)
        tau = compute_tau(t_now, t_start, t_deadline)
        self.assertAlmostEqual(tau, 0.5)

    def test_tau_at_deadline(self):
        t_start = _dt(0)
        t_deadline = _dt(10)
        tau = compute_tau(t_deadline, t_start, t_deadline)
        self.assertAlmostEqual(tau, 1.0)

    def test_tau_expired(self):
        t_start = _dt(0)
        t_deadline = _dt(10)
        t_now = _dt(20)
        tau = compute_tau(t_now, t_start, t_deadline)
        self.assertAlmostEqual(tau, 2.0)

    def test_tau_degenerate_window(self):
        t = _dt(0)
        tau = compute_tau(t, t, t)
        self.assertAlmostEqual(tau, 0.0)

class TestISpam(unittest.TestCase):
    CASES = [(0.0, 360.0), (0.25, 206.875), (0.4, 136.0), (0.5, 97.5), (0.75, 31.875), (0.9, 13.5), (0.95, 10.875), (1.0, 5.0), (1.5, 5.0), (2.0, 5.0)]

    def test_reference_values(self):
        for tau, expected in self.CASES:
            with self.subTest(tau=tau):
                result = compute_i_spam(tau)
                self.assertAlmostEqual(result, expected, places=2, msg=f'τ={tau}: expected {expected}, got {result}')

    def test_formula_monotone_decreasing_below_1(self):
        prev = compute_i_spam(0.0)
        for tau in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99]:
            curr = compute_i_spam(tau)
            self.assertLessEqual(curr, prev, msg=f'Not decreasing at τ={tau}')
            prev = curr

    def test_expired_is_five(self):
        for tau in (1.0, 1.5, 10.0):
            self.assertAlmostEqual(compute_i_spam(tau), 5.0, places=5)

class TestZoneClassification(unittest.TestCase):

    def test_green(self):
        self.assertEqual(classify_zone(0.0), Zone.GREEN)
        self.assertEqual(classify_zone(0.39), Zone.GREEN)

    def test_yellow(self):
        self.assertEqual(classify_zone(0.4), Zone.YELLOW)
        self.assertEqual(classify_zone(0.74), Zone.YELLOW)

    def test_orange(self):
        self.assertEqual(classify_zone(0.75), Zone.ORANGE)
        self.assertEqual(classify_zone(0.94), Zone.ORANGE)

    def test_red(self):
        self.assertEqual(classify_zone(0.95), Zone.RED)
        self.assertEqual(classify_zone(0.999), Zone.RED)

    def test_expired(self):
        self.assertEqual(classify_zone(1.0), Zone.EXPIRED)
        self.assertEqual(classify_zone(2.0), Zone.EXPIRED)

class TestDelta(unittest.TestCase):

    def test_ahead(self):
        t_created = _dt(0)
        t_deadline = _dt(10)
        t_now = _dt(1)
        delta = compute_delta(1, 2, t_now, t_created, t_deadline)
        self.assertGreater(delta, 0.2)
        self.assertEqual(classify_delta(delta), DeltaStatus.AHEAD)

    def test_behind(self):
        t_created = _dt(0)
        t_deadline = _dt(10)
        t_now = _dt(9)
        delta = compute_delta(0, 2, t_now, t_created, t_deadline)
        self.assertLess(delta, -0.1)
        self.assertEqual(classify_delta(delta), DeltaStatus.BEHIND)

    def test_on_track(self):
        t_created = _dt(0)
        t_deadline = _dt(10)
        t_now = _dt(5)
        delta = compute_delta(1, 2, t_now, t_created, t_deadline)
        self.assertAlmostEqual(delta, 0.0, places=5)
        self.assertEqual(classify_delta(delta), DeltaStatus.ON_TRACK)

class TestIU(unittest.TestCase):

    def test_basic(self):
        now = _dt(5)
        t_deadline = _dt(10)
        t_start = _dt(0)
        tau = compute_tau(now, t_start, t_deadline)
        iu = compute_iu(tau, now, t_deadline)
        hours_remaining = 5 * 24
        expected = tau / hours_remaining
        self.assertAlmostEqual(iu, expected, places=10)

    def test_expired_denom_clamped(self):
        now = _dt(15)
        t_deadline = _dt(10)
        t_start = _dt(0)
        tau = compute_tau(now, t_start, t_deadline)
        iu = compute_iu(tau, now, t_deadline)
        expected = tau / 0.1
        self.assertAlmostEqual(iu, expected, places=10)

class TestCooldown(unittest.TestCase):

    def test_no_previous(self):
        now = _dt(1)
        self.assertTrue(cooldown_elapsed(None, 60.0, now))

    def test_elapsed(self):
        last = '2025-01-01 00:00:00'
        now = _dt(1)
        self.assertTrue(cooldown_elapsed(last, 60.0, now))

    def test_not_elapsed(self):
        last = '2025-01-01 00:00:00'
        now = datetime(2025, 1, 1, 0, 30, 0, tzinfo=timezone.utc)
        self.assertFalse(cooldown_elapsed(last, 60.0, now))
if __name__ == '__main__':
    unittest.main(verbosity=2)
