#!/bin/bash
set -eu
build() {
    echo "BUILDING THE PROJECT..."
    cd /src/gecko-dev
    rm -rf obj-debug-asan
    rm -f mozconfig .mozconfig && cat > .mozconfig <<'EOF'
ac_add_options --enable-address-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --enable-optimize="-O1"
ac_add_options --enable-debug
ac_add_options --enable-debug-symbols
ac_add_options --enable-application=js
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-debug-asan
EOF
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
    # Bug 1675905 / CVE-2020-26950: MCallGetProperty marked idempotent but
    # fun_resolve has write side-effects → IC reallocation invalidates the
    # cached object. --no-warp forces Ion path; --no-threads keeps deterministic.
    result=$(/out/js --fuzzing-safe --no-warp --no-threads /testcase/poc.js 2>&1 || true)
    echo "$result"
    if echo "$result" | grep -qi "AddressSanitizer\|Assertion failure\|MOZ_CRASH\|Check failed\|Fatal error\|Segmentation fault\|core dumped\|Aborted\|Trace/breakpoint trap"; then
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
