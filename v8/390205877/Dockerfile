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
ENV ASAN_OPTIONS="handle_sigill=2"

# Clean cipd cache
RUN rm -rf $SRC/.cipd

WORKDIR $SRC/v8

# https://issues.chromium.org/issues/390205877: V8 Sandbox Bypass: UB in ShouldResetInterruptBudgetByICChange because of invalid CachedTieringDecision enum variant
RUN git fetch origin ab875b6ed878b0b1934ab935366224ee4c761985 && git checkout ab875b6ed878b0b1934ab935366224ee4c761985

RUN gclient sync -D

RUN python3 - <<'PY'
from pathlib import Path
path = Path("build/config/compiler/BUILD.gn")
text = path.read_text()
replacements = [
    ('      cflags += [ "-Wa,--crel,--allow-experimental-crel" ]',
     '      #cflags += [ "-Wa,--crel,--allow-experimental-crel" ]'),
    ('      cflags = [ "-O1" ] + common_optimize_on_cflags',
     '      cflags = [ "-O0" ] + common_optimize_on_cflags'),
    ('      cflags = [ "-O2" ] + common_optimize_on_cflags',
     '      cflags = [ "-O0" ] + common_optimize_on_cflags'),
    ('      cflags = [ "-O3" ] + common_optimize_on_cflags',
     '      cflags = [ "-O0" ] + common_optimize_on_cflags'),
    ('  cflags = [ "-O1" ] + common_optimize_on_cflags',
     '  cflags = [ "-O0" ] + common_optimize_on_cflags'),
]
for old, new in replacements:
    text = text.replace(old, new)
path.write_text(text)
PY

RUN gn gen out/x64.asan --args=' \
  is_debug=false \
  is_asan=true \
  dcheck_always_on=false \
  v8_enable_slow_dchecks=false \
  target_cpu="x64" \
  v8_target_cpu="x64" \
  use_sysroot=true \
  v8_enable_sandbox=true \
  v8_enable_pointer_compression=true \
  v8_enable_memory_corruption_api=true \
  v8_static_library=true \
  v8_fuzzilli=false \
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
