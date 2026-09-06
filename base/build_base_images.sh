#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
    cat <<'EOF'
Usage: build_base_images.sh [options] [v8] [sm] [linux]

Build the selected canonical base images. All three are built when no target
is provided. AGENT_CACHE_BUST may be set to an explicit shared cache key.

Options:
  --platform PLATFORM  Set the Docker build platform.
  --no-cache           Disable the Docker build cache.
  -h, --help           Show this help.
EOF
}

platform=""
no_cache=0
targets=()

while (( $# > 0 )); do
    case "$1" in
        --platform)
            if (( $# < 2 )) || [[ -z "$2" ]]; then
                echo "Error: --platform requires a value" >&2
                usage >&2
                exit 1
            fi
            platform="$2"
            shift 2
            ;;
        --no-cache)
            no_cache=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            targets+=("$@")
            break
            ;;
        -*)
            echo "Error: unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
        *)
            targets+=("$1")
            shift
            ;;
    esac
done

if (( ${#targets[@]} == 0 )); then
    targets=(v8 sm linux)
fi

for target in "${targets[@]}"; do
    case "$target" in
        v8|sm|linux) ;;
        *)
            echo "Error: unknown target: $target" >&2
            usage >&2
            exit 1
            ;;
    esac
done

read_npm_version() {
    local package_url="$1"
    curl -fsSL --retry 3 --connect-timeout 15 --max-time 60 "$package_url" |
        python3 -c 'import json, sys; print(json.load(sys.stdin)["version"])'
}

validate_version() {
    local name="$1"
    local version="$2"
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z]+([.-][0-9A-Za-z]+)*)?(\+[0-9A-Za-z]+([.-][0-9A-Za-z]+)*)?$ ]]; then
        echo "Error: $name returned an invalid version: $version" >&2
        exit 1
    fi
}

CODEX_VERSION="$(read_npm_version 'https://registry.npmjs.org/@openai%2Fcodex/latest')"
OPENCODE_VERSION="$(read_npm_version 'https://registry.npmjs.org/opencode-ai/latest')"
CLAUDE_CODE_VERSION="$(curl -fsSL --retry 3 --connect-timeout 15 --max-time 60 \
    'https://downloads.claude.ai/claude-code-releases/latest')"

validate_version "Codex" "$CODEX_VERSION"
validate_version "OpenCode" "$OPENCODE_VERSION"
validate_version "Claude Code" "$CLAUDE_CODE_VERSION"

AGENT_CACHE_BUST="${AGENT_CACHE_BUST:-$(date -u '+%Y%m%dT%H%M%S%NZ')}"

echo "Agent versions: codex=$CODEX_VERSION opencode=$OPENCODE_VERSION claude=$CLAUDE_CODE_VERSION"
echo "Agent cache key: $AGENT_CACHE_BUST"

build_args=(
    --build-arg "CODEX_VERSION=$CODEX_VERSION"
    --build-arg "OPENCODE_VERSION=$OPENCODE_VERSION"
    --build-arg "CLAUDE_CODE_VERSION=$CLAUDE_CODE_VERSION"
    --build-arg "AGENT_CACHE_BUST=$AGENT_CACHE_BUST"
)

docker_options=()
if [[ -n "$platform" ]]; then
    docker_options+=(--platform "$platform")
fi
if (( no_cache )); then
    docker_options+=(--no-cache)
fi

for target in "${targets[@]}"; do
    case "$target" in
        v8)
            docker build -t hwiwonlee/v8.base:latest \
                "${docker_options[@]}" "${build_args[@]}" "$REPO_ROOT/base/v8"
            ;;
        sm)
            docker build -t hwiwonlee/sm.base:latest \
                "${docker_options[@]}" "${build_args[@]}" "$REPO_ROOT/base/sm"
            ;;
        linux)
            docker build -t hwiwonlee/linux.base:latest \
                -f "$REPO_ROOT/base/linux/Dockerfile" \
                "${docker_options[@]}" "${build_args[@]}" "$REPO_ROOT"
            ;;
    esac
done
