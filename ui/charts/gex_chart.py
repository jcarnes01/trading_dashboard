"""Interactive Gamma Exposure (GEX) profile chart component."""
import plotly.graph_objects as go
import streamlit as st

from core.models.options import OptionsStructure


def build_gex_profile_figure(structure: OptionsStructure) -> go.Figure:
    """Build interactive Plotly figure displaying per-strike Call, Put, and Net GEX."""
    if not structure.per_strike_gex:
        return go.Figure()

    strikes = [item.strike for item in structure.per_strike_gex]
    call_gex_m = [item.call_gex / 1_000_000.0 for item in structure.per_strike_gex]
    put_gex_m = [item.put_gex / 1_000_000.0 for item in structure.per_strike_gex]
    net_gex_m = [item.net_gex / 1_000_000.0 for item in structure.per_strike_gex]

    fig = go.Figure()

    # Call GEX Bars (Green - Dealer Long Gamma)
    fig.add_trace(
        go.Bar(
            x=strikes,
            y=call_gex_m,
            name="Call GEX (+$)",
            marker_color="rgba(34, 197, 94, 0.7)",
            hovertemplate="Strike: %{x}<br>Call GEX: $%{y:.2f}M<extra></extra>",
        )
    )

    # Put GEX Bars (Red - Dealer Short Gamma)
    fig.add_trace(
        go.Bar(
            x=strikes,
            y=put_gex_m,
            name="Put GEX (-$)",
            marker_color="rgba(239, 68, 68, 0.7)",
            hovertemplate="Strike: %{x}<br>Put GEX: $%{y:.2f}M<extra></extra>",
        )
    )

    # Net GEX Line
    fig.add_trace(
        go.Scatter(
            x=strikes,
            y=net_gex_m,
            name="Net GEX",
            mode="lines+markers",
            line=dict(color="#38bdf8", width=2.5),
            marker=dict(size=5),
            hovertemplate="Strike: %{x}<br>Net GEX: $%{y:.2f}M<extra></extra>",
        )
    )

    # Spot Price vertical reference line
    fig.add_vline(
        x=structure.underlying_spot,
        line_width=2,
        line_dash="dash",
        line_color="#facc15",
        annotation_text=f"{structure.symbol} Spot",
        annotation_position="top left",
    )

    # Call Wall reference line
    if structure.call_wall_gex:
        fig.add_vline(
            x=structure.call_wall_gex,
            line_width=1.5,
            line_dash="dot",
            line_color="#22c55e",
            annotation_text="GEX Call Wall",
            annotation_position="top right",
        )

    # Put Wall reference line
    if structure.put_wall_gex:
        fig.add_vline(
            x=structure.put_wall_gex,
            line_width=1.5,
            line_dash="dot",
            line_color="#ef4444",
            annotation_text="GEX Put Wall",
            annotation_position="bottom right",
        )

    # Zero Gamma reference line
    if structure.zero_gamma_strike:
        fig.add_vline(
            x=structure.zero_gamma_strike,
            line_width=1.5,
            line_dash="dot",
            line_color="#a855f7",
            annotation_text="Zero Gamma Flip",
            annotation_position="top right",
        )

    # Layout styling
    fig.update_layout(
        title=f"<b>{structure.symbol} Gamma Exposure (GEX) Profile by Strike</b>",
        xaxis_title="Strike Price",
        yaxis_title="Gamma Exposure ($ Millions)",
        barmode="relative",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=450,
        hovermode="x unified",
    )

    return fig


def render_gex_profile_chart(structure: OptionsStructure) -> None:
    """Render interactive GEX profile chart in Streamlit."""
    if not structure.per_strike_gex:
        st.info("Per-strike GEX data unavailable for chart rendering.")
        return

    fig = build_gex_profile_figure(structure)
    st.plotly_chart(fig, use_container_width=True)
