#!/usr/bin/env python3
"""REALITY ACCORD Quickstart — concordance with HOR in ~25 lines."""
from reality_accord import RealityAccordEngine

engine = RealityAccordEngine()
engine.add_agent(
    "drone_pharmacy",
    obstacles=[(15.0, 15.0, 0.5)],
    human_zones=[(12.1, 7.6, 1.2)],
    vmax=1.0,
)
engine.add_agent(
    "drone_grocery",
    obstacles=[(12.0, 8.0, 0.9)],
    human_zones=[(12.4, 7.9, 0.9)],
    vmax=0.9,
)
engine.add_agent(
    "utm_monitor",
    obstacles=[],
    human_zones=[(12.1, 7.6, 1.5)],
    vmax=0.85,
)

engine.propose_effect(
    "corridor_claim",
    target=(12.0, 8.0),
    max_velocity=1.1,
    proposer_id="drone_pharmacy",
    description="Shared corridor within 5s",
)
decision = engine.decide()
print(f"Verdict: {decision.verdict}")
print(f"HOR: {decision.hor_reserve_pct}%")
print(f"Concordant: {decision.concordant}")
print(f"Counterexamples: {len(decision.counterexamples)}")
