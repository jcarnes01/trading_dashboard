"""Directional scoring and trading signal models."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class BiasDirection(str, Enum):
    """Directional bias regime."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class BiasSignal:
    """Consolidated market bias signal and options strategy playbook."""
    total_score: int
    max_possible_score: int
    direction: BiasDirection
    factor_breakdown: Dict[str, int]
    playbook_summary: str
    suggested_strategies: List[str] = field(default_factory=list)
