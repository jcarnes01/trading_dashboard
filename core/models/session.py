"""Market trading session domain models."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketSession:
    """Current US equity market session status."""
    status: str              # "OPEN", "PRE_MARKET", "AFTER_HOURS", "CLOSED"
    badge_text: str          # "🟢 Market Open", "🟡 Pre-Market", etc.
    current_time_str: str    # "09:45 AM ET"
    is_regular_hours: bool   # True between 09:30 and 16:00 ET Mon-Fri
