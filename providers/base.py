"""Abstract interface defining the market data provider contract."""
from abc import ABC, abstractmethod
from typing import List, Tuple
import pandas as pd


class BaseDataProvider(ABC):
    """Abstract interface defining required market data methods."""

    @abstractmethod
    def get_history(self, symbol: str, period: str = "7d", interval: str = "1d") -> pd.DataFrame:
        """Fetch historical price series for a symbol.

        Must return a DataFrame containing at minimum a 'Close' column indexed by date/time.
        """
        pass

    @abstractmethod
    def get_options_expirations(self, symbol: str) -> List[str]:
        """Fetch list of available option expiration date strings (YYYY-MM-DD)."""
        pass

    @abstractmethod
    def get_option_chain(self, symbol: str, expiration: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch call and put option chains for a given symbol and expiration date.

        Must return a tuple (calls_df, puts_df) with standardized columns:
        ['strike', 'lastPrice', 'openInterest', 'impliedVolatility']
        """
        pass
