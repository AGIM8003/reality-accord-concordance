"""REALITY ACCORD core protocol. Author: Haxhijaha, Agim ORCID 0009-0002-3234-7765."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
HOR_MINIMUM_PCT = 25.0


@dataclass
class PrivateWorldModel:
    """Agent-private beliefs — never exported in full."""

    agent_id: str
    obstacle_regions: list[tuple[float, float, float]]  # (x, y, radius)
    human_zones: list[tuple[float, float, float]]
    safe_velocity_max: float

    def model_digest(self) -> str:
        payload = json.dumps(
            {
                "agent": self.agent_id,
                "obstacles": len(self.obstacle_regions),
                "humans": len(self.human_zones),
                "vmax": self.safe_velocity_max,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class ProposedEffect:
    effect_id: str
    description: str
    target_position: tuple[float, float]
    max_velocity: float
    proposer_id: str


@dataclass
class PrivacyMinimizedCounterexample:
    """Harmful scenario class without revealing full private model."""

    agent_id: str
    scenario_class: str
    severity: str
    probe_digest: str
    model_digest: str
    reveals_full_model: bool = False


@dataclass
class ConsequenceTube:
    position_x_bounds: tuple[float, float]
    position_y_bounds: tuple[float, float]
    velocity_bounds: tuple[float, float]
    acceptable: bool
    basis_counterexamples: list[str]


@dataclass
class HumanOptionalityReserve:
    intervention_paths: int
    total_paths: int
    reserve_pct: float
    passes_gate: bool


@dataclass
class AccordResult:
    result_id: str
    verdict: str  # ACCEPT | REJECT | QUARANTINE
    effect_id: str
    interlock_token: str
    expires_at: str
    hor_reserve_pct: float
    tube_acceptable: bool
    concordant: bool


@dataclass
class AccordScenarioResult:
    name: str
    effect: ProposedEffect
    counterexamples: list[PrivacyMinimizedCounterexample]
    consequence_tube: ConsequenceTube
    hor: HumanOptionalityReserve
    accord: AccordResult
    quarantined_agents: list[str] = field(default_factory=list)


def classify_position(model: PrivateWorldModel, position: tuple[float, float]) -> str:
    x, y = position
    for ox, oy, radius in model.obstacle_regions:
        if (x - ox) ** 2 + (y - oy) ** 2 <= radius ** 2:
            return "UNSAFE_OBSTACLE"
    for hx, hy, radius in model.human_zones:
        if (x - hx) ** 2 + (y - hy) ** 2 <= radius ** 2:
            return "UNSAFE_HUMAN_PROXIMITY"
    return "SAFE"


def generate_counterexample(
    model: PrivateWorldModel, effect: ProposedEffect
) -> PrivacyMinimizedCounterexample | None:
    """Privacy-minimized counterexample: scenario class only, not raw model."""
    classification = classify_position(model, effect.target_position)
    if classification == "SAFE" and effect.max_velocity <= model.safe_velocity_max:
        return None

    if classification == "UNSAFE_OBSTACLE":
        scenario_class = "obstacle_collision_class_B"
        severity = "HIGH"
    elif classification == "UNSAFE_HUMAN_PROXIMITY":
        scenario_class = "human_proximity_class_H"
        severity = "CRITICAL"
    else:
        scenario_class = "velocity_exceeds_local_envelope"
        severity = "MEDIUM"

    probe = f"{scenario_class}:{effect.effect_id}:{model.model_digest()}"
    probe_digest = hashlib.sha256(probe.encode()).hexdigest()[:12]

    return PrivacyMinimizedCounterexample(
        agent_id=model.agent_id,
        scenario_class=scenario_class,
        severity=severity,
        probe_digest=probe_digest,
        model_digest=model.model_digest(),
        reveals_full_model=False,
    )


def compute_consequence_tube(
    effect: ProposedEffect,
    counterexamples: list[PrivacyMinimizedCounterexample],
    models: list[PrivateWorldModel],
) -> ConsequenceTube:
    """Bounded envelope of jointly acceptable outcomes."""
    x, y = effect.target_position
    margin = 0.15

    conflicting = [c for c in counterexamples if c.severity in ("HIGH", "CRITICAL")]
    velocity_cap = min((m.safe_velocity_max for m in models), default=effect.max_velocity)
    velocity_cap = min(velocity_cap, effect.max_velocity)

    acceptable = len(conflicting) == 0 and effect.max_velocity <= velocity_cap

    return ConsequenceTube(
        position_x_bounds=(round(x - margin, 3), round(x + margin, 3)),
        position_y_bounds=(round(y - margin, 3), round(y + margin, 3)),
        velocity_bounds=(0.0, round(velocity_cap, 3)),
        acceptable=acceptable,
        basis_counterexamples=[c.scenario_class for c in counterexamples],
    )


def compute_hor(
    models: list[PrivateWorldModel], effect: ProposedEffect
) -> HumanOptionalityReserve:
    """Human Optionality Reserve — fraction of intervention paths still viable."""
    total_paths = 0
    viable_paths = 0

    for model in models:
        for hx, hy, radius in model.human_zones:
            total_paths += 1
            dist_sq = (effect.target_position[0] - hx) ** 2 + (effect.target_position[1] - hy) ** 2
            if dist_sq > (radius * 2.5) ** 2:
                viable_paths += 1
            elif dist_sq > radius ** 2:
                viable_paths += 1  # partial intervention window

    if total_paths == 0:
        reserve_pct = 100.0
    else:
        reserve_pct = round(100.0 * viable_paths / total_paths, 2)

    return HumanOptionalityReserve(
        intervention_paths=viable_paths,
        total_paths=total_paths,
        reserve_pct=reserve_pct,
        passes_gate=reserve_pct >= HOR_MINIMUM_PCT,
    )


def issue_accord_result(
    effect: ProposedEffect,
    tube: ConsequenceTube,
    hor: HumanOptionalityReserve,
    counterexamples: list[PrivacyMinimizedCounterexample],
    concordant: bool,
) -> AccordResult:
    if not concordant or not tube.acceptable or not hor.passes_gate:
        verdict = "QUARANTINE" if not concordant else "REJECT"
    else:
        verdict = "ACCEPT"

    token_payload = f"{effect.effect_id}:{verdict}:{tube.acceptable}:{hor.reserve_pct}"
    interlock_token = hashlib.sha256(token_payload.encode()).hexdigest()[:20]
    result_id = hashlib.sha256(f"accord:{token_payload}".encode()).hexdigest()[:16]

    return AccordResult(
        result_id=result_id,
        verdict=verdict,
        effect_id=effect.effect_id,
        interlock_token=interlock_token,
        expires_at=datetime.now(timezone.utc).isoformat(),
        hor_reserve_pct=hor.reserve_pct,
        tube_acceptable=tube.acceptable,
        concordant=concordant,
    )


def run_accord_scenario(
    name: str,
    proposer: PrivateWorldModel,
    observers: list[PrivateWorldModel],
    effect: ProposedEffect,
) -> AccordScenarioResult:
    all_models = [proposer, *observers]
    counterexamples: list[PrivacyMinimizedCounterexample] = []

    for model in observers:
        cx = generate_counterexample(model, effect)
        if cx is not None:
            counterexamples.append(cx)

    proposer_cx = generate_counterexample(proposer, effect)
    if proposer_cx is not None:
        counterexamples.append(proposer_cx)

    response_classes = {classify_position(m, effect.target_position) for m in all_models}
    concordant = len(response_classes) == 1 and "SAFE" in response_classes

    tube = compute_consequence_tube(effect, counterexamples, all_models)
    hor = compute_hor(all_models, effect)
    accord = issue_accord_result(effect, tube, hor, counterexamples, concordant)

    quarantined: list[str] = []
    if accord.verdict == "QUARANTINE":
        quarantined = list({c.agent_id for c in counterexamples})

    return AccordScenarioResult(
        name=name,
        effect=effect,
        counterexamples=counterexamples,
        consequence_tube=tube,
        hor=hor,
        accord=accord,
        quarantined_agents=quarantined,
    )



