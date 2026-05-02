#!/bin/bash
set -eu

: "${FUZZING_LANGUAGE:=c}"
export FUZZING_LANGUAGE

build() {
    echo "BUILDING THE PROJECT..."
    if /usr/local/bin/compile 1>/dev/null; then
        echo "BUILD COMPLETED SUCCESSFULLY!"
    else
        echo "BUILD FAILED!"
        exit 1
    fi
}

repro() {
    echo "TESTING POC..."
    # https://issues.chromium.org/issues/379009132: Potential type confusion in wasm and js interaction
    # Run from v8 root so wasm-module-builder.js is accessible via relative path.
    result=$(cd /src/v8 && /out/d8 --jit-fuzzing /testcase/poc.js 2>&1 || true)
    echo "$result"
    if echo "$result" | grep -qi "Check failed\|Fatal error\|Aborted\|AddressSanitizer"; then
        return 0
    fi
    echo "FAILED: crash not triggered"
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
