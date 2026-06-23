#!/bin/bash
set -eu
build() {
    echo "BUILDING THE PROJECT..."
    cd /src/gecko-dev
    rm -rf obj-debug-asan
    if ./mach build; then
        mkdir -p /out
        ln -sf /src/gecko-dev/obj-debug-asan/dist/bin/js /out/js
        echo "BUILD COMPLETED SUCCESSFULLY!"
    else
        echo "BUILD FAILED!"; exit 1
    fi
}
repro() {
    echo "TESTING POC..."
    result=$(/out/js --fuzzing-safe --ion-offthread-compile=off /testcase/poc.js 2>&1 || true)
    echo "$result"
    if echo "$result" | grep -qi "AddressSanitizer\|Assertion failure\|MOZ_CRASH\|Check failed\|Fatal error\|Segmentation fault\|core dumped\|Aborted\|TRAP"; then
        echo "CONFIRMED: crash-based reproduction"
        return 0
    fi
    echo "FAILED: vulnerability not triggered"; exit 1
}
if [ "$#" -ge 1 ]; then
    case "$1" in
        build) build ;; repro) repro ;;
        *) echo "Usage: secb [build|repro]"; exit 1 ;;
    esac
else echo "Usage: secb [build|repro]"; exit 1; fi
