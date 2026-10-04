"""Unified Market Catalysts & Volatility Events UI widget combining OpEx and Economic releases."""
from typing import List
import pandas as pd
import streamlit as st

from core.models.calendar import CatalystCategory, MarketCatalyst, VolatilityImpact


def render_catalysts_widget(catalysts: List[MarketCatalyst]) -> None:
    """Render unified timeline combining macro economic prints and options expiration dates."""
    st.subheader("Market Catalysts & Volatility Calendar")
    st.caption("Chronological timeline combining macro economic prints (CPI, FOMC, Jobs) and options expiration dates (OpEx, Quad Witching).")

    if not catalysts:
        st.info("No upcoming market catalysts found.")
        return

    # Display top 3 upcoming catalysts in prominent highlight cards
    highlight_count = min(3, len(catalysts))
    cols = st.columns(highlight_count)

    for i in range(highlight_count):
        cat = catalysts[i]
        with cols[i]:
            days_str = f"{cat.days_remaining}d away" if cat.days_remaining > 0 else "Happening Today!"

            st.metric(
                label=f"{cat.badge_icon} {cat.title}",
                value=days_str,
                delta=cat.formatted_date,
                delta_color="off",
                help=cat.description,
            )

            # Impact badge & release numbers if available
            impact_badge = (
                "🔴 **High Binary Risk**"
                if cat.impact == VolatilityImpact.HIGH
                else (
                    "🟣 **Options Pinning & Roll**"
                    if cat.impact == VolatilityImpact.STRUCTURAL
                    else "🟡 **Moderate Impact**"
                )
            )

            if cat.estimate is not None or cat.actual is not None:
                act_str = f"{cat.actual}{cat.unit}" if cat.actual is not None else "Pending"
                est_str = f"{cat.estimate}{cat.unit}" if cat.estimate is not None else "N/A"
                st.caption(f"{impact_badge} • **Est:** {est_str} | **Act:** {act_str}")
            else:
                st.caption(impact_badge)

    # Detailed expandable table for all catalysts
    with st.expander("📋 View Complete Catalyst Schedule & Details"):
        table_rows = []
        for c in catalysts:
            impact_label = (
                "High"
                if c.impact == VolatilityImpact.HIGH
                else ("Structural" if c.impact == VolatilityImpact.STRUCTURAL else "Medium")
            )
            est_display = f"{c.estimate}{c.unit}" if c.estimate is not None else "—"
            act_display = f"{c.actual}{c.unit}" if c.actual is not None else "—"
            prior_display = f"{c.prior}{c.unit}" if c.prior is not None else "—"

            table_rows.append({
                "Date": c.formatted_date,
                "Days Left": f"{c.days_remaining}d",
                "Category": c.category.value,
                "Event": f"{c.badge_icon} {c.title}",
                "Impact": impact_label,
                "Estimate": est_display,
                "Actual": act_display,
                "Prior": prior_display,
                "Source": c.source,
            })

        df_catalysts = pd.DataFrame(table_rows)
        st.dataframe(df_catalysts, use_container_width=True, hide_index=True)
