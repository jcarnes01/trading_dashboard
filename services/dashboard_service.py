"""Application service orchestrating market data fetching, analytics, and payload assembly."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
import pandas as pd

from config.settings import AppSettings, default_settings
from core.analytics.macro_engine import MacroAnalyticsEngine
from core.analytics.options_engine import OptionsAnalyticsEngine
from core.analytics.scoring_engine import DirectionalScoringEngine
from core.analytics.calendar_engine import CalendarAnalyticsEngine
from core.models.market import MacroSnapshot
from core.models.options import OptionsStructure
from core.models.signal import BiasSignal
from core.models.calendar import OpexEvent
from providers.base import BaseDataProvider
from providers.yfinance_provider import YFinanceProvider


@dataclass(frozen=True)
class DashboardPayload:
    """Consolidated state payload rendered by the UI layer."""
    macro_snapshot: MacroSnapshot
    options_structure: OptionsStructure
    bias_signal: BiasSignal
    opex_events: list[OpexEvent] = field(default_factory=list)
    refreshed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def refreshed_at_str(self) -> str:
        """Formatted timestamp for presentation."""
        return self.refreshed_at.strftime("%Y-%m-%d %H:%M UTC")


class DashboardService:
    """Orchestrates market data providers and domain analytics engines."""

    def __init__(
        self,
        provider: Optional[BaseDataProvider] = None,
        options_engine: Optional[OptionsAnalyticsEngine] = None,
        macro_engine: Optional[MacroAnalyticsEngine] = None,
        scoring_engine: Optional[DirectionalScoringEngine] = None,
        calendar_engine: Optional[CalendarAnalyticsEngine] = None,
        settings: AppSettings = default_settings,
    ):
        self.settings = settings
        self.provider = provider if provider is not None else YFinanceProvider()
        self.options_engine = options_engine if options_engine is not None else OptionsAnalyticsEngine(settings)
        self.macro_engine = macro_engine if macro_engine is not None else MacroAnalyticsEngine(settings)
        self.scoring_engine = scoring_engine if scoring_engine is not None else DirectionalScoringEngine(settings)
        self.calendar_engine = calendar_engine if calendar_engine is not None else CalendarAnalyticsEngine()

    def fetch_macro_snapshot(self) -> MacroSnapshot:
        """Fetch price histories for all configured macro tickers and assemble MacroSnapshot."""
        history_map: Dict[str, pd.DataFrame] = {}

        for label, symbol in self.settings.macro_tickers.items():
            df = self.provider.get_history(symbol, period=self.settings.macro_history_period)
            history_map[label] = df

        return self.macro_engine.compute_macro_snapshot(history_map)

    def fetch_options_structure(self, macro_snapshot: Optional[MacroSnapshot] = None) -> OptionsStructure:
        """Fetch spot price and nearest option chain, computing complete OptionsStructure.

        Includes fallback from ^SPX index to scaled SPY (x10) if index data is delayed.
        """
        # 1. Determine Spot Price
        spot, is_spot_fallback = self._resolve_spot_price()

        # 2. Resolve Nearest Options Chain
        primary_symbol = self.settings.primary_options_symbol
        expirations = self.provider.get_options_expirations(primary_symbol)
        is_chain_fallback = False
        target_symbol = primary_symbol
        multiplier = 1.0

        if not expirations:
            # Fallback to SPY options scaled x10
            target_symbol = self.settings.fallback_options_symbol
            expirations = self.provider.get_options_expirations(target_symbol)
            multiplier = self.settings.fallback_index_multiplier
            is_chain_fallback = True

        if not expirations:
            # No options chains available at all -> generate mathematical fallback
            fallback_struct = self.options_engine._build_fallback_structure(spot, expiration_date="N/A")
            return fallback_struct

        nearest_exp = expirations[0]
        calls_df, puts_df = self.provider.get_option_chain(target_symbol, nearest_exp)

        # Scale fallback strikes and prices if using SPY proxy
        if multiplier != 1.0 and not calls_df.empty and not puts_df.empty:
            calls_df = calls_df.copy()
            puts_df = puts_df.copy()
            for col in ["strike", "lastPrice"]:
                if col in calls_df.columns:
                    calls_df[col] = calls_df[col] * multiplier
                if col in puts_df.columns:
                    puts_df[col] = puts_df[col] * multiplier

        # 3. Calculate DTE in days
        dte_days = self._calculate_dte_days(nearest_exp)

        # 4. Resolve Risk-Free Rate proxy from 10Y Yield
        risk_free_rate = self.settings.default_risk_free_rate
        if macro_snapshot is not None:
            ten_yr_quote = macro_snapshot.get_quote("10Y")
            if ten_yr_quote and ten_yr_quote.is_valid and ten_yr_quote.last_price > 0:
                risk_free_rate = ten_yr_quote.last_price / 100.0

        # 5. Compute Options Boundaries & GEX
        structure = self.options_engine.compute_structure(
            spot=spot,
            calls_df=calls_df,
            puts_df=puts_df,
            dte_days=dte_days,
            risk_free_rate=risk_free_rate,
            expiration_date=nearest_exp,
        )

        # Flag if fallback was used
        if is_spot_fallback or is_chain_fallback or structure.is_fallback:
            return OptionsStructure(
                underlying_spot=structure.underlying_spot,
                call_wall_oi=structure.call_wall_oi,
                put_wall_oi=structure.put_wall_oi,
                call_wall_gex=structure.call_wall_gex,
                put_wall_gex=structure.put_wall_gex,
                net_gex_total=structure.net_gex_total,
                zero_gamma_strike=structure.zero_gamma_strike,
                per_strike_gex=structure.per_strike_gex,
                atm_straddle_price=structure.atm_straddle_price,
                expected_move=structure.expected_move,
                expected_range_low=structure.expected_range_low,
                expected_range_high=structure.expected_range_high,
                is_fallback=True,
                expiration_date=structure.expiration_date,
            )

        return structure

    def get_dashboard_payload(self) -> DashboardPayload:
        """Generate complete, synchronized market dashboard payload."""
        macro_snapshot = self.fetch_macro_snapshot()
        bias_signal = self.scoring_engine.evaluate_bias(macro_snapshot)
        options_structure = self.fetch_options_structure(macro_snapshot=macro_snapshot)
        opex_events = self.calendar_engine.get_upcoming_opex_events(count=3)

        return DashboardPayload(
            macro_snapshot=macro_snapshot,
            options_structure=options_structure,
            bias_signal=bias_signal,
            opex_events=opex_events,
        )

    def _resolve_spot_price(self) -> tuple[float, bool]:
        """Fetch spot price for SPX, falling back to scaled SPY or default."""
        hist = self.provider.get_history(
            self.settings.primary_options_symbol,
            period=self.settings.options_history_period,
        )
        if not hist.empty and "Close" in hist.columns:
            cleaned = hist["Close"].dropna()
            if not cleaned.empty:
                return float(cleaned.iloc[-1]), False

        # Fallback to SPY scaled by 10x
        spy_hist = self.provider.get_history(
            self.settings.fallback_options_symbol,
            period=self.settings.options_history_period,
        )
        if not spy_hist.empty and "Close" in spy_hist.columns:
            cleaned = spy_hist["Close"].dropna()
            if not cleaned.empty:
                return float(cleaned.iloc[-1]) * self.settings.fallback_index_multiplier, True

        return 5000.0, True

    def _calculate_dte_days(self, exp_date_str: str) -> float:
        """Parse expiration date and return days to expiration."""
        try:
            exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            delta = (exp_date - today).days
            return max(float(delta), 0.5)
        except (ValueError, TypeError):
            return 1.0
