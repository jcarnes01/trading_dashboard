"""Unit tests for GEX chart builder."""
import plotly.graph_objects as go
import pytest

from core.models.options import OptionsStructure, StrikeGEX
from ui.charts.gex_chart import build_gex_profile_figure


def test_build_gex_profile_figure_with_data():
    sample_gex = [
        StrikeGEX(strike=4950.0, call_gex=2e6, put_gex=-10e6, net_gex=-8e6),
        StrikeGEX(strike=5000.0, call_gex=15e6, put_gex=-15e6, net_gex=0.0),
        StrikeGEX(strike=5050.0, call_gex=25e6, put_gex=-3e6, net_gex=22e6),
    ]

    structure = OptionsStructure(
        underlying_spot=5000.0,
        call_wall_oi=5050.0,
        put_wall_oi=4950.0,
        call_wall_gex=5050.0,
        put_wall_gex=4950.0,
        net_gex_total=14e6,
        zero_gamma_strike=5000.0,
        per_strike_gex=sample_gex,
    )

    fig = build_gex_profile_figure(structure)

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3  # Call GEX bars, Put GEX bars, Net GEX line
    assert fig.data[0].name == "Call GEX (+$)"
    assert fig.data[1].name == "Put GEX (-$)"
    assert fig.data[2].name == "Net GEX"


def test_build_gex_profile_figure_empty():
    structure = OptionsStructure(
        underlying_spot=5000.0,
        call_wall_oi=5050.0,
        put_wall_oi=4950.0,
        call_wall_gex=5050.0,
        put_wall_gex=4950.0,
        net_gex_total=0.0,
        zero_gamma_strike=None,
        per_strike_gex=[],
    )

    fig = build_gex_profile_figure(structure)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0
