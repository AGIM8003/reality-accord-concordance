# Reproducibility Guide — REALITY ACCORD

## Requirements
- Python 3.10+ (tested on 3.14.4)
- No external dependencies (stdlib only)

## Verify the Core Mechanism
```bash
python reality_accord_poc.py
python reality_accord_gate.py
python ra_benchmark.py
python ra_alt_impl.py
python ra_mutation_test.py
```

## Expected Output (last lines)
- `reality_accord_poc.py`: `REALITY ACCORD PoC complete.`
- `reality_accord_gate.py`: `GATE VERDICT: PASS`
- `ra_benchmark.py`: `Correctness rate    : 100.0% (10/10)`
- `ra_alt_impl.py`: `Replication agree: True`
- `ra_mutation_test.py`: `Mutation score: 90%` or higher

## Verification Time
All scripts complete in under 3 seconds on a standard machine.

## Evidence Files Generated
| File | Contents |
|------|----------|
| `reality_accord_evidence.json` | ACCEPT/QUARANTINE + HOR |
| `reality_accord_gate_results.json` | Gate + defenses |
| `ra_benchmark_results.json` | Benchmarks + scalability |
| `ra_replication_evidence.json` | Hypothesis-testing vs direct concordance |
| `ra_mutation_results.json` | Mutation detections |

## Author
Agim Haxhijaha · ORCID 0009-0002-3234-7765 · Independent Researcher

## REALITY_FORGE additions (v1.7.0)

```bash
python ra_realworld.py
python ra_stress.py
```

Expect EXIT 0 and JSON evidence/results beside the scripts. Deploy reference: `ra_deploy_manifest.json`.

## INVENTION_CRYSTALLIZATION (v1.8.0)

```bash
from reality_accord import RealityAccordEngine
python ra_quickstart.py
python ra_integration_test.py
```
