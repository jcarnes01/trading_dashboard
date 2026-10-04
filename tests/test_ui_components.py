"""Unit tests verifying UI component interfaces and payload compatibility."""
from unittest.mock import MagicMock, patch
import pytest

from core.models.options import OptionsStructure
from providers.mock_provider import MockDataProvider
from services.dashboard_service import DashboardService
from ui.components import (
    render_bias_card,
    render_header,
    render_macro_matrix,
    render_structure_grid,
)
from ui.styles import inject_custom_styles


@pytest.fixture
def mock_payload():
    service = DashboardService(provider=MockDataProvider())
    return service.get_dashboard_payload()


@patch("streamlit.markdown")
def test_inject_custom_styles(mock_markdown):
    inject_custom_styles()
    mock_markdown.assert_called_once()


@patch("streamlit.toggle", return_value=False)
@patch("streamlit.radio", return_value="SPX")
@patch("streamlit.columns")
@patch("streamlit.caption")
@patch("streamlit.title")
def test_render_header(mock_title, mock_caption, mock_columns, mock_radio, mock_toggle, mock_payload):
    mock_columns.side_effect = [
        [MagicMock(), MagicMock()],
        [MagicMock(), MagicMock()],
    ]
    sym, auto_ref = render_header(mock_payload)
    mock_title.assert_called_with("SPX Morning Brief")
    mock_caption.assert_called_once()
    assert sym == "SPX"
    assert auto_ref is False


@patch("streamlit.columns")
@patch("streamlit.info")
@patch("streamlit.markdown")
def test_render_bias_card(mock_markdown, mock_info, mock_columns, mock_payload):
    mock_columns.return_value = [MagicMock(), MagicMock()]
    render_bias_card(mock_payload.bias_signal)
    mock_markdown.assert_called()


@patch("streamlit.expander")
@patch("streamlit.write")
@patch("streamlit.columns")
@patch("streamlit.subheader")
def test_render_structure_grid(mock_subheader, mock_columns, mock_write, mock_expander, mock_payload):
    mock_columns.side_effect = [
        [MagicMock(), MagicMock(), MagicMock()],
        [MagicMock(), MagicMock(), MagicMock(), MagicMock()],
    ]
    render_structure_grid(mock_payload.options_structure)
    mock_subheader.assert_called_with("SPX Structural Levels")
    mock_write.assert_called_once()


@patch("streamlit.columns")
@patch("streamlit.subheader")
def test_render_macro_matrix(mock_subheader, mock_columns, mock_payload):
    mock_columns.side_effect = [
        [MagicMock(), MagicMock()],
        [MagicMock(), MagicMock()],
        [MagicMock(), MagicMock()],
    ]
    render_macro_matrix(mock_payload.macro_snapshot)
    mock_subheader.assert_called_with("Macro Intermarket Matrix")


@patch("streamlit.dataframe")
@patch("streamlit.expander")
@patch("streamlit.columns")
@patch("streamlit.caption")
@patch("streamlit.subheader")
def test_render_catalysts_widget(mock_subheader, mock_caption, mock_columns, mock_expander, mock_df, mock_payload):
    from ui.components.catalysts_widget import render_catalysts_widget

    mock_columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
    render_catalysts_widget(mock_payload.catalysts)
    mock_subheader.assert_called_with("Market Catalysts & Volatility Calendar")
