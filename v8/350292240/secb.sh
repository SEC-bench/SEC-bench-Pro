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
    # https://issues.chromium.org/issues/350292240: V8 Sandbox Bypass: AAR/W via generic function table call_indirect rtt check bypass
    # Run from v8 root so wasm-module-builder.js is accessible via relative path.
    result=$(cd /src/v8 && /out/d8 --sandbox-testing /testcase/poc.js 2>&1 || true)
    echo "$result"
    if echo "$result" | grep -q "V8 sandbox violation"; then
        return 0
    fi
    echo "FAILED: sandbox violation not triggered"
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
