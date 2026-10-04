"""Header, status, and control UI component."""
from typing import Tuple
import streamlit as st
from config.settings import AppSettings, default_settings
from services.dashboard_service import DashboardPayload


def render_header(
    payload: DashboardPayload,
    settings: AppSettings = default_settings,
) -> Tuple[str, bool]:
    """Render top page title, session status badge, ticker switcher, and auto-refresh toggle."""
    col_title, col_controls = st.columns([3, 2])

    with col_title:
        st.title(f"{payload.active_symbol} Morning Brief")
        session_text = (
            f"{payload.market_session.badge_text} ({payload.market_session.current_time_str})"
            if payload.market_session
            else ""
        )
        st.caption(f"{session_text} • Refreshed: {payload.refreshed_at_str}")

    with col_controls:
        # Subtle top margin to align controls with title and prevent clipping
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        c_tick, c_refresh = st.columns([3, 2])
        with c_tick:
            selected_symbol = st.radio(
                "Underlying Asset",
                options=settings.supported_symbols,
                index=settings.supported_symbols.index(payload.active_symbol)
                if payload.active_symbol in settings.supported_symbols
                else 0,
                horizontal=True,
                key="underlying_ticker_selector",
            )
        with c_refresh:
            st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
            auto_refresh = st.toggle("Auto-Refresh (60s)", value=False, key="auto_refresh_toggle")

    if payload.options_structure.is_fallback:
        st.warning(
            f"⚠️ **Notice:** Primary {payload.active_symbol} live index feed is delayed or unavailable. "
            "Displaying scaled proxy structure or theoretical estimation."
        )

    return selected_symbol, auto_refresh
