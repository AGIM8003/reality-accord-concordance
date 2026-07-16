#!/usr/bin/env python3
"""
REALITY ACCORD Alternative Implementation — Statistical hypothesis testing style.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: PoC alternative implementation only. Not production, not peer reviewed.
Models as distributions; concordance as non-rejection of compatibility hypothesis.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
HOR_MINIMUM = 25.0


def gaussian_pdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        return 0.0
    z = (x - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2 * math.pi))


def compatibility_pvalue(mu_a: float, mu_b: float, sigma: float = 0.15) -> float:
    """Two-sided style distance test: larger distance → smaller p (reject compatibility)."""
    dist = abs(mu_a - mu_b)
    # map distance to pseudo-p in (0,1]
    return math.exp(-dist / max(sigma, 1e-6))


def consequence_tube(mu: float, sigma: float, z: float = 1.96) -> tuple[float, float]:
    return (mu - z * sigma, mu + z * sigma)


def hor_from_paths(safe_paths: int, total_paths: int) -> float:
    if total_paths <= 0:
        return 0.0
    return 100.0 * safe_paths / total_paths


def decide(models: list[dict[str, Any]], effect_mu: float, alpha: float = 0.2) -> dict[str, Any]:
    """
    Each model has belief mu about effect position.
    Reject concordance if any model pairwise p < alpha vs proposer belief,
    or if critical severity counterexamples exist.
    """
    counterexamples = []
    for m in models[1:]:
        p = compatibility_pvalue(effect_mu, m["mu"])
        if p < alpha or m.get("critical_conflict"):
            counterexamples.append({
                "agent": m["agent_id"],
                "p_compat": round(p, 4),
                "class": m.get("conflict_class", "distribution_mismatch"),
                "severity": "CRITICAL" if m.get("critical_conflict") or p < alpha / 2 else "HIGH",
            })
    tube = consequence_tube(effect_mu, 0.1)
    # HOR: paths that remain optional for human (models without critical conflict)
    safe = sum(1 for m in models if not m.get("critical_conflict"))
    hor = hor_from_paths(safe, len(models))
    if counterexamples or hor < HOR_MINIMUM:
        verdict = "QUARANTINE"
    else:
        verdict = "ACCEPT"
    return {
        "verdict": verdict,
        "counterexamples": counterexamples,
        "consequence_tube": {"x": tube, "acceptable": verdict == "ACCEPT"},
        "hor_pct": round(hor, 2),
    }


def pass_models() -> list[dict[str, Any]]:
    return [
        {"agent_id": "proposer", "mu": 2.0},
        {"agent_id": "obs-A", "mu": 2.02},
        {"agent_id": "obs-B", "mu": 1.98},
    ]


def fail_models() -> list[dict[str, Any]]:
    return [
        {"agent_id": "proposer", "mu": 2.0},
        {"agent_id": "pedestrian-sensor", "mu": 2.0, "critical_conflict": True, "conflict_class": "human_proximity"},
        {"agent_id": "vehicle-radar", "mu": 3.5, "critical_conflict": True, "conflict_class": "obstacle_collision"},
    ]


def direct_reference(pass_case: bool) -> dict[str, Any]:
    if pass_case:
        return {"verdict": "ACCEPT", "hor_pct": 100.0}
    return {"verdict": "QUARANTINE", "hor_pct": round(100.0 * 1 / 3, 2)}


def main() -> int:
    print("REALITY ACCORD Alternative Implementation (hypothesis testing)")
    print(f"Author: {AUTHOR} ORCID {ORCID}")
    p = decide(pass_models(), 2.0)
    f = decide(fail_models(), 2.0)
    pref = direct_reference(True)
    fref = direct_reference(False)
    agree = p["verdict"] == pref["verdict"] and f["verdict"] == fref["verdict"]
    evidence = {
        "framework": "REALITY_ACCORD",
        "author": AUTHOR,
        "orcid": ORCID,
        "disclaimer": "PoC replication evidence only — not production",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "primary_style": "direct_counterexample_concordance",
        "alternative_style": "statistical_hypothesis_testing",
        "pass_case": p,
        "fail_case": f,
        "reference": {"pass": pref, "fail": fref},
        "replication_pass": agree,
    }
    out = Path(__file__).resolve().parent / "ra_replication_evidence.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"PASS={p['verdict']} HOR={p['hor_pct']}%")
    print(f"FAIL={f['verdict']} HOR={f['hor_pct']}%")
    print(f"Replication agree: {agree}")
    print(f"Evidence: {out}")
    return 0 if agree else 1


if __name__ == "__main__":
    sys.exit(main())
