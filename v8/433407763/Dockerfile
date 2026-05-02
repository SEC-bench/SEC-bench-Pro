FROM hwiwonlee/v8.base:latest

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

# https://issuetracker.google.com/issues/433407763: V8 sandbox bypass due to NativeModule swapping while module instantiation was ongoing
RUN git fetch origin 902bb652f137f5a7bccf45282644a8bc308cbe45 && git checkout 902bb652f137f5a7bccf45282644a8bc308cbe45

RUN gclient sync -D

RUN gn gen out/x64.asan --args=' \
  is_debug=false \
  is_asan=true \
  dcheck_always_on=false \
  v8_enable_slow_dchecks=false \
  target_cpu="x64" \
  v8_target_cpu="x64" \
  use_sysroot=false \
  v8_enable_sandbox=true \
  v8_enable_pointer_compression=true \
  v8_enable_memory_corruption_api=true \
  is_component_build=false \
  '

RUN ninja -C out/x64.asan d8

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

RUN autoninja -C out/x64.release d8

# **IMPORTANT**: DO **NOT** MODIFY OR REMOVE THE BELOW STATEMENTS

RUN mkdir -p /out
RUN ln -sf $SRC/v8/out/x64.asan/d8 /out/d8
RUN ln -sf $SRC/v8/out/x64.asan/snapshot_blob.bin /out/snapshot_blob.bin

COPY build.sh $SRC/
COPY secb.sh /usr/local/bin/secb

RUN chmod +x $SRC/build.sh
RUN chmod +x /usr/local/bin/secb
RUN mkdir -p /app/artifacts
RUN mkdir -p /testcase
WORKDIR $SRC/v8

RUN secb-sanitize-git $SRC/v8
