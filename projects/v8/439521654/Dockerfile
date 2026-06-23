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

RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y --no-install-recommends \
    libc6:i386 \
    libstdc++6:i386 \
    zlib1g:i386 \
    && rm -rf /var/lib/apt/lists/*

# Clean cipd cache
RUN rm -rf $SRC/.cipd

WORKDIR $SRC/v8

# https://issuetracker.google.com/issues/439521654: High impact issue in V8: race condition during TypedArray.sort leads to memory corruption
RUN git fetch origin bcdacbf04300b83755ae4a3770c442412d23cbe8 && git checkout bcdacbf04300b83755ae4a3770c442412d23cbe8

RUN gclient sync -D

RUN python3 build/linux/sysroot_scripts/install-sysroot.py --arch=i386 || true

RUN gn gen out/ia32.asan --args=' \
  is_debug=false \
  is_asan=true \
  dcheck_always_on=false \
  v8_enable_slow_dchecks=false \
  symbol_level=1 \
  target_cpu="x86" \
  v8_target_cpu="x86" \
  use_sysroot=true \
  v8_enable_sandbox=false \
  v8_enable_pointer_compression=false \
  v8_enable_memory_corruption_api=false \
  is_component_build=false \
  '

RUN ninja -j"${NINJA_JOBS:-$(nproc)}" -C out/ia32.asan d8

RUN gn gen out/x64.release --args=' \
  is_debug=false \
  is_asan=false \
  dcheck_always_on=false \
  symbol_level=1 \
  target_cpu="x64" \
  v8_target_cpu="x64" \
  v8_enable_sandbox=true \
  v8_enable_pointer_compression=true \
  v8_enable_memory_corruption_api=true \
  is_component_build=false \
  use_sysroot=true \
  '

RUN autoninja -j"${NINJA_JOBS:-$(nproc)}" -C out/x64.release d8

# **IMPORTANT**: DO **NOT** MODIFY OR REMOVE THE BELOW STATEMENTS

RUN mkdir -p /out
RUN ln -sf $SRC/v8/out/ia32.asan/d8 /out/d8
RUN ln -sf $SRC/v8/out/ia32.asan/snapshot_blob.bin /out/snapshot_blob.bin

COPY build.sh $SRC/
COPY secb.sh /usr/local/bin/secb

RUN chmod +x $SRC/build.sh
RUN chmod +x /usr/local/bin/secb
RUN mkdir -p /app/artifacts
RUN mkdir -p /testcase
RUN secb-sanitize-git $SRC/v8
