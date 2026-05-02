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
    # https://issuetracker.google.com/issues/348598133: DCHECK failure in size() > index in small-vector.h
    result=$(/out/d8 --allow-natives-syntax --experimental-wasm-jspi /testcase/poc.js 2>&1 || true)
    echo "$result"
    if echo "$result" | grep -q "Debug check failed"; then
        return 0
    fi
    echo "FAILED: debug check not triggered"
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
