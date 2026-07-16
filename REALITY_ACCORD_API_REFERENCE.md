# REALITY_ACCORD API Reference — v1.8.0

**Author:** Haxhijaha, Agim · ORCID `0009-0002-3234-7765`  
**License:** CC BY-NC-ND 4.0 (evaluation / research use of PoC code)  
**Import:** `from reality_accord import RealityAccordEngine`

## Quick Start

Run from `poc/`:

```bash
python ra_quickstart.py
```

See also: `poc/ra_quickstart.py`

## Classes

### RealityAccordEngine

Primary entry point. Accepts user-provided data, returns structured results, raises `ValueError` on malformed input. Stdlib only.

Public methods (see `poc/reality_accord/engine.py` for signatures):

- Constructor and state mutators (`add_*` / `set_*` / `propose_*` / `mark_*`)
- Analysis methods (`excise` / `attest` / `settle` / `decide`, plus helpers)
- Advanced accessors where applicable (`.graph` / `.scenario`)

### Result types

Returned as dataclasses (`ExcisionResult`, `AttestationReport`, `SettlementResult`, or `ConcordanceDecision`). Fields are typed and JSON-serializable for evidence capture.

## Configuration

Defaults are research-PoC defaults (e.g., ROOTFALL independence fail when hidden shared roots exist or score < 0.67; REALITY ACCORD HOR minimum 25%). Tune only with understanding that thresholds are heuristic pending calibration.

## Error Handling

| Condition | Exception |
|-----------|-----------|
| Empty / invalid ids | `ValueError` |
| Duplicates | `ValueError` |
| Unknown references | `ValueError` |
| Cycles (DERF) | `ValueError` |
| Missing prerequisite calls | `ValueError` |

## Limitations

- Not production software; not peer reviewed; not a compliance certification.
- Scale limits: see stress results in `poc/*_stress_results.json`.
- Architecture frozen — this library packages the blueprint mechanisms, it does not extend them.
