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
    # https://issues.chromium.org/issues/435630464: V8 Sandbox Bypass: In-sandbox corruption allows execution of dangerous / experimental code
    for i in $(seq 1 30); do
        set +e
        result=$(/out/d8 --sandbox-testing /testcase/poc.js 2>&1)
        set -e
        echo "$result"

        if echo "$result" | grep -q "V8 sandbox violation detected"; then
            return 0
        fi
    done
    echo "FAILED: no sandbox violation after 30 attempts"
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
