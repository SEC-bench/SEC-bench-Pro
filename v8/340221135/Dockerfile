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

# https://issues.chromium.org/issues/340221135: RCE in V8 maglev - Don't build AccessInfo for storing to module exports
RUN git fetch origin 473318dfdb09464902c7633cad03b16431145800 && git checkout 473318dfdb09464902c7633cad03b16431145800

RUN gclient sync -D --nohooks

# Manually install the required clang version using curl (bypasses SSL certificate issue)
# RUN apt-get install -y xz-utils && \
#     rm -rf third_party/llvm-build && \
#     mkdir -p third_party/llvm-build/Release+Asserts && \
#     curl -k -L "https://commondatastorage.googleapis.com/chromium-browser-clang/Linux_x64/clang-llvmorg-19-init-9433-g76ea5feb-1.tar.xz" | tar -xJ -C third_party/llvm-build/Release+Asserts && \
#     echo "llvmorg-19-init-9433-g76ea5feb-1,Linux_x64" > third_party/llvm-build/Release+Asserts/cr_build_revision

RUN mkdir -p /usr/local/ssl && ln -sf /etc/ssl/certs/ca-certificates.crt /usr/local/ssl/cert.pem
RUN /usr/bin/python3 tools/clang/scripts/update.py

RUN gn gen out/x64.debug --args=' \
  is_debug=true \
  symbol_level=2 \
  v8_optimized_debug=false \
  target_cpu="x64" \
  v8_target_cpu="x64" \
  use_sysroot=true \
  v8_enable_sandbox=true \
  v8_enable_pointer_compression=true \
  v8_enable_memory_corruption_api=true \
  is_component_build=true \
  '

RUN ninja -C out/x64.debug d8

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
  use_sysroot=false \
  '

RUN autoninja -C out/x64.release d8

# **IMPORTANT**: DO **NOT** MODIFY OR REMOVE THE BELOW STATEMENTS

RUN mkdir -p /out
RUN ln -sf $SRC/v8/out/x64.debug/d8 /out/d8
RUN ln -sf $SRC/v8/out/x64.debug/snapshot_blob.bin /out/snapshot_blob.bin

COPY build.sh $SRC/
COPY secb.sh /usr/local/bin/secb

RUN chmod +x $SRC/build.sh
RUN chmod +x /usr/local/bin/secb
RUN mkdir -p /app/artifacts
RUN mkdir -p /testcase

# Copy module.txt so the ES module import in poc.js resolves correctly
COPY module.txt /testcase/module.txt
WORKDIR $SRC/v8

RUN secb-sanitize-git $SRC/v8
