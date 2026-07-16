"""RealityAccordEngine — usable research library API. Author: Haxhijaha, Agim ORCID 0009-0002-3234-7765."""
from __future__ import annotations

from .core import (
    ConsequenceTube,
    HumanOptionalityReserve,
    PrivateWorldModel,
    ProposedEffect,
    run_accord_scenario,
)
from .types import ConcordanceDecision
from .validators import require_agent_id, require_position


class RealityAccordEngine:
    """Counterexample-bounded effect concordance with HOR gating.

    Usage:
        engine = RealityAccordEngine()
        engine.add_agent("robot_a", obstacles=[(5,5,0.5)], human_zones=[(8,1,0.4)], vmax=1.0)
        engine.propose_effect("move", target=(2,2), max_velocity=0.8, proposer_id="robot_a")
        decision = engine.decide()
    """

    def __init__(self) -> None:
        self._models: dict[str, PrivateWorldModel] = {}
        self._effect: ProposedEffect | None = None
        self._proposer_id: str | None = None

    def add_agent(
        self,
        agent_id: str,
        *,
        obstacles: list[tuple[float, float, float]] | None = None,
        human_zones: list[tuple[float, float, float]] | None = None,
        vmax: float = 1.0,
    ) -> None:
        agent_id = require_agent_id(agent_id)
        if agent_id in self._models:
            raise ValueError(f"duplicate agent: {agent_id}")
        self._models[agent_id] = PrivateWorldModel(
            agent_id=agent_id,
            obstacle_regions=list(obstacles or []),
            human_zones=list(human_zones or []),
            safe_velocity_max=float(vmax),
        )

    def propose_effect(
        self,
        effect_id: str,
        *,
        target: tuple[float, float],
        max_velocity: float,
        proposer_id: str,
        description: str = "",
    ) -> None:
        proposer_id = require_agent_id(proposer_id)
        if proposer_id not in self._models:
            raise ValueError(f"unknown proposer: {proposer_id}")
        target = require_position(target)
        self._proposer_id = proposer_id
        self._effect = ProposedEffect(
            effect_id=effect_id or "effect",
            description=description or effect_id,
            target_position=target,
            max_velocity=float(max_velocity),
            proposer_id=proposer_id,
        )

    def decide(self, name: str = "accord") -> ConcordanceDecision:
        if not self._models:
            tube = ConsequenceTube((0, 0), (0, 0), (0, 0), True, [])
            hor = HumanOptionalityReserve(0, 0, 100.0, True)
            return ConcordanceDecision(
                verdict="ACCEPT",
                hor_reserve_pct=100.0,
                tube_acceptable=True,
                concordant=True,
                counterexamples=[],
                consequence_tube=tube,
                hor=hor,
                interlock_token="empty",
                quarantined_agents=[],
            )
        if self._effect is None or self._proposer_id is None:
            raise ValueError("call propose_effect() before decide()")
        proposer = self._models[self._proposer_id]
        observers = [m for aid, m in self._models.items() if aid != self._proposer_id]
        scen = run_accord_scenario(name, proposer, observers, self._effect)
        return ConcordanceDecision(
            verdict=scen.accord.verdict,
            hor_reserve_pct=scen.hor.reserve_pct,
            tube_acceptable=scen.consequence_tube.acceptable,
            concordant=scen.accord.concordant,
            counterexamples=scen.counterexamples,
            consequence_tube=scen.consequence_tube,
            hor=scen.hor,
            interlock_token=scen.accord.interlock_token,
            quarantined_agents=scen.quarantined_agents,
        )
