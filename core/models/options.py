"""Options structure and gamma exposure domain models."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class StrikeGEX:
    """Per-strike Gamma Exposure breakdown."""
    strike: float
    call_gex: float          # Spot * Gamma * Call_OI * 100
    put_gex: float           # -Spot * Gamma * Put_OI * 100 (Dealer short put convention)
    net_gex: float           # call_gex + put_gex
    call_oi: float = 0.0
    put_oi: float = 0.0
    gamma: float = 0.0


@dataclass(frozen=True)
class OptionsStructure:
    """Synthesized options structure and dealer positioning boundaries."""
    underlying_spot: float

    # Open Interest Walls
    call_wall_oi: float
    put_wall_oi: float

    # Gamma Exposure (GEX) Boundaries & Metrics
    call_wall_gex: float             # Strike with largest positive Call GEX (dealer resistance)
    put_wall_gex: float              # Strike with most negative Put GEX (dealer support)
    net_gex_total: float             # Aggregate market net GEX
    zero_gamma_strike: Optional[float]  # Strike where net GEX flips from positive to negative
    per_strike_gex: List[StrikeGEX] = field(default_factory=list)

    # ATM Straddle & Expected Move
    atm_straddle_price: float = 0.0
    expected_move: float = 0.0
    expected_range_low: float = 0.0
    expected_range_high: float = 0.0

    # Metadata & Health flags
    is_fallback: bool = False
    expiration_date: str = ""
