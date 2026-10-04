"""Market and macro snapshot domain models."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass(frozen=True)
class Quote:
    """Individual market symbol quote and daily performance."""
    symbol: str
    last_price: float
    previous_close: float
    change_pct: float
    is_valid: bool = True


@dataclass(frozen=True)
class MacroSnapshot:
    """Consolidated intermarket macro environment snapshot."""
    quotes: Dict[str, Quote]
    breadth_ratio_5d_slope: float  # Slope of RSP / SPY ratio over 5 trading days
    timestamp_iso: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Safely fetch quote for a symbol."""
        return self.quotes.get(symbol)

    def get_change_pct(self, symbol: str) -> float:
        """Safely fetch percentage change for a symbol, returning 0.0 if missing."""
        quote = self.get_quote(symbol)
        return quote.change_pct if quote and quote.is_valid else 0.0

    def get_last_price(self, symbol: str) -> float:
        """Safely fetch last price for a symbol, returning 0.0 if missing."""
        quote = self.get_quote(symbol)
        return quote.last_price if quote and quote.is_valid else 0.0
