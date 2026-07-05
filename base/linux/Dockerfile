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
    build-essential gcc make bison flex bc binutils \
    gcc-multilib libc6-dev-i386 \
    libelf-dev libssl-dev libncurses-dev libdw-dev pkg-config \
    jq cpio gzip xz-utils bzip2 lz4 sqlite3 \
    busybox-static \
    qemu-system-x86 qemu-utils \
    python3 python-is-python3 python3-venv python3-pip perl \
    git ca-certificates curl \
    kmod file dwarves gdb gdbserver \
    gettext-base xvfb locales ripgrep gawk rsync \
    strace ltrace valgrind vim xxd \
    && rm -rf /var/lib/apt/lists/*

RUN sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen en_US.UTF-8

RUN git config --global user.email "benchmark@local" \
    && git config --global user.name "secb benchmark" \
    && git config --global advice.detachedHead false

RUN mkdir -p /out /src /testcase /base /app/artifacts

# Keep the heavy Linux clone below the stable toolchain layers and above the
# faster-changing agent layers.
RUN git clone --bare https://github.com/torvalds/linux.git /src/linux.git

COPY base/linux/release.config /base/release.config

ARG CODEX_VERSION=0.142.5
ARG CLAUDE_CODE_VERSION=2.1.198
ARG OPENCODE_VERSION=1.17.13

RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN npm i -g npm@latest @openai/codex@${CODEX_VERSION} opencode-ai@${OPENCODE_VERSION} @beads/bd@0.50.2

RUN ln -sf /usr/bin/make /usr/bin/gmake

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN curl -fsSL https://claude.ai/install.sh | bash -s ${CLAUDE_CODE_VERSION}

COPY base/linux/sanitize-git /usr/local/bin/secb-sanitize-git
RUN chmod +x /usr/local/bin/secb-sanitize-git

# secb-linux-vm-mcp: the in-container harness exposed as MCP tools. Codex spawns
# it outside its sandbox, so QEMU launched from it gets native KVM while the agent
# stays sandboxed. Provides the `secb-linux-vm-mcp` console script (+ fastmcp).
#
# Vendored in this repo at mcps/linux/ and installed from there, so the image
# build is fully self-contained (no private-repo access / gh token needed).
COPY mcps/linux /opt/secb-mcps/linux
RUN (uv pip install --system /opt/secb-mcps/linux \
    || python3 -m pip install --break-system-packages /opt/secb-mcps/linux)

ENV PATH="/root/.local/bin:$PATH"

WORKDIR $SRC
