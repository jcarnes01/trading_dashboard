"""Structural levels and Gamma Exposure (GEX) grid component."""
import pandas as pd
import streamlit as st
from core.models.options import OptionsStructure


def render_structure_grid(structure: OptionsStructure) -> None:
    """Render underlying spot, Open Interest walls, GEX barriers, and expected move range."""
    st.subheader(f"{structure.symbol} Structural Levels")

    # Primary Open Interest Barriers
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{structure.symbol} Spot", f"{structure.underlying_spot:,.1f}")
    c2.metric("Put Wall (OI Support)", f"{structure.put_wall_oi:,.0f}")
    c3.metric("Call Wall (OI Resistance)", f"{structure.call_wall_oi:,.0f}")

    # Gamma Exposure (GEX) Dynamics
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("GEX Put Wall", f"{structure.put_wall_gex:,.0f}", help="Lowest Put GEX strike: dealer short gamma accelerator/support")
    g2.metric("GEX Call Wall", f"{structure.call_wall_gex:,.0f}", help="Largest Call GEX strike: dealer long gamma magnet/resistance")
    zero_g_text = f"{structure.zero_gamma_strike:,.0f}" if structure.zero_gamma_strike else "N/A"
    g3.metric("Zero Gamma Flip", zero_g_text, help="Strike where aggregate dealer gamma changes regime")
    net_gex_m = structure.net_gex_total / 1_000_000.0
    g4.metric("Net GEX", f"${net_gex_m:+,.1f}M", help="Aggregate market dollar Gamma Exposure")

    # Expected Move Banner
    st.write(
        f"**Est. Daily Expected Move:** ±{structure.expected_move:.1f} pts "
        f"(Range: {structure.expected_range_low:,.0f} — {structure.expected_range_high:,.0f})"
    )

    # Optional detailed per-strike GEX table
    if structure.per_strike_gex:
        with st.expander("📊 View Per-Strike GEX Breakdown"):
            table_rows = []
            for item in structure.per_strike_gex:
                table_rows.append({
                    "Strike": f"{item.strike:,.0f}",
                    "Call GEX ($)": f"${item.call_gex:,.0f}",
                    "Put GEX ($)": f"${item.put_gex:,.0f}",
                    "Net GEX ($)": f"${item.net_gex:,.0f}",
                    "Call OI": f"{item.call_oi:,.0f}",
                    "Put OI": f"{item.put_oi:,.0f}",
                })
            df_table = pd.DataFrame(table_rows)
            st.dataframe(df_table, use_container_width=True, hide_index=True)
