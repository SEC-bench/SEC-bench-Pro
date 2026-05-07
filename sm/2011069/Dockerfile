FROM hwiwonlee/sm.base:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV SRC=/src
ENV OUT=/out

RUN ln -sf /usr/local/bin/python3 /usr/bin/python
ENV PATH="/root/.mozbuild/cbindgen:/root/.cargo/bin:${PATH}"

WORKDIR $SRC/gecko-dev

# Bug 2011069 (CVE-2026-2802): GC gray bits invalid during sweeping
# Actual fix: 34384ff7e250e "Wait for sweeping before marking gray bits invalid"
# Checkout parent of actual fix to get vulnerable version
RUN git checkout 34384ff7e250e7bdf10717337eb689c87138863c~1

# Extract test file from the fix commit to use as PoC reference
RUN git show 4faa7e9916a8f:js/src/jit-test/tests/gc/bug-2011069.js > /tmp/poc_test.js 2>/dev/null || true

# Patch: delete broken move constructor/assignment in ExclusiveData.h (clang-19 rejects it)
RUN python3 -c "\
f='js/src/threading/ExclusiveData.h'; t=open(f).read(); \
t=t.replace('  ExclusiveData(ExclusiveData&& rhs)\n      : lock_(std::move(rhs.lock)), value_(std::move(rhs.value_)) {\n    MOZ_ASSERT(&rhs != this, \"self-move disallowed!\");\n  }\n\n  ExclusiveData& operator=(ExclusiveData&& rhs) {\n    this->~ExclusiveData();\n    new (mozilla::KnownNotNull, this) ExclusiveData(std::move(rhs));\n    return *this;\n  }', \
'  ExclusiveData(ExclusiveData&&) = delete;\n  ExclusiveData& operator=(ExclusiveData&&) = delete;'); \
open(f,'w').write(t)" || true

# Build 1: ASAN+debug (for crash verification)
RUN rm -f mozconfig .mozconfig && cat > .mozconfig <<'EOF'
ac_add_options --enable-address-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --enable-optimize="-O1"
ac_add_options --enable-debug
ac_add_options --enable-debug-symbols
ac_add_options --enable-application=js
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-debug-asan
EOF
RUN ./mach build

# Build 2: Release (for normal execution)
RUN rm -f mozconfig .mozconfig && cat > .mozconfig <<'EOF'
ac_add_options --enable-optimize
ac_add_options --disable-debug
ac_add_options --enable-application=js
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
