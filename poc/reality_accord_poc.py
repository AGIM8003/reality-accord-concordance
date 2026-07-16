#!/usr/bin/env python3
"""
REALITY ACCORD Proof-of-Concept — Counterexample-Bounded Effect Concordance.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765
DISCLAIMER: PoC only — not production, not peer reviewed.
Library API: `from reality_accord import RealityAccordEngine`
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reality_accord import (
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
from reality_accord.core import AUTHOR, ORCID

def print_scenario_report(scenario: AccordScenarioResult) -> None:
    print(f"\n=== {scenario.name} ===")
    print(f"Effect: {scenario.effect.description}")
    print(f"Proposer: {scenario.effect.proposer_id}")
    print(f"Counterexamples submitted: {len(scenario.counterexamples)}")
    for cx in scenario.counterexamples:
        print(
            f"  [{cx.agent_id}] {cx.scenario_class} ({cx.severity}) "
            f"probe={cx.probe_digest} reveals_model={cx.reveals_full_model}"
        )
    tube = scenario.consequence_tube
    print(
        f"Consequence tube: x={tube.position_x_bounds} y={tube.position_y_bounds} "
        f"v={tube.velocity_bounds} acceptable={tube.acceptable}"
    )
    print(
        f"Human Optionality Reserve: {scenario.hor.reserve_pct:.2f}% "
        f"({scenario.hor.intervention_paths}/{scenario.hor.total_paths} paths, "
        f"gate={'PASS' if scenario.hor.passes_gate else 'FAIL'})"
    )
    print(
        f"Accord Result: {scenario.accord.verdict} | token={scenario.accord.interlock_token} "
        f"| concordant={scenario.accord.concordant}"
    )
    if scenario.quarantined_agents:
        print(f"Quarantined agents: {', '.join(scenario.quarantined_agents)}")


def build_pass_models() -> tuple[PrivateWorldModel, list[PrivateWorldModel], ProposedEffect]:
    proposer = PrivateWorldModel(
        agent_id="robot-arm-A",
        obstacle_regions=[(5.0, 5.0, 0.5)],
        human_zones=[(8.0, 1.0, 0.4)],
        safe_velocity_max=1.2,
    )
    observer_b = PrivateWorldModel(
        agent_id="safety-monitor-B",
        obstacle_regions=[(5.1, 5.1, 0.45)],
        human_zones=[(8.2, 1.1, 0.35)],
        safe_velocity_max=1.0,
    )
    observer_c = PrivateWorldModel(
        agent_id="floor-scanner-C",
        obstacle_regions=[(4.9, 4.8, 0.55)],
        human_zones=[(7.8, 0.9, 0.5)],
        safe_velocity_max=1.1,
    )
    effect = ProposedEffect(
        effect_id="eff-pass-001",
        description="Robot arm moves to position X=(2.0, 2.0)",
        target_position=(2.0, 2.0),
        max_velocity=0.8,
        proposer_id="robot-arm-A",
    )
    return proposer, [observer_b, observer_c], effect


def build_fail_models() -> tuple[PrivateWorldModel, list[PrivateWorldModel], ProposedEffect]:
    proposer = PrivateWorldModel(
        agent_id="delivery-robot-D",
        obstacle_regions=[(1.0, 1.0, 0.3)],
        human_zones=[(3.0, 3.0, 0.5)],
        safe_velocity_max=1.5,
    )
    observer_e = PrivateWorldModel(
        agent_id="pedestrian-sensor-E",
        obstacle_regions=[(1.0, 1.0, 0.3)],
        human_zones=[(2.0, 2.0, 0.8)],  # human believed near target
        safe_velocity_max=0.9,
    )
    observer_f = PrivateWorldModel(
        agent_id="vehicle-radar-F",
        obstacle_regions=[(2.5, 2.5, 1.2)],  # obstacle at target per this model
        human_zones=[(6.0, 6.0, 0.4)],
        safe_velocity_max=1.0,
    )
    effect = ProposedEffect(
        effect_id="eff-fail-002",
        description="Robot arm moves to position X=(2.0, 2.0)",
        target_position=(2.0, 2.0),
        max_velocity=1.2,
        proposer_id="delivery-robot-D",
    )
    return proposer, [observer_e, observer_f], effect


def scenario_to_dict(scenario: AccordScenarioResult) -> dict[str, Any]:
    return {
        "name": scenario.name,
        "effect": asdict(scenario.effect),
        "counterexamples": [asdict(c) for c in scenario.counterexamples],
        "consequence_tube": asdict(scenario.consequence_tube),
        "human_optionality_reserve": asdict(scenario.hor),
        "accord_result": asdict(scenario.accord),
        "quarantined_agents": scenario.quarantined_agents,
    }


def main() -> None:
    print("REALITY ACCORD PoC - Counterexample-Bounded Effect Concordance")
    print(f"Author: {AUTHOR} | ORCID: {ORCID}")

    pass_proposer, pass_observers, pass_effect = build_pass_models()
    fail_proposer, fail_observers, fail_effect = build_fail_models()

    pass_case = run_accord_scenario(
        "Concordance PASS (compatible private models)",
        pass_proposer,
        pass_observers,
        pass_effect,
    )
    fail_case = run_accord_scenario(
        "Concordance FAIL (conflicting models -> quarantine)",
        fail_proposer,
        fail_observers,
        fail_effect,
    )

    print_scenario_report(pass_case)
    print_scenario_report(fail_case)

    print("\n--- Human Optionality Reserve Summary ---")
    print(f"PASS case HOR: {pass_case.hor.reserve_pct:.2f}%")
    print(f"FAIL case HOR: {fail_case.hor.reserve_pct:.2f}%")

    evidence = {
        "poc": "REALITY_ACCORD",
        "author": AUTHOR,
        "orcid": ORCID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Proof-of-concept only. Not production. Not peer reviewed.",
        "hor_minimum_pct": HOR_MINIMUM_PCT,
        "demonstrations": {
            "concordance_pass": scenario_to_dict(pass_case),
            "conflict_quarantine": scenario_to_dict(fail_case),
        },
        "success_criteria": {
            "pass_verdict_accept": pass_case.accord.verdict == "ACCEPT",
            "fail_verdict_quarantine": fail_case.accord.verdict == "QUARANTINE",
            "privacy_preserved": all(
                not c.reveals_full_model for c in pass_case.counterexamples + fail_case.counterexamples
            ),
        },
    }

    out_path = Path(__file__).resolve().parent / "reality_accord_evidence.json"
    out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"\nEvidence written: {out_path}")
    print("REALITY ACCORD PoC complete.")


if __name__ == "__main__":
    main()

