"""Market events, economic releases, and options expiration domain models."""
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class CatalystCategory(str, Enum):
    """Classification of market catalyst events."""
    CENTRAL_BANK = "CENTRAL_BANK"     # FOMC, Powell Speeches, Rate Decisions
    INFLATION = "INFLATION"           # CPI, PPI, PCE Price Index
    EMPLOYMENT = "EMPLOYMENT"         # Non-Farm Payrolls, Jobless Claims
    GROWTH = "GROWTH"                 # GDP, Retail Sales, ISM PMIs
    OPTIONS_STRUCTURE = "OPTIONS"     # Monthly OpEx, Quad Witching


class VolatilityImpact(str, Enum):
    """Expected volatility and implied volatility risk."""
    HIGH = "HIGH"                     # 🔴 High Binary Event Risk (FOMC, CPI, NFP)
    MEDIUM = "MEDIUM"                 # 🟡 Moderate Market Risk (PPI, Retail Sales)
    STRUCTURAL = "STRUCTURAL"         # 🟣 Liquidity/Pinning Risk (OpEx, Quad Witching)


@dataclass(frozen=True)
class OpexEvent:
    """Represents a scheduled Options Expiration (OpEx) or Quad Witching event."""
    title: str
    event_date: date
    days_remaining: int
    is_quad_witching: bool
    description: str

    @property
    def formatted_date(self) -> str:
        """Human-readable date format (e.g., 'Oct 16, 2026')."""
        return self.event_date.strftime("%b %d, %Y")


@dataclass(frozen=True)
class MarketCatalyst:
    """Unified catalyst item combining economic releases and options structural dates."""
    title: str
    event_date: date
    days_remaining: int
    category: CatalystCategory
    impact: VolatilityImpact
    description: str
    actual: Optional[float] = None
    estimate: Optional[float] = None
    prior: Optional[float] = None
    unit: str = ""
    is_quad_witching: bool = False
    source: str = "SCHEDULED"

    @property
    def formatted_date(self) -> str:
        """Human-readable date format."""
        return self.event_date.strftime("%b %d, %Y")

    @property
    def badge_icon(self) -> str:
        """Display icon for the category."""
        if self.category == CatalystCategory.CENTRAL_BANK:
            return "🏦"
        elif self.category == CatalystCategory.INFLATION:
            return "📊"
        elif self.category == CatalystCategory.EMPLOYMENT:
            return "💼"
        elif self.category == CatalystCategory.GROWTH:
            return "📈"
        elif self.category == CatalystCategory.OPTIONS_STRUCTURE:
            return "🔮" if self.is_quad_witching else "📅"
        return "📌"

