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

# Vulnerable revision: parent of fix fa91ed58b791e04279b8fbfd6476550dd1fcb27b
# Bug 1989978 (CVE-2025-11711) — JSON.stringify SEGV.
# FastSerializeJSONProperty trusts the rawJSON slot pointer cached after the
# first MaybeGetRawJSON probe; an `for ... in` body can rewrite the slot to
# an integer, and the next stringify dereferences the int as a JSString*.
# Fix: Don't support unwritable iterator indices (Jan de Mooij, 2025-09-26).
RUN git checkout fa91ed58b791e04279b8fbfd6476550dd1fcb27b~1

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

RUN secb-sanitize-git $SRC/gecko-dev
