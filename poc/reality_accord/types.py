"""REALITY ACCORD public types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core import (
    AccordResult,
    AccordScenarioResult,
    ConsequenceTube,
    HumanOptionalityReserve,
    PrivacyMinimizedCounterexample,
    PrivateWorldModel,
    ProposedEffect,
)


@dataclass
class ConcordanceDecision:
    verdict: str
    hor_reserve_pct: float
    tube_acceptable: bool
    concordant: bool
    counterexamples: list[PrivacyMinimizedCounterexample]
    consequence_tube: ConsequenceTube
    hor: HumanOptionalityReserve
    interlock_token: str
    quarantined_agents: list[str] = field(default_factory=list)
