"""SPX Morning Playbook - Streamlit bootstrap entry point."""
import streamlit as st

from config.settings import default_settings
from services.dashboard_service import DashboardPayload, DashboardService
from ui.auth import render_auth_gate
from ui.charts import render_gex_profile_chart
from ui.components import (
    render_bias_card,
    render_header,
    render_macro_matrix,
    render_opex_widget,
    render_structure_grid,
)
from ui.styles import inject_custom_styles

st.set_page_config(
    page_title="SPX Morning Playbook",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Apply responsive styling
inject_custom_styles()

# Authentication Guard
if not render_auth_gate(default_settings):
    st.stop()


@st.cache_data(ttl=default_settings.macro_cache_ttl_seconds)
def load_dashboard_payload() -> DashboardPayload:
    """Fetch and compute market dashboard snapshot with caching."""
    service = DashboardService(settings=default_settings)
    return service.get_dashboard_payload()


# Fetch state payload
payload = load_dashboard_payload()

# Render modular views
render_header(payload)
render_bias_card(payload.bias_signal)
st.markdown("---")
render_structure_grid(payload.options_structure)
render_gex_profile_chart(payload.options_structure)
st.markdown("---")
render_macro_matrix(payload.macro_snapshot)
st.markdown("---")
render_opex_widget(payload.opex_events)
