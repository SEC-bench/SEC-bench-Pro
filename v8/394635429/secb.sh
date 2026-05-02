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
    # This bug is a race condition (TOCTOU), so we loop until the sandbox violation triggers.
    for i in $(seq 1 20); do
        output=$(/out/d8 --sandbox-testing /src/v8/poc.js 2>&1 || true)
        echo "$output"
        if echo "$output" | grep -q "sandbox violation"; then
            return 0
        fi
    done
    echo "Sandbox violation not triggered after 20 attempts"
    return 1
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
