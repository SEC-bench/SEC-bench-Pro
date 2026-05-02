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

# Vulnerable revision: parent of fix 0264cf850afd91cdd3956066e0b00b982566f684
# Bug 2003588 / CVE-2026-0884 — Debugger + CCW UAF / assertion failure.
# After nukeAllCCWs(), the Debugger machinery still attempts to create
# cross-compartment wrappers to debugger instances while the wrapper
# machinery refuses; the invariant violation manifests as assertion /
# UAF on a Debugger object.
# Fix author: 2025-12-08 (MFSA 2026-01).
RUN git checkout 0264cf850afd91cdd3956066e0b00b982566f684~1

RUN cargo install cbindgen --force --locked --version 0.29.1

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

RUN curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
  apt-get install -y nodejs
RUN npm i -g npm@latest @openai/codex

RUN ln -s /usr/bin/make /usr/bin/gmake || true

RUN npm install -g @beads/bd@0.50.2 || true

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

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

ENV PATH="/root/.local/bin:${PATH}"
RUN curl -fsSL https://claude.ai/install.sh | bash

RUN bd init || true

RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
