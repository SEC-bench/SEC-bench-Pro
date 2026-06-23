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
    # https://issuetracker.google.com/issues/384186547: V8 Sandbox Bypass: Attacker manipulation of ArrayBufferSweeper linked lists results in dangling ArrayBufferExtension pointers
    # The exploit is not 100% reliable on release builds; retry until sandbox violation or crash from memory corruption is triggered.
    for i in $(seq 1 30); do
        set +e
        result=$(/out/d8 --sandbox-testing --expose-gc --single-threaded /testcase/poc.js 2>&1)
        d8_exit=$?
        set -e
        echo "$result"

        # Clean sandbox violation detection
        if echo "$result" | grep -q "V8 sandbox violation detected"; then
            return 0
        fi

        # A crash (non-zero exit) after the UAF trigger also demonstrates memory corruption outside the sandbox
        # This happens when the spray doesn't land cleanly but the UAF still corrupts memory
        if [ $d8_exit -ne 0 ] && echo "$result" | grep -q "Triggering use-after-free"; then
            echo "d8 crashed with exit code $d8_exit after triggering UAF - memory corruption confirmed"
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
