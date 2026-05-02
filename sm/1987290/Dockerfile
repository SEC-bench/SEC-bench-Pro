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
RUN apt-get update && apt-get install -y python3-venv python3-pip
ENV PATH="/root/.mozbuild/cbindgen:/root/.cargo/bin:${PATH}"

WORKDIR $SRC/gecko-dev

# Vulnerable revision: parent of fix 2b8155c2c4c299955d4ae81423992ed56a838aee
# Bug 1987290 (sec-high) — FinalizationRegistry.unregister OOB args read.
# args[0] is used without bounds check; calling .unregister() with no args
# reads past the call frame outgoing-arg area. Regressed by Bug 1863140
# Part 3 (D263113). Fix: Use args.get() instead of args[] (Tooru
# Fujisawa, 2025-09-08).
RUN git checkout 2b8155c2c4c299955d4ae81423992ed56a838aee~1

# 2025-09 revisions need cbindgen >= 0.29.1 (base image ships 0.28.0)
RUN cargo install cbindgen --force --locked --version 0.29.1

# Build 1: ASAN+debug
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

# Build 2: Release
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
RUN mkdir -p /app/artifacts /testcase
