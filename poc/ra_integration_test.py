#!/usr/bin/env python3
"""REALITY ACCORD public API integration tests."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from reality_accord import RealityAccordEngine

OUT = Path(__file__).with_name("ra_integration_results.json")


def run() -> dict:
    results = []

    e = RealityAccordEngine()
    d = e.decide()
    results.append({"name": "empty_input", "pass": d.verdict == "ACCEPT"})

    e = RealityAccordEngine()
    e.add_agent("solo", obstacles=[], human_zones=[], vmax=1.0)
    e.propose_effect("go", target=(1.0, 1.0), max_velocity=0.5, proposer_id="solo")
    d = e.decide()
    results.append({"name": "single_agent", "pass": d.verdict == "ACCEPT"})

    e = RealityAccordEngine()
    e.add_agent("a", obstacles=[(5, 5, 0.5)], human_zones=[(8, 1, 0.4)], vmax=1.0)
    e.add_agent("b", obstacles=[(5.1, 5.1, 0.45)], human_zones=[(8.2, 1.1, 0.35)], vmax=1.0)
    e.propose_effect("safe", target=(1.0, 1.0), max_velocity=0.5, proposer_id="a")
    d = e.decide()
    results.append({"name": "typical_safe", "pass": d.verdict == "ACCEPT" and d.concordant})

    e = RealityAccordEngine()
    for i in range(12):
        e.add_agent(f"r{i}", obstacles=[(float(i), float(i), 0.3)], human_zones=[(20.0, 20.0, 0.5)], vmax=1.0)
    e.propose_effect("probe", target=(0.0, 0.0), max_velocity=0.4, proposer_id="r0")
    d = e.decide()
    results.append({"name": "large_scale_12_agents", "pass": d.verdict in ("ACCEPT", "REJECT", "QUARANTINE")})

    ok_err = True
    e = RealityAccordEngine()
    e.add_agent("x")
    try:
        e.add_agent("x")
        ok_err = False
    except ValueError:
        pass
    try:
        e.propose_effect("e", target=(0, 0), max_velocity=1.0, proposer_id="missing")
        ok_err = False
    except ValueError:
        pass
    e2 = RealityAccordEngine()
    e2.add_agent("y")
    try:
        e2.decide()
        ok_err = False
    except ValueError:
        pass
    results.append({"name": "error_handling", "pass": ok_err})

    e = RealityAccordEngine()
    e.add_agent("a", obstacles=[], human_zones=[(10, 10, 0.5)], vmax=1.0)
    e.add_agent("b", obstacles=[], human_zones=[(10.1, 10.1, 0.5)], vmax=1.0)
    e.propose_effect("agree", target=(0, 0), max_velocity=0.5, proposer_id="a")
    d = e.decide()
    results.append({"name": "all_agents_agree", "pass": d.concordant and d.verdict == "ACCEPT"})

    return {
        "framework": "REALITY_ACCORD",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "pass": all(x["pass"] for x in results),
    }


def main() -> int:
    evidence = run()
    OUT.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"RA integration pass={evidence['pass']}")
    return 0 if evidence["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
