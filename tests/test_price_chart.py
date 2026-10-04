"""Unit tests for SPX Price Chart builder and service integration."""
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import pytest

from core.models.options import OptionsStructure
from providers.mock_provider import MockDataProvider
from services.dashboard_service import DashboardService
from ui.charts.price_chart import TIMEFRAME_CONFIG, build_spx_price_figure


@pytest.fixture
def sample_price_df():
    dates = [datetime(2026, 10, 1) + timedelta(hours=i) for i in range(10)]
    return pd.DataFrame({"Close": [5000.0 + i * 5 for i in range(10)]}, index=dates)


@pytest.fixture
def sample_structure():
    return OptionsStructure(
        underlying_spot=5050.0,
        call_wall_oi=5100.0,
        put_wall_oi=5000.0,
        call_wall_gex=5100.0,
        put_wall_gex=5000.0,
        net_gex_total=10e6,
        zero_gamma_strike=5025.0,
    )


def test_build_spx_price_figure_valid(sample_price_df, sample_structure):
    fig = build_spx_price_figure(sample_price_df, structure=sample_structure, timeframe="5D")

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].name == "SPX"
    # Verify horizontal layout shapes (Call wall, Put wall, Zero gamma)
    assert len(fig.layout.shapes) >= 3


def test_build_spx_price_figure_long_timeframe(sample_price_df, sample_structure):
    # On 1Y or YTD timeframes, short-term daily walls are omitted
    fig = build_spx_price_figure(sample_price_df, structure=sample_structure, timeframe="1Y")
    assert isinstance(fig, go.Figure)
    assert len(fig.layout.shapes) == 0


def test_build_spx_price_figure_empty():
    fig = build_spx_price_figure(pd.DataFrame(), timeframe="5D")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_service_fetch_underlying_history():
    provider = MockDataProvider()
    service = DashboardService(provider=provider)

    df, is_fallback = service.fetch_underlying_history("5d", "15m")
    assert not df.empty
    assert "Close" in df.columns
    assert is_fallback is False


def test_timeframe_config_completeness():
    for tf in ["1D", "5D", "1M", "YTD", "1Y"]:
        assert tf in TIMEFRAME_CONFIG
        assert "period" in TIMEFRAME_CONFIG[tf]
        assert "interval" in TIMEFRAME_CONFIG[tf]
