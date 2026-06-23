# Linux Kernel Verified Instances

This directory contains 137 verified Linux kernel 1-day CVE benchmark
instances. Each CVE is stored in its own `CVE-*` directory and ships Docker
definitions for a vulnerable KASAN kernel/rootfs and a fixed-kernel image that
verifies the upstream patch closes the issue. PoC sources stay on the host and
are copied into `/src/linux/audit` by the oracle at evaluation time.

The aggregate numbers below are derived from the current snapshot in this
directory:

- `meta.json` provides per-instance labels for the vulnerability-type,
error-type, and subsystem tables.
- `VERIFIED.txt` / `FIX-VERIFIED.txt` presence determines the verified counts.
- `meta.kctf.submission_ids` identifies kernelCTF-sourced entries.

## Summary

- Total verified instances:                         **137**
- Verified on vulnerable image (`VERIFIED.txt`):     **137**
- Verified on fixed image (`FIX-VERIFIED.txt`):      **137**
- Patch regressions (`FIX-NOT-MITIGATED.txt`):       **0**
- Composition by source:
  - kernelCTF-curated (original): **89**
  - syzbot-sourced (verified import): **48**
- Formal kernelCTF submissions (`meta.kctf.submission_ids`): **87 / 137 = 63.5%**
- Non-formal entries (50): the 48 syzbot-sourced leaves, plus
  `CVE-2021-22555` and `CVE-2022-0185` (kernelCTF set, retained without
  submission ids)
- Verification binary: `/out/bzImage` (KASAN-instrumented x86_64 kernel, built per-instance from a pinned upstream commit at `meta.kernel.build_commit`)
- Source tree: `/src/linux` (cloned `torvalds/linux`)
- Schema version (verified entries only): all 137 entries are `schema_version: 3`

The dataset combines Google's kernelCTF mitigation/LTS submissions (public
kernel-bug bounty/exploit catalog) with a verified set of syzbot-sourced
1-day CVEs; each leaf is independently confirmed on both its vulnerable and
fixed image.

## Vulnerability Type Distribution

Computed over the 137 verified entries. Hyphen and case variants of the same
class are merged for the table below; `meta.json` itself is unchanged.


| Vulnerability type                      | Count | Share |
| --------------------------------------- | ----- | ----- |
| Use After Free                          | 75    | 54.7% |
| Out-of-bounds Read                      | 25    | 18.2% |
| Out-of-bounds Write                     | 11    | 8.0%  |
| Double Free                             | 4     | 2.9%  |
| Heap Out-of-bounds Write                | 4     | 2.9%  |
| Heap Out-of-bounds Read                 | 4     | 2.9%  |
| Race Condition / Use After Free         | 3     | 2.2%  |
| Double Free / Use After Free            | 3     | 2.2%  |
| Out-of-bounds Read/Write                | 2     | 1.5%  |
| Integer Underflow / Out-of-bounds Write | 1     | 0.7%  |
| Reference Counter Overflow              | 1     | 0.7%  |
| Stack Out-of-bounds                     | 1     | 0.7%  |
| Use After Free / Double Free            | 1     | 0.7%  |
| Use After Free (race)                   | 1     | 0.7%  |
| Use of Uninitialized Variable           | 1     | 0.7%  |


Normalization rules applied (34 entries):

- `Use-After-Free` → `Use After Free`
- `Double Free / Use-After-Free` → `Double Free / Use After Free`
- `Out-of-Bounds Read` → `Out-of-bounds Read`
- `Out-of-Bounds Write` → `Out-of-bounds Write`

## Error Type Distribution

Computed over the 137 verified entries. The labels match the verdicts emitted
by `secb.sh` (see *Verdict ladder* below).


| Error type          | Count | Share |
| ------------------- | ----- | ----- |
| `KASAN_UAF`         | 89    | 65.0% |
| `KASAN_OOB`         | 46    | 33.6% |
| `KASAN_DOUBLE_FREE` | 2     | 1.5%  |


`KASAN_OOB_WRITE` (1 entry) merged into `KASAN_OOB` to match `secb.sh`'s
verdict ladder, which collapses heap / global / stack OOB into one bucket.

### Why the two tables don't add up by UAF

The two distributions measure **different axes** and should not be summed
across:

- **Vulnerability type** is the *root-cause label* recorded in
  `meta.json.target_vulnerability_type` (taken from upstream CVE / commit
  descriptions).
- **Error type** is the *runtime signal* `secb.sh`'s verdict ladder
  actually printed (see *Verdict ladder* below).

The same bug class can surface as a different KASAN report, and vice
versa. Concretely, of the 89 `KASAN_UAF` entries:

- 82 come from a vulnerability type whose label already contains "Use
  After Free".
- 7 come from labels that are **not** UAF on paper but still trip KASAN's
  use-after-free check at runtime: 3 × `Double Free`
  (`CVE-2024-1085`, `CVE-2024-1086`, `CVE-2024-26809`),
  1 × `Reference Counter Overflow` (`CVE-2023-3609`),
  1 × `Heap Out-of-bounds Write` (`CVE-2023-6560`), 1 × `Out-of-bounds
  Write` (`CVE-2025-37752`), and 1 × `Use of Uninitialized Variable`
  (`CVE-2024-26824`). Double-free bugs in particular are usually caught
  by KASAN on the second access path as use-after-free.

82 + 7 = 89, and both tables independently sum to the 137 verified entries.

## Subsystem Distribution

Computed over the 137 verified entries' `target_subdir` values. Listed are
all 22 subsystems with count ≥ 2; one CVE may touch multiple subsystems
so the column sum exceeds 137.


| Subsystem (`target_subdir`) | Count |
| --------------------------- | ----- |
| `net/netfilter`             | 28    |
| `net/sched`                 | 27    |
| `net` (top-level)           | 6     |
| `net/tls`                   | 5     |
| `fs/ocfs2`                  | 4     |
| `kernel/bpf`                | 4     |
| `fs/ntfs3`                  | 4     |
| `fs/ext4`                   | 3     |
| `crypto`                    | 3     |
| `net/ipv4`                  | 3     |
| `lib`                       | 3     |
| `net/bluetooth`             | 3     |
| `io_uring`                  | 3     |
| `fs/udf`                    | 3     |
| `kernel/events`             | 2     |
| `net/xfrm`                  | 2     |
| `fs/f2fs`                   | 2     |
| `drivers/net`               | 2     |
| `net/netfilter/ipset`       | 2     |
| `fs/hfs`                    | 2     |
| `fs/jfs`                    | 2     |
| `fs` (top-level)            | 2     |


Tail entries (count = 1 each): `arch/x86/kernel`, `drivers/acpi/nfit`,
`drivers/tty/vt`, `fs/bcachefs`, `fs/btrfs`, `fs/erofs`, `fs/fuse`,
`fs/hfsplus`, `fs/isofs`, `fs/nilfs2`, `fs/orangefs`, `fs/smb/client`,
`include/net/netfilter`, `kernel`, `kernel/trace`, `net/bridge/netfilter`,
`net/dsa`, `net/ethtool`, `net/ipv4/netfilter`, `net/ipv6/netfilter`,
`net/netfilter/ipvs`, `net/packet`, `net/qrtr`, `net/unix`,
`net/vmw_vsock`, `net/xdp`.

Networking subsystems (CVEs touching any `net/`*, `drivers/net`, or
`include/net/`* path) account for **87 of the 137 verified entries
(63.5%)**; within that, `net/netfilter` and `net/sched` remain the two
largest single subsystems. The syzbot import broadens the dataset well
beyond networking, adding substantial filesystem coverage (`fs/ocfs2`,
`fs/ntfs3`, `fs/ext4`, `fs/udf`, `fs/f2fs`, `fs/jfs`, `fs/hfs`, and more).

## Per-CVE Layout

```
projects/linux/CVE-YYYY-NNNNN/
├── meta.json                      Bug metadata (kernel commit, error_type, ...)
├── secb_config.json               Runtime config for audit-style images
├── Dockerfile                     KASAN-vuln image, FROM hwiwonlee/linux.base
├── Dockerfile.fixed               Vuln image + patches/ → fixed kernel
├── build.sh                       In-container kernel/PoC/initramfs build
├── secb.sh                        In-container harness (build | repro | validate)
├── init.sh                        Initramfs PID 1: brings up /proc, runs poc.sh
├── poc.sh                         exec /poc/poc (driver shim)
├── config/kernel.config.additions Kconfig deltas applied on top of x86_64_defconfig
├── poc/poc.c                      Reproducer source
├── patches-pre/*.patch            Optional prerequisite patches for vuln image
├── patches/*.patch                Upstream fix patch(es) — used by Dockerfile.fixed
├── output.txt                     Latest `secb repro` log on the vuln kernel
├── output.fixed.txt               Latest `secb repro` log on the fixed kernel
├── VERIFIED.txt                   Present iff vuln run ended with CONFIRMED:* verdict
├── FIX-VERIFIED.txt               Present iff fixed run ended NO_CRASH_DETECTED (patch holds)
└── FIX-NOT-MITIGATED.txt          Present iff fixed run still crashes (regression)
```

## Top-Level Layout

```
projects/linux/
├── README.md
├── build_images.py                Build orchestrator for base/vuln/fixed/latest images
├── crash_check.sh                 Authoritative vuln-side oracle (host re-greps serial log; retries)
├── patch_check.py                 Authoritative fix-side oracle (REPRODUCED vs UNBLOCKED_CRASH semantics)
├── push_images.sh                 Push built image tags
└── CVE-YYYY-NNNNN/                Self-contained leaves (one per CVE)
```

Linux base image definitions live in `base/linux/` at the repository root.

## Quick Start

```bash
# Build the base image once.
python3 projects/linux/build_images.py --mode base --kbuild-jobs 32

# One CVE: vuln image + run.
python3 projects/linux/build_images.py --mode vuln --instances CVE-2022-0185 --kbuild-jobs 32
projects/linux/crash_check.sh CVE-2022-0185
# -> CONFIRMED: KASAN_OOB

# Same CVE: fixed image + run (expect NO_CRASH_DETECTED).
python3 projects/linux/build_images.py --mode fixed --instances CVE-2022-0185 --kbuild-jobs 32
python3 projects/linux/patch_check.py CVE-2022-0185 --attempts 3
# -> NO_CRASH_DETECTED

# Mass-build everything. --kbuild-jobs caps each kernel build inside Docker.
python3 projects/linux/build_images.py --mode all --kbuild-jobs 32 -j 2
```

## Container invocation

Per-leaf images intentionally do **not** declare an `ENTRYPOINT` or `CMD`.
The oracles start a temporary container, copy the host PoC bundle into
`/src/linux/audit`, run `secb build` to rebuild the PoC/initramfs with that
PoC against the existing compiled kernel image, then run `secb repro`:

```sh
projects/linux/crash_check.sh <CVE>
python3 projects/linux/patch_check.py <CVE> --attempts 3
```

Because nothing is wired to PID 1, images are also directly usable for ad-hoc
inspection without overriding an entrypoint. Vulnerable images intentionally
do not contain a baked `/poc` tree:

```sh
docker run --rm hwiwonlee/linux.x86_64:<CVE> git -C /src/linux log -1 --oneline
docker run --rm hwiwonlee/linux.x86_64:<CVE> test ! -e /poc
docker run --rm -it hwiwonlee/linux.x86_64:<CVE> bash
```

For iterative PoC work inside a container, edit or mount a source directory
and run `secb validate /path/to/audit`. That stages the directory as
`/src/linux/audit`, rebuilds only the PoC/initramfs by default, and boots the
already compiled `/out/bzImage`. Use `SECB_REBUILD_KERNEL=1 secb validate ...`
only when the kernel image itself must be rebuilt.

## Authoritative oracle (grader interface)

For grading or CI use the dedicated oracle pair, which copies host PoC sources
into the image, rebuilds the initramfs, **re-greps the serial log host-side**
(decoupled from any per-leaf `secb.sh` drift), and **retries** by default
(kernel boot/repro can be non-deterministic):

```sh
# Vuln-side: did the PoC actually trigger the recorded error_type?
projects/linux/crash_check.sh CVE-2022-0185           # default ATTEMPTS=3
ATTEMPTS=5 projects/linux/crash_check.sh CVE-2022-0185

# Fix-side: is the patch actually mitigating this PoC?
python3 projects/linux/patch_check.py CVE-2022-0185 --attempts 3
```

Exit-code contract (stable; downstream graders depend on it):

| Script           | exit 0                                    | exit 1                                                                                                                                                            | exit 2                              |
| ---------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| `crash_check.sh` | first attempt produced any `CONFIRMED:*`  | no attempt produced a verdict                                                                                                                                     | harness error (missing meta/image)  |
| `patch_check.py` | every attempt was `NO_CRASH_DETECTED`     | at least one attempt was `REPRODUCED:<TYPE>` (intended bug came back) or `UNBLOCKED_CRASH:<TYPE>` (unrelated crash on the fixed kernel — also a fail)             | harness error                       |

- **Trust model.** The oracle ignores the in-container verdict line and
  applies its own regex ladder host-side, so a broken `secb.sh` in one leaf
  cannot mis-grade the dataset.
- **Retries.** `crash_check.sh` and `patch_check.py` retry (default 3,
  override `ATTEMPTS=` / `--attempts=`) to absorb boot/race flakes.
- **Fixed-side semantics.** `patch_check.py` splits fixed-kernel failures into
  `REPRODUCED:<TYPE>` (the original bug regressed) vs
  `UNBLOCKED_CRASH:<TYPE>` (something *else* crashed on the fixed kernel) —
  both fail, but for different reasons.

`crash_check.sh` is marked `DO NOT EDIT THIS FILE!` because its output strings
(`CONFIRMED: KASAN_UAF`, etc.) are part of the public oracle contract.

## Verdict ladder

`secb repro` greps the serial log in this order; the first match wins:

1. `BUG: KASAN: use-after-free`               → `CONFIRMED: KASAN_UAF`
2. `BUG: KASAN: slab-out-of-bounds`           → `CONFIRMED: KASAN_OOB`
3. `BUG: KASAN: (global|stack|vmalloc)-out-of-bounds` → `CONFIRMED: KASAN_OOB`
4. `BUG: KASAN: double-free`                  → `CONFIRMED: KASAN_DOUBLE_FREE`
5. `BUG: KASAN: invalid-free`                 → `CONFIRMED: KASAN_INVALID_FREE`
6. `BUG: KASAN: null-ptr-deref`               → `CONFIRMED: KASAN_NULL_DEREF`
7. `general protection fault.*KASAN`          → `CONFIRMED: KASAN_GPF`
8. `KFENCE:`                                  → `CONFIRMED: KFENCE`
9. `UBSAN:`                                   → `CONFIRMED: UBSAN`
10. `Kernel panic - not syncing`              → `CONFIRMED: PANIC`
11. otherwise                                 → `NO_CRASH_DETECTED`

A plain `WARNING:` line is **not** a verdict signal. Many fix patches
add intentional sanity WARN_ONs that fire on the fixed kernel too —
treating them as crashes would mis-classify those fixes as regressions.
We strip `panic_on_warn=1` from the cmdline so a WARN does not get
promoted to PANIC either.

## Dataset State Markers

Every active CVE directory has `VERIFIED.txt` and `FIX-VERIFIED.txt`. A
`FIX-NOT-MITIGATED.txt` marker indicates a fixed-image regression; the current
snapshot has none.

## Regenerating the Numbers

The summary, vulnerability-type, error-type, and subsystem tables can be
recomputed from each instance's `meta.json`. The `[ -f $d/VERIFIED.txt ]`
guard restricts the distributions to the active verified entries.

```sh
root=projects/linux

# Vulnerability-type table (raw — apply the README normalization rules
# yourself for the merged view):
for d in "$root"/CVE-*/; do
    [ -f "$d/VERIFIED.txt" ] && jq -r '.target_vulnerability_type // "(unset)"' "$d/meta.json"
done | sort | uniq -c | sort -rn

# Error-type table:
for d in "$root"/CVE-*/; do
    [ -f "$d/VERIFIED.txt" ] && jq -r '.error_type // "(unset)"' "$d/meta.json"
done | sort | uniq -c | sort -rn

# Subsystem (target_subdir) distribution:
for d in "$root"/CVE-*/; do
    [ -f "$d/VERIFIED.txt" ] && jq -r '.target_subdir[]? // empty' "$d/meta.json"
done | sort | uniq -c | sort -rn

# Formal kernelCTF-sourced ratio (entries with meta.kctf.submission_ids
# non-empty). Result: 87 / 137 = 63.5%.
total=$(for d in "$root"/CVE-*/; do echo X; done | wc -l)
kctf=$(for d in "$root"/CVE-*/; do
    n=$(jq -r '.kctf.submission_ids // empty | length' "$d/meta.json")
    [ "${n:-0}" -gt 0 ] && echo X
done | wc -l)
printf '%d / %d = %.1f%%\n' "$kctf" "$total" "$(python3 -c "print(100*$kctf/$total)")"
# CVE-2021-22555 and CVE-2022-0185 are retained without formal kernelCTF
# submission ids.

# Verified-state counters:
ls -d "$root"/CVE-*/VERIFIED.txt 2>/dev/null | wc -l           # vuln-verified
ls -d "$root"/CVE-*/FIX-VERIFIED.txt 2>/dev/null | wc -l       # fix-verified
ls -d "$root"/CVE-*/FIX-NOT-MITIGATED.txt 2>/dev/null | wc -l  # patch regressions
```

## License

This directory follows the repository license. See `../../LICENSE`.
