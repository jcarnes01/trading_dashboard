"""Lightweight in-app password gate for user authentication."""
import streamlit as st
from config.settings import AppSettings, default_settings


def render_auth_gate(settings: AppSettings = default_settings) -> bool:
    """Render a password gate, returning True if authenticated, False otherwise."""
    if not settings.auth_enabled:
        return True

    # Check session state
    if st.session_state.get("authenticated", False):
        with st.sidebar:
            st.markdown(f"👤 **Signed in:** `{st.session_state.get('username', 'trader')}`")
            if st.button("Sign Out", use_container_width=True):
                st.session_state["authenticated"] = False
                st.session_state.pop("username", None)
                st.rerun()
        return True

    # Render clean login card
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 🔐 SPX Morning Playbook Access")
        st.caption("Enter your credentials to access live dealer positioning & analytics.")

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="e.g. trader or friend")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                expected_password = settings.auth_credentials.get(username.strip())
                if expected_password and expected_password == password.strip():
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username.strip()
                    st.success("Access granted!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    return False
