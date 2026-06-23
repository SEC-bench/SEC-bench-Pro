#!/usr/bin/env bash
# Build upstream-latest Linux validation images from validated Linux leaves.
#
# Each selected CVE directory must contain the same files as the validated
# vuln/fixed leaves: secb_config.json, build.sh, secb.sh, init.sh, and config/.
# The script builds per-CVE latest leaves tagged as ${IMAGE_REPO}:${CVE}, e.g.
# hwiwonlee/linux.x86_64.latest:CVE-2022-0185. Docker cache shares the
# latest-kernel checkout/tooling layers across leaves.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

IMAGE_REPO="${IMAGE_REPO:-hwiwonlee/linux.x86_64.latest}"
LINUX_REF="${LINUX_REF:-origin/master}"
LINUX_REF_CACHE_BUST="${LINUX_REF_CACHE_BUST:-}"
KBUILD_JOBS="${KBUILD_JOBS:-}"
PARALLEL="${PARALLEL:-1}"
NO_CACHE="${NO_CACHE:-0}"
PUSH="${PUSH:-0}"
SKIP_EXISTING="${SKIP_EXISTING:-0}"
BENCHMARK_DIR="${BENCHMARK_DIR:-}"

usage() {
  cat <<'EOF'
Usage: base/linux/build_latest_images.sh [options] [CVE ...]

Build per-CVE latest Linux leaf images using base/linux/Dockerfile.latest.
Docker cache shares the common latest-kernel layers across leaves.

Options:
  --benchmark-dir DIR  Linux benchmark root containing CVE-* directories.
                       Defaults to ./projects/linux if present, else ~/work/benchmark/linux.
  -j, --parallel N     Number of docker builds to run concurrently (default: 1).
  --linux-ref REF      Linux ref/commit to build (default: origin/master).
  --linux-ref-cache-bust VALUE
                       Cache-bust value for moving refs. Defaults to current
                       UTC timestamp for origin/* refs.
  --kbuild-jobs N      KBUILD_JOBS build arg passed to the kernel build.
  --image-repo REPO    Image repository (default: hwiwonlee/linux.x86_64.latest).
  --no-cache           Pass --no-cache to docker build.
  --push               Push each leaf after successful build.
  --skip-existing      Skip tags already present locally.
  -h, --help           Show this help.

Environment equivalents:
  BENCHMARK_DIR, PARALLEL, LINUX_REF, LINUX_REF_CACHE_BUST, KBUILD_JOBS,
  IMAGE_REPO, NO_CACHE=1, PUSH=1, SKIP_EXISTING=1

Examples:
  base/linux/build_latest_images.sh --benchmark-dir /home/xeon/work/benchmark/linux -j 2
  base/linux/build_latest_images.sh --linux-ref v6.15 CVE-2022-0185
EOF
}

log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmark-dir)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      BENCHMARK_DIR="$2"
      shift 2
      ;;
    -j|--parallel)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      PARALLEL="$2"
      shift 2
      ;;
    --linux-ref)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      LINUX_REF="$2"
      shift 2
      ;;
    --linux-ref-cache-bust)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      LINUX_REF_CACHE_BUST="$2"
      shift 2
      ;;
    --kbuild-jobs)
      [[ $# -ge 2 ]] || die "$1 requires a value"
      KBUILD_JOBS="$2"
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

[[ "$PARALLEL" =~ ^[0-9]+$ && "$PARALLEL" -ge 1 ]] || die "--parallel must be a positive integer"
if [[ -n "$KBUILD_JOBS" ]]; then
  [[ "$KBUILD_JOBS" =~ ^[0-9]+$ && "$KBUILD_JOBS" -ge 1 ]] || die "--kbuild-jobs must be a positive integer"
fi

if [[ -z "$BENCHMARK_DIR" ]]; then
  if [[ -d "$REPO_ROOT/projects/linux" ]]; then
    BENCHMARK_DIR="$REPO_ROOT/projects/linux"
  elif [[ -d "$HOME/work/benchmark/linux" ]]; then
    BENCHMARK_DIR="$HOME/work/benchmark/linux"
  else
    die "could not infer benchmark dir; pass --benchmark-dir"
  fi
fi
BENCHMARK_DIR="$(cd "$BENCHMARK_DIR" && pwd)"
[[ -d "$BENCHMARK_DIR" ]] || die "benchmark dir not found: $BENCHMARK_DIR"

DOCKERFILE="$SCRIPT_DIR/Dockerfile.latest"
[[ -f "$DOCKERFILE" ]] || die "missing Dockerfile.latest: $DOCKERFILE"

if [[ $# -gt 0 ]]; then
  mapfile -t INSTANCES < <(printf '%s\n' "$@" | sort -u)
else
  mapfile -t INSTANCES < <(
    find "$BENCHMARK_DIR" -maxdepth 1 -type d -name 'CVE-*' -printf '%f\n' | sort -u
  )
fi
[[ "${#INSTANCES[@]}" -gt 0 ]] || die "no instances selected"

BUILD_LOG_DIR="$SCRIPT_DIR/latest_build_logs/$(date -u '+%Y%m%dT%H%M%SZ')"
mkdir -p "$BUILD_LOG_DIR"

if [[ -z "$LINUX_REF_CACHE_BUST" && "$LINUX_REF" == origin/* ]]; then
  LINUX_REF_CACHE_BUST="$(date -u '+%Y%m%dT%H%M%SZ')"
fi

validate_instance() {
  local id="$1"
  local dir="$BENCHMARK_DIR/$id"
  [[ -d "$dir" ]] || die "$id: missing directory under $BENCHMARK_DIR"
  [[ -f "$dir/secb_config.json" ]] || die "$id: missing secb_config.json"
  [[ -f "$dir/build.sh" ]] || die "$id: missing build.sh"
  [[ -f "$dir/secb.sh" ]] || die "$id: missing secb.sh"
  [[ -f "$dir/init.sh" ]] || die "$id: missing init.sh"
  [[ -d "$dir/config" ]] || die "$id: missing config/"
}

build_one() {
  local id="$1"
  local dir="$BENCHMARK_DIR/$id"
  local tag="$IMAGE_REPO:$id"
  local log_file="$BUILD_LOG_DIR/$id.log"
  local -a cmd=(
    docker build
    -f "$DOCKERFILE"
    -t "$tag"
    --build-arg "LINUX_REF=$LINUX_REF"
  )

  [[ "$NO_CACHE" == "1" ]] && cmd+=(--no-cache)
  [[ -n "$LINUX_REF_CACHE_BUST" ]] && cmd+=(--build-arg "LINUX_REF_CACHE_BUST=$LINUX_REF_CACHE_BUST")
  [[ -n "$KBUILD_JOBS" ]] && cmd+=(--build-arg "KBUILD_JOBS=$KBUILD_JOBS")
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

  log "$id build FAILED ($log_file)"
  return 1
}

export BENCHMARK_DIR DOCKERFILE IMAGE_REPO
export LINUX_REF LINUX_REF_CACHE_BUST KBUILD_JOBS
export NO_CACHE PUSH SKIP_EXISTING BUILD_LOG_DIR SCRIPT_DIR
export -f log die validate_instance build_one

for id in "${INSTANCES[@]}"; do
  validate_instance "$id"
done

log "selected ${#INSTANCES[@]} instance(s)"
log "benchmark dir: $BENCHMARK_DIR"
log "logs: $BUILD_LOG_DIR"
log "image repo: $IMAGE_REPO"
log "linux ref: $LINUX_REF"
[[ -n "$LINUX_REF_CACHE_BUST" ]] && log "linux ref cache-bust: $LINUX_REF_CACHE_BUST"
log "parallel: $PARALLEL"
[[ -n "$KBUILD_JOBS" ]] && log "kbuild jobs per build: $KBUILD_JOBS"

if [[ "$PARALLEL" -gt 1 && "${#INSTANCES[@]}" -gt 1 ]]; then
  first="${INSTANCES[0]}"
  log "warming shared Docker cache with $first"
  build_one "$first"
  REMAINING=("${INSTANCES[@]:1}")
  printf '%s\n' "${REMAINING[@]}" | xargs -r -n1 -P "$PARALLEL" bash -c 'build_one "$0"'
else
  printf '%s\n' "${INSTANCES[@]}" | xargs -r -n1 -P "$PARALLEL" bash -c 'build_one "$0"'
fi

log "all selected latest images built"
