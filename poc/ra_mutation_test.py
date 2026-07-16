#!/usr/bin/env python3
"""REALITY ACCORD Mutation Testing. Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765. PoC only."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
HOR_MIN = 25.0


def decide(models: list[dict[str, Any]], hor_min: float = HOR_MIN) -> str:
    conflicts = [m for m in models if m.get("critical_conflict")]
    hor = 100.0 * (len(models) - len(conflicts)) / max(len(models), 1)
    if conflicts or hor < hor_min:
        return "QUARANTINE"
    return "ACCEPT"


def oracle(decide_fn: Callable) -> list[tuple[str, bool]]:
    pass_m = [{"agent_id": "a"}, {"agent_id": "b"}, {"agent_id": "c"}]
    fail_m = [{"agent_id": "a"}, {"agent_id": "b", "critical_conflict": True}, {"agent_id": "c", "critical_conflict": True}]
    tests = []
    tests.append(("pass_accept", decide_fn(pass_m) == "ACCEPT"))
    tests.append(("fail_quarantine", decide_fn(fail_m) == "QUARANTINE"))
    tests.append(("hor_gate", decide_fn([{"agent_id": "a", "critical_conflict": True}]) == "QUARANTINE"))
    tests.append(("single_clean_accept", decide_fn([{"agent_id": "a"}]) == "ACCEPT"))
    tests.append(("all_conflict", decide_fn([{"agent_id": "a", "critical_conflict": True}, {"agent_id": "b", "critical_conflict": True}]) == "QUARANTINE"))
    return tests


def main() -> int:
    rows = []

    def run(name, fn):
        try:
            results = oracle(fn)
            failed = [n for n, ok in results if not ok]
            rows.append({"name": name, "detected": bool(failed), "caught_by": failed[0] if failed else None})
        except Exception as exc:
            rows.append({"name": name, "detected": True, "caught_by": f"exc:{exc}"})

    run("skip_conflict_check", lambda m, hor_min=HOR_MIN: "ACCEPT")
    run("invert_verdict", lambda m, hor_min=HOR_MIN: "ACCEPT" if decide(m) == "QUARANTINE" else "QUARANTINE")
    run("ignore_hor", lambda m, hor_min=0.0: decide(m, hor_min=0.0) if not any(x.get("critical_conflict") for x in m) else "ACCEPT")
    run("always_quarantine", lambda m, hor_min=HOR_MIN: "QUARANTINE")
    run("hor_min_100", lambda m, hor_min=HOR_MIN: decide(m, hor_min=100.0))
    run("count_conflicts_wrong", lambda m, hor_min=HOR_MIN: "QUARANTINE" if len(m) > 10 else "ACCEPT")
    run("crash_on_fail_case", lambda m, hor_min=HOR_MIN: 1 / 0 if any(x.get("critical_conflict") for x in m) else "ACCEPT")
    run("drop_models", lambda m, hor_min=HOR_MIN: decide(m[:1], hor_min))
    run("no_init_conflicts", lambda m, hor_min=HOR_MIN: "ACCEPT" if m else "QUARANTINE")
    run("early_return_accept", lambda m, hor_min=HOR_MIN: "ACCEPT")

    detected = sum(1 for r in rows if r["detected"])
    score = detected / len(rows)
    report = {
        "framework": "REALITY_ACCORD",
        "author": AUTHOR,
        "orcid": ORCID,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mutations_total": len(rows),
        "mutations_detected": detected,
        "mutation_score": round(score, 3),
        "pass_threshold": 0.9,
        "mutations": rows,
        "suite_pass": score >= 0.9,
    }
    out = Path(__file__).resolve().parent / "ra_mutation_results.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"REALITY ACCORD mutation score: {score:.0%} ({detected}/{len(rows)})")
    for r in rows:
        print(f"  [{'CAUGHT' if r['detected'] else 'SURVIVED'}] {r['name']}")
    return 0 if report["suite_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
