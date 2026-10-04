"""Macro intermarket matrix UI component."""
import streamlit as st
from core.models.market import MacroSnapshot


def render_macro_matrix(snapshot: MacroSnapshot) -> None:
    """Render intermarket rates, dollar, volatility, and breadth matrix."""
    st.subheader("Macro Intermarket Matrix")

    # Row 1: Volatility & Rates
    m1, m2 = st.columns(2)
    m1.metric(
        "VIX",
        f"{snapshot.get_last_price('VIX'):.2f}",
        f"{snapshot.get_change_pct('VIX'):+.2f}%",
        delta_color="inverse",
    )
    m2.metric(
        "10Y Yield",
        f"{snapshot.get_last_price('10Y'):.3f}%",
        f"{snapshot.get_change_pct('10Y'):+.2f}%",
        delta_color="inverse",
    )

    # Row 2: Currencies & Commodities
    m3, m4 = st.columns(2)
    m3.metric(
        "DXY (USD)",
        f"{snapshot.get_last_price('DXY'):.2f}",
        f"{snapshot.get_change_pct('DXY'):+.2f}%",
        delta_color="inverse",
    )
    m4.metric(
        "Gold",
        f"${snapshot.get_last_price('Gold'):,.1f}",
        f"{snapshot.get_change_pct('Gold'):+.2f}%",
    )

    # Row 3: Market Breadth & Equities
    m5, m6 = st.columns(2)
    m5.metric(
        "RSP/SPY 5D Trend",
        f"{snapshot.breadth_ratio_5d_slope * 100:+.2f}%",
        delta_color="normal",
    )
    m6.metric(
        "SPY",
        f"${snapshot.get_last_price('SPY'):,.2f}",
        f"{snapshot.get_change_pct('SPY'):+.2f}%",
        delta_color="normal",
    )
