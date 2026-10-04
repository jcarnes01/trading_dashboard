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


def test_dashboard_service_multi_ticker_qqq_and_iwm():
    mock_provider = MockDataProvider()
    service = DashboardService(provider=mock_provider)

    # Test QQQ payload
    payload_qqq = service.get_dashboard_payload(symbol_key="QQQ")
    assert payload_qqq.active_symbol == "QQQ"
    assert payload_qqq.options_structure.symbol == "QQQ"
    assert payload_qqq.options_structure.underlying_spot == 492.0
    assert payload_qqq.options_structure.call_wall_oi == 495.0
    assert payload_qqq.market_session is not None

    # Test IWM payload
    payload_iwm = service.get_dashboard_payload(symbol_key="IWM")
    assert payload_iwm.active_symbol == "IWM"
    assert payload_iwm.options_structure.symbol == "IWM"
    assert payload_iwm.options_structure.underlying_spot == 224.0
    assert payload_iwm.options_structure.call_wall_oi == 225.0


def test_dashboard_service_zero_oi_chain_fallback_to_spy():
    """Verify that when primary chain (e.g. ^SPX) has 0 open interest, it falls back to SPY * 10."""
    mock_provider = MockDataProvider()
    # Simulate Yahoo Finance returning zero OI for ^SPX options
    zero_calls = pd.DataFrame([
        {"strike": 5000.0, "lastPrice": 25.0, "openInterest": 0.0, "impliedVolatility": 0.15},
        {"strike": 5100.0, "lastPrice": 10.0, "openInterest": 0.0, "impliedVolatility": 0.14},
    ])
    zero_puts = pd.DataFrame([
        {"strike": 5000.0, "lastPrice": 20.0, "openInterest": 0.0, "impliedVolatility": 0.15},
        {"strike": 4900.0, "lastPrice": 8.0, "openInterest": 0.0, "impliedVolatility": 0.16},
    ])
    mock_provider.set_option_chain("^SPX", "2026-10-16", zero_calls, zero_puts)

    service = DashboardService(provider=mock_provider)
    struct = service.fetch_options_structure(symbol_key="SPX")

    # Should have triggered fallback to SPY options (scaled by 10)
    assert struct.is_fallback is True
    assert struct.call_wall_oi == 5100.0  # From SPY strike 510.0 * 10
    assert struct.put_wall_oi == 5000.0   # From SPY strike 500.0 * 10
    assert struct.net_gex_total != 0.0    # GEX is successfully calculated
    assert len(struct.per_strike_gex) > 0

