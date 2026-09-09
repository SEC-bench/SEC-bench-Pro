# Base image for Linux kernel KASAN benchmark leaf images.
# Tag: hwiwonlee/linux.base:latest
#
# This mirrors the validated Linux benchmark base image shape:
#   1. kernel build toolchain for x86_64
#   2. QEMU + busybox-static for in-container repros
#   3. /src/linux.git bare clone for per-CVE worktrees
#   4. /base/release.config universal KASAN/debug baseline
#   5. shared agent/runtime tooling used by the harness

FROM debian:12-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171

ENV DEBIAN_FRONTEND=noninteractive
ENV SRC=/src
ENV OUT=/out

RUN apt-get -o Acquire::Retries=5 update && \
    apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
    build-essential gcc make bison flex bc binutils \
    gcc-multilib libc6-dev-i386 \
    libelf-dev libssl-dev libncurses-dev libdw-dev pkg-config \
    jq cpio gzip xz-utils bzip2 lz4 sqlite3 \
    busybox-static \
    qemu-system-x86 qemu-utils \
    python3 python-is-python3 python3-venv python3-pip perl \
    git ca-certificates curl \
    kmod file dwarves gdb gdbserver \
    bubblewrap gettext-base less xvfb locales ripgrep gawk rsync \
    procps psmisc socat util-linux \
    strace ltrace valgrind vim xxd \
    && rm -rf /var/lib/apt/lists/*

RUN sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen en_US.UTF-8

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

RUN git config --global user.email "benchmark@local" \
    && git config --global user.name "secb benchmark" \
    && git config --global advice.detachedHead false

RUN mkdir -p /out /src /testcase /base /app/artifacts

# Some task commits are fetchable by object ID but are not reachable from the
# refs copied by a normal bare clone. Fetch only those missing objects and keep
# each one reachable so every leaf can create its worktree without networking.
# Clone and fetch in one layer: a fetch may repack the bare repository, and a
# separate layer would retain both the pre-fetch and post-fetch multi-GB packs.
COPY base/linux/required-commits.txt /base/required-commits.txt
COPY base/linux/fetch-required-commits /usr/local/bin/secb-fetch-required-linux-commits
RUN chmod +x /usr/local/bin/secb-fetch-required-linux-commits && \
    timeout --kill-after=30s 3600s \
        git -c http.lowSpeedLimit=1024 -c http.lowSpeedTime=60 \
        clone --bare https://github.com/torvalds/linux.git /src/linux.git && \
    timeout --kill-after=30s 1800s secb-fetch-required-linux-commits \
        /src/linux.git /base/required-commits.txt

COPY base/linux/release.config /base/release.config

# Shared benchmark runtime.
RUN curl -fsSL https://deb.nodesource.com/setup_24.x -o /tmp/nodesource-setup.sh && \
    bash /tmp/nodesource-setup.sh && \
    rm -f /tmp/nodesource-setup.sh && \
    apt-get -o Acquire::Retries=5 install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/make /usr/bin/gmake

COPY --from=ghcr.io/astral-sh/uv:0.12.10@sha256:2bb3ebca0a796a155094a27773d290c4b074572e6107f171d88d086682fd2500 /uv /uvx /bin/

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

RUN command -v secb-linux-vm-mcp >/dev/null && \
    python3 -c 'import fastmcp, secb_linux_vm_mcp'

# Keep agent refreshes after the expensive kernel clone and vendored MCP setup.
ARG CODEX_VERSION=latest
ARG CLAUDE_CODE_VERSION=latest
ARG OPENCODE_VERSION=latest
ARG AGENT_CACHE_BUST=manual

ENV PATH="/root/.local/bin:$PATH" \
    DISABLE_AUTOUPDATER=1 \
    OPENCODE_DISABLE_AUTOUPDATE=1

RUN set -eux; \
    : "agent-cache-bust=${AGENT_CACHE_BUST}"; \
    npm install --global \
        "@openai/codex@${CODEX_VERSION}" \
        "opencode-ai@${OPENCODE_VERSION}" \
        "@beads/bd@0.50.2"; \
    npm cache clean --force; \
    curl -fsSL https://claude.ai/install.sh -o /tmp/claude-install.sh; \
    bash /tmp/claude-install.sh "${CLAUDE_CODE_VERSION}"; \
    ln -sf /root/.local/bin/claude /usr/local/bin/claude; \
    rm -f /tmp/claude-install.sh; \
    for tool in \
        addr2line bwrap curl file gawk gdb envsubst git jq less locale ltrace \
        make pkg-config ps killall python3 pip3 rg rsync socat sqlite3 strace \
        setpriv unshare valgrind vim xxd xz secb-sanitize-git; \
    do \
        command -v "$tool" >/dev/null; \
    done; \
    bash -lc 'command -v codex >/dev/null && command -v opencode >/dev/null && command -v claude >/dev/null'; \
    test -s /etc/ssl/certs/ca-certificates.crt; \
    python3 -m venv --help >/dev/null; \
    { \
        printf 'node='; node --version; \
        printf 'npm='; npm --version; \
        printf 'codex='; timeout --kill-after=5s 30s codex --version; \
        printf 'opencode='; timeout --kill-after=5s 30s opencode --version; \
        printf 'claude='; timeout --kill-after=5s 30s claude --version; \
        printf 'uv='; uv --version; \
        printf 'bd='; timeout --kill-after=5s 30s bd --version; \
    } > /etc/secb-agent-versions

WORKDIR $SRC
