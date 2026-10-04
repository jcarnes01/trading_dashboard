"""Shared pytest fixtures providing synthetic market and options data."""
from datetime import datetime, timedelta
import pandas as pd
import pytest


@pytest.fixture
def sample_options_chains():
    """Synthetic SPX options chain with clear structural boundaries.

    Spot: 5000.0
    ATM Strike: 5000.0
    Expected Call Wall OI: 5100.0 (OI: 15,000)
    Expected Put Wall OI: 4900.0 (OI: 20,000)
    ATM Call Price: 25.0, ATM Put Price: 20.0 -> Straddle: 45.0
    """
    strikes = [4800.0, 4850.0, 4900.0, 4950.0, 5000.0, 5050.0, 5100.0, 5150.0]

    calls_data = {
        "strike": strikes,
        "lastPrice": [205.0, 155.0, 110.0, 65.0, 25.0, 10.0, 3.5, 1.0],
        "openInterest": [1000, 2000, 3000, 5000, 8000, 9000, 15000, 4000],
        "impliedVolatility": [0.18, 0.17, 0.16, 0.15, 0.15, 0.14, 0.14, 0.14],
    }

    puts_data = {
        "strike": strikes,
        "lastPrice": [1.5, 4.0, 8.5, 12.0, 20.0, 60.0, 105.0, 152.0],
        "openInterest": [5000, 8000, 20000, 7000, 4000, 2000, 1000, 500],
        "impliedVolatility": [0.22, 0.20, 0.19, 0.17, 0.15, 0.15, 0.16, 0.17],
    }

    return pd.DataFrame(calls_data), pd.DataFrame(puts_data)


@pytest.fixture
def sample_macro_histories():
    """Synthetic 5-day price history for macro tickers."""
    dates = [datetime(2026, 10, 1) + timedelta(days=i) for i in range(5)]

    # Bullish scenario setup:
    # 1. RSP outperforming SPY (slope > 0)
    # 2. 10Y yields declining (curr < prev)
    # 3. DXY declining (curr < prev)
    # 4. VIX declining (curr < prev)
    histories = {
        "SPY": pd.DataFrame({"Close": [500.0, 501.0, 502.0, 503.0, 505.0]}, index=dates),
        "RSP": pd.DataFrame({"Close": [160.0, 161.0, 163.0, 165.0, 168.0]}, index=dates),
        "VIX": pd.DataFrame({"Close": [16.5, 16.0, 15.8, 15.5, 14.2]}, index=dates),
        "10Y": pd.DataFrame({"Close": [4.35, 4.30, 4.28, 4.25, 4.20]}, index=dates),
        "DXY": pd.DataFrame({"Close": [104.5, 104.2, 104.0, 103.8, 103.2]}, index=dates),
        "Gold": pd.DataFrame({"Close": [2350.0, 2360.0, 2370.0, 2380.0, 2400.0]}, index=dates),
    }
    return histories
