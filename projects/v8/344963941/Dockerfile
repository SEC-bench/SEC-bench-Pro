FROM hwiwonlee/v8.base:latest

ARG NINJA_JOBS

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV SRC=/src

ENV FUZZING_LANGUAGE="c++"
ENV SANITIZER="address"
ENV ARCHITECTURE="x86_64"
ENV FUZZING_ENGINE="libfuzzer"
ENV PATH="/opt/depot_tools:$PATH"

ENV OUT=/out
ENV CC="clang"
ENV CXX="clang++"
ENV CCC="clang++"
ENV CFLAGS="-O1 -fno-omit-frame-pointer -gline-tables-only"
ENV CXXFLAGS_EXTRA="-stdlib=libc++"
ENV CXXFLAGS="-O1 -fno-omit-frame-pointer -gline-tables-only"
ENV LIB_FUZZING_ENGINE_DEPRECATED="/usr/lib/libFuzzingEngine.a"
ENV LIB_FUZZING_ENGINE="/usr/lib/libFuzzingEngine.a"
ENV COVERAGE_FLAGS="-fsanitize=fuzzer-no-link"
ENV COVERAGE_FLAGS_coverage="-fprofile-instr-generate -fcoverage-mapping -pthread"

# Clean cipd cache
RUN rm -rf $SRC/.cipd

WORKDIR $SRC/v8

# https://issues.chromium.org/issues/344963941: V8 Sandbox Bypass: Irregexp engine bytecode modification leads to arbitrary read/write outside the sandbox
RUN git fetch origin 2106d9c81a1fb9d758ebda1560e2251b0f05150c && git checkout 2106d9c81a1fb9d758ebda1560e2251b0f05150c

RUN gclient sync -D
RUN mkdir -p /usr/local/ssl && ln -sf /etc/ssl/certs/ca-certificates.crt /usr/local/ssl/cert.pem
RUN /usr/bin/python3 tools/clang/scripts/update.py

RUN gn gen out/x64.release --args=' \
  is_debug=false \
  is_asan=false \
  dcheck_always_on=true \
  v8_enable_slow_dchecks=false \
  target_cpu="x64" \
  v8_target_cpu="x64" \
  use_sysroot=true \
  v8_enable_sandbox=true \
  v8_enable_pointer_compression=true \
  v8_enable_memory_corruption_api=true \
  is_component_build=false \
  '

RUN ninja -j"${NINJA_JOBS:-$(nproc)}" -C out/x64.release d8

# **IMPORTANT**: DO **NOT** MODIFY OR REMOVE THE BELOW STATEMENTS

RUN mkdir -p /out
RUN ln -sf $SRC/v8/out/x64.release/d8 /out/d8
RUN ln -sf $SRC/v8/out/x64.release/snapshot_blob.bin /out/snapshot_blob.bin

COPY build.sh $SRC/
COPY secb.sh /usr/local/bin/secb

RUN chmod +x $SRC/build.sh
RUN chmod +x /usr/local/bin/secb
RUN mkdir -p /app/artifacts
RUN mkdir -p /testcase
WORKDIR $SRC/v8

RUN secb-sanitize-git $SRC/v8
