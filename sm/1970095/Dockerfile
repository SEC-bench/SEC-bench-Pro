FROM hwiwonlee/sm.base:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV SRC=/src
ENV OUT=/out

RUN ln -sf /usr/local/bin/python3 /usr/bin/python
RUN apt-get update && apt-get install -y python3-venv python3-pip

WORKDIR $SRC/gecko-dev

RUN git checkout 4f27a916218de6a299db8d00d48ad5e91db9832d~1

ENV PATH="/root/.mozbuild/cbindgen:/root/.cargo/bin:${PATH}"

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
RUN chmod +x $SRC/build.sh && chmod +x /usr/local/bin/secb
RUN mkdir -p /app/artifacts /testcase

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
