#!/bin/bash
# projects/darwin/crash_check.sh - boot and drive an instance image.
#
#   crash_check.sh <instance> <variant>                  # the whole transcript
#   crash_check.sh <instance> <variant> <command> [args] # one step of it
#
#   projects/darwin/crash_check.sh CVE-2026-20698 kdk-development > output.kdk-development.txt
#
#   crash_check.sh CVE-2026-20698 custom-development start --detach
#   crash_check.sh CVE-2026-20698 custom-development exec -- uname -v
#   crash_check.sh CVE-2026-20698 custom-development stop
#   crash_check.sh CVE-2026-20698 custom-development status
#   crash_check.sh CVE-2026-20698 custom-development shell      # a shell in the container
#   DARWIN_BENCH_SDK_DIR=/path/to/MacOSX26.5.sdk \
#       crash_check.sh CVE-2026-20698 kdk-development poc       # bench-cc compiles against the mounted SDK
#
# Without a command the run is the whole reproduce in one shot: stage init.sh,
# poc.sh and the compiled poc (staged at /poc/poc), boot the guest, run the task's
# init.sh on the serial console, and write the console transcript plus one verdict line to
# stdout - the transcript shape documented in docs/quickstart-docker.md.
# Every note the run prints goes to stderr,
# so stdout redirected to output.<variant>.txt is exactly the transcript.
# Options for that form go where the command would be: --timeout S, --no-poc.
#
# Every command but `shell` goes to the image's
# secb.sh (docs/quickstart-docker.md, step 4).
#
# The images, darwin-bench/<instance>:<variant>, are built by
# projects/darwin/build_images.py. <variant> is one of the instance's
# meta.json "variants":
#   ipsw-stock          the IPSW's own kernelcache, unrelinked (no KDK)
#   kdk-development     the KDK's kernel.development.<soc>, relinked with the KDK's kexts
#   kdk-kasan           the KDK's kernel.kasan.<soc> and the kexts' _kasan variants
#   custom-development  a kernel compiled from the xnu sources, relinked the same way
#
# Where docker runs
# -----------------
# On this machine, always. crash_check.sh drives the local docker daemon. To use
# another machine, clone this repository there, ssh in, and run crash_check.sh
# from that checkout; nothing here syncs or tunnels anything.
#
# The macOS SDK
# -------------
# `run` and `shell` mount the newest $DARWIN_BENCH_DOWNLOADS/sdk/MacOSX*.sdk
# (default $HOME/Downloads/darwin-bench, build_images.py's cache directory)
# read-only for bench-cc, unless DARWIN_BENCH_SDK_DIR names another.
#
# No host mount, no privilege
# ---------------------------
# The container edits firmware/ramdisk.dmg in place with apfsftp (a userspace
# APFS writer, base/darwin/scripts), so there is no host mount, no apfs.ko and
# no --privileged. The firmware is a plain docker volume, and the flow is
# identical on a Linux and a macOS docker host.
#
# `run` and `shell` also bind-mount the repo's base/darwin/ read-only at /bench/base.
# That is where an image finds bench-cc and bench-poc.sh (`bench compile`,
# `bench poc`) until the base image is rebuilt with them installed.
#
# Guest lifecycle across invocations
# ----------------------------------
# `start --detach` runs the container detached and named
# darwin-bench-<id>-<variant>; every later `run` for the same task+variant is a
# `docker exec` into it, so the guest survives between commands. Without
# --detach, `start` is a foreground `docker run --rm`.
#
# EULA: the images contain Apple material. This script has no push path and
# never logs in to a registry.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${HERE}/../.." && pwd)"
DOWNLOADS="${DARWIN_BENCH_DOWNLOADS:-${HOME}/Downloads/darwin-bench}"
SDK_DIR="${DARWIN_BENCH_SDK_DIR:-}"

# macOS ships bash 3.2, which has neither `mapfile` nor a safe way to expand an
# empty array under `set -u`. read_into NAME < input is the stand-in; the
# ${arr[@]+"${arr[@]}"} idiom below is the other half.
read_into() {
    local __name="$1" __line
    eval "${__name}=()"
    while IFS= read -r __line; do
        if [[ -n "${__line}" ]]; then
            eval "${__name}+=(\"\${__line}\")"
        fi
    done
}

die()  { echo "crash_check: error: $*" >&2; exit 1; }
note() { echo "crash_check: $*" >&2; }

need_docker() {
    command -v docker >/dev/null 2>&1 \
        || die "docker not found on this machine; crash_check.sh drives the local docker only (docs/README.md)"
}

usage() {
    sed -n '2,/^set -euo pipefail/p' "${BASH_SOURCE[0]}" | sed '$d' | sed 's/^# \{0,1\}//'
    exit 1
}

# --------------------------------------------------------------------------
# naming
# --------------------------------------------------------------------------
# Docker refuses an uppercase repository name ("darwin-bench/CVE-2026-20698" is invalid),
# so the task id is lowercased here and only here: container and volume names
# keep the canonical "CVE-2026-20698" spelling, which docker does allow.
image_for()     { echo "darwin-bench/$(echo "$1" | tr '[:upper:]' '[:lower:]'):$2"; }
volume_for()    { echo "darwin-bench-$1-$2-fw"; }
container_for() { echo "darwin-bench-$1-$2"; }


# "running" | "exited" | "created" | ... | "absent". Only the last line of
# docker's output is used and an empty result means absent.
container_state() {
    local out
    out="$(docker inspect -f '{{.State.Status}}' "$(container_for "$1" "$2")" 2>/dev/null | tail -1 || true)"
    [[ -n "${out}" ]] || out="absent"
    echo "${out}"
}

# --------------------------------------------------------------------------
# one-shot transcript (the whole reproduce)
# --------------------------------------------------------------------------
# `crash_check.sh <instance> <variant>` stages init.sh / poc.sh / the poc,
# boots the guest, runs the task's init.sh on the console and prints the
# serial transcript plus one verdict line to stdout:
#
#   projects/darwin/crash_check.sh CVE-2026-20698 kdk-development > output.kdk-development.txt
#
# init.sh prints `---- poc begin ----`, runs poc.sh and prints
# `---- poc end rc=N ----`; the kernel speaks on the same console, so a crash
# report lands between the two markers. At the end marker the run is over: the
# emulator is exited right there (what ctrl-a x does for a foreground qemu),
# no graceful shutdown and no waiting. A payload that panics the kernel never
# reaches the end marker; its dump is followed to `MACH Reboot` and then the
# emulator is exited the same way.

# Type one line on the guest console. bench_type in the image's
# bench-common.sh does the per-character writes (the emulated UART drops any
# single write of 16 bytes or more), reused through one docker exec rather
# than reimplemented here.
type_console() {
    local name="$1" line="$2"
    docker exec "${name}" bash -c \
        'source /opt/darwin-bench/bench-common.sh; bench_load_task; bench_type "$1"' \
        _ "${line}"
}

# snapshot NAME FILE - the guest console so far. docker cp covers the window
# where the container exited before we read the log.
snapshot_console() {
    docker exec "$1" cat /bench/run/console.log > "$2" 2>/dev/null \
        || docker cp "$1:/bench/run/console.log" "$2" >/dev/null 2>&1 \
        || true
}

# The verdict ladder, the same one secb.sh's `repro` applies to the console
# log (its secb_classify). It is repeated here rather than called because the
# classification runs on the host, on a transcript already in hand.
classify_console() {
    local log="$1" selfre="$2"
    if   grep -qE 'KASAN_TBI: invalid [0-9]+-byte (read|write)' "${log}"; then echo "CONFIRMED: KASAN"
    elif grep -qE 'Bounds safety trap'                       "${log}"; then echo "CONFIRMED: PANIC_BOUNDS"
    elif grep -qE 'Kernel data abort'                        "${log}"; then echo "CONFIRMED: PANIC_DATA_ABORT"
    elif grep -qE 'panic\(cpu [0-9]+ caller'                 "${log}"; then echo "CONFIRMED: PANIC"
    elif [[ -n "${selfre}" ]] && grep -qE "${selfre}" "${log}"; then echo "CONFIRMED: POC_SELFCHECK"
    else echo "NO_CRASH_DETECTED"
    fi
}

cmd_bench_run() {
    local task="${1:-}" variant="${2:-}"
    [[ -n "${task}" && -n "${variant}" ]] || usage
    shift 2
    local timeout="${SECB_RUN_TIMEOUT:-300}" do_poc=1
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --timeout) timeout="${2:?}"; shift 2 ;;
            --no-poc)  do_poc=0; shift ;;
            *) die "run options are --timeout S and --no-poc (got: $1)" ;;
        esac
    done
    need_docker

    local name img state
    name="$(container_for "${task}" "${variant}")"
    img="$(image_for "${task}" "${variant}")"
    # Never let docker go looking for the image in a registry: these carry
    # Apple material and must stay local.
    docker image inspect "${img}" >/dev/null 2>&1 \
        || die "no image ${img}; build it first: projects/darwin/build_images.py --mode ${variant} --instances ${task}"

    state="$(container_state "${task}" "${variant}")"
    if [[ "${state}" == "running" ]]; then
        # The run owns the whole lifecycle and shares a guest with nothing.
        # shellcheck disable=SC2016  # the container's shell expands these, not ours
        if docker exec "${name}" \
               sh -c 'test -f /bench/run/qemu.pid && kill -0 "$(cat /bench/run/qemu.pid)"' \
               >/dev/null 2>&1; then
            die "${name} already has a live guest; 'crash_check.sh ${task} ${variant} stop' first"
        fi
    fi
    if [[ "${state}" != "absent" ]]; then
        note "removing the stopped container ${name}"
        docker rm -f "${name}" >/dev/null
    fi

    # Stage before boot, because the trust cache is a boot-time module: the
    # poc binary (compiled by bench-cc) and the guest-side drivers, which the
    # task directory mount (docker_run_opts) puts at /bench/task.
    if [[ "${do_poc}" == 1 ]]; then
        cmd_run "${task}" "${variant}" poc >&2 \
            || die "staging the poc failed"
    fi
    cmd_run "${task}" "${variant}" stage /bench/task/init.sh /bench/task/poc.sh --to /bench >&2 \
        || die "staging init.sh / poc.sh failed"

    # Boot. `start --detach` returns at "BENCH: guest ready" or dies trying.
    cmd_run "${task}" "${variant}" start --detach >&2 \
        || die "the guest did not come up"

    local snap
    snap="$(mktemp "${TMPDIR:-/tmp}/crash_check.console.XXXXXX")"
    local begin_re='^---- poc begin ----'
    local end_re='^---- poc end rc=[0-9]+ ----'
    local panic_re='Nested panic detected|^panic\(cpu'

    type_console "${name}" "sh /bench/init.sh"

    # Wait for init.sh's end marker, or for the kernel to panic (in which case
    # there is no end marker to wait for). --timeout bounds the poc phase.
    local waited=0 retyped=0 outcome=timeout
    while :; do
        snapshot_console "${name}" "${snap}"
        if grep -qE "${end_re}" "${snap}" 2>/dev/null; then outcome=ended; break; fi
        if grep -qE "${panic_re}" "${snap}" 2>/dev/null; then outcome=panic; break; fi
        if ! grep -qE "${begin_re}" "${snap}" 2>/dev/null \
           && [[ "${retyped}" -eq 0 && "${waited}" -ge 45 ]]; then
            note "init.sh has not printed its begin marker; typing it again"
            type_console "${name}" "sh /bench/init.sh"
            retyped=1
        fi
        if [[ "${waited}" -ge "${timeout}" ]]; then outcome=timeout; break; fi
        if [[ "$(container_state "${task}" "${variant}")" != "running" ]]; then outcome=gone; break; fi
        sleep 5
        waited=$((waited + 5))
    done

    # A panicking payload's report is still printing when the panic is first
    # seen; follow it to MACH Reboot (its last word) before cutting loose.
    if [[ "${outcome}" == "panic" ]]; then
        local settled=0
        while [[ "${settled}" -lt 30 ]]; do
            snapshot_console "${name}" "${snap}"
            if grep -q 'MACH Reboot' "${snap}" 2>/dev/null; then break; fi
            sleep 2
            settled=$((settled + 2))
        done
    fi
    snapshot_console "${name}" "${snap}"
    case "${outcome}" in
        ended)   note "poc finished; exiting the emulator" ;;
        panic)   note "the kernel panicked during the poc; exiting the emulator" ;;
        gone)    note "the guest went away during the poc" ;;
        timeout) note "no poc end marker within ${timeout}s; exiting the emulator" ;;
    esac

    # Exit the emulator (what ctrl-a x does for a foreground qemu) and take
    # the container with it. No graceful shutdown; the transcript ends where
    # the poc did.
    docker exec "${name}" \
        sh -c 'printf "quit\n" | socat - UNIX-CONNECT:/bench/run/monitor.sock' \
        >/dev/null 2>&1 || true
    sleep 1
    snapshot_console "${name}" "${snap}"
    docker rm -f "${name}" >/dev/null 2>&1 || true

    # stdout from here on is the transcript and the verdict line.
    if [[ "${outcome}" == "ended" ]]; then
        # The run is over at init.sh's last word: after it the console goes
        # back to the shell prompt and there is nothing more to record.
        local cut=""
        cut="$(grep -n '^secb: poc exited without crashing the kernel' "${snap}" 2>/dev/null | head -1 | cut -d: -f1 || true)"
        if [[ -z "${cut}" ]]; then
            cut="$(grep -nE "${end_re}" "${snap}" 2>/dev/null | tail -1 | cut -d: -f1 || true)"
        fi
        if [[ -n "${cut}" ]]; then
            head -n "${cut}" "${snap}" > "${snap}.end" && mv "${snap}.end" "${snap}"
        fi
    fi
    cat "${snap}"
    # The console's last line often has no newline (a shell prompt); make the
    # verdict start on a line of its own either way.
    if [[ -n "$(tail -c 1 "${snap}")" ]]; then echo; fi
    local selfre=""
    selfre="$(jq -r '.verdict.selfcheck_regex // empty' "${HERE}/${task}/meta.json" 2>/dev/null || true)"
    classify_console "${snap}" "${selfre}"
    rm -f "${snap}"
    return 0
}

# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------
docker_run_opts() {
    local task="$1" variant="$2"
    # No mount, no kernel module, no privilege: prep and every ramdisk edit go
    # through apfsftp inside the container (base/darwin/scripts, bind-mounted at
    # /bench/base). The firmware is a docker volume on every host, Linux or Mac.
    printf '%s\n' \
        -v "$(volume_for "${task}" "${variant}"):/bench/firmware" \
        -v "${REPO}/base/darwin:/bench/base:ro" \
        -v "${HERE}/${task}/meta.json:/bench/meta.json:ro" \
        -v "${HERE}/${task}/secb.sh:/bench/secb.sh:ro" \
        -v "${HERE}/${task}:/bench/task:ro" \
        -v "${HERE}/${task}/poc:/bench/poc:ro"
    # The task directory read-only at /bench/task: `run` stages its init.sh
    # and poc.sh into the ramdisk. Its poc/ at /bench/poc shadows the copy
    # baked into the image, so an edited poc/poc.c is compiled by `poc` / `run`
    # without an image rebuild (the same trick as meta.json and secb.sh above).
    # The macOS SDK bench-cc compiles guest programs against. Never in an
    # image (Apple licenses it for Apple-branded hardware); mounted under
    # /opt/sdk and named to bench-cc by $BENCH_SDK.
    local sdk="${SDK_DIR}"
    if [[ -z "${sdk}" ]]; then
        sdk="$(ls -d "${DOWNLOADS}"/sdk/MacOSX*.*.sdk 2>/dev/null | sort -V | tail -1 || true)"
    fi
    [[ -n "${sdk}" ]] && printf '%s\n' \
        -v "$(cd "${sdk}" && pwd -P):/opt/sdk/$(basename "${sdk}"):ro" \
        -e "BENCH_SDK=/opt/sdk/$(basename "${sdk}")"
    # Guest kernel boot-args override (the whole string), for experiments such
    # as KASAN tunables; bench-common.sh reads it at `start`.
    [[ -n "${BENCH_BOOT_ARGS:-}" ]] && printf '%s\n' -e "BENCH_BOOT_ARGS=${BENCH_BOOT_ARGS}"
    # The run's knobs, overridable per run from the host.
    [[ -n "${SECB_RUN_TIMEOUT:-}" ]] && printf '%s\n' -e "SECB_RUN_TIMEOUT=${SECB_RUN_TIMEOUT}"
    return 0
}
# The last mount puts the repo's meta.json over the copy baked into the image,
# so qemu settings (cpus, ramdisk_size_mb, extra_args) take effect on the next
# `start` without rebuilding the task image.

cmd_run() {
    local task="${1:-}" variant="${2:-}"
    [[ -n "${task}" && -n "${variant}" ]] || usage
    shift 2
    [[ $# -gt 0 ]] || usage
    need_docker

    local name state
    name="$(container_for "${task}" "${variant}")"
    state="$(container_state "${task}" "${variant}")"

    # `bench stop` kills qemu but the container only exits once the
    # supervising `bench start --detach` inside it notices, one poll later.
    # A `start` issued in that window used to find the container "running",
    # take the `docker exec` path below and boot a *second* guest inside it --
    # and then block forever, because that inner start supervises rather than
    # returns. Wait the window out instead.
    if [[ "$1" == "start" && "${state}" == "running" ]]; then
        # shellcheck disable=SC2016  # the guest's shell expands these, not ours
        if docker exec "${name}" \
               sh -c 'test -f /bench/run/qemu.pid && kill -0 "$(cat /bench/run/qemu.pid)"' \
               >/dev/null 2>&1; then
            die "${name} already has a live guest; 'bench run ${task} ${variant} stop' first"
        fi
        local w=0
        while [[ "${state}" == "running" && "${w}" -lt 30 ]]; do
            note "waiting for the guest-less container ${name} to exit (${w}s)"
            sleep 3
            w=$((w + 3))
            state="$(container_state "${task}" "${variant}")"
        done
        [[ "${state}" == "running" ]] \
            && die "${name} is still up ${w}s after its guest died; 'docker rm -f ${name}'" || true
    fi

    # A running container already has the guest; talk to it.
    if [[ "${state}" == "running" ]]; then
        local -a args=(docker exec)
        if [[ -t 0 && -t 1 ]]; then args+=(-it); fi
        args+=("${name}" /bench/secb.sh "$@")
        local rc=0
        "${args[@]}" || rc=$?
        # `stop` kills qemu, the supervising `start --detach` then exits, the
        # container goes down with it, and docker kills this exec session
        # (137) before it can report. A stopped container is what was asked for.
        if [[ "$1" == "stop" && "${rc}" == 137 && "$(container_state "${task}" "${variant}")" != "running" ]]; then
            note "guest stopped"
            rc=0
        fi
        return "${rc}"
    fi

    if [[ "${state}" != "absent" ]]; then
        note "removing the stopped container ${name}"
        docker rm -f "${name}" >/dev/null
    fi

    local -a opts=()
    read_into opts < <(docker_run_opts "${task}" "${variant}")

    # `start --detach` has to leave a container behind for later `exec`s.
    if [[ "$1" == "start" ]] && [[ " $* " == *" --detach "* || " $* " == *" -d "* ]]; then
        docker run -d --name "${name}" "${opts[@]}" "$(image_for "${task}" "${variant}")" "$@" >/dev/null
        note "booting ${name} (this takes a few minutes under TCG)"
        wait_for_ready "${task}" "${variant}"
        return $?
    fi

    local -a args=(docker run --rm --name "${name}")
    if [[ -t 0 && -t 1 ]]; then args+=(-it); fi
    args+=("${opts[@]}" "$(image_for "${task}" "${variant}")" "$@")
    "${args[@]}"
}

wait_for_ready() {
    local task="$1" variant="$2" name timeout waited=0
    name="$(container_for "${task}" "${variant}")"
    timeout="$(( $(jq -r '.qemu.boot_timeout_s // 300' "${HERE}/${task}/meta.json") \
               * $(jq -r '.qemu.boot_retries // 4' "${HERE}/${task}/meta.json") + 120 ))"
    while [[ "${waited}" -lt "${timeout}" ]]; do
        if docker logs "${name}" 2>&1 | grep -q '^BENCH: guest ready'; then
            note "guest ready after ${waited}s"
            return 0
        fi
        if [[ "$(container_state "${task}" "${variant}")" != "running" ]]; then
            docker logs "${name}" 2>&1 | tail -40 >&2
            die "${name} exited before the guest came up"
        fi
        sleep 5
        waited=$((waited + 5))
    done
    docker logs "${name}" 2>&1 | tail -40 >&2
    die "${name} did not report a ready guest within ${timeout}s"
}

cmd_shell() {
    local task="${1:-}" variant="${2:-}"
    [[ -n "${task}" && -n "${variant}" ]] || usage
    shift 2
    need_docker
    local state
    state="$(container_state "${task}" "${variant}")"
    if [[ "${state}" == "running" ]]; then
        docker exec -it "$(container_for "${task}" "${variant}")" /bin/bash "$@"
    else
        local -a opts=()
        read_into opts < <(docker_run_opts "${task}" "${variant}")
        docker run --rm -it "${opts[@]}" "$(image_for "${task}" "${variant}")" shell "$@"
    fi
}

# --------------------------------------------------------------------------
main() {
    case "${1:-}" in
        ""|-h|--help|help) usage ;;
    esac
    [[ -d "${HERE}/${1}" ]] || die "no instance ${1} under ${HERE}"
    case "${3:-}" in
        ""|-*)
            # No command (or run options where a command would be): the whole
            # reproduce, transcript on stdout.
            cmd_bench_run "$@"
            ;;
        shell)   cmd_shell "$1" "$2" "${@:4}" ;;
        *)       cmd_run "$@" ;;
    esac
}

main "$@"
