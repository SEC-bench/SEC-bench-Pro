#!/bin/bash
# bench-common.sh - the shared half of every task's secb.sh.
#
# Sourced, never executed:  . /opt/darwin-bench/bench-common.sh
#
# It owns everything that is not task-specific: reading meta.json, preparing
# the firmware volume, running qemu with a console *socket* instead of stdio,
# typing on that console with the BEGIN/END marker protocol, staging files into
# the ramdisk and rebuilding the trust cache.
#
# Layout inside a task image
# --------------------------
#   /bench/meta.json            task metadata
#   /bench/secb.sh              the task ENTRYPOINT, which sources this file from
#                               /opt/darwin-bench/bench-common.sh
#   /bench/poc/poc.c            the poc source `bench poc` compiles
#   /bench/kernel/              the compiled kernel (custom-* variants only)
#   /bench/firmware.pristine/   unpatched firmware baked into the image
#   /bench/firmware/            the per-task+variant volume; prep writes here:
#                               bootkc, dtree, ramdisk.dmg, ramdisk.tc,
#                               apple_ramdisk.tc, sptm + txm on SPTM guests,
#                               .bench-prepped and .bench-staged
#   /bench/run/                 console.sock, monitor.sock, console.in (the
#                               typing fifo), console.log, console.attemptN.log,
#                               qemu.log, qemu.pid, mux.pid
#   /darwin-vm/                 the patched darwin-vm checkout from the base
#   /opt/qemu-sptm/bin/         qemu-system-aarch64 from the base
#
# Guest lifecycle
# ---------------
# qemu is launched with
#     -serial  unix:/bench/run/console.sock,server,nowait
#     -monitor unix:/bench/run/monitor.sock,server,nowait
# so the guest stays booted across many `bench exec` calls. A qemu socket
# chardev accepts one client at a time, so exactly one long-lived `socat`
# multiplexer owns the connection: it reads from a fifo (things to type) and
# appends everything the guest says to console.log. `exec`, `attach`, `push`
# and `pull` all go through that pair.
#
# `bench start --detach` boots and then *supervises* qemu rather than
# returning, because returning would end the container and kill the guest. It
# prints "BENCH: guest ready" on the console when the prompt appears; the host
# wrapper (crash_check.sh) does the docker-level detaching and waits for that
# line.

# --------------------------------------------------------------------------
# paths and constants
# --------------------------------------------------------------------------
BENCH_DIR="${BENCH_DIR:-/bench}"
TASK_META="${BENCH_TASK_META:-${BENCH_DIR}/meta.json}"
FW_DIR="${BENCH_FW_DIR:-${BENCH_DIR}/firmware}"
PRISTINE_DIR="${BENCH_PRISTINE_DIR:-${BENCH_DIR}/firmware.pristine}"
RUN_DIR="${BENCH_RUN_DIR:-${BENCH_DIR}/run}"
DVM="${BENCH_DVM:-/darwin-vm}"
QEMU="${BENCH_QEMU:-/opt/qemu-sptm/bin/qemu-system-aarch64}"

CONSOLE_SOCK="${RUN_DIR}/console.sock"
MONITOR_SOCK="${RUN_DIR}/monitor.sock"
CONSOLE_LOG="${RUN_DIR}/console.log"
CONSOLE_FIFO="${RUN_DIR}/console.in"
QEMU_LOG="${RUN_DIR}/qemu.log"
QEMU_PID_FILE="${RUN_DIR}/qemu.pid"
MUX_PID_FILE="${RUN_DIR}/mux.pid"
PREPPED_STAMP="${FW_DIR}/.bench-prepped"
STAGE_QUEUE="${FW_DIR}/.bench-staged"

# run.sh's boot args, verbatim. Override with BENCH_BOOT_ARGS if a task needs
# something else; amfi_get_out_of_my_way=1 and cs_enforcement_disable=1 are
# deliberately not in the default.
BOOT_ARGS_DEFAULT="rd=md0 serial=3 -v -noprogress wdt=-1 wlan-olyhal-abort"
BOOT_ARGS="${BENCH_BOOT_ARGS:-${BOOT_ARGS_DEFAULT}}"
# Appended after bench_load_task: meta.json's qemu.boot_args_extra (task-wide)
# and $BENCH_BOOT_ARGS_EXTRA (set per variant by the task Dockerfile, e.g. the
# kdk-kasan variant's kasan_zrecs=4096). Ignored when
# BENCH_BOOT_ARGS replaces the whole string.

# Same detection strings darwin-vm-entrypoint uses; the shell regex is
# extended with the task's own exec.prompt_regex in bench_load_task.
# LAUNCHD_RE is part of the surface a task's secb.sh may use (as
# darwin-vm-entrypoint's `check` does) rather than something this file greps.
# shellcheck disable=SC2034
LAUNCHD_RE='Darwin Bootstrapper Version'
# A plain `panic(cpu N caller ...)` is the deterministic kind (a kext that
# cannot live with the emulated hardware, a missing device-tree property) and
# does not cascade into the nested one; without matching it here a failed boot
# would sit out the full boot_timeout_s on every retry.
PANIC_RE='Nested panic detected|^panic\(cpu'
SHELL_RE='job control turned off|bash-[0-9]+\.[0-9]+[#$]'

# Per-character pacing on the guest console, in milliseconds.
#
# The exynos4210 UART model darwin-vm wires up mis-reports its RX FIFO free
# space, so a *single* write() of >= 16 bytes is lost in its entirety.
# What breaks it is the chunk size, not the rate: one-byte writes arrive at
# 1-2 ms per character, a single write of 16 bytes or more does not. So the
# invariant this file keeps is "one write() per character" (bench_type below,
# plus socat -b1 in bench_mux_start), and the pacing is only there for margin.
#
# Precedence: $BENCH_TYPE_DELAY_MS > meta.json exec.type_delay_ms > 2 ms.
# $BENCH_TYPE_DELAY (in seconds) still wins over all three.
TYPE_DELAY_MS="${BENCH_TYPE_DELAY_MS:-2}"

# ms -> "S.mmm" without forking bc/awk; bench_type calls this once per line.
bench_ms_to_s() { printf '%d.%03d' "$(( $1 / 1000 ))" "$(( $1 % 1000 ))"; }

TYPE_DELAY="${BENCH_TYPE_DELAY:-$(bench_ms_to_s "${TYPE_DELAY_MS}")}"

# --------------------------------------------------------------------------
# output helpers
# --------------------------------------------------------------------------
bench_note() { echo "bench: $*"; }
bench_warn() { echo "bench: warning: $*" >&2; }
bench_die()  { echo "bench: error: $*" >&2; exit 1; }

# --------------------------------------------------------------------------
# meta.json
# --------------------------------------------------------------------------
# Everything below reads meta.json with jq and nothing else, so a task needs no
# python in the guest-facing path.
# The variables it sets are the task's metadata surface: a task's secb.sh
# is expected to read any of them, so several are unused *here*.
# shellcheck disable=SC2034
bench_load_task() {
    [[ -f "${TASK_META}" ]] || bench_die "no ${TASK_META}"
    command -v jq >/dev/null || bench_die "jq is not on PATH"

    TASK_ID="$(jq -r '.cve_id // (.image_name | split(":") | last)' "${TASK_META}")"
    TASK_TITLE="$(jq -r '.title // .cve_id // .image_name' "${TASK_META}")"

    GUEST_OS="$(jq -r '.guest.os' "${TASK_META}")"
    GUEST_VERSION="$(jq -r '.guest.version' "${TASK_META}")"
    GUEST_BUILD="$(jq -r '.guest.build' "${TASK_META}")"
    GUEST_DEVICE="$(jq -r '.guest.device' "${TASK_META}")"
    GUEST_BOARD="$(jq -r '.guest.board // empty' "${TASK_META}")"
    GUEST_SOC="$(jq -r '.guest.soc' "${TASK_META}")"
    GUEST_KC_TYPE="$(jq -r '.guest.kc_type // empty' "${TASK_META}")"

    IPSW_URL="$(jq -r '.ipsw.url' "${TASK_META}")"
    KDK_URL="$(jq -r '.kdk.url // empty' "${TASK_META}")"
    KDK_VERSION="$(jq -r '.kdk.version // empty' "${TASK_META}")"
    KDK_BUILD="$(jq -r '.kdk.build // empty' "${TASK_META}")"

    XNU_TAG="$(jq -r '.xnu.tag' "${TASK_META}")"
    XNU_COMMIT="$(jq -r '.xnu.commit' "${TASK_META}")"
    KERNEL_CONFIG="$(jq -r '.xnu.kernel_config // "DEVELOPMENT"' "${TASK_META}")"
    MACHINE_CONFIG="$(jq -r '.xnu.machine_config // empty' "${TASK_META}")"

    Q_RAMDISK_MB="$(jq -r '.qemu.ramdisk_size_mb // 0' "${TASK_META}")"
    Q_MEMORY_MB="$(jq -r '.qemu.memory_mb // 8192' "${TASK_META}")"
    Q_CPUS="$(jq -r '.qemu.cpus // 1' "${TASK_META}")"
    Q_BOOT_TIMEOUT="$(jq -r '.qemu.boot_timeout_s // 300' "${TASK_META}")"
    Q_BOOT_ARGS_EXTRA="$(jq -r '.qemu.boot_args_extra // ""' "${TASK_META}")"
    if [[ -z "${BENCH_BOOT_ARGS:-}" ]]; then
        [[ -n "${Q_BOOT_ARGS_EXTRA}" ]] && BOOT_ARGS="${BOOT_ARGS} ${Q_BOOT_ARGS_EXTRA}"
        [[ -n "${BENCH_BOOT_ARGS_EXTRA:-}" ]] && BOOT_ARGS="${BOOT_ARGS} ${BENCH_BOOT_ARGS_EXTRA}"
    fi
    Q_BOOT_RETRIES="$(jq -r '.qemu.boot_retries // 4' "${TASK_META}")"
    Q_EXTRA_ARGS=()
    mapfile -t Q_EXTRA_ARGS < <(jq -r '.qemu.extra_args[]? // empty' "${TASK_META}")

    EXEC_SHELL="$(jq -r '.exec.shell' "${TASK_META}")"
    EXEC_WORKDIR="$(jq -r '.exec.workdir' "${TASK_META}")"
    EXEC_START_COMMAND="$(jq -r '.exec.start_command' "${TASK_META}")"
    EXEC_PROMPT_RE="$(jq -r '.exec.prompt_regex // empty' "${TASK_META}")"

    # A task may slow the console typing down (or speed it up) for its own
    # guest. The environment still wins, so a one-off run can override it.
    EXEC_TYPE_DELAY_MS="$(jq -r '.exec.type_delay_ms // empty' "${TASK_META}")"
    if [[ -n "${EXEC_TYPE_DELAY_MS}" && -z "${BENCH_TYPE_DELAY_MS:-}" ]]; then
        TYPE_DELAY_MS="${EXEC_TYPE_DELAY_MS}"
        TYPE_DELAY="${BENCH_TYPE_DELAY:-$(bench_ms_to_s "${TYPE_DELAY_MS}")}"
    fi

    BENCH_VARIANT="${BENCH_VARIANT:-unknown}"

    # exec.prompt_regex is written to match a live prompt (trailing "$" anchor
    # and a trailing space); the console log is scanned line-wise, where the
    # prompt is the last thing on a line with no newline after it. Strip the
    # anchor so grep -E can see it, and keep darwin-vm-entrypoint's strings as
    # a fallback for guests whose first sign of life is sh complaining.
    if [[ -n "${EXEC_PROMPT_RE}" ]]; then
        local re="${EXEC_PROMPT_RE%\$}"
        re="${re%% }"
        [[ "${SHELL_RE}" == *"${re}"* ]] || SHELL_RE="${SHELL_RE}|${re}"
    fi
}

# --------------------------------------------------------------------------
# apfsftp: the userspace ramdisk editor (no mount, no apfs.ko)
# --------------------------------------------------------------------------
# Every edit of the APFS restore ramdisk goes through base/darwin/scripts/apfsftp,
# a pure-Python tool that rewrites the on-disk catalog directly. There is no
# host mount, no kernel module and no --privileged. Located the same two-place
# way as bench-cc: the base image install, else the repo tree crash_check.sh
# bind-mounts at /bench/base.
bench_apfsftp_path() {
    local c
    for c in "${BENCH_APFSFTP:-}" /opt/darwin-bench/apfsftp /bench/base/scripts/apfsftp; do
        [[ -n "${c}" && -x "${c}" ]] && { echo "${c}"; return 0; } || true
    done
    return 1
}

# bench_apfs <subcommand> <args...> -- run apfsftp against FW_DIR/ramdisk.dmg.
# The image path is inserted as the first argument after the subcommand.
BENCH_APFSFTP_BIN=""
bench_apfs() {
    [[ -n "${BENCH_APFSFTP_BIN}" ]] || BENCH_APFSFTP_BIN="$(bench_apfsftp_path)" || bench_die \
        "no apfsftp found (looked at \$BENCH_APFSFTP, /opt/darwin-bench/apfsftp and /bench/base/scripts/apfsftp)"
    local sub="$1"; shift
    python3 "${BENCH_APFSFTP_BIN}" "${sub}" "${FW_DIR}/ramdisk.dmg" "$@"
}

# Resolve a guest path to its catalog cnid (numeric), for the parent-cnid
# arguments apfsftp's mkdir/rename/rm/addfile take.
bench_cnid() { bench_apfs resolve "$1"; }

# --------------------------------------------------------------------------
# trust cache
# --------------------------------------------------------------------------
# get_files.sh:patch_ramdisk() rebuilt the trust cache by walking the *mounted*
# ramdisk with `ldid -h` and merging Apple's own module in. Without a mount
# there is no walk: Apple's apple_ramdisk.tc already lists every Apple binary, so
# ramdisk.tc is that module merged with the cdhashes of the files this bench
# staged. Those are recorded in STAGE_QUEUE as "<cdhash>\t<guest path>" by
# bench_record_cdhash at stage time. XNU binary-searches the entries, so
# build_tc.py sorts and dedupes.
bench_tc_rebuild() {
    if bench_guest_running; then
        bench_die "the guest is running; the trust cache is a boot-time module (bench stop first)"
    fi
    bench_note "rebuilding trust cache (no mount; apple_ramdisk.tc + staged cdhashes)"
    : > "${FW_DIR}/all_hashes"
    [[ -f "${STAGE_QUEUE}" ]] && cut -f1 "${STAGE_QUEUE}" | grep -i '^[0-9a-f]' > "${FW_DIR}/all_hashes" || true
    local merge_args=()
    [[ -f "${FW_DIR}/apple_ramdisk.tc" ]] && merge_args=(-merge "${FW_DIR}/apple_ramdisk.tc") || true
    "${DVM}/build_tc.py" "${merge_args[@]}" "${FW_DIR}/all_hashes" "${FW_DIR}/ramdisk.tc"
    bench_note "ramdisk.tc: $(bench_tc_count) entries"
}

bench_tc_count() {
    [[ -f "${FW_DIR}/ramdisk.tc" ]] || { echo 0; return; }
    python3 - "${FW_DIR}/ramdisk.tc" <<'PY'
import struct, sys
d = open(sys.argv[1], 'rb').read()
print(struct.unpack_from('<I', d, 20)[0] if len(d) >= 24 else 0)
PY
}

bench_tc_list() {
    [[ -f "${FW_DIR}/ramdisk.tc" ]] || bench_die "no ${FW_DIR}/ramdisk.tc - prep the firmware first"
    if [[ -f "${STAGE_QUEUE}" ]]; then
        echo "cdhashes added by this bench (from ${STAGE_QUEUE}):"
        cat "${STAGE_QUEUE}"
    else
        echo "no bench-added cdhashes recorded yet"
    fi
    echo
    echo "ramdisk.tc total entries: $(bench_tc_count)"
    if [[ -f "${FW_DIR}/apple_ramdisk.tc" ]]; then
        echo "apple_ramdisk.tc merged in: yes"
    else
        echo "apple_ramdisk.tc merged in: no"
    fi
}

# --------------------------------------------------------------------------
# launchd job for the guest shell
# --------------------------------------------------------------------------
# darwin-vm ships launchdaemons/com.jprx.bash.plist, which is Program=/bin/bash
# and nothing else. meta.json wants a working directory, a command line and an
# environment, so the plist is generated. BENCH_PLIST=<path> substitutes a
# hand-written one.
bench_write_plist() {
    local out="$1"
    if [[ -n "${BENCH_PLIST:-}" ]]; then
        cp -a --remove-destination "${BENCH_PLIST}" "${out}"
        return
    fi

    local -a argv=()
    read -r -a argv <<< "${EXEC_START_COMMAND}"
    [[ ${#argv[@]} -gt 0 ]] || bench_die "exec.start_command is empty"

    {
        cat <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN"
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
	<dict>
		<key>Label</key>
		<string>com.darwinbench.shell</string>
EOF
        printf '\t\t<key>Program</key>\n\t\t<string>%s</string>\n' "${argv[0]}"
        printf '\t\t<key>ProgramArguments</key>\n\t\t<array>\n'
        local a
        for a in "${argv[@]}"; do printf '\t\t\t<string>%s</string>\n' "${a}"; done
        printf '\t\t</array>\n'
        printf '\t\t<key>WorkingDirectory</key>\n\t\t<string>%s</string>\n' "${EXEC_WORKDIR}"
        printf '\t\t<key>EnvironmentVariables</key>\n\t\t<dict>\n'
        local k v
        while IFS=$'\t' read -r k v; do
            [[ -n "${k}" ]] || continue
            printf '\t\t\t<key>%s</key>\n\t\t\t<string>%s</string>\n' "${k}" "${v}"
        done < <(jq -r '.exec.env // {} | to_entries[] | "\(.key)\t\(.value)"' "${TASK_META}")
        printf '\t\t</dict>\n'
        cat <<'EOF'
		<key>StandardInPath</key>
		<string>/dev/console</string>
		<key>StandardOutPath</key>
		<string>/dev/console</string>
		<key>StandardErrorPath</key>
		<string>/dev/console</string>
		<key>ProcessType</key>
		<string>Interactive</string>
		<key>KeepAlive</key>
		<true/>
	</dict>
</plist>
EOF
    } > "${out}"
}

# --------------------------------------------------------------------------
# prep: pristine firmware -> a bootable firmware volume
# --------------------------------------------------------------------------
# This is get_files.sh's patch_dtree + silence_logs + patch_ramdisk, plus
# fix_perms.sh, run against the volume instead of at image build time. It is
# idempotent-by-stamp: `bench firmware prep` forces it.
bench_is_prepped() { [[ -f "${PREPPED_STAMP}" ]]; }

bench_copy_pristine() {
    [[ -d "${PRISTINE_DIR}" ]] || bench_die "no ${PRISTINE_DIR} in this image"
    mkdir -p "${FW_DIR}"
    bench_note "copying pristine firmware into the volume"
    # -a keeps the sparse-ish ramdisk cheap; --delete would nuke a user's
    # staged files, so this is a merge and prep starts from a clean stamp.
    cp -a "${PRISTINE_DIR}/." "${FW_DIR}/"
    # A fresh pristine ramdisk carries none of our staged binaries, so the
    # recorded cdhash list starts empty (bench_tc_rebuild reads it).
    : > "${STAGE_QUEUE}"
}

# Prep is a single pass: apfsftp edits ramdisk.dmg in place, so there is no
# mount for a docker host to own and no pre/post split. It runs the same on
# every host, Linux or Mac.
bench_prep() {
    local force="${1:-0}"

    if bench_is_prepped && [[ "${force}" != "1" ]]; then
        bench_note "firmware already prepared in ${FW_DIR}"
        return 0
    fi

    if [[ "${force}" == "1" || ! -f "${FW_DIR}/ramdisk.dmg" ]]; then
        rm -f "${PREPPED_STAMP}"
        bench_copy_pristine
    fi

    [[ -f "${FW_DIR}/bootkc" ]] || bench_die "no ${FW_DIR}/bootkc"
    [[ -f "${FW_DIR}/dtree" ]]  || bench_die "no ${FW_DIR}/dtree"

    # No ramdisk enlargement: the no-mount prep writes the launchd job
    # and the poc binary straight into the pristine image, which
    # has room for them.
    if [[ "${Q_RAMDISK_MB}" -gt 0 ]]; then
        bench_note "ramdisk left at its pristine size"
    fi

    bench_prep_dtree
    bench_prep_bootkc

    bench_prep_ramdisk

    date -u +%Y-%m-%dT%H:%M:%SZ > "${PREPPED_STAMP}"
    echo "variant=${BENCH_VARIANT}" >> "${PREPPED_STAMP}"
    echo "bootkc=$(bench_pristine_bootkc_sha)" >> "${PREPPED_STAMP}"
    local dsha; dsha="$(bench_pristine_dtree_sha)"
    [[ "${dsha}" == none ]] || echo "dtree=${dsha}" >> "${PREPPED_STAMP}"
    bench_note "firmware ready:"
    ls -la "${FW_DIR}"
}

# --------------------------------------------------------------------------
# a rebuilt image vs. an already-prepped volume
# --------------------------------------------------------------------------
# The firmware volume outlives the task image: `bench build` with a new kernel
# collection puts a new bootkc into the image's firmware.pristine, and a
# `start` that skipped prep because .bench-prepped exists would silently boot
# the old bootkc from the volume. So the stamp records the pristine bootkc's
# sha256 at prep time; when the image's differs, bootkc and dtree are refreshed
# from pristine and re-patched, leaving the ramdisk -- and anything staged into
# it -- alone. Volumes prepped before the stamp carried a hash fall back to a
# size comparison (silence_logs.py never changes the size).
bench_pristine_bootkc_sha() {
    [[ -f "${PRISTINE_DIR}/bootkc" ]] || { echo none; return; }
    sha256sum "${PRISTINE_DIR}/bootkc" | cut -d' ' -f1
}

bench_pristine_dtree_sha() {
    [[ -f "${PRISTINE_DIR}/dtree" ]] || { echo none; return; }
    sha256sum "${PRISTINE_DIR}/dtree" | cut -d' ' -f1
}

bench_refresh_stale_bootkc() {
    bench_is_prepped || return 0
    [[ -f "${PRISTINE_DIR}/bootkc" && -f "${FW_DIR}/bootkc" ]] || return 0
    local want_k have_k want_d have_d stale=0
    want_k="$(bench_pristine_bootkc_sha)"
    have_k="$(sed -n 's/^bootkc=//p' "${PREPPED_STAMP}" 2>/dev/null | head -1)"
    want_d="$(bench_pristine_dtree_sha)"
    have_d="$(sed -n 's/^dtree=//p' "${PREPPED_STAMP}" 2>/dev/null | head -1)"
    if [[ -n "${have_k}" ]]; then
        [[ "${have_k}" == "${want_k}" ]] || stale=1
    else
        # pre-hash stamp: the only cheap signal is the size
        [[ "$(stat -c %s "${PRISTINE_DIR}/bootkc")" == "$(stat -c %s "${FW_DIR}/bootkc")" ]] || stale=1
    fi
    # dtree gets rewritten in place by dt_fixup, so FW_DIR/dtree never matches
    # PRISTINE_DIR/dtree by size or sha after prep. The only honest signal is
    # the pristine sha against the one recorded at prep time; a legacy stamp
    # without a dtree= line gets stamped on this run and compared next time.
    if [[ "${want_d}" != none && -n "${have_d}" ]]; then
        [[ "${have_d}" == "${want_d}" ]] || stale=1
    fi
    if [[ "${stale}" == 0 ]]; then
        # record the hashes on legacy stamps so the next check is exact
        [[ -n "${have_k}" ]] || echo "bootkc=${want_k}" >> "${PREPPED_STAMP}"
        [[ "${want_d}" == none || -n "${have_d}" ]] || echo "dtree=${want_d}" >> "${PREPPED_STAMP}"
        return 0
    fi
    bench_warn "the image's bootkc or dtree differs from the one this volume was prepped with (task image rebuilt?)"
    bench_note "refreshing bootkc and dtree from ${PRISTINE_DIR}; the ramdisk and its staged files are kept"
    cp -a --remove-destination "${PRISTINE_DIR}/bootkc" "${FW_DIR}/bootkc"
    [[ -f "${PRISTINE_DIR}/dtree" ]] && cp -a --remove-destination "${PRISTINE_DIR}/dtree" "${FW_DIR}/dtree"
    bench_prep_dtree
    bench_prep_bootkc
    sed -i '/^bootkc=/d; /^dtree=/d' "${PREPPED_STAMP}"
    echo "bootkc=${want_k}" >> "${PREPPED_STAMP}"
    [[ "${want_d}" == none ]] || echo "dtree=${want_d}" >> "${PREPPED_STAMP}"
    bench_note "bootkc refreshed: $(sha256sum "${FW_DIR}/bootkc" | cut -c1-16)"
}

bench_prep_dtree() {
    bench_note "patching the device tree (dt_fixup.py)"
    # iOS 16-era / macOS 14.x AppleImage4 panics "failed to read boot nonce
    # hash" without a BNCH in /chosen/manifest-properties; dt_fixup.py
    # synthesises one only when DARWIN_VM_ADD_BNCH=1, which is the pre-SPTM
    # path (a synthetic BNCH panics TXM on SPTM guests).
    local add_bnch=0
    [[ -f "${FW_DIR}/sptm" ]] || add_bnch=1
    ( cd "${DVM}" && DARWIN_VM_ADD_BNCH="${add_bnch}" ./dt_fixup.py -nvram nvram.bin "${FW_DIR}/dtree" "${FW_DIR}/dtree_patch" )
    mv "${FW_DIR}/dtree_patch" "${FW_DIR}/dtree"
}

bench_prep_bootkc() {
    # Cosmetic: upstream's silence_logs.py zeroes the format strings in its
    # PATCHOUTS table (the per-exec shared_region line, the SEP credential
    # manager timeout, the sandbox's "System Policy:" lines), each searched
    # in its kext's __TEXT only. Runs here rather than in the image because
    # the custom-* variant replaces bootkc after the firmware stage. A string
    # or kext the collection lacks is skipped; a missing kext prints a warning.
    # It edits the file in place, so FW_DIR/bootkc must be a copy of pristine.
    bench_note "patching bootkc (silence_logs.py)"
    ( cd "${DVM}" && ./silence_logs.py "${FW_DIR}/bootkc" )
}

# get_files.sh:patch_ramdisk to the letter, done with apfsftp's catalog ops
# straight against ramdisk.dmg: move Apple's LaunchDaemons aside, install our
# single launchd job, create the working directory. Nothing is chowned -
# apfsftp writes every record owned 0:0, which is what fix_perms.sh restores.
# Idempotent by the LaunchDaemons.old marker.
bench_prep_ramdisk() {
    # A macOS restore ramdisk already ships a usable /bin/bash and dyld cache.
    [[ "${GUEST_OS}" == "macOS" ]] || bench_die "unsupported guest.os ${GUEST_OS}; only macOS guests are supported"

    local sl; sl="$(bench_cnid /System/Library)" \
        || bench_die "cannot resolve /System/Library in ${FW_DIR}/ramdisk.dmg"

    if bench_apfs resolve /System/Library/LaunchDaemons.old >/dev/null 2>&1; then
        bench_note "ramdisk already patched, refreshing the bench launchd job only"
    else
        bench_note "moving Apple's LaunchDaemons aside"
        bench_apfs rename "${sl}" LaunchDaemons LaunchDaemons.old >/dev/null
        bench_apfs mkdir  "${sl}" LaunchDaemons >/dev/null
    fi

    local ld; ld="$(bench_cnid /System/Library/LaunchDaemons)"
    if bench_apfs resolve /System/Library/LaunchDaemons/com.darwinbench.shell.plist >/dev/null 2>&1; then
        bench_apfs rm "${ld}" com.darwinbench.shell.plist >/dev/null
    fi

    local plist; plist="$(mktemp)"
    bench_write_plist "${plist}"
    bench_apfs addfile "${ld}" com.darwinbench.shell.plist "${plist}" 100644 >/dev/null
    rm -f "${plist}"
    bench_note "installed com.darwinbench.shell.plist (${EXEC_START_COMMAND} in ${EXEC_WORKDIR})"

    # exec.workdir has to exist or launchd cannot spawn the job.
    bench_apfs_mkdir_p "${EXEC_WORKDIR}"

    bench_tc_rebuild
}

# Create a guest absolute path as directories, component by component, skipping
# any that already exist. Paths carry no spaces, so word-splitting on / is safe.
bench_apfs_mkdir_p() {
    local path="$1" built="" comp parent=2 cnid
    for comp in ${path//\// }; do
        built="${built}/${comp}"
        if cnid="$(bench_apfs resolve "${built}" 2>/dev/null)"; then
            parent="${cnid}"
        else
            bench_apfs mkdir "${parent}" "${comp}" >/dev/null
            parent="$(bench_apfs resolve "${built}")"
        fi
    done
}

# Put one already-signed host file into a guest directory under a chosen name,
# replacing an existing entry (re-prep / re-stage). apfsftp writes it owned 0:0.
bench_apfs_put() {
    local src="$1" dir="$2" name="$3" mode="${4:-100755}" pcnid
    bench_apfs_mkdir_p "${dir}"
    pcnid="$(bench_apfs resolve "${dir}")"
    if bench_apfs resolve "${dir%/}/${name}" >/dev/null 2>&1; then
        bench_apfs rm "${pcnid}" "${name}" >/dev/null
    fi
    bench_apfs addfile "${pcnid}" "${name}" "${src}" "${mode}" >/dev/null
}

bench_record_cdhash() {
    local guest_path="$1" real_path="$2" cdhash
    cdhash="$(ldid -h "${real_path}" 2>/dev/null | grep -io 'cdhash=[0-9a-f]*' | cut -d= -f2 || true)"
    [[ -n "${cdhash}" ]] || return 0
    printf '%s\t%s\n' "${cdhash}" "${guest_path}" >> "${STAGE_QUEUE}"
}

# --------------------------------------------------------------------------
# `bench stage` / `bench sign`
# --------------------------------------------------------------------------
bench_stage() {
    local to="/bin"
    local -a files=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --to) to="${2:?}"; shift 2 ;;
            *)    files+=("$1"); shift ;;
        esac
    done
    [[ ${#files[@]} -gt 0 ]] || bench_die "usage: bench stage FILE... [--to /guest/dir]"
    if bench_guest_running; then
        bench_die "the guest is running; stage only works before boot (bench stop first)"
    fi

    bench_is_prepped || bench_prep

    local f base
    for f in "${files[@]}"; do
        [[ -f "${f}" ]] || bench_die "no such file: ${f}"
        base="$(basename "${f}")"
        # Sign the artifact in place (it is ours) and record its cdhash, then
        # write it into the ramdisk with apfsftp (owned 0:0, replacing any old copy).
        ldid -Cadhoc -S "${f}" 2>/dev/null || true
        bench_record_cdhash "${to}/${base}" "${f}"
        bench_apfs_put "${f}" "${to}" "${base}" 100755
        bench_note "staged ${f} -> ${to}/${base}"
    done
    bench_tc_rebuild
}

bench_sign() {
    local ents=""
    local -a files=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --ents) ents="${2:?}"; shift 2 ;;
            *)      files+=("$1"); shift ;;
        esac
    done
    [[ ${#files[@]} -gt 0 ]] || bench_die "usage: bench sign [--ents plist] MACHO..."
    local f
    for f in "${files[@]}"; do
        [[ -f "${f}" ]] || bench_die "no such file: ${f}"
        if [[ -n "${ents}" ]]; then
            ldid -Cadhoc "-S${ents}" "${f}"
        else
            ldid -Cadhoc -S "${f}"
        fi
        bench_record_cdhash "${f}" "${f}"
        echo "$(ldid -h "${f}")  ${f}"
    done
    bench_note "cdhashes recorded in ${STAGE_QUEUE}; run 'bench tc rebuild' after staging them"
}

# --------------------------------------------------------------------------
# console multiplexer
# --------------------------------------------------------------------------
# One socat owns the qemu console socket. Its stdin is a fifo held open
# read-write by the wrapper (so it never sees EOF when a writer goes away) and
# its stdout appends to console.log.
bench_mux_running() {
    local pid
    [[ -f "${MUX_PID_FILE}" ]] || return 1
    pid="$(cat "${MUX_PID_FILE}")"
    [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

bench_mux_start() {
    bench_mux_running && return 0 || true
    command -v socat >/dev/null || bench_die "socat is not on PATH (it is in the base image's apt list)"
    [[ -p "${CONSOLE_FIFO}" ]] || { rm -f "${CONSOLE_FIFO}"; mkfifo -m 600 "${CONSOLE_FIFO}"; }
    touch "${CONSOLE_LOG}"
    # Single-quoted on purpose: the paths are passed as $1..$3 so no quoting
    # of the wrapper string is needed.
    # shellcheck disable=SC2016
    setsid bash -c '
        exec 9<>"$1"
        exec socat -b1 "UNIX-CONNECT:$2" - <&9 >>"$3" 2>/dev/null
    ' _ "${CONSOLE_FIFO}" "${CONSOLE_SOCK}" "${CONSOLE_LOG}" &
    echo $! > "${MUX_PID_FILE}"
    # Give socat a moment to connect before anyone types.
    local i
    for i in 1 2 3 4 5 6 7 8 9 10; do
        bench_mux_running || break
        [[ -s "${CONSOLE_LOG}" ]] && break
        sleep 0.2 || true
    done
    bench_mux_running || bench_die "the console multiplexer died (is qemu listening on ${CONSOLE_SOCK}?)"
}

bench_mux_stop() {
    bench_mux_running || return 0
    kill "$(cat "${MUX_PID_FILE}")" 2>/dev/null || true
    rm -f "${MUX_PID_FILE}"
}

# A sub-tick sleep that does not fork. `sleep 0.002` pays a fork+exec on top
# of the delay it is asked for; a timed-out `read` on a fifo nobody writes to
# is a builtin and stays close to the request. The fifo is opened read-write
# so read(2) blocks forever instead of seeing EOF.
BENCH_NAP_FD=""
bench_nap() {
    if [[ -z "${BENCH_NAP_FD}" ]]; then
        local f="${RUN_DIR:-/tmp}/nap.fifo.$$"
        if mkfifo -m 600 "${f}" 2>/dev/null && exec 8<>"${f}" 2>/dev/null; then
            BENCH_NAP_FD=8
            rm -f "${f}"
        else
            BENCH_NAP_FD=none
            rm -f "${f}"
        fi
    fi
    if [[ "${BENCH_NAP_FD}" == "none" ]]; then
        sleep "$1"
    else
        # `read` returns >128 on timeout, which `set -e` would treat as fatal.
        read -r -t "$1" -u "${BENCH_NAP_FD}" _ || true
    fi
}

# Type a line on the guest console, one character every TYPE_DELAY seconds.
#
# One printf per character is deliberate: the emulated UART
# loses a whole write() of >= 16 bytes (see TYPE_DELAY_MS above). printf is a
# builtin writing straight to fd 9, so each iteration is exactly one write(2)
# of one byte into the fifo, and socat -b1 forwards it as one write(2) of one
# byte to the console socket.
bench_type() {
    local s="$1" i
    bench_mux_start
    exec 9>"${CONSOLE_FIFO}"
    for (( i = 0; i < ${#s}; i++ )); do
        printf '%s' "${s:i:1}" >&9
        bench_nap "${TYPE_DELAY}"
    done
    printf '\n' >&9
    exec 9>&-
}

# Wait for an extended regex to appear in the console log.
# bench_wait_for RE TIMEOUT [FAIL_RE]
bench_wait_for() {
    local re="$1" timeout="$2" fail_re="${3:-}" waited=0
    while [[ "${waited}" -lt "${timeout}" ]]; do
        grep -Eq "${re}" "${CONSOLE_LOG}" 2>/dev/null && return 0
        if [[ -n "${fail_re}" ]] && grep -Eq "${fail_re}" "${CONSOLE_LOG}" 2>/dev/null; then
            return 2
        fi
        bench_qemu_running || return 3
        sleep 1
        waited=$((waited + 1))
    done
    return 1
}

# --------------------------------------------------------------------------
# qemu
# --------------------------------------------------------------------------
bench_qemu_running() {
    local pid
    [[ -f "${QEMU_PID_FILE}" ]] || return 1
    pid="$(cat "${QEMU_PID_FILE}")"
    [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

bench_guest_running() { bench_qemu_running; }

bench_qemu_args() {
    QEMU_ARGS=(
        -M darwin
        -bootkc  "${FW_DIR}/bootkc"
        -dtree   "${FW_DIR}/dtree"
        -tc      "${FW_DIR}/ramdisk.tc"
        -ramdisk "${FW_DIR}/ramdisk.dmg"
        -args    "${BOOT_ARGS}"
        # run.sh uses -nographic, which only *defaults* the serial and monitor
        # chardevs to stdio. Both are given explicitly here, so -display none
        # says the same thing without the ambiguity.
        -display none
        -serial  "unix:${CONSOLE_SOCK},server,nowait"
        -monitor "unix:${MONITOR_SOCK},server,nowait"
        -m       "${Q_MEMORY_MB}M"
    )
    [[ "${Q_CPUS}" -gt 1 ]] && QEMU_ARGS+=(-smp "${Q_CPUS}") || true
    if [[ -f "${FW_DIR}/sptm" ]]; then
        QEMU_ARGS+=(-sptm "${FW_DIR}/sptm" -txm "${FW_DIR}/txm")
    fi
    [[ ${#Q_EXTRA_ARGS[@]} -gt 0 ]] && QEMU_ARGS+=("${Q_EXTRA_ARGS[@]}") || true
}

bench_qemu_kill() {
    if [[ -f "${QEMU_PID_FILE}" ]]; then
        kill "$(cat "${QEMU_PID_FILE}")" 2>/dev/null || true
        sleep 1
        kill -9 "$(cat "${QEMU_PID_FILE}")" 2>/dev/null || true
    fi
    rm -f "${QEMU_PID_FILE}" "${CONSOLE_SOCK}" "${MONITOR_SOCK}"
}

bench_qemu_start_once() {
    mkdir -p "${RUN_DIR}"
    rm -f "${CONSOLE_SOCK}" "${MONITOR_SOCK}"
    : > "${CONSOLE_LOG}"
    bench_qemu_args
    # On the SPTM path XNU does not own TCR_EL1 -- SPTM programs it -- and the
    # release SPTM the IPSW ships leaves both TCR_AS_16BIT_ASID and TBI1 clear.
    # DEVELOPMENT and KASAN kernels assert on the first and KASAN-TBI needs the
    # second, so they die before the console is up while the release kernel
    # does not (dev_kernel_tcr.patch). Supply what a
    # development SPTM sets, only for those variants on an SPTM guest.
    case "${BENCH_VARIANT:-}" in
        *-development|*-kasan)
            if [[ -f "${FW_DIR}/sptm" ]]; then
                export DARWIN_VM_DEV_KERNEL_TCR=1
                bench_note "${BENCH_VARIANT} on the SPTM path: DARWIN_VM_DEV_KERNEL_TCR=1"
            fi
            ;;
    esac
    bench_note "qemu: ${QEMU} ${QEMU_ARGS[*]}"
    # qemu runs from RUN_DIR, next to its sockets and logs.
    ( cd "${RUN_DIR}" && exec setsid "${QEMU}" "${QEMU_ARGS[@]}" >>"${QEMU_LOG}" 2>&1 ) &
    echo $! > "${QEMU_PID_FILE}"

    local i
    for i in $(seq 1 50); do
        [[ -S "${CONSOLE_SOCK}" ]] && break
        bench_qemu_running || { bench_warn "qemu exited immediately:"; tail -20 "${QEMU_LOG}" >&2; return 1; }
        sleep 0.2
    done
    [[ -S "${CONSOLE_SOCK}" ]] || { bench_warn "qemu never created ${CONSOLE_SOCK}"; return 1; }
    bench_mux_start
}

# Boot with retries. Some bringups die in a data abort that cascades into
# "Nested panic detected"; the same firmware boots on a retry.
bench_boot() {
    local attempt=1 rc
    while [[ "${attempt}" -le "${Q_BOOT_RETRIES}" ]]; do
        bench_note "boot attempt ${attempt}/${Q_BOOT_RETRIES}"
        if bench_qemu_start_once; then
            # `rc=0; ... || rc=$?` and not a bare call: under `set -e` a
            # non-zero return from a shell function aborts the script, which
            # would make the whole retry loop below dead code.
            rc=0
            bench_wait_for "${SHELL_RE}" "${Q_BOOT_TIMEOUT}" "${PANIC_RE}" || rc=$?
            if [[ "${rc}" -eq 0 ]]; then
                bench_note "guest reached a shell"
                return 0
            fi
            case "${rc}" in
                1) bench_warn "no shell within ${Q_BOOT_TIMEOUT}s" ;;
                2) bench_warn "panicked during bringup" ;;
                3) bench_warn "qemu exited" ;;
            esac
        fi
        bench_mux_stop
        bench_qemu_kill
        # bench_qemu_start_once truncates the console log, so without this the
        # next attempt destroys the evidence of why this one failed - which is
        # exactly the log a "panicked during bringup" needs.
        if [[ -s "${CONSOLE_LOG}" ]]; then
            mv -f "${CONSOLE_LOG}" "${RUN_DIR}/console.attempt${attempt}.log"
            bench_warn "attempt ${attempt}'s console log kept at ${RUN_DIR}/console.attempt${attempt}.log"
        fi
        attempt=$((attempt + 1))
    done
    bench_die "guest did not reach a shell in ${Q_BOOT_RETRIES} attempts (console log: ${CONSOLE_LOG})"
}

# --------------------------------------------------------------------------
# bench exec
# --------------------------------------------------------------------------
# Types
#   printf '\n<<BENCH:%s:BEGIN>>\n' ID; ( CMD ); printf '\n<<BENCH:%s:END:%d>>\n' ID $?
# on the console. The %s/%d in the format string is what makes the guest's
# *echo* of this line distinguishable from the markers it later prints, so the
# log can be sliced without anchoring tricks.
bench_exec() {
    local timeout=120
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --timeout) timeout="${2:?}"; shift 2 ;;
            --)        shift; break ;;
            *)         break ;;
        esac
    done
    [[ $# -gt 0 ]] || bench_die "usage: bench exec [--timeout S] -- CMD..."
    bench_qemu_running || bench_die "no guest is running (bench start --detach first)"
    bench_mux_start

    local id cmd line
    # NOT `tr -dc … </dev/urandom | head -c 8`: head closes the pipe, tr dies
    # of SIGPIPE, and `set -o pipefail` + `set -e` then abort secb.sh with 141
    # before a single character has been typed. od reads a bounded 4 bytes.
    id="$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"
    cmd="$(printf '%q ' "$@")"
    line="printf '\\n<<BENCH:%s:BEGIN>>\\n' ${id}; ( ${cmd}); printf '\\n<<BENCH:%s:END:%d>>\\n' ${id} \$?"

    local start_line
    start_line="$(wc -l < "${CONSOLE_LOG}")"

    bench_type "${line}"

    if ! bench_wait_for "<<BENCH:${id}:END:[0-9]+>>" "${timeout}"; then
        bench_warn "timed out after ${timeout}s waiting for the guest to finish"
        return 124
    fi

    local status
    status="$(tail -n "+${start_line}" "${CONSOLE_LOG}" | tr -d '\r' \
        | grep -oE "<<BENCH:${id}:END:[0-9]+>>" | tail -1 | grep -oE '[0-9]+>>$' | tr -d '>')"

    # awk reads to the end rather than exiting at the END marker: console
    # lines that arrive after it (launchd is still chatty right after boot)
    # would otherwise SIGPIPE tail/tr, and pipefail + set -e turns that into
    # exit 141 for a command that succeeded.
    tail -n "+${start_line}" "${CONSOLE_LOG}" | tr -d '\r' | awk -v b="<<BENCH:${id}:BEGIN>>" -v e="<<BENCH:${id}:END:" '
        done { next }
        index($0, b) == 1 { on = 1; next }
        on && index($0, e) == 1 { on = 0; done = 1; next }
        on { print }
    '
    return "${status:-125}"
}

# --------------------------------------------------------------------------
# push / pull
# --------------------------------------------------------------------------
bench_push() {
    local src="${1:?usage: bench push HOST_PATH GUEST_PATH}" dst="${2:?}"
    [[ -f "${src}" ]] || bench_die "no such file: ${src}"
    bench_qemu_running || bench_die "no guest is running"

    # The restore ramdisks have no base64, but every one has bash, whose
    # printf %b turns \xNN back into any byte, NUL included. The bytes are
    # typed as plain hex, which needs no quoting, into ${dst}.hex, and one
    # loop in the guest decodes that. Typing is slow: put large files in the
    # ramdisk before boot with 'bench stage' instead.
    local hex chunk n=0
    hex="$(od -An -v -tx1 < "${src}" | tr -d ' \n')"
    bench_note "typing ${src} ($(( ${#hex} / 2 )) bytes) as hex at $(awk "BEGIN{printf \"%.0f\", 1/${TYPE_DELAY}}") chars/s"
    if ! bench_exec --timeout 30 -- /bin/bash -c ": > ${dst}.hex" >/dev/null; then
        # A restore ramdisk's root is read-only APFS and `mount -uw /` is
        # refused, so there is nowhere to write until a scratch filesystem
        # exists. Every ramdisk we boot ships /sbin/mount_tmpfs and empty
        # /mnt1../mnt11 mount points.
        bench_warn "the guest could not create ${dst}.hex"
        bench_warn "         the ramdisk root is read-only; make a scratch fs first:"
        bench_warn "           bench exec -- /sbin/mount_tmpfs /mnt1"
        bench_warn "           bench push ${src} /mnt1/$(basename "${dst}")"
        bench_die "         or put the file in the ramdisk before boot with 'bench stage'"
    fi
    while [[ -n "${hex}" ]]; do
        chunk="${hex:0:1024}"
        hex="${hex:1024}"
        bench_exec --timeout 120 -- /bin/bash -c "printf %s ${chunk} >> ${dst}.hex" >/dev/null \
            || bench_die "push failed at chunk ${n}"
        n=$((n + 1))
    done
    # shellcheck disable=SC2016  # expanded by the guest's bash
    bench_exec --timeout 600 -- /bin/bash -c \
        'while read -r -n2 h; do printf %b "\x${h}"; done < "$1.hex" > "$1" && rm -f "$1.hex"' _ "${dst}" >/dev/null \
        || bench_die "could not decode ${dst}.hex in the guest"
    bench_note "pushed ${src} -> ${dst}"
}

bench_pull() {
    local src="${1:?usage: bench pull GUEST_PATH HOST_PATH}" dst="${2:?}"
    bench_qemu_running || bench_die "no guest is running"

    # Output is the cheap direction: the guest prints the bytes as hex with
    # od, and only od's lines are kept, since launchd's warnings share the
    # console.
    bench_exec --timeout 300 -- /bin/bash -c "od -An -v -tx1 ${src}" \
        | tr -d '\r' | grep -E '^[[:space:]0-9a-f]+$' | tr -d ' \t\n' \
        | python3 -c 'import sys, binascii; sys.stdout.buffer.write(binascii.unhexlify(sys.stdin.read()))' > "${dst}" \
        || bench_die "pull failed"
    bench_note "pulled ${src} -> ${dst} ($(wc -c < "${dst}") bytes)"
}

# --------------------------------------------------------------------------
# lifecycle commands
# --------------------------------------------------------------------------
bench_start() {
    local detach=0
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --detach|-d) detach=1; shift ;;
            *) bench_die "bench start: unknown argument $1" ;;
        esac
    done

    if bench_qemu_running; then
        bench_die "a guest is already running (pid $(cat "${QEMU_PID_FILE}"))"
    fi

    mkdir -p "${RUN_DIR}"
    bench_is_prepped || bench_prep
    bench_refresh_stale_bootkc
    bench_boot

    echo "BENCH: guest ready (${TASK_ID}/${BENCH_VARIANT})"

    if [[ "${detach}" -eq 1 ]]; then
        # Returning here would end the container and take the guest with it,
        # so supervise instead. crash_check.sh does the docker-level detaching
        # and waits for the line above.
        bench_note "supervising qemu (pid $(cat "${QEMU_PID_FILE}")); container stays up until it exits"
        # 1 s, not 5: this loop is what keeps the container alive, so its
        # period is also how long `bench stop` leaves a guest-less container
        # "running" - long enough and the next `bench start` lands in it as a
        # `docker exec` and hangs supervising a second guest (crash_check.sh has
        # a guard for that too).
        while bench_qemu_running; do sleep 1; done
        bench_note "qemu exited"
        return 0
    fi

    bench_attach
}

bench_attach() {
    bench_qemu_running || bench_die "no guest is running"
    bench_mux_start
    echo "bench: attached to ${TASK_ID}/${BENCH_VARIANT}; detach with ctrl-]"
    # socat drives the terminal on the left and, on the right, a shell whose
    # stdin is piped into the console fifo and whose stdout is the log tail.
    socat "-,raw,echo=0,escape=0x1d" \
          "SYSTEM:tail -n +1 -f '${CONSOLE_LOG}' & exec cat > '${CONSOLE_FIFO}'" || true
    echo
    bench_note "detached; the guest is still running"
}

bench_stop() {
    if ! bench_qemu_running; then
        bench_note "no guest is running"
        bench_mux_stop
        return 0
    fi
    bench_note "asking the guest to halt"
    bench_type "sync; halt" || true
    sleep 3
    if [[ -S "${MONITOR_SOCK}" ]]; then
        printf 'quit\n' | socat - "UNIX-CONNECT:${MONITOR_SOCK}" >/dev/null 2>&1 || true
        sleep 1
    fi
    bench_mux_stop
    bench_qemu_kill
    bench_note "guest stopped"
}

bench_status() {
    echo "task     : ${TASK_ID} - ${TASK_TITLE}"
    echo "variant  : ${BENCH_VARIANT}"
    echo "guest    : ${GUEST_OS} ${GUEST_VERSION} (${GUEST_BUILD}) ${GUEST_DEVICE} / ${GUEST_SOC}"
    echo "xnu      : ${XNU_TAG} ${KERNEL_CONFIG}/${MACHINE_CONFIG}"
    echo "prepared : $(bench_is_prepped && sed -n 1p "${PREPPED_STAMP}" || echo no)"
    if bench_qemu_running; then
        local pid
        pid="$(cat "${QEMU_PID_FILE}")"
        echo "qemu     : running (pid ${pid}, up $(ps -o etime= -p "${pid}" 2>/dev/null | tr -d ' '))"
        echo "console  : ${CONSOLE_LOG} ($(wc -l < "${CONSOLE_LOG}") lines)"
        echo -n "kernel   : "
        bench_exec --timeout 60 -- /usr/bin/uname -v || echo "(uname failed)"
    else
        echo "qemu     : not running"
    fi
}

bench_log() {
    # --qemu prints the emulator's own stderr instead of the guest console. On
    # a guest that never emits a serial byte that is the only evidence there
    # is - qemu says there which boot path it took and why it stopped.
    if [[ "${1:-}" == "--qemu" ]]; then
        [[ -f "${QEMU_LOG}" ]] || bench_die "no qemu log yet"
        cat "${QEMU_LOG}"
        return
    fi
    [[ -f "${CONSOLE_LOG}" ]] || bench_die "no console log yet"
    if [[ "${1:-}" == "-f" ]]; then
        tail -f "${CONSOLE_LOG}"
    else
        cat "${CONSOLE_LOG}"
    fi
}

bench_firmware() {
    case "${1:-info}" in
        prep)  bench_prep 1 ;;
        reset)
            if bench_guest_running; then bench_die "stop the guest first"; fi
            bench_note "wiping ${FW_DIR} back to the image's pristine firmware"
            rm -rf "${FW_DIR:?}"/* "${FW_DIR:?}"/.bench-* 2>/dev/null || true
            bench_copy_pristine
            ;;
        info)
            echo "pristine : ${PRISTINE_DIR}"
            ls -la "${PRISTINE_DIR}" 2>/dev/null || true
            echo
            echo "volume   : ${FW_DIR}"
            ls -la "${FW_DIR}" 2>/dev/null || true
            echo
            if [[ -f "${FW_DIR}/info" ]]; then
                echo "device   : $(sed -n 1p "${FW_DIR}/info")"
                echo "ipsw     : $(sed -n 2p "${FW_DIR}/info")"
            fi
            if [[ -f "${FW_DIR}/bootkc" ]]; then
                ipsw macho info "${FW_DIR}/bootkc" 2>/dev/null | head -20 || true
            fi
            ;;
        *) bench_die "usage: bench firmware prep|reset|info" ;;
    esac
}

bench_task_info() {
    jq . "${TASK_META}"
}

# --------------------------------------------------------------------------
# kernel / kc - Path A only for now
# --------------------------------------------------------------------------
bench_path_a_recipe() {
    cat <<EOF
bench: kernels and kernel collections are not built inside a running task
       container. Both are built on the Linux docker host and baked into the
       task image:

  # compile + link the kernel from ${XNU_TAG} on Linux, relink the KDK's kexts
  # around it and rebuild the image
  projects/darwin/build_images.py --mode custom-development --instances ${TASK_ID}

KDK: ${KDK_VERSION:-?} (${KDK_BUILD:-?})   kc_type: ${GUEST_KC_TYPE:-?}
EOF
    return 2
}

bench_kernel() {
    case "${1:-which}" in
        which)
            if bench_qemu_running; then
                bench_exec --timeout 60 -- /usr/bin/uname -v || return $?
            else
                echo "guest not running; image variant is ${BENCH_VARIANT}"
                ls -la "${BENCH_DIR}/kernel" 2>/dev/null || echo "no ${BENCH_DIR}/kernel in this image"
            fi
            ;;
        build|link|install) bench_path_a_recipe ;;
        *) bench_die "usage: bench kernel build|link|install|which" ;;
    esac
}

bench_kc() {
    case "${1:-kexts}" in
        kexts)
            [[ -f "${FW_DIR}/bootkc" ]] || bench_die "no ${FW_DIR}/bootkc"
            ipsw kernel kexts "${FW_DIR}/bootkc"
            ;;
        build|install) bench_path_a_recipe ;;
        *) bench_die "usage: bench kc build|install|kexts" ;;
    esac
}

bench_usage() {
    cat <<'EOF'
usage: secb.sh <command> [args]

  start [--detach]          prep on first run, boot with retries, then attach
                            (--detach: report readiness and supervise qemu)
  attach                    attach to the running guest's console (detach: ctrl-])
  stop                      halt the guest and kill qemu
  status                    variant, prep state, uptime, guest `uname -v`
  log [-f]                  the serial console log

  exec [--timeout S] -- CMD...   run CMD in the guest, propagate its exit code

  push HOST_PATH GUEST_PATH      copy into the running guest
  pull GUEST_PATH HOST_PATH      copy out of the running guest
  stage FILE... [--to DIR]       copy into the ramdisk BEFORE boot (signed + trust-cached)

  compile [opts] SOURCE...       cross-compile C to an arm64 Mach-O for this guest
                                 (bench-cc; platform/minos come from meta.json)
  poc [--to DIR]                 compile poc/poc.c and stage it

  sign [--ents plist] MACHO...   ldid -Cadhoc -S, recording cdhashes
  tc rebuild | tc list           rebuild / inspect the ramdisk trust cache

  kernel build|link|install|which
  kc build|install|kexts
  firmware prep|reset|info
  task info
EOF
}
