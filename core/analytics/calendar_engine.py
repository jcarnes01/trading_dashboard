"""Calendar analytics engine: Monthly OpEx and Quad Witching scheduling."""
from datetime import date
from typing import List, Optional

from core.models.calendar import OpexEvent


class CalendarAnalyticsEngine:
    """Calculates standard monthly options expiration (OpEx) and Quad Witching dates."""

    QUAD_WITCHING_MONTHS = {3, 6, 9, 12}

    @staticmethod
    def get_third_friday(year: int, month: int) -> date:
        """Calculate the 3rd Friday of a given year and month.

        In the US, standard monthly options expire on the third Friday of the month.
        """
        # Day of week: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4
        first_day_weekday = date(year, month, 1).weekday()
        first_friday_day = 1 + (4 - first_day_weekday) % 7
        third_friday_day = first_friday_day + 14
        return date(year, month, third_friday_day)

    def is_quad_witching(self, month: int) -> bool:
        """Check if month corresponds to quarterly Quad Witching (March, June, Sept, Dec)."""
        return month in self.QUAD_WITCHING_MONTHS

    def get_upcoming_opex_events(
        self, reference_date: Optional[date] = None, count: int = 3
    ) -> List[OpexEvent]:
        """Generate list of upcoming monthly OpEx and Quad Witching events."""
        ref_date = reference_date if reference_date is not None else date.today()
        events: List[OpexEvent] = []

        curr_year = ref_date.year
        curr_month = ref_date.month

        # Scan up to 12 months forward
        for _ in range(12):
            opex_date = self.get_third_friday(curr_year, curr_month)

            if opex_date >= ref_date:
                days_left = (opex_date - ref_date).days
                is_quad = self.is_quad_witching(curr_month)
                month_name = opex_date.strftime("%B")

                if is_quad:
                    title = f"{month_name} Quad Witching"
                    description = (
                        "Simultaneous expiration of index futures, index options, stock options, "
                        "and single stock futures. Expect heightened institutional rolling & pinning."
                    )
                else:
                    title = f"{month_name} Monthly OpEx"
                    description = (
                        "Standard monthly equity & index options expiration. "
                        "Major dealer gamma roll date."
                    )

                event = OpexEvent(
                    title=title,
                    event_date=opex_date,
                    days_remaining=days_left,
                    is_quad_witching=is_quad,
                    description=description,
                )
                events.append(event)
                if len(events) >= count:
                    break

            # Advance month
            if curr_month == 12:
                curr_month = 1
                curr_year += 1
            else:
                curr_month += 1

        return events

    def get_unified_catalysts(
        self,
        reference_date: Optional[date] = None,
        economic_events: Optional[List["MarketCatalyst"]] = None,
        count: int = 6,
    ) -> List["MarketCatalyst"]:
        """Merge options expiration events and macro economic catalysts into a unified timeline."""
        from core.models.calendar import CatalystCategory, MarketCatalyst, VolatilityImpact

        ref_date = reference_date if reference_date is not None else date.today()
        opex_events = self.get_upcoming_opex_events(reference_date=ref_date, count=4)

        all_catalysts: List[MarketCatalyst] = []

        # 1. Map OpEx events into unified catalyst model
        for opex in opex_events:
            all_catalysts.append(
                MarketCatalyst(
                    title=opex.title,
                    event_date=opex.event_date,
                    days_remaining=opex.days_remaining,
                    category=CatalystCategory.OPTIONS_STRUCTURE,
                    impact=VolatilityImpact.STRUCTURAL,
                    description=opex.description,
                    is_quad_witching=opex.is_quad_witching,
                    source="SCHEDULED",
                )
            )

        # 2. Add economic catalysts if supplied
        if economic_events:
            for econ in economic_events:
                if econ.event_date >= ref_date:
                    days_left = (econ.event_date - ref_date).days
                    all_catalysts.append(
                        MarketCatalyst(
                            title=econ.title,
                            event_date=econ.event_date,
                            days_remaining=days_left,
                            category=econ.category,
                            impact=econ.impact,
                            description=econ.description,
                            actual=econ.actual,
                            estimate=econ.estimate,
                            prior=econ.prior,
                            unit=econ.unit,
                            source=econ.source,
                        )
                    )

        # 3. Sort chronologically by date, prioritizing HIGH impact if on the same date
        impact_priority = {
            VolatilityImpact.HIGH: 0,
            VolatilityImpact.STRUCTURAL: 1,
            VolatilityImpact.MEDIUM: 2,
        }
        all_catalysts.sort(key=lambda c: (c.event_date, impact_priority.get(c.impact, 3)))

        return all_catalysts[:count]
