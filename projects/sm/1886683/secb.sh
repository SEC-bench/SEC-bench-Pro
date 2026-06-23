#!/bin/bash
set -eu
repro() {
    echo "TESTING POC..."
    result=$(/out/js --fast-warmup --ion-check-range-analysis --ion-extra-checks --fuzzing-safe --disable-oom-functions /testcase/poc.js 2>&1 || true)
    echo "$result"
    if echo "$result" | grep -qi "AddressSanitizer\|Assertion failure\|MOZ_CRASH\|Check failed\|Fatal error\|Segmentation fault\|core dumped\|Aborted\|TRAP"; then
        echo "CONFIRMED: crash-based reproduction"; return 0
    fi
    echo "FAILED: vulnerability not triggered"; exit 1
}
case "${1:-}" in build) cd /src/gecko-dev && ./mach build ;; repro) repro ;; *) echo "Usage: secb [build|repro]"; exit 1 ;; esac
