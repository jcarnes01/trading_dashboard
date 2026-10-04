"""Yahoo Finance data provider implementation."""
from typing import List, Tuple
import pandas as pd
import yfinance as yf

from providers.base import BaseDataProvider


class YFinanceProvider(BaseDataProvider):
    """Fetches market history and option chains via yfinance."""

    REQUIRED_OPTION_COLS = ["strike", "lastPrice", "openInterest", "impliedVolatility"]

    def get_history(self, symbol: str, period: str = "7d") -> pd.DataFrame:
        """Fetch historical price series for a symbol via yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            if df.empty or "Close" not in df.columns:
                return pd.DataFrame()

            # Ensure single-level columns and clean NaN closes
            df = df.dropna(subset=["Close"])
            return df
        except Exception:
            return pd.DataFrame()

    def get_options_expirations(self, symbol: str) -> List[str]:
        """Fetch available option expiration dates."""
        try:
            ticker = yf.Ticker(symbol)
            options = ticker.options
            return list(options) if options else []
        except Exception:
            return []

    def get_option_chain(self, symbol: str, expiration: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch standardized call and put DataFrames for a given expiration."""
        try:
            ticker = yf.Ticker(symbol)
            chain = ticker.option_chain(expiration)

            calls = self._standardize_option_df(chain.calls)
            puts = self._standardize_option_df(chain.puts)
            return calls, puts
        except Exception:
            return pd.DataFrame(), pd.DataFrame()

    def _standardize_option_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names, types, and fill missing attributes."""
        if df is None or df.empty:
            return pd.DataFrame(columns=self.REQUIRED_OPTION_COLS)

        cleaned = df.copy()
        for col in self.REQUIRED_OPTION_COLS:
            if col not in cleaned.columns:
                cleaned[col] = 0.0
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").fillna(0.0)

        return cleaned[self.REQUIRED_OPTION_COLS]
