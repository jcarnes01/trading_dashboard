"""Interactive SPX Price Chart with timeframe selectors and structural level overlays."""
from typing import Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.models.options import OptionsStructure
from services.dashboard_service import DashboardService

TIMEFRAME_CONFIG = {
    "1D": {"period": "1d", "interval": "5m"},
    "5D": {"period": "5d", "interval": "15m"},
    "1M": {"period": "1mo", "interval": "1d"},
    "YTD": {"period": "ytd", "interval": "1d"},
    "1Y": {"period": "1y", "interval": "1d"},
}


def build_spx_price_figure(
    df: pd.DataFrame,
    structure: Optional[OptionsStructure] = None,
    timeframe: str = "5D",
) -> go.Figure:
    """Build Plotly price chart with area fill and optional structural levels overlay."""
    if df.empty or "Close" not in df.columns:
        return go.Figure()

    fig = go.Figure()

    # Price Line with gradient area fill
    symbol_name = structure.symbol if structure else "Price"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name=symbol_name,
            line=dict(color="#38bdf8", width=2),
            fill="tozeroy",
            fillcolor="rgba(56, 189, 248, 0.08)",
            hovertemplate="<b>%{x|%b %d, %H:%M}</b><br>Price: %{y:,.2f}<extra></extra>",
        )
    )

    # For short timeframes (1D, 5D), overlay key structural barriers
    if structure is not None and timeframe in ("1D", "5D"):
        # Call Wall (Resistance)
        if structure.call_wall_oi > 0:
            fig.add_hline(
                y=structure.call_wall_oi,
                line_width=1.5,
                line_dash="dot",
                line_color="#22c55e",
                annotation_text=f"Call Wall ({structure.call_wall_oi:,.0f})",
                annotation_position="top right",
            )

        # Put Wall (Support)
        if structure.put_wall_oi > 0:
            fig.add_hline(
                y=structure.put_wall_oi,
                line_width=1.5,
                line_dash="dot",
                line_color="#ef4444",
                annotation_text=f"Put Wall ({structure.put_wall_oi:,.0f})",
                annotation_position="bottom right",
            )

        # Zero Gamma Flip Point
        if structure.zero_gamma_strike and structure.zero_gamma_strike > 0:
            fig.add_hline(
                y=structure.zero_gamma_strike,
                line_width=1.5,
                line_dash="dash",
                line_color="#a855f7",
                annotation_text=f"Zero Gamma ({structure.zero_gamma_strike:,.0f})",
                annotation_position="top left",
            )

    # Configure axes and dark layout
    min_price = float(df["Close"].min()) * 0.995
    max_price = float(df["Close"].max()) * 1.005

    # If short-term overlays exceed min/max, adjust range slightly
    if structure is not None and timeframe in ("1D", "5D"):
        min_price = min(min_price, structure.put_wall_oi * 0.998)
        max_price = max(max_price, structure.call_wall_oi * 1.002)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=20, b=30),
        height=380,
        hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            range=[min_price, max_price],
            tickformat=",.0f",
        ),
        showlegend=False,
    )

    return fig


def render_spx_price_chart(
    structure: OptionsStructure,
    service: DashboardService,
) -> None:
    """Render interactive SPX price chart with 1D, 5D, 1M, YTD, 1Y timeframe selector."""
    c_title, c_picker = st.columns([3, 2])
    with c_title:
        st.subheader(f"{structure.symbol} Price Chart")
    with c_picker:
        timeframe = st.radio(
            "Range",
            options=["1D", "5D", "1M", "YTD", "1Y"],
            index=1,  # Default: 5D
            horizontal=True,
            label_visibility="collapsed",
            key=f"{structure.symbol}_timeframe_selector",
        )

    config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["5D"])

    # Load history with fast TTL
    hist_df, is_fallback = service.fetch_underlying_history(
        symbol_key=structure.symbol,
        period=config["period"],
        interval=config["interval"],
    )

    if hist_df.empty:
        st.warning("⚠️ Historical price series temporarily unavailable.")
        return

    fig = build_spx_price_figure(hist_df, structure=structure, timeframe=timeframe)
    st.plotly_chart(fig, use_container_width=True)
