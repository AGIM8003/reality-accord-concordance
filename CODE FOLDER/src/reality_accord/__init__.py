"""REALITY ACCORD — Counterexample-Bounded Effect Concordance (research library)."""
from .core import (
    HOR_MINIMUM_PCT,
    AccordResult,
    AccordScenarioResult,
    ConsequenceTube,
    HumanOptionalityReserve,
    PrivacyMinimizedCounterexample,
    PrivateWorldModel,
    ProposedEffect,
    classify_position,
    compute_consequence_tube,
    compute_hor,
    generate_counterexample,
    issue_accord_result,
    run_accord_scenario,
)
from .engine import RealityAccordEngine
from .types import ConcordanceDecision

__all__ = [
    "RealityAccordEngine",
    "ConcordanceDecision",
    "PrivateWorldModel",
    "ProposedEffect",
    "run_accord_scenario",
    "generate_counterexample",
    "compute_hor",
    "compute_consequence_tube",
    "classify_position",
    "issue_accord_result",
    "HOR_MINIMUM_PCT",
    "AccordResult",
    "AccordScenarioResult",
    "ConsequenceTube",
    "HumanOptionalityReserve",
    "PrivacyMinimizedCounterexample",
]
__version__ = "1.8.0"
