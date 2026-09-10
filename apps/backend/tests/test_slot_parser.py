from datetime import datetime

import pytest

from app.services.slot_parser import (
    build_proposed_at,
    extract_requested_slot,
)

NOW = datetime(2026, 9, 10, 12, 0)  # Thursday


@pytest.mark.parametrize(
    "text,intent,date,time",
    [
        ("Can we do it next Tuesday?", True, "2026-09-15", None),
        ("Can we do it next Tuesday at 3 pm?", True, "2026-09-15", "15:00:00"),
        ("Is Monday ok?", True, "2026-09-14", None),
        ("18th at 2:30pm works", True, "2026-09-18", "14:30:00"),
        ("I would like to reschedule to 15/09", True, "2026-09-15", None),
        ("What is the office address?", False, None, None),
        ("tomorrow 10 AM", False, "2026-09-11", "10:00:00"),
        ("3pm is fine with me thanks", True, None, "15:00:00"),
        ("can you move it to wednesday afternoon?", True, "2026-09-16", None),
        ("please postpone to nov 5th", True, "2026-11-05", None),
        ("Change to 2026-09-18 at 11:00", True, "2026-09-18", "11:00:00"),
        ("not available that day, 19 September works", True, "2026-09-19", None),
        ("", False, None, None),
        (None, False, None, None),
    ],
)
def test_extract_requested_slot(text, intent, date, time):
    parsed = extract_requested_slot(text, now=NOW)
    got_date = parsed["date"].isoformat() if parsed["date"] else None
    got_time = parsed["time"].isoformat() if parsed["time"] else None
    assert parsed["intent"] is intent
    assert got_date == date
    assert got_time == time


def test_build_proposed_at_date_only_midnight_local():
    parsed = {"date": None, "time": None}
    result = build_proposed_at(parsed)
    assert result is None

    from datetime import date

    parsed = {"date": date(2026, 9, 15), "time": None}
    as_utc = build_proposed_at(parsed)
    # Tuesday 15 Sep 00:00 Asia/Karachi == Monday 14 Sep 19:00 UTC
    assert as_utc.isoformat() == "2026-09-14T19:00:00+00:00"


def test_build_proposed_at_full_datetime():
    from datetime import date, time

    parsed = {"date": date(2026, 9, 15), "time": time(15, 0)}
    as_utc = build_proposed_at(parsed)
    assert as_utc.isoformat() == "2026-09-15T10:00:00+00:00"


def test_extract_requested_slot_karachi_wallclock():
    # "next Tuesday" computed from local (Asia/Karachi) day, independent of UTC.
    parsed = extract_requested_slot("next Tuesday", now=NOW)
    assert parsed["date"].isoformat() == "2026-09-15"