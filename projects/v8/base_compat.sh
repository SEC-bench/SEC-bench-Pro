#!/usr/bin/env bash

# Shared compatibility gate for V8 leaf builders.  Keep this file source-only:
# callers retain their existing option parsing and build orchestration.

V8_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V8_REPO_ROOT="$(cd "$V8_PROJECT_DIR/../.." && pwd)"
V8_BASE_BUILDER="$V8_REPO_ROOT/base/build_base_images.sh"
V8_BASE_IMAGE="hwiwonlee/v8.base:latest"
V8_GCLIENT_WRAPPER="$V8_REPO_ROOT/base/v8/gclient-wrapper"
V8_BASE_LINEAGE_LABEL="org.secbench.base-image-id"

v8_image_id() {
    local image="$1"
    local image_id
    image_id="$(docker image inspect --format '{{.Id}}' "$image" 2>/dev/null)" || return 1
    [[ "$image_id" =~ ^sha256:[0-9a-f]{64}$ ]] || return 1
    printf '%s\n' "$image_id"
}

v8_image_has_current_base_lineage() {
    local image="$1"
    local base_id marker base_layers image_layers

    base_id="$(v8_image_id "$V8_BASE_IMAGE")" || return 1
    v8_image_id "$image" >/dev/null || return 1
    marker="$(
        docker image inspect \
            --format '{{ index .Config.Labels "org.secbench.base-image-id" }}' \
            "$image" 2>/dev/null
    )" || return 1
    [[ "$marker" == "$base_id" ]] || return 1

    base_layers="$(
        docker image inspect --format '{{json .RootFS.Layers}}' \
            "$V8_BASE_IMAGE" 2>/dev/null
    )" || return 1
    image_layers="$(
        docker image inspect --format '{{json .RootFS.Layers}}' \
            "$image" 2>/dev/null
    )" || return 1
    python3 -c '
import json
import sys
base = json.loads(sys.argv[1])
image = json.loads(sys.argv[2])
valid = (
    isinstance(base, list)
    and bool(base)
    and isinstance(image, list)
    and image[:len(base)] == base
)
raise SystemExit(0 if valid else 1)
' "$base_layers" "$image_layers"
}

v8_base_is_compatible() {
    local expected_wrapper_sha
    [[ -f "$V8_GCLIENT_WRAPPER" ]] || return 1
    expected_wrapper_sha="$(sha256sum "$V8_GCLIENT_WRAPPER" | awk '{print $1}')" || return 1

    docker image inspect "$V8_BASE_IMAGE" >/dev/null 2>&1 &&
        docker run --rm --network none --entrypoint /bin/sh "$V8_BASE_IMAGE" \
            -c 'set -eu
                test -x /usr/local/bin/secb-sanitize-git
                test -s /etc/secb-agent-versions
                test -x /opt/depot_tools/gclient
                test -x /opt/depot_tools/gclient.unbounded
                test "$(sha256sum /opt/depot_tools/gclient | awk "{print \$1}")" = "$1"
                grep -Fq GCLIENT_JOBS /opt/depot_tools/gclient
                grep -Fq GCLIENT_SYNC_TIMEOUT_SEC /opt/depot_tools/gclient
                for tool in python3 timeout bwrap socat setpriv unshare gdb strace ltrace valgrind rg jq xxd codex opencode claude; do
                    command -v "$tool" >/dev/null
                done' \
            sh "$expected_wrapper_sha" \
            >/dev/null 2>&1
}

v8_build_canonical_base() {
    if [[ ! -x "$V8_BASE_BUILDER" ]]; then
        echo "Error: canonical base builder is missing or not executable: $V8_BASE_BUILDER" >&2
        return 1
    fi

    echo "Building canonical base image: $V8_BASE_IMAGE"
    "$V8_BASE_BUILDER" v8
}

v8_ensure_compatible_base() {
    local force_rebuild="${1:-0}"
    if (( force_rebuild )) || ! v8_base_is_compatible; then
        if (( force_rebuild )); then
            echo "Rebuilding V8 base image by request."
        else
            echo "V8 base image is missing the bounded gclient/runtime contract; rebuilding it."
        fi
        if ! v8_build_canonical_base || ! v8_base_is_compatible; then
            echo "Error: failed to build a compatible $V8_BASE_IMAGE" >&2
            return 1
        fi
    else
        echo "Using compatible base image: $V8_BASE_IMAGE"
    fi
}
