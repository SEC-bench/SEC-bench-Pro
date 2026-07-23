# Mozilla SpiderMonkey Verified Instances

This directory contains 104 verified Mozilla SpiderMonkey benchmark instances. Each instance is stored in its own numeric directory and includes the artifacts needed to reproduce and validate a real-world issue, such as `meta.json`, `poc.js`, `Report.md`, `VERIFIED.txt`, `Dockerfile.fixed`, `patches/`, and execution logs.

The aggregate numbers below are derived from the current snapshot in this directory:

- `meta.json` provides the per-instance labels used for the vulnerability-type and error-type distributions.
- `output.txt` stores the validation log for the packaged PoC.

## Summary

- Total verified instances: 104
- Verification binary: `/out/js` (ASAN + debug SpiderMonkey JS shell, built per-instance; one CVE-2025-4919 instance uses `/out/js-release` to surface a wrong-result OOB inside a 4 GB allocation that ASAN does not flag)
- Source tree: `/src/gecko-dev` (revision pinned per-instance via Dockerfile)
- Fixed-image definitions: 104 instances include `Dockerfile.fixed` and `patches/`

## Fixed Images

The public fixed-image convention is
`hwiwonlee/sm.x86_64.fixed:<Bugzilla issue id>`. The grader uses this repository
by default. Build one tag locally with:

```sh
projects/sm/build_fixed_images.sh 1675905
python projects/sm/patch_check.py 1675905
```

For a release, validate and publish only tags absent from Docker Hub:

```sh
projects/sm/push_images.sh --fixed --missing --verify
```

`--verify` runs the packaged PoC against each fixed image before publishing.
Builds are per-instance SpiderMonkey builds and can require substantial CPU,
memory, disk, and elapsed time. Use `--image-repo` and grade with
`--fixed-repo` when publishing to a separate registry.

Mozilla Foundation does not run a structured per-bug VRP payout for SpiderMonkey comparable to Chrome's VRP; every instance in this directory has `vrp: null`. The dataset is drawn from Bugzilla `sec-high` / `sec-critical` entries, MFSA advisories (2018 – 2026), Pwn2Own winners, CISA KEV in-the-wild exploited bugs, and the Anthropic/Claude-reported Firefox 148 batch (MFSA 2026-13 / 14 / 15).

## Vulnerability Type Distribution

| Vulnerability type | Count | Share |
| --- | ---: | ---: |
| Use-after-free | 35 | 33.65% |
| Type confusion | 29 | 27.88% |
| Out-of-bounds read | 9 | 8.65% |
| Incorrect JIT optimization | 6 | 5.77% |
| Cross-compartment violation | 5 | 4.81% |
| Stack corruption | 3 | 2.88% |
| Out-of-bounds write | 3 | 2.88% |
| Uninitialized memory read | 2 | 1.92% |
| Integer truncation | 2 | 1.92% |
| Integer overflow | 2 | 1.92% |
| Incorrect code generation | 2 | 1.92% |
| Stack buffer overflow | 1 | 0.96% |
| Race condition | 1 | 0.96% |
| Null pointer dereference | 1 | 0.96% |
| Invalid free | 1 | 0.96% |
| Debug assertion failure | 1 | 0.96% |
| Control-flow integrity violation | 1 | 0.96% |

## Error Type Distribution

| Error type | Count | Share |
| --- | ---: | ---: |
| `ASAN_CRASH` | 100 | 96.15% |
| `RUNTIME_CRASH` | 4 | 3.85% |

## Regenerating the Numbers

The vulnerability-type and error-type tables can be recomputed from the `target_vulnerability_type` and `error_type` fields in each instance's `meta.json`.
