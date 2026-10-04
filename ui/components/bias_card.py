"""Directional bias card and strategy playbook component."""
import streamlit as st
from core.models.signal import BiasDirection, BiasSignal


def render_bias_card(signal: BiasSignal) -> None:
    """Render directional bias banner, score breakdown, and suggested playbook strategies."""
    # Main directional alert banner
    if signal.direction == BiasDirection.BULLISH:
        st.success(signal.playbook_summary)
    elif signal.direction == BiasDirection.BEARISH:
        st.error(signal.playbook_summary)
    else:
        st.info(signal.playbook_summary)

    # Strategy recommendations & Factor chips
    c1, c2 = st.columns([3, 2])
    with c1:
        if signal.suggested_strategies:
            strat_html = " ".join(
                [f'<span class="strategy-pill">🎯 {s}</span>' for s in signal.suggested_strategies]
            )
            st.markdown(strat_html, unsafe_allow_html=True)

    with c2:
        factor_items = []
        for factor_name, score in signal.factor_breakdown.items():
            symbol = "🟢 +1" if score > 0 else ("🔴 -1" if score < 0 else "⚪ 0")
            factor_items.append(f'<span class="factor-pill">{factor_name}: {symbol}</span>')
        st.markdown(" ".join(factor_items), unsafe_allow_html=True)
