#!/bin/bash

# Push Docker images for verified top-level SpiderMonkey case directories only.
# Each directory name is used as the image ID.

set -euo pipefail

IMAGE_REPO="hwiwonlee/sm.x86_64"
IMAGE_KIND="vulnerable"
target_ids=()

usage() {
    cat <<'EOF'
Usage: push_images.sh [--fixed] [id ...] [-h|--help]

Push SpiderMonkey Docker images for verified instance directories.
When IDs are provided, push only those verified instance directories.

Options:
  --fixed       Push fixed images: hwiwonlee/sm.x86_64.fixed:<id>
  -h, --help    Show this help.

Default:
  Push vulnerable images: hwiwonlee/sm.x86_64:<id>
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fixed)
            IMAGE_REPO="hwiwonlee/sm.x86_64.fixed"
            IMAGE_KIND="fixed"
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

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Pushing Docker images from: $SCRIPT_DIR"
echo "Image kind: $IMAGE_KIND"
echo "Image repo: $IMAGE_REPO"

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

push_count=0

echo "Found $total_verified verified images to push."

for dir in "${verified_dirs[@]}"; do
    # Extract the directory name (image ID)
    id=$(basename "$dir")
    current=$((push_count + 1))

    image="$IMAGE_REPO:$id"

    echo -e "\033[1;34m[$current/$total_verified] Pushing $IMAGE_KIND image for ID: $id\033[0m"

    if ! docker image inspect "$image" >/dev/null 2>&1; then
        echo "Error: local image not found: $image" >&2
        echo "Build it before pushing." >&2
        exit 1
    fi

    # Push the Docker image
    docker push "$image"
    push_count=$((push_count + 1))

    echo "Successfully pushed: $image"
    echo "---"
done

echo "Pushed $push_count $IMAGE_KIND verified images successfully."
echo "Skipped $skip_count non-verified directories."
