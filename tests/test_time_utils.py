from datetime import datetime, timezone
from app.time_utils import _parse_utc, _utcnow_iso

def test_parse_utc():
    iso_str = '2026-08-22 12:00:00'
    dt = _parse_utc(iso_str)
    assert dt.year == 2026
    assert dt.month == 8
    assert dt.day == 22
    assert dt.hour == 12
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.tzinfo == timezone.utc

def test_utcnow_iso():
    iso_str = _utcnow_iso()
    dt = _parse_utc(iso_str)
    assert dt.tzinfo == timezone.utc
    assert dt.year >= 2024
