#!/bin/bash

# Build Docker images for all subdirectories in v8/
# Each subdirectory name is used as the image ID
# Usage: build_images.sh [-n NUM_WORKERS] [-f INPUT_FILE]

# Require bash >= 4.3 for wait -n support
if (( BASH_VERSINFO[0] < 4 || (BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] < 3) )); then
    echo "Error: bash >= 4.3 required (found ${BASH_VERSION})" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NUM_WORKERS=1
INPUT_FILE=""

usage() {
    echo "Usage: $(basename "$0") [-n NUM_WORKERS] [-f INPUT_FILE]"
    echo "  -n NUM_WORKERS  Number of parallel build workers (default: 1)"
    echo "  -f INPUT_FILE   File with case IDs to build (one per line); builds all if omitted"
    exit 1
}

while getopts ":n:f:" opt; do
    case $opt in
        n) NUM_WORKERS="$OPTARG" ;;
        f) INPUT_FILE="$OPTARG" ;;
        :) echo "Error: -$OPTARG requires an argument" >&2; usage ;;
        \?) echo "Error: Unknown option -$OPTARG" >&2; usage ;;
    esac
done

if ! [[ "$NUM_WORKERS" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: -n must be a positive integer, got: '$NUM_WORKERS'" >&2
    exit 1
fi

if [[ -n "$INPUT_FILE" && ! -f "$INPUT_FILE" ]]; then
    echo "Error: input file not found: '$INPUT_FILE'" >&2
    exit 1
fi

# Load allowed IDs from input file (if given) into a set
declare -A allowed_ids
if [[ -n "$INPUT_FILE" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%%#*}"   # strip inline comments
        line="${line// /}"   # strip spaces
        [[ -z "$line" ]] && continue
        allowed_ids["$line"]=1
    done < "$INPUT_FILE"
fi

echo "Building Docker images from: $SCRIPT_DIR"
echo "Parallel workers: $NUM_WORKERS"
[[ -n "$INPUT_FILE" ]] && echo "Input file: $INPUT_FILE (${#allowed_ids[@]} cases)"

# Temp directory for per-image logs and result markers
TMP_DIR=$(mktemp -d)
interrupted=0
trap 'rm -rf "$TMP_DIR"' EXIT

# On SIGINT/SIGTERM: kill all background build jobs and exit cleanly
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

# Build a single image; writes result marker and streams log to a temp file
# Args: id dir total_buildable
build_one() {
    local id="$1"
    local dir="$2"
    local total="$3"
    local log_file="$TMP_DIR/${id}.log"
    local result_file="$TMP_DIR/${id}.result"

    echo -e "\033[1;34m[START] $id\033[0m"
    if docker build -t "hwiwonlee/v8.x86_64:$id" "$dir" >"$log_file" 2>&1; then
        echo "succeeded" >"$result_file"
        # Atomically increment completed counter and print progress
        {
            flock -x 9
            local done
            done=$(( $(cat "$TMP_DIR/.completed" 2>/dev/null || echo 0) + 1 ))
            echo "$done" >"$TMP_DIR/.completed"
            echo -e "\033[1;32m[OK]    [$done/$total] $id\033[0m"
        } 9>"$TMP_DIR/.output.lock"
    else
        echo "failed" >"$result_file"
        # Atomically increment counter and print full error log
        {
            flock -x 9
            local done
            done=$(( $(cat "$TMP_DIR/.completed" 2>/dev/null || echo 0) + 1 ))
            echo "$done" >"$TMP_DIR/.completed"
            echo -e "\033[1;31m[FAIL]  [$done/$total] $id\033[0m"
            echo "  --- build log: $id ---"
            cat "$log_file"
            echo "  --- end: $id ---"
        } 9>"$TMP_DIR/.output.lock"
    fi
}

# Collect directories sorted in descending order, same as original behaviour
# If an input file was given, restrict to only those IDs
all_dirs=()
while IFS= read -r dir; do
    [[ -d "$dir" ]] || continue
    id=$(basename "$dir")
    if [[ -n "$INPUT_FILE" && -z "${allowed_ids[$id]+x}" ]]; then
        continue
    fi
    all_dirs+=("$dir")
done < <(find "$SCRIPT_DIR" -mindepth 1 -maxdepth 1 -type d | sort -r)

# Pre-count buildable images for progress display
total_buildable=0
for dir in "${all_dirs[@]}"; do
    [[ -f "$dir/Dockerfile" ]] && total_buildable=$(( total_buildable + 1 ))
done
echo "Total images to build : $total_buildable  |  skippable: $(( ${#all_dirs[@]} - total_buildable ))"
echo ""

skipped=()
active_jobs=0

for dir in "${all_dirs[@]}"; do
    id=$(basename "$dir")

    if [[ ! -f "$dir/Dockerfile" ]]; then
        echo -e "\033[1;33m[SKIP]  $id: no Dockerfile\033[0m"
        skipped+=("$id")
        continue
    fi

    # If at capacity, wait for one worker slot to free up
    if (( active_jobs >= NUM_WORKERS )); then
        wait -n
        active_jobs=$(( active_jobs - 1 ))
    fi

    build_one "$id" "$dir" "$total_buildable" &
    active_jobs=$(( active_jobs + 1 ))
done

# Wait for all remaining background jobs
wait

# Collect results in the same sorted order for deterministic output
succeeded=()
failed=()

for dir in "${all_dirs[@]}"; do
    id=$(basename "$dir")
    result_file="$TMP_DIR/${id}.result"
    [[ -f "$result_file" ]] || continue
    case "$(cat "$result_file")" in
        succeeded) succeeded+=("$id") ;;
        failed)    failed+=("$id") ;;
    esac
done

# Skip summary if we were interrupted before all jobs completed
if (( interrupted )); then
    exit 130
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
