#!/bin/bash

# Push Docker images for verified top-level Linux case directories only.
# Each verified directory name is used as the image tag.

set -euo pipefail

declare -A IMAGE_REPOS=(
    [vuln]="hwiwonlee/linux.x86_64"
    [fixed]="hwiwonlee/linux.x86_64.fixed"
    [latest]="hwiwonlee/linux.x86_64.latest"
)

image_kinds=("vuln")
target_ids=()

usage() {
    cat <<'EOF'
Usage: push_images.sh [--fixed|--latest|--all] [id ...] [-h|--help]

Push Linux Docker images for verified instance directories.
When IDs are provided, push only those verified instance directories.

Options:
  --fixed       Push fixed images: hwiwonlee/linux.x86_64.fixed:<id>
  --latest      Push latest images: hwiwonlee/linux.x86_64.latest:<id>
  --all         Push vulnerable, fixed, and latest images for each verified ID
  -h, --help    Show this help.

Default:
  Push vulnerable images: hwiwonlee/linux.x86_64:<id>
EOF
}

set_single_kind() {
    if [ "${#image_kinds[@]}" -ne 1 ] || [ "${image_kinds[0]}" != "vuln" ]; then
        echo "Error: choose only one of --fixed, --latest, or --all" >&2
        usage >&2
        exit 1
    fi
    image_kinds=("$@")
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fixed)
            set_single_kind "fixed"
            shift
            ;;
        --latest)
            set_single_kind "latest"
            shift
            ;;
        --all)
            set_single_kind "vuln" "fixed" "latest"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*)
            echo "Error: unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
        *)
            target_ids+=("$1")
            shift
            ;;
    esac
done

# Get the directory where this script is located.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Pushing Docker images from: $SCRIPT_DIR"
echo "Image kinds: ${image_kinds[*]}"

skip_count=0
verified_dirs=()

# Find requested directories, or all top-level verified directories by default.
if [ "${#target_ids[@]}" -gt 0 ]; then
    for id in "${target_ids[@]}"; do
        dir="$SCRIPT_DIR/$id"
        if [ ! -d "$dir" ]; then
            echo "Error: instance directory not found: $dir" >&2
            exit 1
        fi
        if [ ! -f "$dir/VERIFIED.txt" ]; then
            echo "Error: instance is not verified: $id" >&2
            exit 1
        fi

        verified_dirs+=("$dir")
    done
else
    for dir in "$SCRIPT_DIR"/*; do
        if [ -d "$dir" ]; then
            if [ ! -f "$dir/VERIFIED.txt" ]; then
                skip_count=$((skip_count + 1))
                continue
            fi
            verified_dirs+=("$dir")
        fi
    done
fi

total_verified=${#verified_dirs[@]}

if [ "$total_verified" -eq 0 ]; then
    echo "No verified images found."
    echo "Skipped $skip_count non-verified directories."
    exit 0
fi

total_images=$((total_verified * ${#image_kinds[@]}))
push_count=0

echo "Found $total_verified verified instance(s)."
echo "Found $total_images image(s) to push."

for dir in "${verified_dirs[@]}"; do
    id=$(basename "$dir")

    for kind in "${image_kinds[@]}"; do
        repo="${IMAGE_REPOS[$kind]}"
        image="$repo:$id"
        current=$((push_count + 1))

        echo -e "\033[1;34m[$current/$total_images] Pushing $kind image for ID: $id\033[0m"

        if ! docker image inspect "$image" >/dev/null 2>&1; then
            echo "Error: local image not found: $image" >&2
            echo "Build it before pushing." >&2
            exit 1
        fi

        docker push "$image"
        push_count=$((push_count + 1))

        echo "Successfully pushed: $image"
        echo "---"
    done
done

echo "Pushed $push_count Linux image(s) successfully."
echo "Skipped $skip_count non-verified directories."
