#!/usr/bin/env python3
"""
REALITY ACCORD Real-World Scenario — Delivery drones + pedestrian in shared airspace.

Two delivery drones need the same low-altitude corridor within ~5 seconds while a
human (ground worker / pedestrian) occupies a zone visible differently to each
drone's noisy world model. Concordance must resolve without full-plan disclosure;
HOR must keep intervention paths for the human supervisor (ATC-style).

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: Illustrative research fiction. Not production UTM software.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reality_accord_poc import (
    HOR_MINIMUM_PCT,
    PrivateWorldModel,
    ProposedEffect,
    generate_counterexample,
    run_accord_scenario,
    scenario_to_dict,
)

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
OUT = Path(__file__).with_name("ra_realworld_evidence.json")


def drone_kinematics(
    position: tuple[float, float, float],
    velocity: tuple[float, float, float],
    accel: tuple[float, float, float],
    dt: float = 5.0,
) -> tuple[float, float, float]:
    """Simple kinematic projection over the conflict horizon (seconds)."""
    x = position[0] + velocity[0] * dt + 0.5 * accel[0] * dt * dt
    y = position[1] + velocity[1] * dt + 0.5 * accel[1] * dt * dt
    z = position[2] + velocity[2] * dt + 0.5 * accel[2] * dt * dt
    return (round(x, 3), round(y, 3), round(z, 3))


def build_conflict() -> dict[str, Any]:
    """
    Urban last-mile corridor at (12.0, 8.0). Drone A plans entry; Drone B's map
    has a shifted obstacle; pedestrian zone differs by sensor noise.
    """
    # Physical state (3D)
    drone_a_state = {
        "agent": "drone_A_pharmacy",
        "position": (10.0, 8.0, 25.0),
        "velocity": (0.4, 0.0, 0.0),
        "acceleration": (0.05, 0.0, 0.0),
        "sensor_range_m": 40.0,
        "map_version": "A_city_grid_v3.2",
        "planner": "A*_energy_aware",
    }
    drone_b_state = {
        "agent": "drone_B_grocery",
        "position": (14.0, 8.2, 24.5),
        "velocity": (-0.35, -0.02, 0.0),
        "acceleration": (-0.04, 0.0, 0.0),
        "sensor_range_m": 35.0,
        "map_version": "B_city_grid_v3.1_stale_obstacle",
        "planner": "RRT*_time_optimal",
    }
    pedestrian = {
        "role": "ground_worker_crossing",
        "position": (12.1, 7.6, 0.0),
        "supervisor": "municipal_utm_controller",
    }

    pred_a = drone_kinematics(
        drone_a_state["position"],
        drone_a_state["velocity"],
        drone_a_state["acceleration"],
        5.0,
    )
    pred_b = drone_kinematics(
        drone_b_state["position"],
        drone_b_state["velocity"],
        drone_b_state["acceleration"],
        5.0,
    )
    conflict_distance = math.dist(pred_a[:2], pred_b[:2])

    # World models: different sensor noise / map versions (2D projection used by PoC)
    proposer = PrivateWorldModel(
        agent_id="drone_A_pharmacy",
        obstacle_regions=[(15.0, 15.0, 0.6), (20.0, 5.0, 0.5)],
        human_zones=[(12.1, 7.6, 1.2)],  # sees pedestrian clearly
        safe_velocity_max=1.0,
    )
    observer_b = PrivateWorldModel(
        agent_id="drone_B_grocery",
        # Stale map: thinks obstacle is at corridor center (false positive)
        obstacle_regions=[(12.0, 8.0, 0.9), (20.0, 5.0, 0.5)],
        # Noisier human zone (shifted)
        human_zones=[(12.4, 7.9, 0.9)],
        safe_velocity_max=0.9,
    )
    observer_utm = PrivateWorldModel(
        agent_id="utm_safety_monitor",
        obstacle_regions=[(15.0, 15.0, 0.55)],
        human_zones=[(12.1, 7.6, 1.5), (12.0, 8.5, 0.8)],
        safe_velocity_max=0.85,
    )

    # Unsafe proposed effect: both want corridor point near pedestrian
    unsafe_effect = ProposedEffect(
        effect_id="corridor_claim_t5s",
        description="Claim shared corridor waypoint (12.0, 8.0) within 5s horizon",
        target_position=(12.0, 8.0),
        max_velocity=1.1,
        proposer_id="drone_A_pharmacy",
    )
    # Safe alternative: offset away from human
    safe_effect = ProposedEffect(
        effect_id="corridor_offset_south",
        description="Offset claim to (12.0, 5.0) preserving human optionality",
        target_position=(12.0, 5.0),
        max_velocity=0.8,
        proposer_id="drone_A_pharmacy",
    )

    return {
        "kinematics": {
            "drone_a": drone_a_state,
            "drone_b": drone_b_state,
            "pedestrian": pedestrian,
            "predicted_a_t5": pred_a,
            "predicted_b_t5": pred_b,
            "predicted_xy_separation_m": round(conflict_distance, 3),
            "conflict_within_5s": conflict_distance < 3.0,
        },
        "models": (proposer, [observer_b, observer_utm]),
        "unsafe_effect": unsafe_effect,
        "safe_effect": safe_effect,
    }


def privacy_check(scenario_dict: dict[str, Any]) -> bool:
    """No counterexample may reveal full private model."""
    for cx in scenario_dict.get("counterexamples", []):
        if cx.get("reveals_full_model") is True:
            return False
    return True


def run() -> dict[str, Any]:
    built = build_conflict()
    proposer, observers = built["models"]

    reject = run_accord_scenario(
        "drone_corridor_conflict_REJECT_path",
        proposer,
        observers,
        built["unsafe_effect"],
    )
    accept = run_accord_scenario(
        "drone_corridor_offset_ACCEPT_path",
        proposer,
        observers,
        built["safe_effect"],
    )

    reject_d = scenario_to_dict(reject)
    accept_d = scenario_to_dict(accept)

    # Extra counterexample exchanges (sensor disagreement rounds)
    exchanges = []
    for i in range(50):
        # Probe slight position jitter as exchange rounds
        jitter = (12.0 + (i % 5) * 0.05, 8.0 - (i % 3) * 0.05)
        probe = ProposedEffect(
            effect_id=f"probe_exchange_{i:02d}",
            description="Counterexample exchange probe",
            target_position=jitter,
            max_velocity=1.0,
            proposer_id="drone_A_pharmacy",
        )
        cxs = []
        for m in [proposer, *observers]:
            cx = generate_counterexample(m, probe)
            if cx is not None:
                cxs.append(
                    {
                        "agent_id": cx.agent_id,
                        "scenario_class": cx.scenario_class,
                        "severity": cx.severity,
                        "reveals_full_model": cx.reveals_full_model,
                    }
                )
        exchanges.append({"round": i, "counterexamples": cxs})

    evidence = {
        "framework": "REALITY_ACCORD",
        "script": "ra_realworld.py",
        "author": AUTHOR,
        "orcid": ORCID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario": {
            "incident_class": "multi_agent_drone_airspace_conflict_with_human",
            "horizon_s": 5,
            "agents": ["drone_A_pharmacy", "drone_B_grocery", "utm_safety_monitor"],
            "human": built["kinematics"]["pedestrian"],
            "why_realistic": (
                "Last-mile drones share low-altitude corridors; map versions drift; "
                "sensor noise shifts human zones; UTM supervisors need HOR without "
                "each drone uploading its full flight plan."
            ),
            "kinematics": built["kinematics"],
        },
        "reject_path": {
            "verdict": reject.accord.verdict,
            "hor_pct": reject.hor.reserve_pct,
            "concordant": reject.accord.concordant,
            "counterexamples": len(reject.counterexamples),
            "privacy_minimized": privacy_check(reject_d),
            "report": reject_d,
        },
        "accept_path": {
            "verdict": accept.accord.verdict,
            "hor_pct": accept.hor.reserve_pct,
            "concordant": accept.accord.concordant,
            "counterexamples": len(accept.counterexamples),
            "privacy_minimized": privacy_check(accept_d),
            "report": accept_d,
        },
        "counterexample_exchanges": {
            "rounds": len(exchanges),
            "rounds_with_conflict_signal": sum(1 for e in exchanges if e["counterexamples"]),
            "any_full_model_leak": any(
                cx["reveals_full_model"]
                for e in exchanges
                for cx in e["counterexamples"]
            ),
        },
        "what_reality_accord_revealed": (
            "Unsafe corridor claim is REJECT/QUARANTINE with privacy-minimized "
            "counterexamples (obstacle/human classes) while the offset claim can "
            f"ACCEPT with HOR>={HOR_MINIMUM_PCT}% for the municipal UTM supervisor — "
            "without either drone revealing its full private world model or planner."
        ),
        "pass": (
            built["kinematics"]["conflict_within_5s"] is True
            and reject.accord.verdict in ("REJECT", "QUARANTINE")
            and privacy_check(reject_d)
            and privacy_check(accept_d)
            and accept.hor.reserve_pct >= HOR_MINIMUM_PCT
            and len(exchanges) == 50
            and not any(
                cx["reveals_full_model"]
                for e in exchanges
                for cx in e["counterexamples"]
            )
        ),
    }
    return evidence


def main() -> int:
    evidence = run()
    # Trim huge nested reports in printed size but keep full JSON
    OUT.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    print(
        f"RA real-world: pass={evidence['pass']} "
        f"reject={evidence['reject_path']['verdict']} "
        f"accept={evidence['accept_path']['verdict']} "
        f"HOR={evidence['accept_path']['hor_pct']}"
    )
    print(f"Wrote {OUT.name}")
    return 0 if evidence["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
