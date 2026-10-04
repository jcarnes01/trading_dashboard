"""Upcoming Options Expiration (OpEx) and Quad Witching UI widget."""
from typing import List
import streamlit as st

from core.models.calendar import OpexEvent


def render_opex_widget(events: List[OpexEvent]) -> None:
    """Render upcoming OpEx and Quad Witching countdowns and dealer rebalancing alerts."""
    st.subheader("OpEx & Witching Calendar")

    if not events:
        st.info("No upcoming OpEx events scheduled.")
        return

    cols = st.columns(len(events))
    for col, event in zip(cols, events):
        with col:
            badge_icon = "🔮" if event.is_quad_witching else "📅"
            days_text = f"{event.days_remaining}d away" if event.days_remaining > 0 else "Expires Today!"

            st.metric(
                label=f"{badge_icon} {event.title}",
                value=days_text,
                delta=event.formatted_date,
                delta_color="off",
                help=event.description,
            )

            if event.is_quad_witching:
                st.caption("⚡ **Quad Witching Alert:** High pin risk & institutional futures roll.")
