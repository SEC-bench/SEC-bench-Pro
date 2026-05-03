FROM hwiwonlee/sm.base:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV SRC=/src
ENV SHELL=/bin/bash

ENV SANITIZER="address"
ENV ARCHITECTURE="x86_64"

ENV OUT=/out

RUN ln -sf /usr/local/bin/python3 /usr/bin/python || true
ENV PATH="/root/.mozbuild/cbindgen:/root/.cargo/bin:${PATH}"

WORKDIR $SRC/gecko-dev

# Vulnerable revision: parent of fix 0d8fa127358980af62ad70abdcba632f0c683a91
# Bug 2023024 (embargoed, likely sec-high) — CacheIR
# IRGenerator::canOptimizeConstantDataProperty creates an ObjectFuse for a
# property that lives in a JSClass reserved slot. Watchtower does not watch
# reserved-slot writes, so the fuse is never invalidated when the engine
# rewrites the slot (e.g. RegExp `lastIndex`), and Ion-compiled reads return
# the stale cached value — a type-confused Value.
# Fix author: Iain Ireland, 2026-03-16
RUN git checkout 0d8fa127358980af62ad70abdcba632f0c683a91~1

# 2026-03 revisions require cbindgen >= 0.29.1; base image ships 0.28.0.
RUN cargo install cbindgen --force --locked --version 0.29.1

# Build 1: ASAN+debug (for crash verification)
RUN rm -f mozconfig .mozconfig && cat > .mozconfig <<'EOF'
ac_add_options --enable-address-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --enable-optimize="-O1"
ac_add_options --enable-debug
ac_add_options --enable-debug-symbols
ac_add_options --enable-application=js
ac_add_options --disable-bootstrap
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-debug-asan
EOF
RUN ./mach build

# Build 2: Release (for normal execution)
RUN rm -f mozconfig .mozconfig && cat > .mozconfig <<'EOF'
ac_add_options --enable-optimize
ac_add_options --disable-debug
ac_add_options --enable-application=js
ac_add_options --disable-bootstrap
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-release
EOF
RUN ./mach build

RUN mkdir -p /out
RUN ln -sf $SRC/gecko-dev/obj-debug-asan/dist/bin/js /out/js
RUN ln -sf $SRC/gecko-dev/obj-release/dist/bin/js /out/js-release

COPY build.sh $SRC/
COPY secb.sh /usr/local/bin/secb

RUN chmod +x $SRC/build.sh
RUN chmod +x /usr/local/bin/secb
RUN mkdir -p /app/artifacts
RUN mkdir -p /testcase
