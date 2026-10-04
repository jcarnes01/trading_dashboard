"""Unit tests for OptionsAnalyticsEngine."""
import math
import pandas as pd
import pytest

from core.analytics.options_engine import OptionsAnalyticsEngine
from core.models.options import OptionsStructure


def test_black_scholes_gamma_standard():
    engine = OptionsAnalyticsEngine()
    gamma = engine.calculate_bs_gamma(
        spot=5000.0,
        strike=5000.0,
        dte_years=30.0 / 365.25,
        iv=0.20,
        risk_free_rate=0.04,
        dividend_yield=0.015,
    )
    assert gamma > 0.0
    assert math.isfinite(gamma)
    # Check realistic magnitude: for SPX ~5000, 30DTE, IV 20%, gamma is ~0.001 - 0.002
    assert 0.0001 < gamma < 0.01


def test_black_scholes_gamma_edge_cases():
    engine = OptionsAnalyticsEngine()
    # Zero or negative IV
    assert engine.calculate_bs_gamma(5000.0, 5000.0, 0.1, 0.0) == 0.0
    assert engine.calculate_bs_gamma(5000.0, 5000.0, 0.1, -0.2) == 0.0
    # Zero or negative spot
    assert engine.calculate_bs_gamma(0.0, 5000.0, 0.1, 0.2) == 0.0
    assert engine.calculate_bs_gamma(-100.0, 5000.0, 0.1, 0.2) == 0.0
    # Zero or negative strike
    assert engine.calculate_bs_gamma(5000.0, 0.0, 0.1, 0.2) == 0.0
    # Very short DTE (0DTE intraday) should not raise ZeroDivisionError
    gamma_0dte = engine.calculate_bs_gamma(5000.0, 5000.0, 0.0, 0.2)
    assert gamma_0dte > 0.0


def test_compute_structure_walls_and_straddle(sample_options_chains):
    calls, puts = sample_options_chains
    engine = OptionsAnalyticsEngine()

    spot = 5000.0
    structure = engine.compute_structure(
        spot=spot,
        calls_df=calls,
        puts_df=puts,
        dte_days=1.0,
        expiration_date="2026-10-05",
    )

    assert isinstance(structure, OptionsStructure)
    assert structure.is_fallback is False
    assert structure.underlying_spot == 5000.0

    # Max OI Call Wall (strike 5100 with OI 15000)
    assert structure.call_wall_oi == 5100.0
    # Max OI Put Wall (strike 4900 with OI 20000)
    assert structure.put_wall_oi == 4900.0

    # ATM Straddle: Strike 5000 Call (25.0) + Put (20.0) = 45.0
    assert structure.atm_straddle_price == 45.0
    assert structure.expected_move == 45.0
    assert structure.expected_range_low == 4955.0
    assert structure.expected_range_high == 5045.0


def test_compute_structure_gex_metrics(sample_options_chains):
    calls, puts = sample_options_chains
    engine = OptionsAnalyticsEngine()

    structure = engine.compute_structure(
        spot=5000.0,
        calls_df=calls,
        puts_df=puts,
        dte_days=1.0,
    )

    # Check GEX records generated
    assert len(structure.per_strike_gex) > 0

    for strike_item in structure.per_strike_gex:
        # Call GEX is positive, Put GEX is negative (dealer convention)
        assert strike_item.call_gex >= 0.0
        assert strike_item.put_gex <= 0.0
        assert math.isclose(strike_item.net_gex, strike_item.call_gex + strike_item.put_gex, abs_tol=1e-5)

    # GEX Call wall should be a valid strike
    assert structure.call_wall_gex in calls["strike"].values
    assert structure.put_wall_gex in puts["strike"].values


def test_compute_structure_fallback_on_empty_data():
    engine = OptionsAnalyticsEngine()
    empty_df = pd.DataFrame()

    fallback = engine.compute_structure(
        spot=5000.0,
        calls_df=empty_df,
        puts_df=None,
    )

    assert fallback.is_fallback is True
    assert fallback.underlying_spot == 5000.0
    assert fallback.call_wall_oi == 5050.0  # +1%
    assert fallback.put_wall_oi == 4950.0  # -1%
    assert fallback.expected_move == 5000.0 * 0.008  # 40.0
    assert fallback.expected_range_low == 4960.0
    assert fallback.expected_range_high == 5040.0
