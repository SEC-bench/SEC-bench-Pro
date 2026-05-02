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
RUN apt-get update && apt-get install -y python3-venv python3-pip
ENV PATH="/root/.mozbuild/cbindgen:/root/.cargo/bin:${PATH}"

WORKDIR $SRC/gecko-dev

# Vulnerable revision: parent of fix d867a6f69b9f026674f2e846572748818a61a41b
# Bug 2013741 / CVE-2026-2767 (sec-high, MFSA 2026-15) —
# js/src/wasm/WasmBaselineCompile.cpp:BaseCompiler::emitArrayFill emits the
# per-element store of a WASM GC array.fill with PreBarrierKind::None. For
# array element writes that overwrite an existing reference, the missing
# pre-write barrier means SpiderMonkey's snapshot-at-the-beginning incremental
# marker can lose track of the overwritten reference, leaving a swept-but-still
# referenced cell that becomes a dangling pointer.
# Fix author: Ben Visness, 2026-02-09
RUN git checkout d867a6f69b9f026674f2e846572748818a61a41b~1

# This revision (2026-02-09) requires cbindgen >= 0.29.1; base image ships 0.28.0.
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

# Install Node.js, latest npm, and OpenAI Codex
RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
  apt-get install -y nodejs
RUN npm i -g npm@latest @openai/codex

RUN ln -s /usr/bin/make /usr/bin/gmake || true

# Install beads
RUN npm install -g @beads/bd@0.50.2 || true

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# API KEY config entrypoint
RUN apt-get update && apt-get install -y gettext-base
RUN cat > /entrypoint.sh <<'ENTRYEOF'
#!/bin/bash
mkdir -p /root/.codex
cat <<EOT | envsubst > /root/.codex/auth.json
{
  "OPENAI_API_KEY": "${OPENAI_API_KEY}",
  "model": "gpt-5-mini",
  "provider": "openai"
}
EOT
exec "$@"
ENTRYEOF

# Install Claude Code
ENV PATH="/root/.local/bin:${PATH}"
RUN curl -fsSL https://claude.ai/install.sh | bash

RUN bd init || true

RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
