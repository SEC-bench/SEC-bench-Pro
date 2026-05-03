FROM hwiwonlee/sm.base:latest
ENV DEBIAN_FRONTEND=noninteractive
ENV SRC=/src
ENV OUT=/out
RUN ln -sf /usr/local/bin/python3 /usr/bin/python
ENV PATH="/root/.mozbuild/cbindgen:/root/.cargo/bin:${PATH}"
WORKDIR $SRC/gecko-dev
RUN git checkout 3b81464999d7697966fcd3807dd2ebd89f30339b~1

# Build 1: ASAN+debug (for crash verification)
RUN rm -f mozconfig .mozconfig && cat > .mozconfig <<'EOF'
ac_add_options --enable-address-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --enable-optimize="-O1"
ac_add_options --enable-debug
ac_add_options --enable-debug-symbols
ac_add_options --enable-application=js
ac_add_options --enable-fuzzing
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
