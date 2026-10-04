"""Options Morning Playbook - Streamlit bootstrap entry point."""
import streamlit as st

from config.settings import default_settings
from services.dashboard_service import DashboardPayload, DashboardService
from ui.auth import render_auth_gate
from ui.charts import render_gex_profile_chart, render_spx_price_chart
from ui.components import (
    render_bias_card,
    render_catalysts_widget,
    render_header,
    render_macro_matrix,
    render_structure_grid,
)
from ui.styles import inject_custom_styles

st.set_page_config(
    page_title="Options Morning Playbook",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Apply responsive styling
inject_custom_styles()

# Authentication Guard
if not render_auth_gate(default_settings):
    st.stop()

# Initialize application service
service = DashboardService(settings=default_settings)

# Read active ticker from session state (defaults to SPX)
active_symbol = st.session_state.get("underlying_ticker_selector", "SPX")


@st.cache_data(ttl=default_settings.macro_cache_ttl_seconds)
def load_dashboard_payload(symbol_key: str) -> DashboardPayload:
    """Fetch and compute market dashboard snapshot with caching."""
    return service.get_dashboard_payload(symbol_key=symbol_key)


# Fetch payload for initial render
initial_payload = load_dashboard_payload(active_symbol)

# Render Header with session badge, ticker switcher, and auto-refresh toggle
selected_symbol, auto_refresh_enabled = render_header(initial_payload, settings=default_settings)

# If user switched symbol, reload
if selected_symbol != active_symbol:
    active_symbol = selected_symbol
    initial_payload = load_dashboard_payload(active_symbol)


def render_dashboard_content(payload: DashboardPayload) -> None:
    """Render the primary dashboard views."""
    render_bias_card(payload.bias_signal)
    st.markdown("---")
    render_structure_grid(payload.options_structure)
    render_spx_price_chart(payload.options_structure, service=service)
    render_gex_profile_chart(payload.options_structure)
    st.markdown("---")
    render_macro_matrix(payload.macro_snapshot)
    st.markdown("---")
    render_catalysts_widget(payload.catalysts)


@st.fragment(run_every=60)
def render_live_auto_refresh_view(symbol: str) -> None:
    """Live auto-refresh container polling every 60 seconds."""
    payload = service.get_dashboard_payload(symbol_key=symbol)
    render_dashboard_content(payload)


@st.fragment
def render_cached_view(symbol: str) -> None:
    """Standard cached container with 300s TTL."""
    payload = load_dashboard_payload(symbol)
    render_dashboard_content(payload)


# Render body based on auto-refresh toggle
if auto_refresh_enabled:
    render_live_auto_refresh_view(active_symbol)
else:
    render_cached_view(active_symbol)
