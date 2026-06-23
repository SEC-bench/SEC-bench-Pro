# Base image for Linux kernel KASAN benchmark leaf images.
# Tag: hwiwonlee/linux.base:latest
#
# This mirrors the validated Linux benchmark base image shape:
#   1. kernel build toolchain for x86_64
#   2. QEMU + busybox-static for in-container repros
#   3. /src/linux.git bare clone for per-CVE worktrees
#   4. /base/release.config universal KASAN/debug baseline
#   5. shared agent/runtime tooling used by the harness

FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV SRC=/src
ENV OUT=/out

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc make bison flex bc \
        libelf-dev libssl-dev libncurses-dev \
        jq cpio gzip xz-utils \
        busybox-static \
        qemu-system-x86 qemu-utils \
        python3 python3-venv python3-pip \
        git ca-certificates curl \
        kmod file dwarves \
        gettext-base xvfb locales \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8

RUN git config --global user.email "benchmark@local" \
 && git config --global user.name "secb benchmark" \
 && git config --global advice.detachedHead false

RUN mkdir -p /out /src /testcase /base /app/artifacts

# Keep the heavy Linux clone below the stable toolchain layers and above the
# faster-changing agent layers.
RUN git clone --bare https://github.com/torvalds/linux.git /src/linux.git

COPY release.config /base/release.config

ARG CODEX_VERSION=0.128.0
ARG CLAUDE_CODE_VERSION=2.1.126
ARG OPENCODE_VERSION=1.14.19

RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN npm i -g npm@latest @openai/codex@${CODEX_VERSION} opencode-ai@${OPENCODE_VERSION} @beads/bd@0.50.2

RUN ln -sf /usr/bin/make /usr/bin/gmake

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN curl -fsSL https://claude.ai/install.sh | bash -s ${CLAUDE_CODE_VERSION}

COPY sanitize-git /usr/local/bin/secb-sanitize-git
RUN chmod +x /usr/local/bin/secb-sanitize-git

ENV PATH="/root/.local/bin:$PATH"

WORKDIR $SRC
