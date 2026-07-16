#!/usr/bin/env python3
"""
REALITY ACCORD Benchmark Harness — Concordance Performance & Correctness

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: Proof-of-concept benchmark only. Not production validation.
Stdlib only. Reuses reality_accord_gate.py and reality_accord_poc.py logic.
"""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from reality_accord_gate import (
    PrivateWorldModel3D,
    Vec3,
    accord_still_valid,
    build_scale_models,
    defense_model_spoofing,
    run_accord_protocol,
    test_cascading_effects,
    test_hor_stress,
    test_near_miss_quarantine,
    test_privacy,
    test_scale_3d,
    test_temporal_validity,
)
from reality_accord_poc import build_fail_models, build_pass_models, run_accord_scenario

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
DISCLAIMER = "PoC benchmark only — not production, not peer reviewed"
RESULTS_FILE = "ra_benchmark_results.json"


@dataclass
class ScenarioResult:
    name: str
    size: str
    expected_pass: bool
    actual_pass: bool
    execution_time_ms: float
    memory_bytes_peak: int
    details: dict[str, Any]


def _measure(
    name: str, size: str, expected_pass: bool, fn: Callable[[], tuple[bool, dict[str, Any]]]
) -> ScenarioResult:
    tracemalloc.start()
    t0 = time.perf_counter()
    actual_pass, details = fn()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return ScenarioResult(
        name=name, size=size, expected_pass=expected_pass, actual_pass=actual_pass,
        execution_time_ms=round(elapsed_ms, 3), memory_bytes_peak=peak, details=details,
    )


def s01_poc_pass() -> tuple[bool, dict[str, Any]]:
    proposer, observers, effect = build_pass_models()
    result = run_accord_scenario("pass", proposer, observers, effect)
    return result.accord.verdict == "ACCEPT", {"verdict": result.accord.verdict}


def s02_poc_fail_quarantine() -> tuple[bool, dict[str, Any]]:
    proposer, observers, effect = build_fail_models()
    result = run_accord_scenario("fail", proposer, observers, effect)
    return result.accord.verdict == "QUARANTINE", {
        "verdict": result.accord.verdict, "quarantined": result.quarantined_agents,
    }


def s03_model_spoofing() -> tuple[bool, dict[str, Any]]:
    d = defense_model_spoofing()
    return d.blocked, {"mechanism": d.mechanism}


def s04_near_miss() -> tuple[bool, dict[str, Any]]:
    t = test_near_miss_quarantine()
    return t.passed, {"verdict": t.details.get("verdict")}


def s05_privacy() -> tuple[bool, dict[str, Any]]:
    t = test_privacy()
    return t.passed, {"entropy_bits": t.details.get("reconstruction_entropy_bits")}


def s06_cascading_tube() -> tuple[bool, dict[str, Any]]:
    t = test_cascading_effects()
    return t.passed, {"secondary_margin": t.details.get("secondary_margin_x")}


def s07_scale_3d() -> tuple[bool, dict[str, Any]]:
    t = test_scale_3d()
    return t.passed, {"agents": t.details.get("agents"), "verdict": t.details.get("verdict")}


def s08_hor_stress() -> tuple[bool, dict[str, Any]]:
    t = test_hor_stress()
    return t.passed, {"refused_at_pct": t.details.get("refused_at_pct")}


def s09_temporal_validity() -> tuple[bool, dict[str, Any]]:
    t = test_temporal_validity()
    return t.passed, {"ttl_seconds": t.details.get("ttl_seconds")}


def s10_multi_observer_scale() -> tuple[bool, dict[str, Any]]:
    proposer, observers, effect = build_scale_models()
    extra = [
        PrivateWorldModel3D(
            f"agent-{label}",
            obstacle_regions=[(5.0 + i * 0.1, 5.0, 1.0, 0.4)],
            human_zones=[(8.0 + i * 0.1, 1.0, 0.5, 0.35)],
            safe_velocity_max=Vec3(1.0, 1.0, 0.4),
            intent_vector=Vec3(0.6, 0.2, 0.0),
        )
        for i, label in enumerate("FGHIJKLM")
    ]
    result = run_accord_protocol(proposer, observers + extra, effect)
    issued = datetime.fromisoformat(result["accord"].issued_at)
    valid = accord_still_valid(result["accord"], issued + timedelta(seconds=1))
    ok = result["accord"].verdict == "ACCEPT" and len(observers) + len(extra) >= 10 and valid
    return ok, {"observers": len(observers) + len(extra), "verdict": result["accord"].verdict}


SCENARIOS = [
    ("poc_concordance_pass", "small", True, s01_poc_pass),
    ("poc_conflict_quarantine", "small", True, s02_poc_fail_quarantine),
    ("model_spoofing_blocked", "small", True, s03_model_spoofing),
    ("near_miss_quarantine", "medium", True, s04_near_miss),
    ("privacy_no_reconstruction", "medium", True, s05_privacy),
    ("cascading_second_order_tube", "medium", True, s06_cascading_tube),
    ("scale_5_agents_3d", "large", True, s07_scale_3d),
    ("hor_stress_refuse_below_min", "large", True, s08_hor_stress),
    ("temporal_validity_ttl", "large", True, s09_temporal_validity),
    ("multi_observer_12_agents", "large", True, s10_multi_observer_scale),
]


def compute_rates(results: list[ScenarioResult]) -> dict[str, float]:
    total = len(results)
    correct = sum(1 for r in results if r.expected_pass == r.actual_pass)
    fp = sum(1 for r in results if not r.expected_pass and r.actual_pass)
    fn = sum(1 for r in results if r.expected_pass and not r.actual_pass)
    neg = sum(1 for r in results if not r.expected_pass)
    pos = sum(1 for r in results if r.expected_pass)
    return {
        "correctness_rate": round(correct / total, 4) if total else 0.0,
        "false_positive_rate": round(fp / neg, 4) if neg else 0.0,
        "false_negative_rate": round(fn / pos, 4) if pos else 0.0,
        "correct": correct, "false_positives": fp, "false_negatives": fn, "total": total,
    }


def scalability_projection(results: list[ScenarioResult]) -> dict[str, Any]:
    large = [r for r in results if r.size == "large"]
    base_ms = sum(r.execution_time_ms for r in large) / max(len(large), 1)
    base_agents = 5
    return {
        "baseline_ms": round(base_ms, 3),
        "baseline_reference": "mean of large scenarios",
        "assumption": "linear O(n) extrapolation over observer agent count",
        "projections": {
            "10x": round(base_ms * 10, 3),
            "100x": round(base_ms * 100, 3),
            "1000x": round(base_ms * 1000, 3),
        },
        "projected_agents": {"10x": base_agents * 10, "100x": base_agents * 100, "1000x": base_agents * 1000},
    }


def run_benchmark() -> dict[str, Any]:
    results = [_measure(name, size, exp, fn) for name, size, exp, fn in SCENARIOS]
    rates = compute_rates(results)
    scale = scalability_projection(results)
    by_size = {}
    for sz in ("small", "medium", "large"):
        subset = [r for r in results if r.size == sz]
        if subset:
            by_size[sz] = {
                "count": len(subset),
                "mean_time_ms": round(sum(r.execution_time_ms for r in subset) / len(subset), 3),
                "mean_memory_kb": round(sum(r.memory_bytes_peak for r in subset) / len(subset) / 1024, 2),
            }
    return {
        "framework": "REALITY_ACCORD",
        "harness": "ra_benchmark",
        "author": AUTHOR,
        "orcid": ORCID,
        "disclaimer": DISCLAIMER,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "scenarios": [
            {
                "name": r.name, "size": r.size, "expected_pass": r.expected_pass,
                "actual_pass": r.actual_pass, "correct": r.expected_pass == r.actual_pass,
                "execution_time_ms": r.execution_time_ms, "memory_bytes_peak": r.memory_bytes_peak,
                "memory_kb_peak": round(r.memory_bytes_peak / 1024, 2), "details": r.details,
            }
            for r in results
        ],
        "metrics": rates,
        "by_size": by_size,
        "scalability_projection": scale,
        "memory_profile": {
            "largest_scenario": max(results, key=lambda r: r.memory_bytes_peak).name,
            "peak_memory_bytes": max(r.memory_bytes_peak for r in results),
            "peak_memory_kb": round(max(r.memory_bytes_peak for r in results) / 1024, 2),
        },
    }


def print_summary(report: dict[str, Any]) -> None:
    m, s = report["metrics"], report["scalability_projection"]
    print("\n" + "=" * 72)
    print("REALITY ACCORD BENCHMARK SUMMARY")
    print("=" * 72)
    print(f"{'SCENARIO':<42} {'SIZE':<8} {'PASS':<6} {'TIME(ms)':>10} {'MEM(KB)':>10}")
    print("-" * 72)
    for sc in report["scenarios"]:
        mark = "OK" if sc["correct"] else "MISS"
        print(f"{sc['name']:<42} {sc['size']:<8} {mark:<6} {sc['execution_time_ms']:>10.1f} {sc['memory_kb_peak']:>10.1f}")
    print("-" * 72)
    print(f"Correctness rate    : {m['correctness_rate']:.1%} ({m['correct']}/{m['total']})")
    print(f"False positive rate : {m['false_positive_rate']:.1%}")
    print(f"False negative rate : {m['false_negative_rate']:.1%}")
    print(f"\nScalability (baseline {s['baseline_ms']:.1f} ms):")
    for factor in ("10x", "100x", "1000x"):
        proj = s["projections"][factor]
        agents = s["projected_agents"][factor]
        print(f"  {factor:>5} (~{agents} agents): {proj:,.1f} ms ({proj / 1000:.2f} s)")
    print("=" * 72)


def main() -> int:
    print("REALITY ACCORD Benchmark Harness")
    print(f"Author: {AUTHOR} (ORCID {ORCID})")
    print(DISCLAIMER)
    report = run_benchmark()
    print_summary(report)
    out_path = Path(__file__).resolve().parent / RESULTS_FILE
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(f"\nResults written to: {out_path}")
    return 0 if report["metrics"]["correctness_rate"] == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
