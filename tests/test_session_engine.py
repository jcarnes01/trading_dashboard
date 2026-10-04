"""Unit tests for MarketSessionEngine."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from core.analytics.session_engine import MarketSessionEngine


def test_regular_market_hours():
    engine = MarketSessionEngine()
    # Monday Oct 5, 2026 at 10:30 AM ET
    ny_tz = ZoneInfo("America/New_York")
    dt = datetime(2026, 10, 5, 10, 30, tzinfo=ny_tz)

    session = engine.get_session(dt)
    assert session.status == "OPEN"
    assert session.is_regular_hours is True
    assert "Live Market Open" in session.badge_text
    assert "10:30 AM ET" in session.current_time_str


def test_pre_market_hours():
    engine = MarketSessionEngine()
    # Monday Oct 5, 2026 at 08:15 AM ET
    ny_tz = ZoneInfo("America/New_York")
    dt = datetime(2026, 10, 5, 8, 15, tzinfo=ny_tz)

    session = engine.get_session(dt)
    assert session.status == "PRE_MARKET"
    assert session.is_regular_hours is False
    assert "Pre-Market" in session.badge_text


def test_after_hours():
    engine = MarketSessionEngine()
    # Monday Oct 5, 2026 at 05:30 PM ET
    ny_tz = ZoneInfo("America/New_York")
    dt = datetime(2026, 10, 5, 17, 30, tzinfo=ny_tz)

    session = engine.get_session(dt)
    assert session.status == "AFTER_HOURS"
    assert session.is_regular_hours is False
    assert "After-Hours" in session.badge_text


def test_weekend_closed():
    engine = MarketSessionEngine()
    # Sunday Oct 4, 2026 at 02:00 PM ET
    ny_tz = ZoneInfo("America/New_York")
    dt = datetime(2026, 10, 4, 14, 0, tzinfo=ny_tz)

    session = engine.get_session(dt)
    assert session.status == "CLOSED"
    assert session.is_regular_hours is False
    assert "Weekend" in session.badge_text
