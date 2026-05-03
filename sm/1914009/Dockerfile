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
ENV PATH="/root/.mozbuild/cbindgen:/root/.cargo/bin:${PATH}"
WORKDIR $SRC/gecko-dev
# Wasm baseline emitReturnCallRef incorrectly handled multi-value stack results, leaving stack corruption on tail call. CVE-2024-9402 / MFSA 2024-50 cluster (sec-high, Firefox 130/131). Fix: properly handle return_call_ref results in baseline.
RUN git checkout d942bcd55a236074e4fd0601a103e8c252e56899~1
RUN python3 -c "\
f='js/src/threading/ExclusiveData.h'; t=open(f).read(); \
t=t.replace('  ExclusiveData(ExclusiveData&& rhs)\n      : lock_(std::move(rhs.lock)), value_(std::move(rhs.value_)) {\n    MOZ_ASSERT(&rhs != this, \"self-move disallowed!\");\n  }\n\n  ExclusiveData& operator=(ExclusiveData&& rhs) {\n    this->~ExclusiveData();\n    new (mozilla::KnownNotNull, this) ExclusiveData(std::move(rhs));\n    return *this;\n  }', \
'  ExclusiveData(ExclusiveData&&) = delete;\n  ExclusiveData& operator=(ExclusiveData&&) = delete;'); \
open(f,'w').write(t)" || true
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
RUN mkdir -p /app/artifacts /testcase
