# V8 base image built on OSS-Fuzz Ubuntu 24.04 base
# Reference: https://github.com/google/oss-fuzz/blob/master/infra/base-images/base-image/ubuntu-24-04.Dockerfile

# ---- OSS-Fuzz base image (Ubuntu 24.04) ----
FROM ubuntu:24.04@sha256:9cbed754112939e914291337b5e554b07ad7c392491dba6daf25eef1332a22e8

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y libc6-dev binutils libgcc-13-dev tzdata sqlite3 ripgrep && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV OUT=/out
ENV SRC=/src
ENV WORK=/work
ENV PATH="$PATH:/out"
ENV HWASAN_OPTIONS=random_tags=0

RUN mkdir -p $OUT $SRC $WORK && chmod a+rwx $OUT $SRC $WORK

# ---- System dependencies for depot_tools and V8 ----
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    file \
    git \
    gdb \
    gettext-base \
    gnupg \
    jq \
    make \
    ripgrep \
    vim \
    libglib2.0-dev \
    locales \
    lsb-release \
    pkg-config \
    python3 \
    python3-pip \
    python3-setuptools \
    python3-venv \
    sudo \
    wget \
    xvfb \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Set up locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Symlink python3 to python for depot_tools compatibility
RUN ln -sf /usr/bin/python3 /usr/bin/python

# ---- Install depot_tools (provides gclient, gn, autoninja, fetch, etc.) ----
RUN git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git /opt/depot_tools
ENV PATH="/opt/depot_tools:$PATH"

# Make git fetches more robust in Docker (big repos + googlesource mirrors)
ENV GIT_HTTP_VERSION=HTTP/1.1

# ---- Fetch V8 source ----
WORKDIR $SRC

# fetch v8: creates .gclient in $SRC and clones source into $SRC/src
RUN fetch v8

WORKDIR $SRC/v8

# ---- Shared benchmark runtime and coding agents ----
ARG CODEX_VERSION=0.122.0
ARG CLAUDE_CODE_VERSION=2.1.116
ARG OPENCODE_VERSION=1.14.19

RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN npm i -g npm@latest @openai/codex@${CODEX_VERSION} opencode-ai@${OPENCODE_VERSION} @beads/bd@0.50.2

RUN ln -sf /usr/bin/make /usr/bin/gmake

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY sanitize-git /usr/local/bin/secb-sanitize-git
RUN chmod +x /usr/local/bin/secb-sanitize-git

RUN curl -fsSL https://claude.ai/install.sh | bash -s ${CLAUDE_CODE_VERSION}

ENV PATH="/root/.local/bin:$PATH"
