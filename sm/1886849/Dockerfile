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

WORKDIR $SRC/gecko-dev

# Checkout vulnerable revision (parent of fix 45d29e78c0d8)
# https://bugzilla.mozilla.org/show_bug.cgi?id=1886849: MObjectKeysLength::computeRange is incorrect
RUN git checkout 81806e7ccec7dde41e37c9891592a6e39ce46380~1

# Patch: delete broken move constructor/assignment in ExclusiveData.h (clang-19 rejects it)
RUN python3 -c "\
f='js/src/threading/ExclusiveData.h'; t=open(f).read(); \
t=t.replace('  ExclusiveData(ExclusiveData&& rhs)\n      : lock_(std::move(rhs.lock)), value_(std::move(rhs.value_)) {\n    MOZ_ASSERT(&rhs != this, \"self-move disallowed!\");\n  }\n\n  ExclusiveData& operator=(ExclusiveData&& rhs) {\n    this->~ExclusiveData();\n    new (mozilla::KnownNotNull, this) ExclusiveData(std::move(rhs));\n    return *this;\n  }', \
'  ExclusiveData(ExclusiveData&&) = delete;\n  ExclusiveData& operator=(ExclusiveData&&) = delete;'); \
open(f,'w').write(t)"

# Remove bootstrap-generated mozconfig and configure Debug+ASAN build for JS shell
# Point to bootstrapped tools from base image
ENV PATH="/root/.mozbuild/cbindgen:/root/.cargo/bin:${PATH}"


# Build 1: ASAN+debug (for crash verification) — standard config
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
