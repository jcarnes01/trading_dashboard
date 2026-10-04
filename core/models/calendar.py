"""Options expiration and witching event domain models."""
from dataclasses import dataclass
from datetime import date


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
