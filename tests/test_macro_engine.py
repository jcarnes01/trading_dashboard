"""Unit tests for MacroAnalyticsEngine."""
import pandas as pd
import pytest

from core.analytics.macro_engine import MacroAnalyticsEngine
from core.models.market import MacroSnapshot, Quote


def test_compute_quote_valid():
    engine = MacroAnalyticsEngine()
    df = pd.DataFrame({"Close": [100.0, 105.0]})

    quote = engine.compute_quote("TEST", df)

    assert isinstance(quote, Quote)
    assert quote.symbol == "TEST"
    assert quote.last_price == 105.0
    assert quote.previous_close == 100.0
    assert quote.change_pct == 5.0
    assert quote.is_valid is True


def test_compute_quote_edge_cases():
    engine = MacroAnalyticsEngine()

    # Empty DataFrame
    q_empty = engine.compute_quote("EMPTY", pd.DataFrame())
    assert q_empty.is_valid is False
    assert q_empty.change_pct == 0.0

    # None DataFrame
    q_none = engine.compute_quote("NONE", None)
    assert q_none.is_valid is False

    # DataFrame with only 1 row
    q_single = engine.compute_quote("SINGLE", pd.DataFrame({"Close": [150.0]}))
    assert q_single.last_price == 150.0
    assert q_single.change_pct == 0.0

    # DataFrame with NaNs
    q_nan = engine.compute_quote("NAN", pd.DataFrame({"Close": [100.0, None, 102.0]}))
    assert q_nan.last_price == 102.0
    assert q_nan.previous_close == 100.0
    assert pytest.approx(q_nan.change_pct, 0.01) == 2.0


def test_compute_breadth_slope(sample_macro_histories):
    engine = MacroAnalyticsEngine()
    rsp_df = sample_macro_histories["RSP"]
    spy_df = sample_macro_histories["SPY"]

    slope = engine.compute_breadth_slope(rsp_df, spy_df)

    # In sample_macro_histories:
    # Day 0: RSP 160 / SPY 500 = 0.3200
    # Day 4: RSP 168 / SPY 505 = 0.33267
    # Slope = (0.33267 - 0.32) / 0.32 = +0.0396 > 0 (broadening)
    assert slope > 0.0
    assert pytest.approx(slope, 0.001) == ( (168.0 / 505.0) - (160.0 / 500.0) ) / (160.0 / 500.0)


def test_compute_breadth_slope_empty():
    engine = MacroAnalyticsEngine()
    assert engine.compute_breadth_slope(None, None) == 0.0
    assert engine.compute_breadth_slope(pd.DataFrame(), pd.DataFrame()) == 0.0


def test_compute_macro_snapshot(sample_macro_histories):
    engine = MacroAnalyticsEngine()
    snapshot = engine.compute_macro_snapshot(sample_macro_histories)

    assert isinstance(snapshot, MacroSnapshot)
    assert "SPY" in snapshot.quotes
    assert "VIX" in snapshot.quotes
    assert snapshot.breadth_ratio_5d_slope > 0.0

    # Test helper methods
    assert snapshot.get_change_pct("VIX") < 0.0  # VIX dropped from 15.5 to 14.2
    assert snapshot.get_last_price("Gold") == 2400.0
    assert snapshot.get_change_pct("UNKNOWN_TICKER") == 0.0
