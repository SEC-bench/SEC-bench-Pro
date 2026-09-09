# V8 base image built on OSS-Fuzz Ubuntu 24.04 base
# Reference: https://github.com/google/oss-fuzz/blob/master/infra/base-images/base-image/ubuntu-24-04.Dockerfile

# ---- OSS-Fuzz base image (Ubuntu 24.04) ----
FROM ubuntu:24.04@sha256:9cbed754112939e914291337b5e554b07ad7c392491dba6daf25eef1332a22e8

ENV DEBIAN_FRONTEND=noninteractive

ARG UBUNTU_ARCHIVE_MIRROR=http://archive.ubuntu.com/ubuntu
RUN sed -i "s|http://archive.ubuntu.com/ubuntu|${UBUNTU_ARCHIVE_MIRROR}|g" \
        /etc/apt/sources.list.d/ubuntu.sources && \
    apt-get -o Acquire::Retries=5 update && \
    apt-get -o Acquire::Retries=5 upgrade -y && \
    apt-get -o Acquire::Retries=5 install -y libc6-dev libgcc-13-dev tzdata && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV OUT=/out
ENV SRC=/src
ENV WORK=/work
ENV PATH="$PATH:/out"
ENV HWASAN_OPTIONS=random_tags=0

RUN mkdir -p $OUT $SRC $WORK && chmod a+rwx $OUT $SRC $WORK

# ---- Shared analysis/runtime tools and V8 build dependencies ----
RUN apt-get -o Acquire::Retries=5 update && apt-get -o Acquire::Retries=5 install -y \
    binutils \
    bubblewrap \
    ca-certificates \
    curl \
    file \
    gawk \
    gdb \
    gettext-base \
    git \
    gnupg \
    jq \
    less \
    libglib2.0-dev \
    locales \
    ltrace \
    lsb-release \
    make \
    pkg-config \
    procps \
    psmisc \
    python3 \
    python3-pip \
    python3-setuptools \
    python3-venv \
    ripgrep \
    rsync \
    socat \
    sqlite3 \
    strace \
    sudo \
    util-linux \
    valgrind \
    vim \
    wget \
    xvfb \
    xxd \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Set up locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Symlink python3 to python for depot_tools compatibility
RUN ln -sf /usr/bin/python3 /usr/bin/python

# ---- Install depot_tools (provides gclient, gn, autoninja, fetch, etc.) ----
ARG DEPOT_TOOLS_REF=1ea94929dc77e2b9b9b9e2ede3bbc0f39c10ebc9
ARG GCLIENT_JOBS=16
ARG GCLIENT_SYNC_TIMEOUT_SEC=3600
ENV DEPOT_TOOLS_UPDATE=0 \
    DEPOT_TOOLS_METRICS=0 \
    COLLECT_METRICS=0 \
    GCLIENT_JOBS=${GCLIENT_JOBS} \
    GCLIENT_SYNC_TIMEOUT_SEC=${GCLIENT_SYNC_TIMEOUT_SEC} \
    PATH="/opt/depot_tools:$PATH"
COPY gclient-wrapper /tmp/secb-gclient-wrapper

# Apply the transport guards before the first Chromium fetch. The wall-clock
# timeout prevents an indefinitely stalled depot_tools clone from hanging a
# Docker build even when the server keeps the connection open.
RUN git config --system http.version HTTP/1.1 && \
    git config --system http.lowSpeedLimit 1024 && \
    git config --system http.lowSpeedTime 60

RUN timeout --kill-after=10s 600s \
        git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git /opt/depot_tools && \
    git -C /opt/depot_tools checkout --detach "$DEPOT_TOOLS_REF" && \
    timeout --kill-after=10s 300s /opt/depot_tools/ensure_bootstrap && \
    mv /opt/depot_tools/gclient /opt/depot_tools/gclient.unbounded && \
    install -m 0755 /tmp/secb-gclient-wrapper /opt/depot_tools/gclient && \
    gclient help >/dev/null && \
    gclient sync --help | grep -q -- '--nohooks' && \
    fetch --help >/dev/null && \
    luci-auth --help >/dev/null && \
    python3 /opt/depot_tools/gsutil.py -- version >/dev/null

# ---- Fetch V8 source ----
WORKDIR $SRC

# Clone the pinned source first. `fetch v8` syncs the current upstream head
# before a later checkout, which makes this supposedly pinned layer depend on
# mutable upstream state and can fan out hundreds of gclient jobs on large hosts.
ARG V8_BASE_REF=dbb6746443d3db53c5067d4a846a1dd192844558
RUN git init "$SRC/v8" && \
    git -C "$SRC/v8" remote add origin \
        https://chromium.googlesource.com/v8/v8.git && \
    git -C "$SRC/v8" fetch --depth=1 --no-tags origin "$V8_BASE_REF" && \
    git -C "$SRC/v8" checkout --detach FETCH_HEAD && \
    gclient config --name v8 --unmanaged \
        https://chromium.googlesource.com/v8/v8.git && \
    git -C "$SRC/v8" clean -xdf

WORKDIR $SRC/v8

# ---- Shared benchmark runtime and coding agents ----
RUN curl -fsSL https://deb.nodesource.com/setup_24.x -o /tmp/nodesource-setup.sh && \
    bash /tmp/nodesource-setup.sh && \
    rm -f /tmp/nodesource-setup.sh && \
    apt-get -o Acquire::Retries=5 install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/make /usr/bin/gmake

COPY --from=ghcr.io/astral-sh/uv:0.12.10@sha256:2bb3ebca0a796a155094a27773d290c4b074572e6107f171d88d086682fd2500 /uv /uvx /bin/

COPY sanitize-git /usr/local/bin/secb-sanitize-git
RUN chmod +x /usr/local/bin/secb-sanitize-git

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
