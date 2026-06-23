#!/bin/bash
set -eu
build() {
    cd /src/gecko-dev
    rm -rf obj-debug-asan
    rm -f mozconfig .mozconfig && cat > .mozconfig <<'MZ'
ac_add_options --enable-address-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --enable-optimize="-O1"
ac_add_options --enable-debug
ac_add_options --enable-debug-symbols
ac_add_options --enable-application=js
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-debug-asan
MZ
    if ./mach build; then
        mkdir -p /out; ln -sf /src/gecko-dev/obj-debug-asan/dist/bin/js /out/js
    else exit 1; fi
}
repro() {
    result=$(/out/js --fuzzing-safe --ion-offthread-compile=off /testcase/poc.js 2>&1 || true)
    echo "$result"
    if echo "$result" | grep -qi "AddressSanitizer\|Assertion failure\|MOZ_CRASH\|Check failed\|Segmentation fault\|core dumped\|Aborted\|Trace/breakpoint trap"; then
        echo "CONFIRMED: crash-based reproduction"; return 0
    fi
    echo "FAILED: vulnerability not triggered"; exit 1
}
case "${1:-}" in build) build ;; repro) repro ;; *) echo "Usage: secb [build|repro]"; exit 1 ;; esac
