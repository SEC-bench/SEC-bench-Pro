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
    # https://issuetracker.google.com/issues/342866373: V8 Sandbox Bypass: JSToWasmWrapperAsm accessible and allows type confusion
    result=$(cd /src/v8 && /out/d8 --sandbox-testing --allow-natives-syntax /testcase/poc.js 2>&1 || true)
    echo "$result"
    if echo "$result" | grep -qiE "V8 sandbox violation|Segmentation fault|SEGV|Aborted|core dumped"; then
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
