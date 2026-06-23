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

# https://issues.chromium.org/issues/452605803: OOB access on ExposedTrustedObject backed by wasm import wrappers
RUN mkdir -p out/x64.release /tmp/d8bin && \
    curl -L -o /tmp/d8.zip https://storage.googleapis.com/v8-asan/linux-release/d8-sandbox-testing-linux-release-v8-component-102149.zip && \
    python3 -c "import zipfile; zipfile.ZipFile('/tmp/d8.zip').extractall('/tmp/d8bin')" && \
    cp /tmp/d8bin/d8 out/x64.release/d8 && \
    cp /tmp/d8bin/snapshot_blob.bin out/x64.release/snapshot_blob.bin && \
    chmod +x out/x64.release/d8 && \
    rm -rf /tmp/d8.zip /tmp/d8bin

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
RUN secb-sanitize-git $SRC/v8
