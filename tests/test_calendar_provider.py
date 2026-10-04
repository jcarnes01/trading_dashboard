"""Unit tests for Economic Calendar Providers (Fallback and Finnhub)."""
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from core.models.calendar import CatalystCategory, VolatilityImpact
from providers.calendar_provider import (
    FallbackScheduleProvider,
    FinnhubCalendarProvider,
    MockCalendarProvider,
)


def test_fallback_schedule_provider():
    provider = FallbackScheduleProvider()
    from_dt = date(2026, 10, 1)
    to_dt = date(2026, 10, 31)

    events = provider.get_economic_events(from_dt, to_dt)
    assert len(events) > 0

    # Ensure all events are within requested range
    for ev in events:
        assert from_dt <= ev.event_date <= to_dt
        assert ev.category in list(CatalystCategory)
        assert ev.impact in list(VolatilityImpact)
        assert ev.source == "SCHEDULED"


def test_finnhub_provider_without_api_key():
    # When no API key is supplied, automatically falls back to curated schedule
    provider = FinnhubCalendarProvider(api_key="")
    from_dt = date(2026, 10, 1)
    to_dt = date(2026, 10, 31)

    events = provider.get_economic_events(from_dt, to_dt)
    assert len(events) > 0
    assert any("CPI" in e.title for e in events)


@patch("requests.get")
def test_finnhub_provider_with_api_key_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "economicCalendar": [
            {
                "event": "US CPI MoM",
                "time": "2026-10-14 12:30:00",
                "actual": 3.3,
                "estimate": 3.1,
                "prev": 3.0,
                "unit": "%",
            },
            {
                "event": "Low impact irrelevant event",
                "time": "2026-10-14 14:00:00",
                "actual": 1.0,
            },
        ]
    }
    mock_get.return_value = mock_response

    provider = FinnhubCalendarProvider(api_key="mock_finnhub_token")
    from_dt = date(2026, 10, 1)
    to_dt = date(2026, 10, 31)

    events = provider.get_economic_events(from_dt, to_dt)
    assert len(events) == 1  # Only high-impact CPI kept, low impact filtered
    assert events[0].title == "US CPI MoM"
    assert events[0].actual == 3.3
    assert events[0].estimate == 3.1
    assert events[0].source == "FINNHUB"


@patch("requests.get", side_effect=Exception("Network timeout"))
def test_finnhub_provider_network_failure_fallback(mock_get):
    # Network error triggers fallback schedule seamlessly
    provider = FinnhubCalendarProvider(api_key="mock_token")
    from_dt = date(2026, 10, 1)
    to_dt = date(2026, 10, 31)

    events = provider.get_economic_events(from_dt, to_dt)
    assert len(events) > 0
    assert events[0].source == "SCHEDULED"


def test_mock_calendar_provider():
    provider = MockCalendarProvider()
    events = provider.get_economic_events(date(2026, 10, 1), date(2026, 10, 15))
    assert len(events) == 1
    assert events[0].source == "MOCK"


def test_resolve_finnhub_api_key_from_env(monkeypatch):
    from providers.calendar_provider import resolve_finnhub_api_key

    monkeypatch.setenv("FINNHUB_API_KEY", "env_secret_key_123")
    assert resolve_finnhub_api_key() == "env_secret_key_123"


def test_resolve_finnhub_api_key_from_streamlit_secrets(monkeypatch):
    from unittest.mock import MagicMock
    import sys
    from providers.calendar_provider import resolve_finnhub_api_key

    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    mock_st = MagicMock()
    mock_st.secrets = {"FINNHUB_API_KEY": "streamlit_secret_abc"}
    monkeypatch.setitem(sys.modules, "streamlit", mock_st)

    assert resolve_finnhub_api_key() == "streamlit_secret_abc"


