"""Unit tests for DirectionalScoringEngine."""
import pytest

from core.analytics.scoring_engine import DirectionalScoringEngine
from core.models.market import MacroSnapshot, Quote
from core.models.signal import BiasDirection, BiasSignal


def create_snapshot(slope: float, ten_yr_chg: float, dxy_chg: float, vix_chg: float) -> MacroSnapshot:
    """Helper to construct MacroSnapshot with specified deltas."""
    quotes = {
        "10Y": Quote(symbol="10Y", last_price=4.0, previous_close=4.0, change_pct=ten_yr_chg),
        "DXY": Quote(symbol="DXY", last_price=104.0, previous_close=104.0, change_pct=dxy_chg),
        "VIX": Quote(symbol="VIX", last_price=15.0, previous_close=15.0, change_pct=vix_chg),
        "SPY": Quote(symbol="SPY", last_price=500.0, previous_close=500.0, change_pct=1.0),
    }
    return MacroSnapshot(quotes=quotes, breadth_ratio_5d_slope=slope)


def test_bullish_bias_scoring():
    engine = DirectionalScoringEngine()

    # All 4 factors bullish:
    # 1. Slope > 0 (+1)
    # 2. 10Y < 0 (+1)
    # 3. DXY < 0 (+1)
    # 4. VIX < 0 (+1)
    # Total = +4
    snapshot = create_snapshot(slope=0.02, ten_yr_chg=-1.5, dxy_chg=-0.4, vix_chg=-5.0)
    signal = engine.evaluate_bias(snapshot)

    assert isinstance(signal, BiasSignal)
    assert signal.total_score == 4
    assert signal.direction == BiasDirection.BULLISH
    assert "BULLISH" in signal.playbook_summary
    assert "Bull Put Credit Spreads" in signal.suggested_strategies


def test_bearish_bias_scoring():
    engine = DirectionalScoringEngine()

    # All 4 factors bearish:
    # 1. Slope < 0 (-1)
    # 2. 10Y > 0 (-1)
    # 3. DXY > 0 (-1)
    # 4. VIX > 0 (-1)
    # Total = -4
    snapshot = create_snapshot(slope=-0.02, ten_yr_chg=2.0, dxy_chg=0.6, vix_chg=8.0)
    signal = engine.evaluate_bias(snapshot)

    assert signal.total_score == -4
    assert signal.direction == BiasDirection.BEARISH
    assert "BEARISH" in signal.playbook_summary
    assert "Bear Call Credit Spreads" in signal.suggested_strategies


def test_neutral_bias_scoring():
    engine = DirectionalScoringEngine()

    # Mixed factors:
    # Slope > 0 (+1), 10Y > 0 (-1), DXY < 0 (+1), VIX > 0 (-1) -> Score = 0
    snapshot = create_snapshot(slope=0.01, ten_yr_chg=1.0, dxy_chg=-0.2, vix_chg=2.0)
    signal = engine.evaluate_bias(snapshot)

    assert signal.total_score == 0
    assert signal.direction == BiasDirection.NEUTRAL
    assert "NEUTRAL" in signal.playbook_summary
    assert "Iron Condors" in signal.suggested_strategies


def test_threshold_boundary_cases():
    engine = DirectionalScoringEngine()

    # Score = +2 -> Just reaches BULLISH
    snap_bullish_edge = create_snapshot(slope=0.01, ten_yr_chg=-0.5, dxy_chg=0.5, vix_chg=0.5)
    # Factors: +1, +1, -1, -1 -> wait, that's 0.
    # Let's do: slope +1, 10Y +1, DXY 0, VIX 0 -> score = +2
    snap_bullish_edge = create_snapshot(slope=0.01, ten_yr_chg=-0.5, dxy_chg=0.0, vix_chg=0.0)
    signal = engine.evaluate_bias(snap_bullish_edge)
    assert signal.total_score == 2
    assert signal.direction == BiasDirection.BULLISH

    # Score = +1 -> Falls into NEUTRAL
    snap_neutral_edge = create_snapshot(slope=0.01, ten_yr_chg=0.0, dxy_chg=0.0, vix_chg=0.0)
    signal = engine.evaluate_bias(snap_neutral_edge)
    assert signal.total_score == 1
    assert signal.direction == BiasDirection.NEUTRAL
