"""Market session analytics engine for US equity trading hours."""
from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from core.models.session import MarketSession


class MarketSessionEngine:
    """Evaluates whether US equity markets are in Pre-Market, Regular, After-Hours, or Closed session."""

    ET_TIMEZONE = ZoneInfo("America/New_York")

    PRE_MARKET_OPEN = time(4, 0)
    REGULAR_OPEN = time(9, 30)
    REGULAR_CLOSE = time(16, 0)
    AFTER_HOURS_CLOSE = time(20, 0)

    def get_session(self, reference_dt: Optional[datetime] = None) -> MarketSession:
        """Determine current market session status based on Eastern Time."""
        if reference_dt is not None:
            if reference_dt.tzinfo is None:
                now_et = reference_dt.replace(tzinfo=self.ET_TIMEZONE)
            else:
                now_et = reference_dt.astimezone(self.ET_TIMEZONE)
        else:
            now_et = datetime.now(self.ET_TIMEZONE)

        current_time = now_et.time()
        weekday = now_et.weekday()  # Monday = 0, Sunday = 6
        time_str = now_et.strftime("%I:%M %p ET")

        # Weekend Check
        if weekday in (5, 6):
            return MarketSession(
                status="CLOSED",
                badge_text="🔴 Weekend / Closed",
                current_time_str=time_str,
                is_regular_hours=False,
            )

        # Weekday Sessions
        if current_time < self.PRE_MARKET_OPEN:
            return MarketSession(
                status="CLOSED",
                badge_text="🔴 Overnight / Closed",
                current_time_str=time_str,
                is_regular_hours=False,
            )
        elif current_time < self.REGULAR_OPEN:
            return MarketSession(
                status="PRE_MARKET",
                badge_text="🟡 Pre-Market Session",
                current_time_str=time_str,
                is_regular_hours=False,
            )
        elif current_time < self.REGULAR_CLOSE:
            return MarketSession(
                status="OPEN",
                badge_text="🟢 Live Market Open",
                current_time_str=time_str,
                is_regular_hours=True,
            )
        elif current_time < self.AFTER_HOURS_CLOSE:
            return MarketSession(
                status="AFTER_HOURS",
                badge_text="🟠 After-Hours Session",
                current_time_str=time_str,
                is_regular_hours=False,
            )
        else:
            return MarketSession(
                status="CLOSED",
                badge_text="🔴 Market Closed",
                current_time_str=time_str,
                is_regular_hours=False,
            )
