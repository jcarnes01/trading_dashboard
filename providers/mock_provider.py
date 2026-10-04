"""Mock data provider for offline testing and development."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

from providers.base import BaseDataProvider


class MockDataProvider(BaseDataProvider):
    """In-memory mock provider returning deterministic market and options data."""

    def __init__(
        self,
        custom_histories: Optional[Dict[str, pd.DataFrame]] = None,
        custom_chains: Optional[Tuple[pd.DataFrame, pd.DataFrame]] = None,
        expirations: Optional[List[str]] = None,
    ):
        self._histories: Dict[str, pd.DataFrame] = custom_histories or {}
        self._chains: Optional[Tuple[pd.DataFrame, pd.DataFrame]] = custom_chains
        self._expirations: List[str] = expirations or ["2026-10-05", "2026-10-06", "2026-10-09"]

        # If no histories were supplied, populate standard default fixture
        if not self._histories:
            self._init_default_histories()

        # If no custom chain supplied, populate standard chain fixture
        if self._chains is None:
            self._init_default_chain()

    def _init_default_histories(self) -> None:
        """Populate default 5-day market data."""
        dates = [datetime(2026, 10, 1) + timedelta(days=i) for i in range(5)]
        self._histories = {
            "^SPX": pd.DataFrame({"Close": [5000.0, 5010.0, 5020.0, 5035.0, 5050.0]}, index=dates),
            "SPY": pd.DataFrame({"Close": [500.0, 501.0, 502.0, 503.5, 505.0]}, index=dates),
            "QQQ": pd.DataFrame({"Close": [480.0, 482.0, 485.0, 488.0, 492.0]}, index=dates),
            "IWM": pd.DataFrame({"Close": [218.0, 219.0, 220.5, 222.0, 224.0]}, index=dates),
            "RSP": pd.DataFrame({"Close": [160.0, 161.0, 162.5, 164.0, 166.5]}, index=dates),
            "^VIX": pd.DataFrame({"Close": [16.5, 16.0, 15.8, 15.2, 14.5]}, index=dates),
            "^TNX": pd.DataFrame({"Close": [4.35, 4.32, 4.30, 4.25, 4.20]}, index=dates),
            "DX-Y.NYB": pd.DataFrame({"Close": [104.5, 104.2, 104.0, 103.8, 103.4]}, index=dates),
            "GC=F": pd.DataFrame({"Close": [2350.0, 2360.0, 2370.0, 2385.0, 2400.0]}, index=dates),
        }

    def _init_default_chain(self) -> None:
        """Populate default options chain for SPX (Spot 5050)."""
        strikes = [4900.0, 4950.0, 5000.0, 5050.0, 5100.0, 5150.0, 5200.0]
        calls = pd.DataFrame({
            "strike": strikes,
            "lastPrice": [160.0, 115.0, 72.0, 32.0, 11.0, 3.2, 0.8],
            "openInterest": [2000, 3500, 7000, 9500, 16000, 5000, 1200],
            "impliedVolatility": [0.18, 0.17, 0.16, 0.15, 0.14, 0.14, 0.15],
        })
        puts = pd.DataFrame({
            "strike": strikes,
            "lastPrice": [1.2, 3.5, 8.0, 28.0, 68.0, 112.0, 160.0],
            "openInterest": [6000, 12000, 22000, 8000, 3000, 1000, 400],
            "impliedVolatility": [0.22, 0.20, 0.18, 0.15, 0.15, 0.16, 0.17],
        })
        self._chains = (calls, puts)

    def get_history(self, symbol: str, period: str = "7d", interval: str = "1d") -> pd.DataFrame:
        """Return registered or empty history DataFrame."""
        return self._histories.get(symbol, pd.DataFrame()).copy()

    def get_options_expirations(self, symbol: str) -> List[str]:
        """Return mock expirations."""
        return list(self._expirations)

    def get_option_chain(self, symbol: str, expiration: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Return mock call and put chain for symbol."""
        if symbol == "QQQ":
            strikes = [475.0, 480.0, 485.0, 490.0, 495.0, 500.0]
            calls = pd.DataFrame({
                "strike": strikes,
                "lastPrice": [18.0, 14.0, 9.5, 5.2, 2.1, 0.8],
                "openInterest": [3000, 4500, 8000, 12000, 15000, 6000],
                "impliedVolatility": [0.20, 0.19, 0.18, 0.17, 0.17, 0.17],
            })
            puts = pd.DataFrame({
                "strike": strikes,
                "lastPrice": [0.9, 1.8, 3.5, 6.2, 10.5, 15.0],
                "openInterest": [5000, 9000, 18000, 7000, 3000, 1000],
                "impliedVolatility": [0.22, 0.21, 0.19, 0.18, 0.17, 0.17],
            })
            return calls, puts
        elif symbol == "IWM":
            strikes = [215.0, 220.0, 225.0, 230.0]
            calls = pd.DataFrame({
                "strike": strikes,
                "lastPrice": [10.0, 6.0, 2.5, 0.8],
                "openInterest": [2000, 5000, 9000, 3000],
                "impliedVolatility": [0.24, 0.22, 0.20, 0.20],
            })
            puts = pd.DataFrame({
                "strike": strikes,
                "lastPrice": [0.8, 2.1, 5.5, 9.0],
                "openInterest": [4000, 8000, 3000, 1000],
                "impliedVolatility": [0.25, 0.23, 0.21, 0.21],
            })
            return calls, puts

        if self._chains is None:
            return pd.DataFrame(), pd.DataFrame()
        calls, puts = self._chains
        return calls.copy(), puts.copy()

    def set_history(self, symbol: str, df: pd.DataFrame) -> None:
        """Allow callers to inject custom history."""
        self._histories[symbol] = df

    def set_chains(self, calls: pd.DataFrame, puts: pd.DataFrame) -> None:
        """Allow callers to inject custom option chains."""
        self._chains = (calls, puts)
