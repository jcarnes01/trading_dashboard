"""Application service orchestrating market data fetching, analytics, and payload assembly."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import pandas as pd

from config.settings import AppSettings, UnderlyingConfig, default_settings
from core.analytics.calendar_engine import CalendarAnalyticsEngine
from core.analytics.macro_engine import MacroAnalyticsEngine
from core.analytics.options_engine import OptionsAnalyticsEngine
from core.analytics.scoring_engine import DirectionalScoringEngine
from core.analytics.session_engine import MarketSessionEngine
from core.models.calendar import MarketCatalyst, OpexEvent
from core.models.market import MacroSnapshot
from core.models.options import OptionsStructure
from core.models.session import MarketSession
from core.models.signal import BiasSignal
from providers.base import BaseDataProvider
from providers.calendar_provider import BaseCalendarProvider, FinnhubCalendarProvider
from providers.yfinance_provider import YFinanceProvider


@dataclass(frozen=True)
class DashboardPayload:
    """Consolidated state payload rendered by the UI layer."""
    macro_snapshot: MacroSnapshot
    options_structure: OptionsStructure
    bias_signal: BiasSignal
    opex_events: list[OpexEvent] = field(default_factory=list)
    catalysts: list[MarketCatalyst] = field(default_factory=list)
    market_session: Optional[MarketSession] = None
    active_symbol: str = "SPX"
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
        calendar_provider: Optional[BaseCalendarProvider] = None,
        session_engine: Optional[MarketSessionEngine] = None,
        settings: AppSettings = default_settings,
    ):
        self.settings = settings
        self.provider = provider if provider is not None else YFinanceProvider()
        self.options_engine = options_engine if options_engine is not None else OptionsAnalyticsEngine(settings)
        self.macro_engine = macro_engine if macro_engine is not None else MacroAnalyticsEngine(settings)
        self.scoring_engine = scoring_engine if scoring_engine is not None else DirectionalScoringEngine(settings)
        self.calendar_engine = calendar_engine if calendar_engine is not None else CalendarAnalyticsEngine()
        self.calendar_provider = (
            calendar_provider
            if calendar_provider is not None
            else FinnhubCalendarProvider(api_key=settings.finnhub_api_key)
        )
        self.session_engine = session_engine if session_engine is not None else MarketSessionEngine()

    def fetch_macro_snapshot(self) -> MacroSnapshot:
        """Fetch price histories for all configured macro tickers and assemble MacroSnapshot."""
        history_map: Dict[str, pd.DataFrame] = {}

        for label, symbol in self.settings.macro_tickers.items():
            df = self.provider.get_history(symbol, period=self.settings.macro_history_period)
            history_map[label] = df

        return self.macro_engine.compute_macro_snapshot(history_map)

    def fetch_options_structure(
        self,
        symbol_key: str = "SPX",
        macro_snapshot: Optional[MacroSnapshot] = None,
    ) -> OptionsStructure:
        """Fetch spot price and nearest option chain for requested asset."""
        config = self._get_underlying_config(symbol_key)

        # 1. Determine Spot Price
        spot, is_spot_fallback = self._resolve_spot_price(config)

        # 2. Resolve Nearest Options Chain
        primary_symbol = config.primary_symbol
        expirations = self.provider.get_options_expirations(primary_symbol)
        is_chain_fallback = False
        target_symbol = primary_symbol
        multiplier = 1.0

        if not expirations:
            # Fallback to secondary options symbol
            target_symbol = config.fallback_symbol
            expirations = self.provider.get_options_expirations(target_symbol)
            multiplier = config.fallback_multiplier
            is_chain_fallback = True

        if not expirations:
            # No options chains available -> generate mathematical fallback
            fallback_struct = self.options_engine._build_fallback_structure(spot, expiration_date="N/A")
            return OptionsStructure(
                underlying_spot=fallback_struct.underlying_spot,
                call_wall_oi=fallback_struct.call_wall_oi,
                put_wall_oi=fallback_struct.put_wall_oi,
                call_wall_gex=fallback_struct.call_wall_gex,
                put_wall_gex=fallback_struct.put_wall_gex,
                net_gex_total=fallback_struct.net_gex_total,
                zero_gamma_strike=fallback_struct.zero_gamma_strike,
                per_strike_gex=fallback_struct.per_strike_gex,
                atm_straddle_price=fallback_struct.atm_straddle_price,
                expected_move=fallback_struct.expected_move,
                expected_range_low=fallback_struct.expected_range_low,
                expected_range_high=fallback_struct.expected_range_high,
                symbol=symbol_key,
                is_fallback=True,
                expiration_date="N/A",
            )

        nearest_exp = expirations[0]
        calls_df, puts_df = self.provider.get_option_chain(target_symbol, nearest_exp)

        # Check if resolved chain has zero total open interest
        # (CBOE index tickers like ^SPX on Yahoo Finance regularly report 0 open interest across all strikes)
        total_oi = (
            (calls_df["openInterest"].sum() if not calls_df.empty and "openInterest" in calls_df.columns else 0.0) +
            (puts_df["openInterest"].sum() if not puts_df.empty and "openInterest" in puts_df.columns else 0.0)
        )

        if total_oi <= 0 and config.fallback_symbol != target_symbol:
            fallback_exps = self.provider.get_options_expirations(config.fallback_symbol)
            if fallback_exps:
                fb_target = config.fallback_symbol
                fb_exp = fallback_exps[0]
                fb_calls, fb_puts = self.provider.get_option_chain(fb_target, fb_exp)
                fb_total_oi = (
                    (fb_calls["openInterest"].sum() if not fb_calls.empty and "openInterest" in fb_calls.columns else 0.0) +
                    (fb_puts["openInterest"].sum() if not fb_puts.empty and "openInterest" in fb_puts.columns else 0.0)
                )
                if fb_total_oi > 0:
                    target_symbol = fb_target
                    nearest_exp = fb_exp
                    calls_df = fb_calls
                    puts_df = fb_puts
                    multiplier = config.fallback_multiplier
                    is_chain_fallback = True

        # Scale fallback strikes and prices if using scaled proxy
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
            symbol=symbol_key,
            is_fallback=(is_spot_fallback or is_chain_fallback or structure.is_fallback),
            expiration_date=structure.expiration_date,
        )

    def get_dashboard_payload(self, symbol_key: str = "SPX") -> DashboardPayload:
        """Generate complete, synchronized market dashboard payload."""
        macro_snapshot = self.fetch_macro_snapshot()
        bias_signal = self.scoring_engine.evaluate_bias(macro_snapshot)
        options_structure = self.fetch_options_structure(symbol_key=symbol_key, macro_snapshot=macro_snapshot)
        today = datetime.now(timezone.utc).date()
        end_date = today + timedelta(days=90)
        econ_events = self.calendar_provider.get_economic_events(today, end_date)
        catalysts = self.calendar_engine.get_unified_catalysts(
            reference_date=today,
            economic_events=econ_events,
            count=6,
        )
        opex_events = self.calendar_engine.get_upcoming_opex_events(reference_date=today, count=3)
        market_session = self.session_engine.get_session()

        return DashboardPayload(
            macro_snapshot=macro_snapshot,
            options_structure=options_structure,
            bias_signal=bias_signal,
            opex_events=opex_events,
            catalysts=catalysts,
            market_session=market_session,
            active_symbol=symbol_key,
        )

    def fetch_underlying_history(
        self,
        symbol_key: str = "SPX",
        period: str = "5d",
        interval: str = "15m",
    ) -> tuple[pd.DataFrame, bool]:
        """Fetch historical price series across requested timeframe, with fallback."""
        config = self._get_underlying_config(symbol_key)
        hist = self.provider.get_history(
            config.primary_symbol,
            period=period,
            interval=interval,
        )
        if not hist.empty and "Close" in hist.columns:
            return hist, False

        # Fallback to secondary symbol
        fallback_hist = self.provider.get_history(
            config.fallback_symbol,
            period=period,
            interval=interval,
        )
        if not fallback_hist.empty and "Close" in fallback_hist.columns:
            scaled_hist = fallback_hist.copy()
            if config.fallback_multiplier != 1.0:
                for col in ["Open", "High", "Low", "Close"]:
                    if col in scaled_hist.columns:
                        scaled_hist[col] = scaled_hist[col] * config.fallback_multiplier
            return scaled_hist, True

        return pd.DataFrame(), True

    def _get_underlying_config(self, symbol_key: str) -> UnderlyingConfig:
        """Retrieve UnderlyingConfig, defaulting to SPX if unknown."""
        return self.settings.underlying_configs.get(
            symbol_key,
            self.settings.underlying_configs.get("SPX"),
        )

    def _resolve_spot_price(self, config: UnderlyingConfig) -> tuple[float, bool]:
        """Fetch spot price for underlying symbol with fallback."""
        hist = self.provider.get_history(
            config.primary_symbol,
            period=self.settings.options_history_period,
        )
        if not hist.empty and "Close" in hist.columns:
            cleaned = hist["Close"].dropna()
            if not cleaned.empty:
                return float(cleaned.iloc[-1]), False

        # Fallback symbol check
        fallback_hist = self.provider.get_history(
            config.fallback_symbol,
            period=self.settings.options_history_period,
        )
        if not fallback_hist.empty and "Close" in fallback_hist.columns:
            cleaned = fallback_hist["Close"].dropna()
            if not cleaned.empty:
                return float(cleaned.iloc[-1]) * config.fallback_multiplier, True

        return config.default_spot, True

    def _calculate_dte_days(self, exp_date_str: str) -> float:
        """Parse expiration date and return days to expiration."""
        try:
            exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            delta = (exp_date - today).days
            return max(float(delta), 0.5)
        except (ValueError, TypeError):
            return 1.0
