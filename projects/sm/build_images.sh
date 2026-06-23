#!/bin/bash

# Build Docker images for all subdirectories in spidermonkey/
# Each subdirectory name is used as the image ID
# Usage: build_images.sh [-n NUM_WORKERS] [instance_id ...]

# Require bash >= 4.3 for wait -n support
if (( BASH_VERSINFO[0] < 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] < 3) )); then
    echo "Error: bash >= 4.3 required (found ${BASH_VERSION})" >&2
    exit 1
fi

set -o pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
RUN_TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
NUM_WORKERS=1

usage() {
    echo "Usage: $(basename "$0") [-n NUM_WORKERS] [instance_id ...]"
    echo "  -n NUM_WORKERS  Number of parallel build workers (default: 1)"
    echo "  instance_id     Optional explicit instance IDs to build"
    exit 1
}

while getopts ":n:" opt; do
    case $opt in
        n) NUM_WORKERS="$OPTARG" ;;
        :) echo "Error: -$OPTARG requires an argument" >&2; usage ;;
        \?) echo "Error: Unknown option -$OPTARG" >&2; usage ;;
    esac
done

shift $((OPTIND - 1))

if ! [[ "$NUM_WORKERS" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: -n must be a positive integer, got: '$NUM_WORKERS'" >&2
    exit 1
fi

echo "Building Docker images from: $SCRIPT_DIR"
echo "Parallel workers: $NUM_WORKERS"

TMP_DIR="$(mktemp -d)"
interrupted=0
echo 0 > "$TMP_DIR/.completed"
trap 'rm -rf "$TMP_DIR"' EXIT

handle_interrupt() {
    interrupted=1
    echo "" >&2
    echo -e "\033[1;31mInterrupted. Killing active build jobs...\033[0m" >&2
    trap - INT TERM
    local pids
    pids=$(jobs -p)
    [[ -n "$pids" ]] && kill $pids 2>/dev/null
    wait 2>/dev/null
    exit 130
}
trap handle_interrupt INT TERM

print_progress() {
    local status="$1"
    local done="$2"
    local total="$3"
    local id="$4"

    case "$status" in
        ok)
            echo -e "\033[1;32m[OK]    [$done/$total] $id\033[0m"
            ;;
        fail)
            echo -e "\033[1;31m[FAIL]  [$done/$total] $id\033[0m"
            ;;
    esac
}

build_one() {
    local id="$1"
    local dir="$2"
    local total="$3"
    local log_file="$TMP_DIR/${id}.log"
    local result_file="$TMP_DIR/${id}.result"

    {
        flock -x 9
        echo -e "\033[1;34m[START] $id\033[0m"
    } 9>"$TMP_DIR/.output.lock"

    if docker build -t "hwiwonlee/sm.x86_64:$id" "$dir" >"$log_file" 2>&1; then
        echo "succeeded" > "$result_file"
        {
            flock -x 9
            local done
            done=$(( $(cat "$TMP_DIR/.completed") + 1 ))
            echo "$done" > "$TMP_DIR/.completed"
            print_progress "ok" "$done" "$total" "$id"
        } 9>"$TMP_DIR/.output.lock"
    else
        echo "failed" > "$result_file"
        {
            flock -x 9
            local done
            done=$(( $(cat "$TMP_DIR/.completed") + 1 ))
            echo "$done" > "$TMP_DIR/.completed"
            print_progress "fail" "$done" "$total" "$id"
        } 9>"$TMP_DIR/.output.lock"
    fi
}

all_dirs=()
explicit_selection=0

if (( $# > 0 )); then
    explicit_selection=1
    mapfile -t selected_ids < <(printf '%s\n' "$@" | sort -u)

    for id in "${selected_ids[@]}"; do
        dir="$SCRIPT_DIR/$id"
        if [[ ! -d "$dir" ]]; then
            echo "Error: instance directory not found: '$id'" >&2
            exit 1
        fi
        all_dirs+=("$dir")
    done
else
    for dir in "$SCRIPT_DIR"/*/; do
        id="$(basename "$dir")"
        [[ "$id" == "logs" ]] && continue
        all_dirs+=("$dir")
    done
fi

total_buildable=0
skipped=()

for dir in "${all_dirs[@]}"; do
    if [[ -f "$dir/Dockerfile" ]]; then
        total_buildable=$(( total_buildable + 1 ))
    elif (( explicit_selection )); then
        id="$(basename "$dir")"
        echo "Error: selected instance has no Dockerfile: '$id'" >&2
        exit 1
    fi
done

if (( total_buildable == 0 )); then
    echo "Error: no buildable instances selected" >&2
    exit 1
fi

echo "Total images to build : $total_buildable  |  skippable: $(( ${#all_dirs[@]} - total_buildable ))"
echo ""

active_jobs=0

for dir in "${all_dirs[@]}"; do
    id="$(basename "$dir")"

    if [[ ! -f "$dir/Dockerfile" ]]; then
        {
            flock -x 9
            echo -e "\033[1;33m[SKIP]  $id: no Dockerfile\033[0m"
        } 9>"$TMP_DIR/.output.lock"
        skipped+=("$id")
        continue
    fi

    if (( active_jobs >= NUM_WORKERS )); then
        wait -n
        active_jobs=$(( active_jobs - 1 ))
    fi

    build_one "$id" "$dir" "$total_buildable" &
    active_jobs=$(( active_jobs + 1 ))
done

wait

succeeded=()
failed=()

for dir in "${all_dirs[@]}"; do
    id="$(basename "$dir")"
    result_file="$TMP_DIR/${id}.result"
    [[ -f "$result_file" ]] || continue

    case "$(cat "$result_file")" in
        succeeded) succeeded+=("$id") ;;
        failed) failed+=("$id") ;;
    esac
done

if (( interrupted )); then
    exit 130
fi

FAILED_LOG=""
if (( ${#failed[@]} > 0 )); then
    mkdir -p "$LOG_DIR"
    FAILED_LOG="$LOG_DIR/$RUN_TIMESTAMP.txt"
    : > "$FAILED_LOG"

    for id in "${failed[@]}"; do
        {
            echo "===== $id ====="
            cat "$TMP_DIR/${id}.log"
            echo ""
        } >> "$FAILED_LOG"
    done
fi

echo ""
echo "===== Build Statistics ====="
echo "  Succeeded : ${#succeeded[@]}"
echo "  Failed    : ${#failed[@]}"
echo "  Skipped   : ${#skipped[@]}"

if (( ${#failed[@]} > 0 )); then
    echo ""
    echo "Failed builds:"
    for id in "${failed[@]}"; do
        echo "  - $id"
    done
    echo "Failure log: $FAILED_LOG"
fi

if (( ${#skipped[@]} > 0 )); then
    echo ""
    echo "Skipped (no Dockerfile):"
    for id in "${skipped[@]}"; do
        echo "  - $id"
    done
fi

echo "============================"

(( ${#failed[@]} == 0 ))
