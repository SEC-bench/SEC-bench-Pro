#!/bin/bash
# Parallel rebuild + crash_check sweep for the spidermonkey/ dataset.
#
# Builds each bug image with --no-cache (so the new base image is exercised
# from a clean state), runs crash_check.sh, compares the resulting
# CONFIMRED: TYPE token to the bug's meta.json error_type field, then
# rmis the image and prunes the buildkit cache to keep disk usage flat.
#
# Concurrency: PARALLEL env var (default 5). Override on the CLI:
#   PARALLEL=3 ./parallel_verify.sh                # 3 at a time
#   PARALLEL=5 ./parallel_verify.sh 1810711 1814899  # only those IDs
#
# By default the gate bug 1804626 is skipped (assumed already verified).
# Pass GATE=1 to include it.
#
# Outputs:
#   /tmp/sm-parallel.log         — combined chronological log
#   /tmp/sm-parallel-<id>.log    — full docker build log per bug
#   /tmp/sm-parallel-table.txt   — pipe-separated results
#
# Requirements: docker (with buildkit), jq, flock, xargs (all standard).

set -u
SM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARALLEL="${PARALLEL:-5}"
GATE="${GATE:-0}"
RUN_ID="${RUN_ID:-parallel}"
LOG="${LOG:-/tmp/sm-$RUN_ID.log}"
TABLE="${TABLE:-/tmp/sm-$RUN_ID-table.txt}"
LOCK="${LOCK:-/tmp/sm-$RUN_ID.lock}"

: > "$LOG"
: > "$TABLE"
: > "$LOCK"

ts() { date -Is; }
echo "=== $(ts) parallel sweep PARALLEL=$PARALLEL ===" | tee -a "$LOG"

verify_one() {
    local id="$1"
    local img="smlijun/spidermonkey.x86_64:$id"
    local bug_log="/tmp/sm-parallel-$id.log"
    local OUT GOT EXP line color

    local C_RED=$'\033[1;31m' C_BLUE=$'\033[1;34m' C_OFF=$'\033[0m'

    line="[$id] start $(ts)"
    ( flock -x 200; echo "$line" >> "$LOG" ) 200>"$LOCK"

    if ! docker build --no-cache -t "$img" "$SM/$id" > "$bug_log" 2>&1; then
        line="[$id] BUILD_FAILED ($(ts))"
        ( flock -x 200; echo "$line" >> "$LOG"; echo "$id|BUILD_FAILED|-|-" >> "$TABLE" ) 200>"$LOCK"
        printf '%s%s%s\n' "$C_RED" "$line" "$C_OFF"
        return
    fi

    OUT=$(bash "$SM/crash_check.sh" "$id" 2>&1)
    GOT=$(echo "$OUT" | grep -oE 'CONFIMRED: [A-Z_]+' | head -1 | sed 's/CONFIMRED: //')
    EXP=$(jq -r '.error_type' "$SM/$id/meta.json" 2>/dev/null)

    if [ -z "$GOT" ]; then
        line="[$id] CRASH_NOT_DETECTED expected=$EXP ($(ts))"
        color="$C_RED"
        ( flock -x 200; echo "$line" >> "$LOG"; echo "$id|FAIL|$EXP|none" >> "$TABLE" ) 200>"$LOCK"
    elif [ "$GOT" = "$EXP" ]; then
        line="[$id] PASS $GOT ($(ts))"
        color="$C_BLUE"
        ( flock -x 200; echo "$line" >> "$LOG"; echo "$id|PASS|$EXP|$GOT" >> "$TABLE" ) 200>"$LOCK"
    else
        line="[$id] MISMATCH expected=$EXP got=$GOT ($(ts))"
        color="$C_RED"
        ( flock -x 200; echo "$line" >> "$LOG"; echo "$id|MISMATCH|$EXP|$GOT" >> "$TABLE" ) 200>"$LOCK"
    fi
    printf '%s%s%s\n' "$color" "$line" "$C_OFF"

    docker rmi -f "$img" >/dev/null 2>&1 || true
    # Prune dangling build cache. Concurrent builds' in-use layers are
    # protected by buildkit's reference counting, so this is safe to run
    # while other workers are mid-build.
    docker builder prune -af >/dev/null 2>&1 || true
}

export -f verify_one ts
export SM LOG TABLE LOCK

if [ "$#" -gt 0 ]; then
    BUGS=("$@")
else
    mapfile -t BUGS < <(find "$SM" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -n)
    if [ "$GATE" = "0" ]; then
        BUGS=("${BUGS[@]/1804626}")
        # Drop empty slot left by the substitution.
        TMP=()
        for b in "${BUGS[@]}"; do [ -n "$b" ] && TMP+=("$b"); done
        BUGS=("${TMP[@]}")
    fi
fi

echo "=== $(ts) ${#BUGS[@]} bugs queued ===" | tee -a "$LOG"

printf '%s\n' "${BUGS[@]}" | xargs -P "$PARALLEL" -I{} bash -c 'verify_one "$1"' _ {}

echo "" | tee -a "$LOG"
echo "=== $(ts) summary ===" | tee -a "$LOG"

C_RED=$'\033[1;31m'; C_BLUE=$'\033[1;34m'; C_OFF=$'\033[0m'
{
    printf '%-8s %-16s %-18s %s\n' BUG RESULT EXPECTED REBUILT
    sort -t'|' -k1,1n "$TABLE" | while IFS='|' read -r id res exp got; do
        case "$res" in
            PASS) c="$C_BLUE" ;;
            *)    c="$C_RED" ;;
        esac
        printf '%s%-8s %-16s %-18s %s%s\n' "$c" "$id" "$res" "$exp" "$got" "$C_OFF"
    done
} | tee -a "$LOG"

PASS=$(grep -c '|PASS|' "$TABLE" 2>/dev/null || echo 0)
TOT=$(wc -l < "$TABLE" 2>/dev/null || echo 0)
FAIL=$((TOT - PASS))
echo "" | tee -a "$LOG"
printf '=== TOTAL: %s%d pass%s / %s%d fail%s / %d bugs ===\n' \
    "$C_BLUE" "$PASS" "$C_OFF" "$C_RED" "$FAIL" "$C_OFF" "$TOT" | tee -a "$LOG"
