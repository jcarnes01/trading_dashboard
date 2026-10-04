"""Macro analytics engine: Quote deltas, intermarket ratios, and breadth trend."""
from typing import Dict, Optional
import pandas as pd

from config.settings import AppSettings, default_settings
from core.models.market import MacroSnapshot, Quote


class MacroAnalyticsEngine:
    """Computes daily price changes, ratio slopes, and consolidated macro snapshots."""

    def __init__(self, settings: AppSettings = default_settings):
        self.settings = settings

    def compute_quote(self, symbol: str, history_df: Optional[pd.DataFrame]) -> Quote:
        """Extract latest quote and 1-day percentage change from price history."""
        if history_df is None or history_df.empty:
            return Quote(symbol=symbol, last_price=0.0, previous_close=0.0, change_pct=0.0, is_valid=False)

        # Drop NaN closes
        cleaned = history_df.dropna(subset=["Close"]) if "Close" in history_df.columns else pd.DataFrame()
        if len(cleaned) < 2:
            last = float(cleaned["Close"].iloc[-1]) if len(cleaned) == 1 else 0.0
            return Quote(symbol=symbol, last_price=last, previous_close=last, change_pct=0.0, is_valid=(len(cleaned) == 1))

        curr_val = float(cleaned["Close"].iloc[-1])
        prev_val = float(cleaned["Close"].iloc[-2])

        if prev_val == 0:
            change_pct = 0.0
        else:
            change_pct = ((curr_val - prev_val) / prev_val) * 100.0

        return Quote(
            symbol=symbol,
            last_price=curr_val,
            previous_close=prev_val,
            change_pct=change_pct,
            is_valid=True,
        )

    def compute_breadth_slope(
        self,
        rsp_df: Optional[pd.DataFrame],
        spy_df: Optional[pd.DataFrame],
    ) -> float:
        """Compute the 5-day slope of the RSP / SPY equal-weight to cap-weight ratio.

        A rising slope indicates broadening market participation (bullish breadth).
        A declining slope indicates narrow or deteriorating participation.
        """
        if rsp_df is None or spy_df is None or rsp_df.empty or spy_df.empty:
            return 0.0

        if "Close" not in rsp_df.columns or "Close" not in spy_df.columns:
            return 0.0

        rsp_close = rsp_df["Close"].dropna()
        spy_close = spy_df["Close"].dropna()

        # Align on common trading days
        common_idx = rsp_close.index.intersection(spy_close.index)
        if len(common_idx) < 2:
            return 0.0

        ratio_series = rsp_close.loc[common_idx] / spy_close.loc[common_idx]
        first_val = ratio_series.iloc[0]
        last_val = ratio_series.iloc[-1]

        if first_val == 0:
            return 0.0

        return float((last_val - first_val) / first_val)

    def compute_macro_snapshot(self, history_map: Dict[str, pd.DataFrame]) -> MacroSnapshot:
        """Generate complete MacroSnapshot from a map of symbol -> history DataFrame."""
        quotes: Dict[str, Quote] = {}
        for symbol_key, df in history_map.items():
            quotes[symbol_key] = self.compute_quote(symbol_key, df)

        rsp_df = history_map.get("RSP")
        spy_df = history_map.get("SPY")
        breadth_slope = self.compute_breadth_slope(rsp_df, spy_df)

        return MacroSnapshot(quotes=quotes, breadth_ratio_5d_slope=breadth_slope)
