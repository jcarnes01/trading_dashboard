"""Directional scoring engine: Multi-factor sentiment matrix and playbook strategy generator."""
from typing import Dict, List
from config.settings import AppSettings, default_settings
from core.models.market import MacroSnapshot
from core.models.signal import BiasDirection, BiasSignal


class DirectionalScoringEngine:
    """Evaluates macro indicators against quantitative rules to produce directional bias."""

    def __init__(self, settings: AppSettings = default_settings):
        self.settings = settings

    def evaluate_bias(self, snapshot: MacroSnapshot) -> BiasSignal:
        """Score macro market snapshot across intermarket factors."""
        factors: Dict[str, int] = {}
        score = 0

        # 1. Market Breadth: 5D RSP/SPY slope
        slope = snapshot.breadth_ratio_5d_slope
        if slope > 0:
            breadth_score = 1
        elif slope < 0:
            breadth_score = -1
        else:
            breadth_score = 0
        factors["RSP/SPY Breadth"] = breadth_score
        score += breadth_score

        # 2. Interest Rates: 10Y Yield change (Lower yields -> Equity Bullish)
        ten_year_change = snapshot.get_change_pct("10Y")
        if ten_year_change < 0:
            rates_score = 1
        elif ten_year_change > 0:
            rates_score = -1
        else:
            rates_score = 0
        factors["10Y Yield"] = rates_score
        score += rates_score

        # 3. Currency: US Dollar (DXY) change (Weaker dollar -> Equity Bullish)
        dxy_change = snapshot.get_change_pct("DXY")
        if dxy_change < 0:
            dxy_score = 1
        elif dxy_change > 0:
            dxy_score = -1
        else:
            dxy_score = 0
        factors["DXY Dollar"] = dxy_score
        score += dxy_score

        # 4. Volatility: VIX change (Falling volatility -> Equity Bullish)
        vix_change = snapshot.get_change_pct("VIX")
        if vix_change < 0:
            vix_score = 1
        elif vix_change > 0:
            vix_score = -1
        else:
            vix_score = 0
        factors["VIX Volatility"] = vix_score
        score += vix_score

        # Determine directional regime & playbook recommendations
        direction, summary, strategies = self._resolve_playbook(score)

        return BiasSignal(
            total_score=score,
            max_possible_score=self.settings.max_directional_score,
            direction=direction,
            factor_breakdown=factors,
            playbook_summary=summary,
            suggested_strategies=strategies,
        )

    def _resolve_playbook(self, score: int) -> tuple[BiasDirection, str, List[str]]:
        """Map score to direction, playbook summary narrative, and strategy list."""
        if score >= self.settings.bullish_score_threshold:
            direction = BiasDirection.BULLISH
            summary = (
                f"🟢 **Directional Bias: BULLISH (Score: +{score}/{self.settings.max_directional_score})** — "
                "Look for Bull Put Spreads + 7/14 DTE Long Calls."
            )
            strategies = [
                "Bull Put Credit Spreads",
                "7-14 DTE Long Calls",
                "Bullish Call Debit Spreads",
            ]
        elif score <= self.settings.bearish_score_threshold:
            direction = BiasDirection.BEARISH
            summary = (
                f"🔴 **Directional Bias: BEARISH (Score: {score}/{self.settings.max_directional_score})** — "
                "Look for Bear Call Spreads + 7/14 DTE Long Puts."
            )
            strategies = [
                "Bear Call Credit Spreads",
                "7-14 DTE Long Puts",
                "Bearish Put Debit Spreads",
            ]
        else:
            direction = BiasDirection.NEUTRAL
            summary = (
                f"⚪ **Directional Bias: NEUTRAL (Score: {score}/{self.settings.max_directional_score})** — "
                "Market rangebound. Favor pure OTM credit spreads."
            )
            strategies = [
                "Iron Condors",
                "Wide Out-Of-The-Money Credit Spreads",
                "Neutral Strangle Selling",
            ]

        return direction, summary, strategies
