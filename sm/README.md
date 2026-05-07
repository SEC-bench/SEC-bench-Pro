# SpiderMonkey Verified Instances

This directory contains 80 verified Mozilla SpiderMonkey benchmark instances. Each instance is stored in its own numeric directory and includes the artifacts needed to reproduce and validate a real-world issue, such as `meta.json`, `poc.js`, `Report.md`, `VERIFIED.txt`, and execution logs.

The aggregate numbers below are derived from the current snapshot in this directory:

- `meta.json` provides the per-instance labels used for the vulnerability-type and error-type distributions.
- `crash_check.sh` runs each PoC against its docker image (100 iterations) and records the classified crash type in `output.txt`.

## Summary

- Total verified instances: 80
- Verification binary: `/out/js` (ASAN + debug SpiderMonkey JS shell, built per-instance; one CVE-2025-4919 instance uses `/out/js-release` to surface a wrong-result OOB inside a 4 GB allocation that ASAN does not flag)
- Source tree: `/src/gecko-dev` (revision pinned per-instance via Dockerfile)

Mozilla Foundation does not run a structured per-bug VRP payout for SpiderMonkey comparable to Chrome's VRP; every instance in this directory has `vrp: null`. The dataset is drawn from Bugzilla `sec-high` / `sec-critical` entries, MFSA advisories (2018 – 2026), Pwn2Own winners, CISA KEV in-the-wild exploited bugs, and the Anthropic/Claude-reported Firefox 148 batch (MFSA 2026-13 / 14 / 15).

## Vulnerability Type Distribution

| Vulnerability type | Count | Share |
| --- | ---: | ---: |
| Use-after-free | 27 | 33.75% |
| Type confusion | 15 | 18.75% |
| Out-of-bounds read | 6 | 7.5% |
| Incorrect JIT optimization | 6 | 7.5% |
| Cross-compartment violation | 5 | 6.25% |
| Stack corruption | 3 | 3.75% |
| Out-of-bounds write | 3 | 3.75% |
| Uninitialized memory read | 2 | 2.5% |
| Integer truncation | 2 | 2.5% |
| Integer overflow | 2 | 2.5% |
| Incorrect code generation | 2 | 2.5% |
| Stack buffer overflow | 1 | 1.25% |
| Race condition | 1 | 1.25% |
| Out-of-bounds access | 1 | 1.25% |
| Null pointer dereference | 1 | 1.25% |
| Invalid free | 1 | 1.25% |
| Debug assertion failure | 1 | 1.25% |
| Control-flow integrity violation | 1 | 1.25% |

## Error Type Distribution

| Error type | Count | Share |
| --- | ---: | ---: |
| `ASAN_CRASH` | 79 | 98.75% |
| `RUNTIME_CRASH` | 1 | 1.25% |
