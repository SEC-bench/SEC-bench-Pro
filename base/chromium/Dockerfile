# Chromium base image built on OSS-Fuzz Ubuntu 24.04 base
# Reference: https://github.com/google/oss-fuzz/blob/master/infra/base-images/base-image/ubuntu-24-04.Dockerfile

# ---- OSS-Fuzz base image (Ubuntu 24.04) ----
FROM ubuntu:24.04@sha256:9cbed754112939e914291337b5e554b07ad7c392491dba6daf25eef1332a22e8

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y libc6-dev binutils libgcc-13-dev tzdata sqlite3 && \
    apt-get autoremove -y

ENV OUT=/out
ENV SRC=/src
ENV WORK=/work
ENV PATH="$PATH:/out"
ENV HWASAN_OPTIONS=random_tags=0

RUN mkdir -p $OUT $SRC $WORK && chmod a+rwx $OUT $SRC $WORK

# ---- System dependencies for depot_tools and Chromium ----
RUN apt-get update && apt-get install -y \
    curl \
    file \
    git \
    locales \
    lsb-release \
    python3 \
    python3-setuptools \
    sudo \
    wget \
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

# ---- Fetch Chromium source ----
WORKDIR $SRC

# fetch chromium: creates .gclient in $SRC and clones source into $SRC/src
RUN fetch --nohooks --no-history chromium

WORKDIR $SRC/src

# Install Chromium-specific build dependencies (sysroot, libraries, etc.)
RUN ./build/install-build-deps.sh --no-prompt --no-arm --no-chromeos-fonts --no-nacl

# Run gclient hooks to pull toolchains (clang, rust, etc.) and generated files
RUN gclient runhooks
