"""Unit tests for CalendarAnalyticsEngine."""
from datetime import date
import pytest

from core.analytics.calendar_engine import CalendarAnalyticsEngine


def test_third_friday_calculation():
    engine = CalendarAnalyticsEngine()

    # October 2026: Oct 1 is Thursday -> 1st Friday is Oct 2 -> 3rd Friday is Oct 16
    assert engine.get_third_friday(2026, 10) == date(2026, 10, 16)

    # December 2026: Dec 1 is Tuesday -> 1st Friday is Dec 4 -> 3rd Friday is Dec 18
    assert engine.get_third_friday(2026, 12) == date(2026, 12, 18)

    # January 2026: Jan 1 is Thursday -> 1st Friday is Jan 2 -> 3rd Friday is Jan 16
    assert engine.get_third_friday(2026, 1) == date(2026, 1, 16)


def test_quad_witching_flag():
    engine = CalendarAnalyticsEngine()
    assert engine.is_quad_witching(3) is True   # March
    assert engine.is_quad_witching(6) is True   # June
    assert engine.is_quad_witching(9) is True   # September
    assert engine.is_quad_witching(12) is True  # December
    assert engine.is_quad_witching(10) is False # October
    assert engine.is_quad_witching(11) is False # November


def test_get_upcoming_opex_events():
    engine = CalendarAnalyticsEngine()
    # Reference date: Oct 4, 2026
    ref = date(2026, 10, 4)
    events = engine.get_upcoming_opex_events(reference_date=ref, count=3)

    assert len(events) == 3

    # Event 1: October 2026 Monthly OpEx (Oct 16, 2026)
    assert events[0].event_date == date(2026, 10, 16)
    assert events[0].days_remaining == 12
    assert events[0].is_quad_witching is False
    assert "October" in events[0].title

    # Event 2: November 2026 Monthly OpEx (Nov 20, 2026)
    assert events[1].event_date == date(2026, 11, 20)
    assert events[1].is_quad_witching is False

    # Event 3: December 2026 Quad Witching (Dec 18, 2026)
    assert events[2].event_date == date(2026, 12, 18)
    assert events[2].is_quad_witching is True
    assert "Quad Witching" in events[2].title
