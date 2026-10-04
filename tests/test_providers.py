"""Contract and unit tests for Data Providers."""
import pandas as pd
import pytest

from providers.base import BaseDataProvider
from providers.mock_provider import MockDataProvider
from providers.yfinance_provider import YFinanceProvider


def test_base_provider_interface():
    # Verify both providers implement BaseDataProvider
    assert issubclass(MockDataProvider, BaseDataProvider)
    assert issubclass(YFinanceProvider, BaseDataProvider)


def test_mock_provider_histories():
    provider = MockDataProvider()

    df_spx = provider.get_history("^SPX")
    assert not df_spx.empty
    assert "Close" in df_spx.columns
    assert len(df_spx) == 5

    df_unknown = provider.get_history("NONEXISTENT")
    assert df_unknown.empty


def test_mock_provider_options():
    provider = MockDataProvider()

    expirations = provider.get_options_expirations("^SPX")
    assert len(expirations) > 0
    assert expirations[0] == "2026-10-05"

    calls, puts = provider.get_option_chain("^SPX", expirations[0])
    assert not calls.empty
    assert not puts.empty
    for col in ["strike", "lastPrice", "openInterest", "impliedVolatility"]:
        assert col in calls.columns
        assert col in puts.columns


def test_yfinance_provider_standardization():
    provider = YFinanceProvider()

    # Test standardization with missing columns & dirty data
    dirty_df = pd.DataFrame({
        "strike": ["5000", "invalid", 5100],
        "lastPrice": [25.0, None, 10.0],
        # openInterest missing
        "impliedVolatility": [0.15, 0.20, None],
    })

    cleaned = provider._standardize_option_df(dirty_df)

    assert list(cleaned.columns) == YFinanceProvider.REQUIRED_OPTION_COLS
    assert cleaned.loc[0, "strike"] == 5000.0
    assert cleaned.loc[1, "strike"] == 0.0  # Coerced invalid to 0.0
    assert cleaned.loc[0, "openInterest"] == 0.0  # Filled missing column


def test_yfinance_provider_empty_inputs():
    provider = YFinanceProvider()
    cleaned = provider._standardize_option_df(pd.DataFrame())
    assert list(cleaned.columns) == YFinanceProvider.REQUIRED_OPTION_COLS
    assert cleaned.empty
