"""Unit tests for DashboardService application service."""
from datetime import datetime, timezone
import pandas as pd
import pytest

from core.models.options import OptionsStructure
from providers.mock_provider import MockDataProvider
from services.dashboard_service import DashboardPayload, DashboardService


def test_dashboard_service_normal_flow():
    mock_provider = MockDataProvider()
    service = DashboardService(provider=mock_provider)

    payload = service.get_dashboard_payload()

    assert isinstance(payload, DashboardPayload)
    assert payload.options_structure.is_fallback is False
    assert payload.options_structure.underlying_spot == 5050.0

    # Verify structural levels
    assert payload.options_structure.call_wall_oi == 5100.0  # Max call OI in mock
    assert payload.options_structure.put_wall_oi == 5000.0   # Max put OI in mock
    assert payload.options_structure.atm_straddle_price > 0.0

    # Verify macro
    assert payload.macro_snapshot.get_last_price("SPY") == 505.0
    assert payload.macro_snapshot.get_last_price("10Y") == 4.20

    # Verify bias signal
    assert payload.bias_signal.direction is not None
    assert isinstance(payload.refreshed_at_str, str)


def test_dashboard_service_spot_fallback_to_spy():
    # Empty SPX, but valid SPY (505.0)
    mock_provider = MockDataProvider()
    mock_provider.set_history("^SPX", pd.DataFrame())

    service = DashboardService(provider=mock_provider)
    structure = service.fetch_options_structure()

    # Should resolve spot from SPY * 10 = 5050.0 and flag fallback
    assert structure.underlying_spot == 5050.0
    assert structure.is_fallback is True


def test_dashboard_service_complete_fallback():
    # Provider returns empty for all queries
    class EmptyProvider(MockDataProvider):
        def get_history(self, symbol, period="7d"):
            return pd.DataFrame()

        def get_options_expirations(self, symbol):
            return []

        def get_option_chain(self, symbol, expiration):
            return pd.DataFrame(), pd.DataFrame()

    service = DashboardService(provider=EmptyProvider())
    payload = service.get_dashboard_payload()

    assert payload.options_structure.is_fallback is True
    assert payload.options_structure.underlying_spot == 5000.0
    assert payload.options_structure.call_wall_oi == 5050.0
    assert payload.options_structure.put_wall_oi == 4950.0
