# V8 Verified Instances

This directory contains 103 verified Chromium V8 benchmark instances. Each instance is stored in its own numeric directory and includes the artifacts needed to reproduce and validate a real-world issue, such as `meta.json`, `poc.js`, `Report.md`, `VERIFIED.txt`, and execution logs.

The aggregate numbers below are derived from the current snapshot in this directory:

- `check_bounties.py` parses each `Report.md` file and computes the VRP bounty totals.
- `meta.json` provides the per-instance labels used for the vulnerability-type and error-type distributions.

## Summary

- Total verified instances: 103
- Instances with a VRP bounty: 86
- Instances without a VRP bounty: 17
- Total VRP bounty: $1,540,750

Among the 17 non-bounty instances, the current `VRP-Reward` statuses are:

- `INT`: 8
- `DUP`: 5
- `BUG`: 2
- `CRN`: 1
- `TBD`: 1

## Vulnerability Type Distribution

| Vulnerability type | Count | Share |
| --- | ---: | ---: |
| Type confusion | 35 | 34.0% |
| Sandbox bypass | 15 | 14.6% |
| Use-after-free | 12 | 11.7% |
| Out-of-bounds write | 8 | 7.8% |
| Out-of-bounds read | 5 | 4.9% |
| Integer overflow | 4 | 3.9% |
| Race condition | 4 | 3.9% |
| Heap buffer overflow | 3 | 2.9% |
| Debug assertion failure | 2 | 1.9% |
| Out-of-bounds memory access | 2 | 1.9% |
| Stack corruption | 2 | 1.9% |
| Integer truncation | 2 | 1.9% |
| Hole leak | 2 | 1.9% |
| Incorrect JIT optimization | 1 | 1.0% |
| Incorrect code generation | 1 | 1.0% |
| Undefined Behavior (invalid enum variant) | 1 | 1.0% |
| Uninitialized memory read | 1 | 1.0% |
| Stack use-after-return | 1 | 1.0% |
| Control-flow integrity violation | 1 | 1.0% |
| Out-of-bounds read/write | 1 | 1.0% |

## Error Type Distribution

| Error type | Count | Share |
| --- | ---: | ---: |
| `SANDBOX_VIOLATION` | 50 | 48.5% |
| `DCHECK` | 21 | 20.4% |
| `ASAN_CRASH` | 17 | 16.5% |
| `RUNTIME_CRASH` | 15 | 14.6% |

## Regenerating The Numbers

Run the bounty analysis script from this directory:

```sh
python3 check_bounties.py
```

The vulnerability-type and error-type tables can be recomputed from the `target_vulnerability_type` and `error_type` fields in each instance's `meta.json`.
