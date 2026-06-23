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

# Checkout vulnerable revision (parent of fix)
# https://bugzilla.mozilla.org/show_bug.cgi?id=1970811
# Crash [@ js::NativeDefineProperty] / Assertion failure: isObject(), at js/Value.h:972
# Type confusion: missing OOM check when creating a SuppressedError during
# AsyncDisposableStack disposal (explicit resource management). Regressed by
# bug 1927195 (enabled the ERM build flag on nightly). Fix: hg c3ab38fe90bf
# "Check for out of memory when creating SuppressedError" (Phabricator D230733).
RUN git checkout 7d8ed94f78e0

# Build 1: ASAN+debug (for crash verification)
# Patch ExclusiveData.h (clang-19 rejects pre-Q2-2024 move ctor).
COPY patches/fix_exclusive_data.sh /tmp/
RUN bash /tmp/fix_exclusive_data.sh

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
RUN chmod +x $SRC/build.sh && chmod +x /usr/local/bin/secb
RUN mkdir -p /app/artifacts /testcase

RUN secb-sanitize-git $SRC/gecko-dev
