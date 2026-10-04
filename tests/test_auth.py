"""Unit tests for authentication gate."""
from unittest.mock import MagicMock, patch
import pytest

from config.settings import AppSettings
from ui.auth import render_auth_gate


def test_auth_gate_disabled():
    settings = AppSettings(auth_enabled=False)
    assert render_auth_gate(settings) is True


@patch("streamlit.sidebar")
@patch("streamlit.session_state", {"authenticated": True, "username": "trader"})
def test_auth_gate_already_authenticated(mock_sidebar):
    settings = AppSettings(auth_enabled=True)
    assert render_auth_gate(settings) is True


@patch("streamlit.form_submit_button", return_value=False)
@patch("streamlit.text_input")
@patch("streamlit.form")
@patch("streamlit.columns")
@patch("streamlit.session_state", {"authenticated": False})
def test_auth_gate_unauthenticated_prompts_form(mock_cols, mock_form, mock_input, mock_submit):
    mock_cols.return_value = [MagicMock(), MagicMock(), MagicMock()]
    settings = AppSettings(auth_enabled=True)
    assert render_auth_gate(settings) is False
