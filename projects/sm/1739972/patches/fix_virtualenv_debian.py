"""Fix two Debian-distutils-vs-venv path mismatches in Mozilla's mach virtualenv:

1. `_disable_pip_outdated_warning` calls `os.listdir(self._site_packages_dir())`,
   but Debian distutils returns `<venv>/local/lib/python3.11/dist-packages` —
   a path the venv never creates. Short-circuit the function.
2. `_site_packages_dir()` returns the same Debian path. The Nov-2021 mach already
   patches the `local/` prefix away, but it never converts `dist-packages` to
   `site-packages` — which is what the actual venv layout uses. Translate it.

Apply this AFTER `git checkout <sha>` and BEFORE `./mach build`. Idempotent.
The Oct-2021 mach kept these methods in python/mozbuild/mozbuild/virtualenv.py;
the Nov-2021 refactor moved them to python/mach/mach/virtualenv.py. Try both."""
import os
import sys

CANDIDATES = [
    "python/mach/mach/virtualenv.py",          # Nov 2021+
    "python/mozbuild/mozbuild/virtualenv.py",  # pre-Nov 2021
]

PATCHED_MARKER = "# DEBIAN_VENV_HACK_APPLIED"


def patch_one(path):
    if not os.path.exists(path):
        return f"  {path}: not present, skipping"
    src = open(path).read()
    if PATCHED_MARKER in src:
        return f"  {path}: already patched"

    # 1) Short-circuit _disable_pip_outdated_warning.
    src = src.replace(
        "    def _disable_pip_outdated_warning(self):",
        "    def _disable_pip_outdated_warning(self):\n"
        "        " + PATCHED_MARKER + "\n"
        "        return  # Debian distutils path mismatch; pip warning suppression is non-essential",
        1,
    )

    # 2) Translate dist-packages → site-packages at the tail of _site_packages_dir.
    # The Nov-2021 method ends with `return path` after the local-folder hack.
    # The Oct-2021 method ends with `return installer.install_purelib`.
    # In either case, patch by inserting a translation step before the function
    # returns. Use a unique nearby anchor.
    if "Hack around https://github.com/pypa/virtualenv/issues/2208" in src:
        # Nov 2021: insert translation before final `return path`
        src = src.replace(
            "        return path\n",
            "        path = path.replace('/dist-packages', '/site-packages')\n"
            "        return path\n",
            1,
        )
    elif "return installer.install_purelib" in src:
        # Oct 2021: replace the return statement
        src = src.replace(
            "        return installer.install_purelib",
            "        path = installer.install_purelib\n"
            "        path = path.replace('/dist-packages', '/site-packages')\n"
            "        return path",
            1,
        )

    open(path, "w").write(src)
    return f"  {path}: patched"


for p in CANDIDATES:
    print(patch_one(p))
