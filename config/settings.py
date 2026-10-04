"""Centralized application settings and constants."""
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class UnderlyingConfig:
    """Configuration for an underlying equity/index asset."""
    key: str
    display_name: str
    primary_symbol: str
    fallback_symbol: str
    fallback_multiplier: float
    default_spot: float


@dataclass(frozen=True)
class AppSettings:
    """Immutable application settings container."""

    # Ticker configurations
    underlying_configs: Dict[str, UnderlyingConfig] = field(
        default_factory=lambda: {
            "SPX": UnderlyingConfig(
                key="SPX",
                display_name="S&P 500 (SPX)",
                primary_symbol="^SPX",
                fallback_symbol="SPY",
                fallback_multiplier=10.0,
                default_spot=5000.0,
            ),
            "QQQ": UnderlyingConfig(
                key="QQQ",
                display_name="Nasdaq 100 (QQQ)",
                primary_symbol="QQQ",
                fallback_symbol="QQQ",
                fallback_multiplier=1.0,
                default_spot=480.0,
            ),
            "IWM": UnderlyingConfig(
                key="IWM",
                display_name="Russell 2000 (IWM)",
                primary_symbol="IWM",
                fallback_symbol="IWM",
                fallback_multiplier=1.0,
                default_spot=220.0,
            ),
        }
    )
    supported_symbols: list[str] = field(default_factory=lambda: ["SPX", "QQQ", "IWM"])

    macro_tickers: Dict[str, str] = field(
        default_factory=lambda: {
            "SPY": "SPY",
            "RSP": "RSP",
            "VIX": "^VIX",
            "10Y": "^TNX",
            "DXY": "DX-Y.NYB",
            "Gold": "GC=F",
        }
    )
    primary_options_symbol: str = "^SPX"
    fallback_options_symbol: str = "SPY"
    fallback_index_multiplier: float = 10.0

    # Lookbacks & TTLs (in seconds)
    macro_history_period: str = "7d"
    options_history_period: str = "5d"
    macro_cache_ttl_seconds: int = 300
    options_cache_ttl_seconds: int = 600

    # Financial / Options Modeling constants
    default_risk_free_rate: float = 0.04
    default_dividend_yield: float = 0.015
    default_expected_move_ratio: float = 0.008  # 0.8% fallback rule of thumb
    min_dte_years: float = 0.5 / 365.25  # Lower bound for 0DTE intraday gamma stability

    # Directional Scoring thresholds
    bullish_score_threshold: int = 2
    bearish_score_threshold: int = -2
    max_directional_score: int = 4

    # Authentication settings
    auth_enabled: bool = True
    auth_credentials: Dict[str, str] = field(
        default_factory=lambda: {
            "trader": "spxplaybook2026",
            "friend": "alpha2026",
        }
    )

    # Finnhub & Economic Calendar
    finnhub_api_key: Optional[str] = None
    calendar_cache_ttl_seconds: int = 3600


# Global default instance
default_settings = AppSettings()
