FROM ubuntu:24.04@sha256:9cbed754112939e914291337b5e554b07ad7c392491dba6daf25eef1332a22e8

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get -o Acquire::Retries=5 update && \
    apt-get -o Acquire::Retries=5 upgrade -y && \
    apt-get -o Acquire::Retries=5 install -y \
    libgcc-13-dev \
    libc6-dev \
    tzdata && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV OUT=/out
ENV SRC=/src
ENV WORK=/work
ENV PATH="$PATH:/out"
ENV HWASAN_OPTIONS=random_tags=0

RUN mkdir -p $OUT $SRC $WORK && chmod a+rwx $OUT $SRC $WORK

# Shared analysis/runtime tools plus Gecko/SpiderMonkey build dependencies.
RUN apt-get -o Acquire::Retries=5 update && apt-get -o Acquire::Retries=5 install -y \
    autoconf2.13 \
    automake \
    binutils \
    bubblewrap \
    build-essential \
    ca-certificates \
    ccache \
    clang \
    cmake \
    curl \
    file \
    gawk \
    gdb \
    gettext-base \
    git \
    jq \
    less \
    lld \
    llvm \
    locales \
    ltrace \
    libtool \
    m4 \
    make \
    ninja-build \
    pkg-config \
    procps \
    psmisc \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-venv \
    ripgrep \
    rsync \
    socat \
    sqlite3 \
    strace \
    sudo \
    unzip \
    util-linux \
    valgrind \
    vim \
    wget \
    xxd \
    xz-utils \
    zip \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV SHELL=/bin/bash

# Pre-2024 SpiderMonkey's mach imports the `imp` module which Python 3.12
# (the default on ubuntu:24.04) removed. Install python3.11 from deadsnakes
# and point /usr/local/bin/python ahead of /usr/bin/python3 so mach picks
# it up while leaving the system python3.12 in place for apt and friends.
RUN apt-get -o Acquire::Retries=5 update && \
    apt-get -o Acquire::Retries=5 install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get -o Acquire::Retries=5 install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/python3.11 /usr/local/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/local/bin/python3 && \
    ln -sf /usr/bin/make /usr/bin/gmake

# Shared benchmark runtime.
RUN curl -fsSL https://deb.nodesource.com/setup_24.x -o /tmp/nodesource-setup.sh && \
    bash /tmp/nodesource-setup.sh && \
    rm -f /tmp/nodesource-setup.sh && \
    apt-get -o Acquire::Retries=5 install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Keep Rust compatible with the oldest SpiderMonkey revisions in this dataset.
# Newer rustc host triples are not understood by their configure scripts.
ARG RUST_VERSION=1.95.0
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal --default-toolchain "${RUST_VERSION}"
ENV PATH="/root/.cargo/bin:/root/.mozbuild/cbindgen:$PATH"
RUN cargo install cbindgen --locked --version 0.28.0

WORKDIR $SRC

# SpiderMonkey lives in two unrelated git universes after Mozilla's hg→git
# migration. Post-2025 instance Dockerfiles checkout commits that exist only
# in mozilla-firefox/firefox; pre-2025 instance Dockerfiles checkout commits
# that exist only in mozilla/gecko-dev. Carry both remotes so both eras
# resolve from a clean build.
#
# Firefox is the primary remote (cloned into $SRC/gecko-dev — the historical
# path the instance Dockerfiles use). gecko-dev is fetched as a second
# remote without --filter so legacy `git checkout <gecko-dev sha>` doesn't
# need to lazy-fetch from a partial-clone promisor that points elsewhere.
ARG FIREFOX_REF=dab03896ede1413be148884e054b311767bcf1a0
ARG GECKO_DEV_REF=5836a062726f715fda621338a17b51aff30d0a8c
RUN git clone --filter=blob:none --single-branch --branch main https://github.com/mozilla-firefox/firefox.git $SRC/gecko-dev && \
    cd $SRC/gecko-dev && \
    git remote rename origin firefox && \
    git remote add gecko-dev https://github.com/mozilla/gecko-dev.git && \
    git fetch firefox "$FIREFOX_REF" && \
    git checkout --detach "$FIREFOX_REF" && \
    git fetch gecko-dev "$GECKO_DEV_REF:refs/remotes/gecko-dev/master" && \
    git clean -xdf

WORKDIR $SRC/gecko-dev

RUN MOZBUILD_STATE_PATH=/root/.mozbuild MACH_NO_INTERACTIVE=1 ./mach bootstrap --application-choice=js

ENV PATH="/root/.mozbuild/clang/bin:/root/.cargo/bin:/root/.mozbuild/cbindgen:$PATH"

# Keep pip/pip3 on the same Python 3.11 interpreter selected above for mach.
RUN printf '%s\n' '#!/bin/sh' 'exec /usr/local/bin/python3 -m pip "$@"' \
        > /usr/local/bin/pip3 && \
    chmod 0755 /usr/local/bin/pip3 && \
    ln -sf /usr/local/bin/pip3 /usr/local/bin/pip

# Keep agent refreshes after the expensive source clone and mach bootstrap.
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
    python3 -m pip --version | grep -q 'python 3.11'; \
    pip3 --version | grep -q 'python 3.11'; \
    { \
        printf 'node='; node --version; \
        printf 'npm='; npm --version; \
        printf 'codex='; timeout --kill-after=5s 30s codex --version; \
        printf 'opencode='; timeout --kill-after=5s 30s opencode --version; \
        printf 'claude='; timeout --kill-after=5s 30s claude --version; \
        printf 'uv='; uv --version; \
        printf 'bd='; timeout --kill-after=5s 30s bd --version; \
    } > /etc/secb-agent-versions
