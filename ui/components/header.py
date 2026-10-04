"""Header and status UI component."""
import streamlit as st
from services.dashboard_service import DashboardPayload


def render_header(payload: DashboardPayload) -> None:
    """Render top page title, timestamp metadata, and fallback notices."""
    st.title("SPX Morning Brief")
    st.caption(f"Refreshed: {payload.refreshed_at_str}")

    if payload.options_structure.is_fallback:
        st.warning(
            "⚠️ **Notice:** Primary ^SPX options feed is delayed or unavailable. "
            "Displaying scaled proxy structure (SPY x10 / model estimation)."
        )
