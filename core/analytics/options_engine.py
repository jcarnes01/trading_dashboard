"""Options analytics engine: OI walls, GEX, ATM Straddle, and Expected Moves."""
import math
from typing import List, Optional, Tuple
import pandas as pd

from config.settings import AppSettings, default_settings
from core.models.options import OptionsStructure, StrikeGEX


class OptionsAnalyticsEngine:
    """Calculates options positioning boundaries, Gamma Exposure, and expected moves."""

    def __init__(self, settings: AppSettings = default_settings):
        self.settings = settings

    @staticmethod
    def normal_pdf(x: float) -> float:
        """Standard Normal probability density function N'(x)."""
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

    def calculate_bs_gamma(
        self,
        spot: float,
        strike: float,
        dte_years: float,
        iv: float,
        risk_free_rate: Optional[float] = None,
        dividend_yield: Optional[float] = None,
    ) -> float:
        """Calculate Black-Scholes gamma for European options.

        Gamma is identical for calls and puts under standard Black-Scholes assumptions.
        """
        r = risk_free_rate if risk_free_rate is not None else self.settings.default_risk_free_rate
        q = dividend_yield if dividend_yield is not None else self.settings.default_dividend_yield

        # Boundary checks & sanitization
        if spot <= 0 or strike <= 0 or iv <= 0:
            return 0.0

        t = max(dte_years, self.settings.min_dte_years)
        sqrt_t = math.sqrt(t)
        sigma_sqrt_t = iv * sqrt_t

        if sigma_sqrt_t <= 0:
            return 0.0

        try:
            d1 = (math.log(spot / strike) + (r - q + 0.5 * iv * iv) * t) / sigma_sqrt_t
            pdf_d1 = self.normal_pdf(d1)
            gamma = (math.exp(-q * t) * pdf_d1) / (spot * sigma_sqrt_t)
            return gamma if math.isfinite(gamma) else 0.0
        except (ValueError, OverflowError, ZeroDivisionError):
            return 0.0

    def compute_structure(
        self,
        spot: float,
        calls_df: Optional[pd.DataFrame],
        puts_df: Optional[pd.DataFrame],
        dte_days: float = 1.0,
        risk_free_rate: Optional[float] = None,
        expiration_date: str = "",
    ) -> OptionsStructure:
        """Compute complete options market structure including OI and GEX metrics."""
        # Check for empty or invalid data
        if calls_df is None or puts_df is None or calls_df.empty or puts_df.empty or spot <= 0:
            return self._build_fallback_structure(spot, expiration_date)

        # Standardize and clean DataFrames
        calls = self._clean_chain_df(calls_df)
        puts = self._clean_chain_df(puts_df)

        if calls.empty and puts.empty:
            return self._build_fallback_structure(spot, expiration_date)

        # 1. Open Interest Walls
        call_wall_oi = self._find_max_oi_strike(calls, default=spot * 1.01)
        put_wall_oi = self._find_max_oi_strike(puts, default=spot * 0.99)

        # 2. ATM Straddle & Expected Move
        straddle, atm_call_strike, atm_put_strike = self._compute_atm_straddle(spot, calls, puts)
        expected_move = straddle
        expected_range_low = spot - expected_move
        expected_range_high = spot + expected_move

        # 3. Gamma Exposure (GEX) Calculations
        dte_years = max(dte_days, 0.5) / 365.25
        r = risk_free_rate if risk_free_rate is not None else self.settings.default_risk_free_rate
        strike_gex_list, total_net_gex = self._compute_per_strike_gex(spot, calls, puts, dte_years, r)

        # 4. GEX Walls & Zero Gamma Flip
        call_wall_gex, put_wall_gex, zero_gamma = self._resolve_gex_boundaries(
            spot, strike_gex_list, call_wall_oi, put_wall_oi
        )

        return OptionsStructure(
            underlying_spot=spot,
            call_wall_oi=call_wall_oi,
            put_wall_oi=put_wall_oi,
            call_wall_gex=call_wall_gex,
            put_wall_gex=put_wall_gex,
            net_gex_total=total_net_gex,
            zero_gamma_strike=zero_gamma,
            per_strike_gex=strike_gex_list,
            atm_straddle_price=straddle,
            expected_move=expected_move,
            expected_range_low=expected_range_low,
            expected_range_high=expected_range_high,
            is_fallback=False,
            expiration_date=expiration_date,
        )

    def _clean_chain_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure required columns exist and handle NaNs."""
        cleaned = df.copy()
        required_cols = ["strike", "openInterest", "lastPrice", "impliedVolatility"]
        for col in required_cols:
            if col not in cleaned.columns:
                cleaned[col] = 0.0
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").fillna(0.0)

        cleaned = cleaned[cleaned["strike"] > 0]
        return cleaned

    def _find_max_oi_strike(self, df: pd.DataFrame, default: float) -> float:
        """Find the strike with highest Open Interest."""
        if df.empty or df["openInterest"].sum() <= 0:
            return float(default)
        max_idx = df["openInterest"].idxmax()
        return float(df.loc[max_idx, "strike"])

    def _compute_atm_straddle(
        self, spot: float, calls: pd.DataFrame, puts: pd.DataFrame
    ) -> Tuple[float, float, float]:
        """Compute the ATM straddle pricing."""
        default_move = spot * self.settings.default_expected_move_ratio
        if calls.empty or puts.empty:
            return default_move, spot, spot

        # Find closest strike to spot
        calls_sorted = calls.iloc[(calls["strike"] - spot).abs().argsort()]
        puts_sorted = puts.iloc[(puts["strike"] - spot).abs().argsort()]

        atm_call = calls_sorted.iloc[0] if not calls_sorted.empty else None
        atm_put = puts_sorted.iloc[0] if not puts_sorted.empty else None

        call_price = float(atm_call["lastPrice"]) if atm_call is not None else 0.0
        put_price = float(atm_put["lastPrice"]) if atm_put is not None else 0.0
        straddle = call_price + put_price

        # Fallback if quotes are zero
        if straddle <= 0.0:
            straddle = default_move

        atm_call_strike = float(atm_call["strike"]) if atm_call is not None else spot
        atm_put_strike = float(atm_put["strike"]) if atm_put is not None else spot

        return straddle, atm_call_strike, atm_put_strike

    def _compute_per_strike_gex(
        self,
        spot: float,
        calls: pd.DataFrame,
        puts: pd.DataFrame,
        dte_years: float,
        r: float,
    ) -> Tuple[List[StrikeGEX], float]:
        """Compute dollar Gamma Exposure per strike and total net GEX."""
        # Combine unique strikes
        all_strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
        if not all_strikes:
            return [], 0.0

        calls_by_strike = calls.set_index("strike")
        puts_by_strike = puts.set_index("strike")

        gex_records: List[StrikeGEX] = []
        total_net_gex = 0.0

        for strike in all_strikes:
            call_row = calls_by_strike.loc[strike] if strike in calls_by_strike.index else None
            put_row = puts_by_strike.loc[strike] if strike in puts_by_strike.index else None

            # Handle duplicated index safely
            if isinstance(call_row, pd.DataFrame):
                call_row = call_row.iloc[0]
            if isinstance(put_row, pd.DataFrame):
                put_row = put_row.iloc[0]

            call_oi = float(call_row["openInterest"]) if call_row is not None else 0.0
            put_oi = float(put_row["openInterest"]) if put_row is not None else 0.0
            call_iv = float(call_row["impliedVolatility"]) if call_row is not None else 0.0
            put_iv = float(put_row["impliedVolatility"]) if put_row is not None else 0.0

            # Estimate blend IV if one side is zero
            iv = (
                (call_iv + put_iv) / 2.0
                if (call_iv > 0 and put_iv > 0)
                else (call_iv if call_iv > 0 else (put_iv if put_iv > 0 else 0.20))
            )

            gamma = self.calculate_bs_gamma(
                spot=spot,
                strike=strike,
                dte_years=dte_years,
                iv=iv,
                risk_free_rate=r,
            )

            # Standard dealer GEX convention:
            # Calls: Dealers Long Call -> Positive Gamma (+spot * gamma * oi * 100)
            # Puts: Dealers Short Put -> Negative Gamma (-spot * gamma * oi * 100)
            call_gex = spot * gamma * call_oi * 100.0
            put_gex = -spot * gamma * put_oi * 100.0
            net_gex = call_gex + put_gex

            record = StrikeGEX(
                strike=strike,
                call_gex=call_gex,
                put_gex=put_gex,
                net_gex=net_gex,
                call_oi=call_oi,
                put_oi=put_oi,
                gamma=gamma,
            )
            gex_records.append(record)
            total_net_gex += net_gex

        return gex_records, total_net_gex

    def _resolve_gex_boundaries(
        self,
        spot: float,
        strike_gex_list: List[StrikeGEX],
        default_call_wall: float,
        default_put_wall: float,
    ) -> Tuple[float, float, Optional[float]]:
        """Identify Call GEX Wall, Put GEX Wall, and Zero Gamma Flip Point."""
        if not strike_gex_list:
            return default_call_wall, default_put_wall, None

        # Call Wall GEX: Strike with max positive Call GEX
        best_call_gex = max(strike_gex_list, key=lambda x: x.call_gex, default=None)
        call_wall_gex = best_call_gex.strike if best_call_gex and best_call_gex.call_gex > 0 else default_call_wall

        # Put Wall GEX: Strike with most negative Put GEX
        best_put_gex = min(strike_gex_list, key=lambda x: x.put_gex, default=None)
        put_wall_gex = best_put_gex.strike if best_put_gex and best_put_gex.put_gex < 0 else default_put_wall

        # Zero Gamma Flip Point: Strike where Net GEX changes sign
        # Find consecutive strikes where sign flips
        zero_gamma: Optional[float] = None
        for i in range(len(strike_gex_list) - 1):
            s1 = strike_gex_list[i]
            s2 = strike_gex_list[i + 1]
            if (s1.net_gex < 0 and s2.net_gex >= 0) or (s1.net_gex > 0 and s2.net_gex <= 0):
                # Linear interpolation for strike level
                delta = s2.net_gex - s1.net_gex
                if delta != 0:
                    weight = abs(s1.net_gex) / (abs(s1.net_gex) + abs(s2.net_gex))
                    zero_gamma = s1.strike + weight * (s2.strike - s1.strike)
                else:
                    zero_gamma = (s1.strike + s2.strike) / 2.0
                break

        return call_wall_gex, put_wall_gex, zero_gamma

    def _build_fallback_structure(self, spot: float, expiration_date: str) -> OptionsStructure:
        """Generate safe fallback structure when option chains are unavailable."""
        safe_spot = spot if spot > 0 else 5000.0
        expected_move = safe_spot * self.settings.default_expected_move_ratio
        return OptionsStructure(
            underlying_spot=safe_spot,
            call_wall_oi=safe_spot * 1.01,
            put_wall_oi=safe_spot * 0.99,
            call_wall_gex=safe_spot * 1.01,
            put_wall_gex=safe_spot * 0.99,
            net_gex_total=0.0,
            zero_gamma_strike=None,
            per_strike_gex=[],
            atm_straddle_price=expected_move,
            expected_move=expected_move,
            expected_range_low=safe_spot - expected_move,
            expected_range_high=safe_spot + expected_move,
            is_fallback=True,
            expiration_date=expiration_date,
        )
