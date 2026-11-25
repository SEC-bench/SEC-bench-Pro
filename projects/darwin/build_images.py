#!/usr/bin/env python3
"""Build the Darwin-bench docker images.

    build_images.py --mode base
    build_images.py --mode kdk-development --instances CVE-2026-20698 CVE-2026-28897
    build_images.py --mode custom-development --instances CVE-2026-20698
    build_images.py --mode ipsw-stock --instances CVE-2022-42845 --cache-dir /data/apple

--mode base builds hwiwonlee/darwin.base:latest from base/darwin/. --base-image names the tag to build, or, for the
other modes, an image to build FROM (pulled when it is not local).

The other modes build one image per --instances directory under
projects/darwin/, darwin-bench/<instance>:<mode>, and need the base image:

  ipsw-stock          the IPSW's own kernelcache
  kdk-development     the KDK's development kernel, relinked into a boot KC
  kdk-kasan           the KDK's KASAN kernel, relinked
  custom-development  a kernel compiled from the instance's xnu tag and
                      patches, which this script builds first

Everything downloaded from Apple goes to --cache-dir (default
$DARWIN_BENCH_DOWNLOADS, else ~/Downloads/darwin-bench) and is fetched once:

  firmware/<device>_<build>/   the IPSW members (bench-fetch-firmware); `,` in
                               the device becomes `-` (Macmini9-1_25F71)
  kdk/KDK_<version>_<build>.kdk  the unpacked KDK (bench-fetch-kdk)
  clt/                         libclang_rt.cc_kext.a from the CLT (custom-*)
  sdk/MacOSX<version>.sdk      the macOS SDK bench-cc compiles against
  dl/                          partial IPSW downloads

The kernel build tree goes to --work-dir (default <repo>/out), as
<instance>/xnu, laid out as darwin-xnu-build's, and the linked kernel to
<instance>/kernel/.

Instance images contain Apple material: never push them.
"""
import argparse
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
MODES = ('base', 'ipsw-stock', 'kdk-development', 'kdk-kasan', 'custom-development', 'custom-fixed')
# Command Line Tools for Xcode 26.6: its libclang_rt.cc_kext.a is what every
# custom kernel links.
CLT_PRODUCT = '140-17812'

DRY_RUN = False


def note(msg):
    print('build_images: ' + msg, file=sys.stderr, flush=True)


def die(msg):
    print('build_images: error: ' + msg, file=sys.stderr, flush=True)
    sys.exit(1)


def run(cmd, check=True):
    print('+ ' + ' '.join(shlex.quote(str(c)) for c in cmd), file=sys.stderr, flush=True)
    if DRY_RUN:
        return 0
    r = subprocess.run([str(c) for c in cmd])
    if check and r.returncode != 0:
        die('command failed with exit status %d' % r.returncode)
    return r.returncode


def have_image(image):
    return subprocess.run(['docker', 'image', 'inspect', image],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def ensure_base(image):
    if DRY_RUN or have_image(image):
        return
    note('%s is not local; pulling it' % image)
    if subprocess.run(['docker', 'pull', image]).returncode != 0:
        die('no base image %s: build it with --mode base, or pass --base-image <registry image>' % image)


def as_user():
    # The calling user, so nothing in the cache or the work dir is root's.
    return ['--user', '%d:%d' % (os.getuid(), os.getgid()), '-e', 'HOME=/tmp']


def in_base(base, mounts, cmd, env=(), workdir=None, root=False, check=True):
    """Run cmd in a throwaway container of the base image."""
    args = ['docker', 'run', '--rm'] + ([] if root else as_user())
    for src, dst, mode in mounts:
        if not mode and not DRY_RUN:
            pathlib.Path(src).mkdir(parents=True, exist_ok=True)
        args += ['-v', '%s:%s%s' % (src, dst, ':' + mode if mode else '')]
    for e in env:
        args += ['-e', e]
    if workdir:
        args += ['-w', workdir]
    return run(args + [base] + list(cmd), check=check)


def has_stage(dockerfile, name):
    return re.search(r'^\s*FROM\s.*\sAS\s+%s\s*$' % re.escape(name), dockerfile, re.M) is not None


# ---------------------------------------------------------------------------
# the cache: everything that comes from Apple
# ---------------------------------------------------------------------------
def fetch_firmware(base, cache, meta):
    g = meta['guest']
    # No comma in the name: docker reads --build-context values as name=path.
    d = cache / 'firmware' / ('%s_%s' % (g['device'].replace(',', '-'), g['build']))
    if (d / 'bootkc').is_file() and (d / 'ramdisk.dmg').is_file():
        note('firmware: %s' % d)
        return d
    for sub in ('dl', 'firmware'):
        (cache / sub).mkdir(parents=True, exist_ok=True)
    tmp = d.with_name(d.name + '.partial')
    in_base(base, [(cache, '/cache', '')],
            ['bench-fetch-firmware', '--device', g['device'], '--url', meta['ipsw']['url'],
             '--build', g['build'], '--os', g['os'], '--out', '/cache/firmware/' + tmp.name],
            env=['BENCH_DL_CACHE=/cache/dl'])
    if not DRY_RUN:
        tmp.rename(d)
    return d


def fetch_kdk(base, cache, meta):
    k = meta['kdk']
    name = 'KDK_%s_%s.kdk' % (k['version'], k['build'])
    d = cache / 'kdk' / name
    if (d / 'System/Library/Extensions').is_dir():
        note('KDK: %s' % d)
        return d
    (cache / 'kdk').mkdir(parents=True, exist_ok=True)
    cmd = ['bench-fetch-kdk', '--build', k['build'], '--version', k['version'], '--out', '/cache/kdk/' + name]
    if k.get('sha256'):
        cmd += ['--sha256', k['sha256']]
    # KDKs before macOS 14 have no KDK_SDK.pkg, so no Kernel.framework or
    # usr/local/lib/kernel/platform, and bench-fetch-kdk calls the unpack
    # incomplete. A task pins that with kdk.sdk_package = false; the kexts and
    # kernels the collection link needs are then all there is to check.
    rc = in_base(base, [(cache, '/cache', '')], cmd, env=['BENCH_DL_CACHE=/cache/dl'],
                 check=k.get('sdk_package', True))
    if rc != 0 and not DRY_RUN:
        if not ((d / 'System/Library/Extensions').is_dir() and (d / 'System/Library/Kernels').is_dir()):
            die('bench-fetch-kdk failed and %s has no Extensions/Kernels' % d)
        note('KDK: %s (no KDK_SDK.pkg, as meta.json kdk.sdk_package says)' % d)
    return d


def fetch_clt(base, cache, product):
    d = cache / 'clt'
    if list(d.glob('toolchain-libs/libclang_rt.cc_kext.a')):
        note('CLT runtime: %s' % d)
        return d
    d.mkdir(parents=True, exist_ok=True)
    in_base(base, [(cache, '/cache', '')],
            ['bench-fetch-xcode-tools', '--clt', '--clt-product', product, '--out', '/cache/clt'],
            env=['BENCH_DL_CACHE=/cache/dl'])
    return d


def fetch_sdk(base, cache, meta):
    g = meta['guest']
    if g['os'] != 'macOS':
        return None
    d = cache / 'sdk'
    have = sorted(d.glob('MacOSX%s*.sdk' % g['version']))
    if have:
        note('SDK: %s' % have[-1])
        return have[-1]
    d.mkdir(parents=True, exist_ok=True)
    # The SDK only serves `bench compile`/`bench poc`; an image builds without it.
    (cache / 'dl').mkdir(parents=True, exist_ok=True)
    args = ['docker', 'run', '--rm'] + as_user() + ['-v', '%s:/cache' % cache, '-e', 'BENCH_DL_CACHE=/cache/dl', base,
            'bench-fetch-xcode-tools', '--clt', '--clt-for-macos', g['version'], '--sdk', '--out', '/cache/sdk']
    print('+ ' + ' '.join(shlex.quote(str(c)) for c in args), file=sys.stderr, flush=True)
    if not DRY_RUN and subprocess.run(args).returncode != 0:
        note('warning: no macOS %s SDK fetched; bench compile/hello will not work' % g['version'])
    return None


# ---------------------------------------------------------------------------
# the custom kernel
# ---------------------------------------------------------------------------
def build_bounds_safety_tc(base, task_dir):
    """Build the task's bounds-safety-tc stage: the base image plus Apple's
    swiftlang clang (Swift 6.2 / clang-17), which enforces -fbounds-safety where
    the repo's clang-24 cannot. The kernel compile runs inside it. Returns the
    image tag."""
    if not has_stage((task_dir / 'Dockerfile').read_text(), 'bounds-safety-tc'):
        die('%s sets xnu.bounds_safety but its Dockerfile has no `AS bounds-safety-tc` stage'
            % task_dir.name)
    tag = 'darwin-bench/%s:bounds-safety-tc' % task_dir.name.lower()
    run(['docker', 'build', '--target', 'bounds-safety-tc', '-t', tag,
         '--build-arg', 'BASE_IMAGE=' + base, task_dir])
    return tag


def build_kernel(base, cache, work, instance, meta, kdk, clt, mode):
    x = meta['xnu']
    g = meta['guest']
    # xnu names the kernel after its machine config, which is the SoC except
    # where a tag builds an M1 as T8101 (CVE-2022-42845).
    kernel_name = 'kernel.%s.%s' % (x.get('kernel_config', 'DEVELOPMENT').lower(),
                                    x.get('machine_config', g['soc']).lower())
    # Vuln and fixed builds use separate work trees: linux-xnu-build applies the
    # patch dirs only onto a fresh checkout, so sharing a tree would let whichever
    # ran first pin the patch state for the other.
    suffix = '-fixed' if mode == 'custom-fixed' else ''
    xnu_dir = work / instance / ('xnu' + suffix)
    kernel_dir = work / instance / ('kernel' + suffix)
    xnu_dir.mkdir(parents=True, exist_ok=True)
    kernel_dir.mkdir(parents=True, exist_ok=True)
    kdk_path = '/Library/Developer/KDKs/' + kdk.name
    # linux-xnu-build in darwin-xnu-build's layout under /work; the task's
    # patches apply to a fresh checkout only, so a rebuild reuses the tree.
    # It runs as root, because it writes xnu-host-cc and two headers into the
    # image's CLT, and then hands the tree back. libclang_rt.cc_kext.a goes
    # where the Command Line Tools install it, which is where the script looks.
    owner = '%d:%d' % (os.getuid(), os.getgid())
    script = 'linux-xnu-build; rc=$?; chown -R %s /work; exit $rc' % owner
    cc_kext_dir = '/Library/Developer/CommandLineTools/usr/lib/clang/clt/lib/darwin'
    mounts = [(xnu_dir, '/work', ''), (clt / 'toolchain-libs', cc_kext_dir, 'ro'), (kdk, kdk_path, 'ro'),
              (REPO, '/repo', 'ro')]
    # patches-pre/ (build-enablement prerequisites) applies to both the
    # vuln and the fixed build; patches/ (the upstream security fix)
    # applies only to custom-fixed. The vuln custom-development build
    # therefore never sees patches/.
    env = ['MACOS_VERSION=' + g['version'], 'KDKROOT=' + kdk_path,
           'XNU_TAG=' + x['tag'],
           'XNU_PATCHES=' + ('/repo/projects/darwin/%s/patches-pre:/repo/projects/darwin/%s/patches' % (instance, instance)
                             if mode == 'custom-fixed'
                             else '/repo/projects/darwin/%s/patches-pre' % instance),
           'KERNEL_CONFIG=' + x.get('kernel_config', 'DEVELOPMENT'),
           'MACHINE_CONFIG=' + x.get('machine_config', g['soc'].upper())]
    # meta.json's xnu.build_env: further linux-xnu-build / make
    # variables the instance pins (CVE-2022-42845: RC_DARWIN_KERNEL_VERSION, IIG).
    env += ['%s=%s' % kv for kv in sorted(x.get('build_env', {}).items())]
    # xnu.bounds_safety: build this kernel with Apple's -fbounds-safety enabled.
    # The repo's upstream clang-24 cannot enforce it, so compile in the task's
    # bounds-safety-tc image (base + the swiftlang clang-17, baked by the task
    # Dockerfile) and point CROSS_CLANG at its xnu-swift-cc wrapper. The one gap
    # -- xnu's kalloc-type builtins -- is shimmed by the force-included
    # xnu_bs_stub.h in that wrapper; XNU_SKIP_BUILTIN_CHECK=1 skips the
    # has_xnu_builtins gate that a macro cannot satisfy. xnu's makedefs then
    # turns BOUND_CHECKS on for every `bound-checks` file (bsd/net, incl rtsock.c).
    if x.get('bounds_safety'):
        base = build_bounds_safety_tc(base, HERE / instance)
        env += ['CROSS_CLANG=/usr/local/bin/xnu-swift-cc', 'XNU_SKIP_BUILTIN_CHECK=1']
    in_base(base, mounts, ['sh', '-c', script], env=env, workdir='/work', root=True)
    src = xnu_dir / 'build' / 'xnu.obj' / kernel_name
    if not DRY_RUN:
        if not src.exists():
            die('no %s after linux-xnu-build; see %s' % (src, xnu_dir / 'build' / 'log'))
        (kernel_dir / kernel_name).write_bytes(src.resolve().read_bytes())
    note('kernel: %s' % (kernel_dir / kernel_name))
    return kernel_dir


# ---------------------------------------------------------------------------
def build_base(args):
    tag = args.base_image or 'hwiwonlee/darwin.base:latest'
    cmd = ['docker', 'build', '-t', tag, '-f', REPO / 'base/darwin/Dockerfile']
    for a in args.build_arg:
        cmd += ['--build-arg', a]
    run(cmd + [REPO / 'base/darwin'])


def build_instance(args, instance, cache, work, base):
    d = HERE / instance
    if not (d / 'Dockerfile').is_file():
        die('no %s' % (d / 'Dockerfile'))
    meta = json.loads((d / 'meta.json').read_text())
    dockerfile = (d / 'Dockerfile').read_text()
    mode = args.mode
    if mode not in meta.get('variants', []):
        die('%s has no variant %s (meta.json variants: %s)' % (instance, mode, ', '.join(meta.get('variants', []))))
    if not has_stage(dockerfile, mode):
        die('%s lists %s but its Dockerfile has no `AS %s` stage' % (instance, mode, mode))

    cmd = ['docker', 'build', '--target', mode, '-t',
           'darwin-bench/%s:%s' % (instance.lower(), mode), '--build-arg', 'BASE_IMAGE=' + base]
    cmd += ['--build-context', 'firmware=%s' % fetch_firmware(base, cache, meta)]
    fetch_sdk(base, cache, meta)
    if mode != 'ipsw-stock':
        kdk = fetch_kdk(base, cache, meta)
        cmd += ['--build-arg', 'KC_SOURCE=stage', '--build-arg', 'KDK_SOURCE=stage',
                '--build-context', 'kdk=%s' % kdk]
        if mode.startswith('custom-'):
            clt = fetch_clt(base, cache, args.clt_product)
            cmd += ['--build-context', 'kernel=%s' % build_kernel(base, cache, work, instance, meta, kdk, clt, mode)]
    run(cmd + [d])


def main():
    global DRY_RUN
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', required=True, choices=MODES)
    ap.add_argument('--instances', nargs='+', metavar='CVE-ID', default=[],
                    help='instance directories under projects/darwin/ (required unless --mode base)')
    ap.add_argument('--cache-dir', type=pathlib.Path,
                    default=pathlib.Path(os.environ.get('DARWIN_BENCH_DOWNLOADS',
                                                        pathlib.Path.home() / 'Downloads/darwin-bench')),
                    help='where everything downloaded from Apple is kept')
    ap.add_argument('--work-dir', type=pathlib.Path, default=REPO / 'out',
                    help='kernel build trees and linked kernels (custom-*)')
    ap.add_argument('--base-image', default=None,
                    help='--mode base: the tag to build; otherwise the image to build FROM '
                         '(default hwiwonlee/darwin.base:latest, pulled when not local)')
    ap.add_argument('--build-arg', action='append', default=[], metavar='NAME=VALUE',
                    help='--mode base: passed to docker build (e.g. BASE_IMAGE=ubuntu:24.04)')
    ap.add_argument('--clt-product', default=CLT_PRODUCT,
                    help='custom-*: the CLT product whose libclang_rt.cc_kext.a the kernel links')
    ap.add_argument('--dry-run', action='store_true', help='print the commands instead of running them')
    args = ap.parse_args()
    DRY_RUN = args.dry_run

    if args.mode == 'base':
        if args.instances:
            die('--mode base takes no --instances')
        build_base(args)
        return
    if not args.instances:
        die('--mode %s needs --instances, e.g. --instances CVE-2026-20698' % args.mode)
    cache = args.cache_dir.expanduser().resolve()
    work = args.work_dir.expanduser().resolve()
    base = args.base_image or 'hwiwonlee/darwin.base:latest'
    ensure_base(base)
    for instance in args.instances:
        build_instance(args, instance.rstrip('/').split('/')[-1], cache, work, base)


if __name__ == '__main__':
    main()
