#!/usr/bin/env python3
"""
REALITY ACCORD Stress-Scale Test — 10 agents, 100 world-model params each,
50 counterexample exchanges.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765
"""

from __future__ import annotations

import json
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reality_accord_poc import (
    PrivateWorldModel,
    ProposedEffect,
    generate_counterexample,
    run_accord_scenario,
)

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
OUT = Path(__file__).with_name("ra_stress_results.json")

BASE = {"agents": 10, "params_per_agent": 100, "exchanges": 50}


def build_models(n_agents: int, params: int) -> list[PrivateWorldModel]:
    models: list[PrivateWorldModel] = []
    for a in range(n_agents):
        obstacles = []
        humans = []
        # Split params across obstacle+human circles (3 floats each ≈ param units)
        # Use params entries as (x,y,r) tuples — ~params/3 regions, pad to params count
        n_obs = max(1, params // 4)
        n_hum = max(1, params // 4)
        for i in range(n_obs):
            obstacles.append((float(i % 20), float((i * 3) % 20), 0.2 + (i % 5) * 0.05))
        for i in range(n_hum):
            humans.append((float(5 + i % 15), float(5 + (i * 2) % 15), 0.3 + (i % 4) * 0.05))
        # Record param count as len(obstacles)*3 + len(humans)*3 + 1 vmax
        models.append(
            PrivateWorldModel(
                agent_id=f"robot_{a:02d}",
                obstacle_regions=obstacles,
                human_zones=humans,
                safe_velocity_max=0.8 + (a % 5) * 0.05,
            )
        )
    return models


def param_count(m: PrivateWorldModel) -> int:
    return len(m.obstacle_regions) * 3 + len(m.human_zones) * 3 + 1


def run_once(n_agents: int, params: int, exchanges: int) -> dict[str, Any]:
    tracemalloc.start()
    t0 = time.perf_counter()
    models = build_models(n_agents, params)
    t_build = time.perf_counter() - t0
    assert all(param_count(m) >= params * 0.5 for m in models)

    proposer = models[0]
    observers = models[1:]

    # Safe-ish effect far from dense zones
    effect_ok = ProposedEffect(
        effect_id="stress_safe",
        description="stress safe effect",
        target_position=(50.0, 50.0),
        max_velocity=0.5,
        proposer_id=proposer.agent_id,
    )
    effect_bad = ProposedEffect(
        effect_id="stress_conflict",
        description="stress conflict effect",
        target_position=(5.0, 5.0),
        max_velocity=1.5,
        proposer_id=proposer.agent_id,
    )

    t1 = time.perf_counter()
    scen_ok = run_accord_scenario("stress_ok", proposer, observers, effect_ok)
    scen_bad = run_accord_scenario("stress_bad", proposer, observers, effect_bad)
    t_accord = time.perf_counter() - t1

    t2 = time.perf_counter()
    exchange_hits = 0
    for i in range(exchanges):
        probe = ProposedEffect(
            effect_id=f"ex_{i:03d}",
            description="exchange",
            target_position=(float(i % 20), float((i * 2) % 20)),
            max_velocity=1.0,
            proposer_id=proposer.agent_id,
        )
        for m in models:
            cx = generate_counterexample(m, probe)
            if cx is not None:
                exchange_hits += 1
    t_exchanges = time.perf_counter() - t2

    # Concordance checks across all agents for a fixed effect
    t3 = time.perf_counter()
    for _ in range(exchanges):
        _ = run_accord_scenario("stress_loop", proposer, observers, effect_bad)
    t_concordance_loop = time.perf_counter() - t3

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total = time.perf_counter() - t0

    return {
        "scale": {
            "agents": n_agents,
            "params_per_agent_target": params,
            "params_per_agent_actual": [param_count(m) for m in models],
            "exchanges": exchanges,
        },
        "timing_s": {
            "build": round(t_build, 6),
            "accord_pair": round(t_accord, 6),
            "counterexample_exchanges": round(t_exchanges, 6),
            "concordance_loop_50": round(t_concordance_loop, 6),
            "total": round(total, 6),
            "per_exchange_ms": round(1000 * t_exchanges / max(exchanges, 1), 6),
            "per_concordance_check_ms": round(1000 * t_concordance_loop / max(exchanges, 1), 6),
        },
        "memory": {
            "current_bytes": current,
            "peak_bytes": peak,
            "peak_mb": round(peak / (1024 * 1024), 4),
        },
        "results": {
            "ok_verdict": scen_ok.accord.verdict,
            "bad_verdict": scen_bad.accord.verdict,
            "exchange_counterexample_hits": exchange_hits,
            "ok_hor": scen_ok.hor.reserve_pct,
            "bad_hor": scen_bad.hor.reserve_pct,
        },
    }


def main() -> int:
    curve = []
    for m in [1, 2, 5, 10]:
        n = BASE["agents"]  # keep agent count; scale params/exchanges
        params = BASE["params_per_agent"] * m
        exchanges = BASE["exchanges"] * m
        # Also scale agents modestly for higher multipliers
        n_agents = BASE["agents"] if m == 1 else BASE["agents"] * min(m, 5)
        if m == 10:
            n_agents = BASE["agents"] * 5  # cap agents; params/exchanges still 10x
        print(f"RA stress {m}x agents={n_agents} params={params} exchanges={exchanges}")
        row = run_once(n_agents, params, exchanges)
        row["multiplier"] = m
        curve.append(row)
        print(f"  total={row['timing_s']['total']}s peak_mb={row['memory']['peak_mb']}")

    base_t = curve[0]["timing_s"]
    ops = ["build", "accord_pair", "counterexample_exchanges", "concordance_loop_50"]
    bottleneck = max(ops, key=lambda k: base_t[k])
    growth = {
        op: [
            {
                "multiplier": r["multiplier"],
                "seconds": r["timing_s"][op],
                "vs_1x": round(r["timing_s"][op] / max(base_t[op], 1e-9), 3),
            }
            for r in curve
        ]
        for op in ops
    }

    out = {
        "framework": "REALITY_ACCORD",
        "script": "ra_stress.py",
        "author": AUTHOR,
        "orcid": ORCID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_target": BASE,
        "scalability_curve": curve,
        "bottleneck_operation": bottleneck,
        "bottleneck_rationale": (
            f"At 1×, '{bottleneck}' dominates; concordance loops scale with "
            "agents × exchanges × region checks."
        ),
        "growth_by_operation": growth,
        "pass": (
            curve[0]["scale"]["agents"] == 10
            and curve[0]["scale"]["exchanges"] == 50
            and min(curve[0]["scale"]["params_per_agent_actual"]) >= 50
            and len(curve) == 4
        ),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"bottleneck={bottleneck} pass={out['pass']}")
    print(f"Wrote {OUT.name}")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
