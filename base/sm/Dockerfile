FROM ubuntu:24.04@sha256:9cbed754112939e914291337b5e554b07ad7c392491dba6daf25eef1332a22e8

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
    binutils \
    jq \
    vim \
    libgcc-13-dev \
    libc6-dev \
    ripgrep \
    sqlite3 \
    tzdata && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV OUT=/out
ENV SRC=/src
ENV WORK=/work
ENV PATH="$PATH:/out"
ENV HWASAN_OPTIONS=random_tags=0

RUN mkdir -p $OUT $SRC $WORK && chmod a+rwx $OUT $SRC $WORK

# System dependencies for building Gecko/SpiderMonkey and for the instance
# Dockerfiles that layer on top of this base image.
RUN apt-get update && apt-get install -y \
    autoconf2.13 \
    automake \
    build-essential \
    ca-certificates \
    ccache \
    clang \
    cmake \
    curl \
    file \
    gettext-base \
    git \
    lld \
    llvm \
    locales \
    libtool \
    m4 \
    make \
    ninja-build \
    pkg-config \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-venv \
    sudo \
    unzip \
    wget \
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
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/python3.11 /usr/local/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/local/bin/python3 && \
    ln -sf /usr/bin/make /usr/bin/gmake || true

# Shared benchmark runtime and coding agents.
ARG CODEX_VERSION=0.122.0
ARG CLAUDE_CODE_VERSION=2.1.116
ARG OPENCODE_VERSION=1.14.19

RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN npm i -g npm@latest @openai/codex@${CODEX_VERSION} opencode-ai@${OPENCODE_VERSION} @beads/bd@0.50.2

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY sanitize-git /usr/local/bin/secb-sanitize-git
RUN chmod +x /usr/local/bin/secb-sanitize-git

RUN curl -fsSL https://claude.ai/install.sh | bash -s ${CLAUDE_CODE_VERSION}

ENV PATH="/root/.local/bin:$PATH"

# Install Rust tooling and the cbindgen version the existing SpiderMonkey
# instance images expect by default.
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal --default-toolchain stable
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
RUN git clone --filter=blob:none --single-branch --branch main https://github.com/mozilla-firefox/firefox.git $SRC/gecko-dev && \
    cd $SRC/gecko-dev && \
    git remote rename origin firefox && \
    git remote add gecko-dev https://github.com/mozilla/gecko-dev.git && \
    git fetch gecko-dev master

WORKDIR $SRC/gecko-dev

RUN MOZBUILD_STATE_PATH=/root/.mozbuild MACH_NO_INTERACTIVE=1 ./mach bootstrap --application-choice=js

ENV PATH="/root/.mozbuild/clang/bin:/root/.cargo/bin:/root/.mozbuild/cbindgen:$PATH"
