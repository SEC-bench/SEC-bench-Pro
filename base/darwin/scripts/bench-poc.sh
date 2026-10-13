#!/bin/bash
# bench-poc.sh - `bench compile` and `bench poc`, sourced by a task's secb.sh.
#
# Sourced, never executed, and always *after* bench-common.sh: it uses
# bench_die / bench_note / bench_stage / TASK_META / RUN_DIR from there.
#
# A file of its own, not part of bench-common.sh
# ----------------------------------------------
# bench-common.sh lives in the base image, and rebuilding the base image
# re-tags it, which invalidates every task image's `firmware` stage. These two
# commands only need the task images' last layer, so they ship as their own
# file and a task's secb.sh sources whichever copy it can find:
#
#   /bench/base/scripts/bench-poc.sh the repo, bind-mounted read-only by
#                                    crash_check.sh
#   /opt/darwin-bench/bench-poc.sh   the base image
#
# The compiler itself is base/darwin/scripts/bench-cc; see that file for how a Darwin
# arm64 Mach-O is produced on Linux with no Apple SDK in the image.

# Where bench-cc is. Same two-place search as above.
bench_cc_path() {
    local c
    for c in "${BENCH_CC:-}" /bench/base/scripts/bench-cc /usr/local/bin/bench-cc; do
        [[ -n "${c}" && -x "${c}" ]] && { echo "${c}"; return 0; } || true
    done
    return 1
}

# bench compile [bench-cc options] SOURCE...
#
# Thin wrapper: it only pins --meta-json to this task's, so the platform and
# minimum OS version come from guest.os / guest.version without being repeated
# on the command line. Everything else is bench-cc's own interface.
bench_compile() {
    local cc
    cc="$(bench_cc_path)" || bench_die \
        "no bench-cc found (looked at \$BENCH_CC, /usr/local/bin/bench-cc and /bench/base/scripts/bench-cc).
       crash_check.sh mounts the repo's base/darwin/ at /bench/base; a bare 'docker run' has to add
       -v <repo>/base/darwin:/bench/base:ro or rebuild the base image so bench-cc is installed."
    [[ $# -gt 0 ]] || bench_die "usage: bench compile [options] SOURCE... (see bench-cc --help)"
    "${cc}" --meta-json "${TASK_META}" "$@"
}

# bench poc [--src FILE] [-o PATH] [--to GUEST_DIR] [--no-stage]
#
# Compile the task's poc/poc.c for this guest and stage it into the
# ramdisk. Staging is the whole point: an ad-hoc signed Mach-O whose cdhash is
# not in the boot trust cache is SIGKILLed by AMFI, and the trust cache is a
# boot-time module, so the binary has to be in the ramdisk before boot.
# bench_stage refuses to run while the guest is up, for exactly that reason.
bench_poc() {
    local src="${BENCH_DIR}/poc/poc.c"
    local out="" to="${EXEC_WORKDIR:-/bench}" stage=1
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --src)      src="${2:?}"; shift 2 ;;
            -o)         out="${2:?}"; shift 2 ;;
            --to)       to="${2:?}"; shift 2 ;;
            --no-stage) stage=0; shift ;;
            *)          bench_die "usage: bench poc [--src FILE] [-o PATH] [--to GUEST_DIR] [--no-stage]" ;;
        esac
    done
    [[ -f "${src}" ]] || bench_die "no ${src} (the task image should carry poc/poc.c)"
    [[ -n "${out}" ]] || out="${RUN_DIR}/poc/$(basename "${src}" .c)"
    mkdir -p "$(dirname "${out}")"

    local t0 t1
    t0="$(date +%s%N)"
    bench_compile -o "${out}" "${src}" >/dev/null
    t1="$(date +%s%N)"
    bench_note "compiled ${src} -> ${out} in $(bench_ms_to_s $(( (t1 - t0) / 1000000 )) )s"

    [[ "${stage}" == 1 ]] || { echo "${out}"; return 0; }

    bench_stage "${out}" --to "${to}"
    bench_note "staged; boot and run it with:  bench exec -- ${to%/}/$(basename "${out}")"
    echo "${to%/}/$(basename "${out}")"
}
