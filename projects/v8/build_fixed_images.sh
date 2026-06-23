#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_REPO="${IMAGE_REPO:-hwiwonlee/v8.x86_64.fixed}"
NINJA_JOBS="${NINJA_JOBS:-}"
PARALLEL="${PARALLEL:-1}"
NO_CACHE="${NO_CACHE:-0}"
PUSH="${PUSH:-0}"
SKIP_EXISTING="${SKIP_EXISTING:-0}"

usage() {
  cat <<'EOF'
Usage: v8/build_fixed_images.sh [options] [instance_id ...]

Build fixed V8 Docker images from per-instance Dockerfile.fixed files.

Options:
  -j, --parallel N       Number of docker builds to run concurrently (default: 1).
      --ninja-jobs N    NINJA_JOBS build arg passed into Dockerfile.fixed.
      --image-repo R    Image repository (default: hwiwonlee/v8.x86_64.fixed).
      --no-cache        Pass --no-cache to docker build.
      --push            Push each image after successful build.
      --skip-existing   Skip tags already present locally.
  -h, --help            Show this help.

Environment equivalents:
  PARALLEL, NINJA_JOBS, IMAGE_REPO, NO_CACHE=1, PUSH=1, SKIP_EXISTING=1

Examples:
  v8/build_fixed_images.sh --parallel 4 --ninja-jobs 64
  v8/build_fixed_images.sh --ninja-jobs 230 427918760
EOF
}

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -j|--parallel)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      PARALLEL="$2"
      shift 2
      ;;
    --ninja-jobs)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      NINJA_JOBS="$2"
      shift 2
      ;;
    --image-repo)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      IMAGE_REPO="$2"
      shift 2
      ;;
    --no-cache)
      NO_CACHE=1
      shift
      ;;
    --push)
      PUSH=1
      shift
      ;;
    --skip-existing)
      SKIP_EXISTING=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      break
      ;;
  esac
done

[[ "$PARALLEL" =~ ^[0-9]+$ ]] || die "--parallel must be an integer"
[[ "$PARALLEL" -ge 1 ]] || die "--parallel must be >= 1"
if [[ -n "$NINJA_JOBS" ]]; then
  [[ "$NINJA_JOBS" =~ ^[0-9]+$ ]] || die "--ninja-jobs must be an integer"
  [[ "$NINJA_JOBS" -ge 1 ]] || die "--ninja-jobs must be >= 1"
fi

if [[ $# -gt 0 ]]; then
  mapfile -t INSTANCES < <(printf '%s\n' "$@" | sort -u)
else
  mapfile -t INSTANCES < <(find "$ROOT_DIR" -mindepth 2 -maxdepth 2 -name fix.json -printf '%h\n' | xargs -r -n1 basename | sort)
fi

[[ "${#INSTANCES[@]}" -gt 0 ]] || die "no instances selected"

BUILD_ROOT="$ROOT_DIR/fixed_build_logs/$(date -u '+%Y%m%dT%H%M%SZ')"
mkdir -p "$BUILD_ROOT"

validate_instance() {
  local id="$1"
  local dir="$ROOT_DIR/$id"
  [[ -f "$dir/fix.json" ]] || die "$id: missing fix.json"
  [[ -f "$dir/Dockerfile.fixed" ]] || die "$id: missing Dockerfile.fixed"
  [[ -d "$dir/patches" ]] || die "$id: missing patches directory"
  if ! find "$dir/patches" -maxdepth 1 -type f -name '*.patch' -size +0c | grep -q .; then
    die "$id: patches directory does not contain a non-empty .patch file"
  fi
}

build_one() {
  local id="$1"
  local dir="$ROOT_DIR/$id"
  local tag="$IMAGE_REPO:$id"
  local log_file="$BUILD_ROOT/$id.log"
  local -a cmd=(docker build -f "$dir/Dockerfile.fixed" -t "$tag")

  if [[ "$NO_CACHE" == "1" ]]; then
    cmd+=(--no-cache)
  fi
  if [[ -n "$NINJA_JOBS" ]]; then
    cmd+=(--build-arg "NINJA_JOBS=$NINJA_JOBS")
  fi
  cmd+=("$dir")

  if [[ "$SKIP_EXISTING" == "1" ]] && docker image inspect "$tag" >/dev/null 2>&1; then
    log "$id skip existing $tag"
    printf 'SKIPPED existing %s\n' "$tag" >"$log_file"
    return 0
  fi

  log "$id build start -> $tag"
  if "${cmd[@]}" >"$log_file" 2>&1; then
    log "$id build ok -> $tag"
    if [[ "$PUSH" == "1" ]]; then
      log "$id push start -> $tag"
      docker push "$tag" >>"$log_file" 2>&1
      log "$id push ok -> $tag"
    fi
    return 0
  fi

  log "$id build failed; see $log_file"
  return 1
}

export ROOT_DIR IMAGE_REPO NINJA_JOBS NO_CACHE PUSH SKIP_EXISTING BUILD_ROOT
export -f log die validate_instance build_one

for id in "${INSTANCES[@]}"; do
  validate_instance "$id"
done

log "selected ${#INSTANCES[@]} instance(s)"
log "logs: $BUILD_ROOT"
log "image repo: $IMAGE_REPO"
log "parallel: $PARALLEL"
if [[ -n "$NINJA_JOBS" ]]; then
  log "ninja jobs per build: $NINJA_JOBS"
fi

printf '%s\n' "${INSTANCES[@]}" | xargs -r -n1 -P "$PARALLEL" bash -c 'build_one "$0"'

log "all selected fixed images built"
