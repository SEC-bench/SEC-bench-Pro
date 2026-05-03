FROM hwiwonlee/sm.base:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV SRC=/src

ENV SANITIZER="address"
ENV ARCHITECTURE="x86_64"

ENV OUT=/out

RUN ln -sf /usr/local/bin/python3 /usr/bin/python
ENV PATH="/root/.mozbuild/cbindgen:/root/.cargo/bin:${PATH}"

WORKDIR $SRC/gecko-dev

# Vulnerable revision: parent of fix 23cf0b3985c329aae2898bae518a7f5813c132ae
# Bug 2013562 / CVE-2026-2765 — same-thread Atomics.waitAsync resolves cross-realm
# promise without entering its realm in atomics_notify_impl, leading to a
# compartment/realm mismatch at PromiseObject::resolve.
# Fix author: Iain Ireland, 2026-02-09
RUN git checkout 23cf0b3985c329aae2898bae518a7f5813c132ae~1

# This revision (2026-02-09) requires cbindgen >= 0.29.1; the base image ships 0.28.0.
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
