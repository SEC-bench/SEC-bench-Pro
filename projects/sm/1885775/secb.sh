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
        echo "BUILD FAILED!"
        exit 1
    fi
}

repro() {
    echo "TESTING POC..."
    # https://bugzilla.mozilla.org/show_bug.cgi?id=1966614
    # CVE-2025-4919: Incorrect bounds check elimination when using ExtractLinearSum
    # Bug type: silent OOB (no crash). Verification is output-based:
    #   Vulnerable: prints "0"  (OOB read succeeds, bounds check eliminated)
    #   Fixed:     prints "undefined" (bounds check correctly applied)
    result=$(/out/js --fuzzing-safe --ion-offthread-compile=off --spectre-mitigations=off /testcase/poc.js 2>&1 || true)
    echo "$result"

    # Check for ASAN/assertion crashes (in case future builds trigger them)
    if echo "$result" | grep -qi "AddressSanitizer\|Assertion failure\|MOZ_CRASH\|Check failed\|Fatal error\|Segmentation fault\|core dumped\|Aborted"; then
        echo "CONFIRMED: crash-based reproduction"
        return 0
    fi

    # Output-diff verification: vulnerable build outputs "0", not "undefined"
    if echo "$result" | grep -qx "0"; then
        echo "CONFIRMED: output-diff reproduction (OOB read returned 0, expected undefined)"
        return 0
    fi

    echo "FAILED: vulnerability not triggered (expected output '0', got '$result')"
    exit 1
}

if [ "$#" -ge 1 ]; then
    command="$1"
    case "$command" in
        build)
            build "$@"
            ;;
        repro)
            repro "$@"
            ;;
        *)
            echo "Unknown command: $command"
            echo "Usage: secb [build|repro]"
            exit 1
            ;;
    esac
else
    echo "Usage: secb [build|repro]"
    exit 1
fi
