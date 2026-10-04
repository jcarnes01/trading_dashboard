"""Custom CSS injection and visual styling utilities."""
import streamlit as st


def inject_custom_styles() -> None:
    """Inject polished, responsive CSS styles into the Streamlit app."""
    custom_css = """
    <style>
        /* Compact typography & padding for responsive mobile screens */
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2.5rem;
            max-width: 1200px;
        }

        /* Metric card styling */
        [data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 12px 16px;
        }

        /* Strategy badge pills */
        .strategy-pill {
            display: inline-block;
            background: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.35);
            border-radius: 16px;
            padding: 4px 12px;
            font-size: 0.85rem;
            margin-right: 8px;
            margin-top: 6px;
            font-weight: 500;
        }

        /* Factor badge pills */
        .factor-pill {
            display: inline-block;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 2px 10px;
            font-size: 0.8rem;
            margin-right: 6px;
            margin-top: 4px;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
