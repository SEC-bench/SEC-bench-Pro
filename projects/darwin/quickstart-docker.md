We can containerize every step in [quickstart-ubuntu.md](quickstart-ubuntu.md). After installing [Docker](https://docs.docker.com/engine/install/ubuntu/), the user should be able to launch every project with one command.

# Single command reproduction

All image builds go through `projects/darwin/build_images.py --mode {base,ipsw-stock,kdk-development,kdk-kasan,custom-development,custom-fixed}`.

```bash
# Build the base image once (toolchain). Shared by every leaf.
projects/darwin/build_images.py --mode base

# One CVE: vuln image, then confirm the PoC trips the recorded error_type.
projects/darwin/build_images.py --mode ipsw-stock --instances CVE-2026-39868
projects/darwin/crash_check.sh CVE-2026-39868 ipsw-stock > output.ipsw-stock.txt

# Same CVE: fixed image, then confirm the patch mitigates the PoC.
projects/darwin/build_images.py --mode custom-fixed --instances CVE-2026-39868
projects/darwin/patch_check.py CVE-2026-39868 > output.custom-fixed.txt
```

## Leaf layout

```
projects/darwin/<project_id>
├── meta.json                      Bug metadata (kernel commit, error_type, ...)
├── Dockerfile                     vuln and fixed image, FROM hwiwonlee/darwin.base
├── build.sh                       In-container kernel/PoC/ramdisk build
├── secb.sh                        In-container harness (build | repro | validate)
├── init.sh                        ramdisk PID 3 (after kernel_task, launchd): runs poc.sh
├── poc.sh                         exec /poc/poc (driver shim)
├── poc/poc.c                      Reproducer source
├── patches-pre/*.patch            Optional prerequisite patches for vuln image
├── patches/*.patch                Upstream fix patch(es) — used by Dockerfile.fixed
├── output.<variant>.txt           Latest `secb repro` log on the vuln kernel
```

## Top-level layout

```
projects/darwin/
├── build_images.py                Build base/ipsw-stock/kdk-development/kdk-kasan/custom-development/custom-fixed images (--mode)
├── crash_check.sh                 Authoritative vuln-side oracle (PoC must crash; host re-greps serial log, retries)
├── patch_check.py                 Authoritative fix-side oracle (patch must mitigate; NO_CRASH vs regression semantics)
├── README.md
└── CVE-YYYY-NNNNN/                 Self-contained leaves (one per CVE)

base/darwin/                        (repo root) Base-image sources shared by every leaf
└── Dockerfile                     Base image: toolchain
```

## Container invocation

```bash
docker run --rm -it darwin-bench/<image_name> bash
docker run -d --name <container_name> darwin-bench/<image_name>
docker exec -it <container_name> bash 
```

## Caches

Caches for large files (IPSW, KDK, CLT, SDK, ...) are bind mounted in the dockerfile so you can reuse them across projects. Each leaf image must not be published, only the base image may be published.
