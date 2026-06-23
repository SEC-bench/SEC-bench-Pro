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
ENV MACH_USE_SYSTEM_PYTHON=1

# Old-era (2020) compat: this revision's mach is incompatible with the base's
# Python 3.11 (collections.Sequence / open(mode='rU') removed). Provide a
# uv-managed Python 3.9 and use the system-python path for the build.
RUN uv python install 3.9 && \
    ln -sf "$(uv python find 3.9)" /usr/local/bin/python && \
    ln -sf "$(uv python find 3.9)" /usr/local/bin/python3

WORKDIR $SRC/gecko-dev

# Checkout vulnerable revision (parent of fix)
# https://bugzilla.mozilla.org/show_bug.cgi?id=1736310
# WeakCache::needsSweep collided with GCPolicy sweep on TypedArray buffer. sec-high; fix landed as git a05bddc2ecd5.
RUN git checkout 109d3a5473a8

# Patch: delete broken move constructor/assignment in ExclusiveData.h
# (clang-19 rejects it on older revisions)
RUN python3 -c "\
f='js/src/threading/ExclusiveData.h'; t=open(f).read(); \
t=t.replace('  ExclusiveData(ExclusiveData&& rhs)\n      : lock_(std::move(rhs.lock)), value_(std::move(rhs.value_)) {\n    MOZ_ASSERT(&rhs != this, \"self-move disallowed!\");\n  }\n\n  ExclusiveData& operator=(ExclusiveData&& rhs) {\n    this->~ExclusiveData();\n    new (mozilla::KnownNotNull, this) ExclusiveData(std::move(rhs));\n    return *this;\n  }', \
'  ExclusiveData(ExclusiveData&&) = delete;\n  ExclusiveData& operator=(ExclusiveData&&) = delete;'); \
open(f,'w').write(t)" || true

# clang-12+ no longer accepts -fexperimental-new-pass-manager (new PM is default).
# Remove the flag from 2020 mach build config.
RUN sed -i 's|return \["-fexperimental-new-pass-manager"\]|return []|; s|return \["-Xclang", "-fexperimental-new-pass-manager"\]|return []|' build/moz.configure/flags.configure || true

# Cargo 1.50+ rejects deps that specify both `branch` and `rev`; 2020 Cargo.toml
# had `nix` and `spirv_cross` with both. Drop branch=, keep rev= (more precise).
RUN sed -i 's/, branch = "r0.13.1"//; s/, branch = "wgpu4"//' Cargo.toml || true

# 2021-Oct mozbuild/virtualenv.py uses Debian-patched distutils to locate the
# new virtualenv's site-packages — distutils answers .../local/lib/.../dist-packages
# (a Debian-only invention the venv never creates), so the listdir() crashes.
# Short-circuit _disable_pip_outdated_warning (the warning we'd suppress is harmless).
RUN sed -i 's|def _disable_pip_outdated_warning(self):|def _disable_pip_outdated_warning(self):\n        return  # debian distutils path mismatch|' python/mozbuild/mozbuild/virtualenv.py || true

# Build 1: ASAN+debug (for crash verification)
RUN rm -f mozconfig .mozconfig && cat > .mozconfig <<'EOF'
ac_add_options --enable-optimize="-O1"
ac_add_options --enable-debug
ac_add_options --enable-debug-symbols
ac_add_options --enable-application=js
ac_add_options --disable-bootstrap
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-debug
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
RUN ln -sf $SRC/gecko-dev/obj-debug/dist/bin/js /out/js
RUN ln -sf $SRC/gecko-dev/obj-release/dist/bin/js /out/js-release

COPY build.sh $SRC/
COPY secb.sh /usr/local/bin/secb
RUN chmod +x $SRC/build.sh && chmod +x /usr/local/bin/secb
RUN mkdir -p /app/artifacts /testcase

RUN secb-sanitize-git $SRC/gecko-dev
