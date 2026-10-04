"""Economic calendar data providers with Finnhub integration and curated fallback schedule."""
from abc import ABC, abstractmethod
from datetime import date, datetime
import os
from typing import List, Optional
import requests

from core.models.calendar import CatalystCategory, MarketCatalyst, VolatilityImpact


class BaseCalendarProvider(ABC):
    """Abstract interface defining the economic calendar provider contract."""

    @abstractmethod
    def get_economic_events(self, from_date: date, to_date: date) -> List[MarketCatalyst]:
        """Fetch economic calendar releases between from_date and to_date."""
        pass


class FallbackScheduleProvider(BaseCalendarProvider):
    """Deterministic schedule for high-impact US economic catalysts."""

    # Curated high-impact catalysts for Q3/Q4 2026 and standard release cadence
    CURATED_EVENTS = [
        # Central Bank (FOMC)
        {"date": "2026-10-07", "title": "FOMC Meeting Minutes", "category": CatalystCategory.CENTRAL_BANK, "impact": VolatilityImpact.HIGH, "desc": "Detailed record of Fed policy committee discussions & rate outlook."},
        {"date": "2026-11-04", "title": "FOMC Rate Decision & Press Conf", "category": CatalystCategory.CENTRAL_BANK, "impact": VolatilityImpact.HIGH, "desc": "Federal Reserve monetary policy decision & Jerome Powell press conference."},
        {"date": "2026-12-16", "title": "FOMC Rate Decision & SEP Projections", "category": CatalystCategory.CENTRAL_BANK, "impact": VolatilityImpact.HIGH, "desc": "Year-end Fed decision with updated economic projections and dot plot."},
        # Inflation (CPI / PCE / PPI)
        {"date": "2026-10-14", "title": "CPI Inflation Report", "category": CatalystCategory.INFLATION, "impact": VolatilityImpact.HIGH, "desc": "Consumer Price Index (MoM & YoY). Major driver for rate expectations."},
        {"date": "2026-10-15", "title": "PPI Wholesale Inflation", "category": CatalystCategory.INFLATION, "impact": VolatilityImpact.MEDIUM, "desc": "Producer Price Index measuring wholesale pipeline inflation pressures."},
        {"date": "2026-10-30", "title": "Core PCE Price Index", "category": CatalystCategory.INFLATION, "impact": VolatilityImpact.HIGH, "desc": "Fed's preferred inflation gauge measuring personal consumption expenditures."},
        {"date": "2026-11-12", "title": "CPI Inflation Report", "category": CatalystCategory.INFLATION, "impact": VolatilityImpact.HIGH, "desc": "Consumer Price Index (MoM & YoY). Major driver for rate expectations."},
        {"date": "2026-12-10", "title": "CPI Inflation Report", "category": CatalystCategory.INFLATION, "impact": VolatilityImpact.HIGH, "desc": "Consumer Price Index (MoM & YoY). Major driver for rate expectations."},
        # Employment (NFP)
        {"date": "2026-11-06", "title": "Non-Farm Payrolls & Unemployment", "category": CatalystCategory.EMPLOYMENT, "impact": VolatilityImpact.HIGH, "desc": "Bureau of Labor Statistics monthly employment situation report."},
        {"date": "2026-12-04", "title": "Non-Farm Payrolls & Unemployment", "category": CatalystCategory.EMPLOYMENT, "impact": VolatilityImpact.HIGH, "desc": "Bureau of Labor Statistics monthly employment situation report."},
        # Growth / GDP
        {"date": "2026-10-29", "title": "US Q3 GDP Advance Estimate", "category": CatalystCategory.GROWTH, "impact": VolatilityImpact.HIGH, "desc": "First official estimate of third-quarter annualized economic growth."},
    ]

    def get_economic_events(self, from_date: date, to_date: date) -> List[MarketCatalyst]:
        """Filter curated events between from_date and to_date."""
        results: List[MarketCatalyst] = []
        for item in self.CURATED_EVENTS:
            ev_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
            if from_date <= ev_date <= to_date:
                days_left = (ev_date - from_date).days
                results.append(
                    MarketCatalyst(
                        title=item["title"],
                        event_date=ev_date,
                        days_remaining=days_left,
                        category=item["category"],
                        impact=item["impact"],
                        description=item["desc"],
                        source="SCHEDULED",
                    )
                )
        return results


def resolve_finnhub_api_key(explicit_key: Optional[str] = None) -> str:
    """Resolve Finnhub API key from argument, environment, or Streamlit secrets."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    env_key = os.getenv("FINNHUB_API_KEY", "").strip()
    if env_key:
        return env_key

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            try:
                if "FINNHUB_API_KEY" in st.secrets:
                    return str(st.secrets["FINNHUB_API_KEY"]).strip()
                if "finnhub_api_key" in st.secrets:
                    return str(st.secrets["finnhub_api_key"]).strip()
                if "finnhub" in st.secrets and isinstance(st.secrets["finnhub"], dict):
                    return str(st.secrets["finnhub"].get("api_key", "")).strip()
            except Exception:
                pass
    except Exception:
        pass

    return ""


class FinnhubCalendarProvider(BaseCalendarProvider):
    """Fetches live economic calendar events from Finnhub API with graceful local fallback."""

    BASE_URL = "https://finnhub.io/api/v1/calendar/economic"

    HIGH_IMPACT_KEYWORDS = {
        "cpi": (CatalystCategory.INFLATION, VolatilityImpact.HIGH),
        "fomc": (CatalystCategory.CENTRAL_BANK, VolatilityImpact.HIGH),
        "interest rate": (CatalystCategory.CENTRAL_BANK, VolatilityImpact.HIGH),
        "fed": (CatalystCategory.CENTRAL_BANK, VolatilityImpact.HIGH),
        "non farm": (CatalystCategory.EMPLOYMENT, VolatilityImpact.HIGH),
        "nonfarm": (CatalystCategory.EMPLOYMENT, VolatilityImpact.HIGH),
        "payrolls": (CatalystCategory.EMPLOYMENT, VolatilityImpact.HIGH),
        "pce": (CatalystCategory.INFLATION, VolatilityImpact.HIGH),
        "gdp": (CatalystCategory.GROWTH, VolatilityImpact.HIGH),
        "ppi": (CatalystCategory.INFLATION, VolatilityImpact.MEDIUM),
        "retail sales": (CatalystCategory.GROWTH, VolatilityImpact.MEDIUM),
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = resolve_finnhub_api_key(api_key)
        self.fallback = FallbackScheduleProvider()

    def get_economic_events(self, from_date: date, to_date: date) -> List[MarketCatalyst]:
        """Fetch from Finnhub if API key is configured; otherwise use fallback."""
        if not self.api_key:
            return self.fallback.get_economic_events(from_date, to_date)

        try:
            params = {
                "from": from_date.strftime("%Y-%m-%d"),
                "to": to_date.strftime("%Y-%m-%d"),
                "token": self.api_key,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=3.5)
            if resp.status_code != 200:
                return self.fallback.get_economic_events(from_date, to_date)

            data = resp.json()
            raw_events = data.get("economicCalendar", [])
            if not raw_events:
                return self.fallback.get_economic_events(from_date, to_date)

            parsed_events: List[MarketCatalyst] = []
            for item in raw_events:
                event_name = str(item.get("event", "")).strip()
                event_time_str = str(item.get("time", "")).split(" ")[0]

                category, impact = self._classify_event(event_name)
                if category is None:
                    continue  # Filter out low-impact noise

                try:
                    ev_date = datetime.strptime(event_time_str, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    continue

                if not (from_date <= ev_date <= to_date):
                    continue

                days_left = (ev_date - from_date).days
                actual_val = self._safe_float(item.get("actual"))
                est_val = self._safe_float(item.get("estimate"))
                prior_val = self._safe_float(item.get("prev"))
                unit = str(item.get("unit", ""))

                parsed_events.append(
                    MarketCatalyst(
                        title=event_name,
                        event_date=ev_date,
                        days_remaining=days_left,
                        category=category,
                        impact=impact,
                        description=f"US Economic Release: {event_name}",
                        actual=actual_val,
                        estimate=est_val,
                        prior=prior_val,
                        unit=unit,
                        source="FINNHUB",
                    )
                )

            return parsed_events if parsed_events else self.fallback.get_economic_events(from_date, to_date)

        except Exception:
            return self.fallback.get_economic_events(from_date, to_date)

    def _classify_event(self, event_name: str) -> tuple[Optional[CatalystCategory], VolatilityImpact]:
        """Classify event title into category and volatility impact; return None if non-critical."""
        lower_name = event_name.lower()
        for keyword, (cat, imp) in self.HIGH_IMPACT_KEYWORDS.items():
            if keyword in lower_name:
                return cat, imp
        return None, VolatilityImpact.MEDIUM

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None


class MockCalendarProvider(BaseCalendarProvider):
    """In-memory mock calendar provider for deterministic unit testing."""

    def __init__(self, mock_events: Optional[List[MarketCatalyst]] = None):
        self._events = mock_events if mock_events is not None else []

    def get_economic_events(self, from_date: date, to_date: date) -> List[MarketCatalyst]:
        if not self._events:
            # Default fallback mock
            return [
                MarketCatalyst(
                    title="Mock CPI Release",
                    event_date=from_date,
                    days_remaining=0,
                    category=CatalystCategory.INFLATION,
                    impact=VolatilityImpact.HIGH,
                    description="Mock consumer price index report",
                    estimate=3.1,
                    actual=3.2,
                    unit="%",
                    source="MOCK",
                )
            ]
        return [e for e in self._events if from_date <= e.event_date <= to_date]

