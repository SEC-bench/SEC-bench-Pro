# Using this repository with a coding agent

Darwin-bench is designed to be driven by AI coding agents (Claude Code, Codex,
Cursor or similar) working in a terminal. This page says what an agent needs to
know and gives prompts that have the right shape.

## What the agent has to understand first

* **Long steps are long.** The base image build compiles clang and QEMU, the
  kernel compile is more than a thousand translation units, and a guest boot
  under emulation takes minutes. Run these in the background with output to a log
  file, poll the log at a sensible interval, and never infer progress from CPU
  usage.
* **Rebuilds and caches.** `projects/darwin/build_images.py` keeps every Apple
  artifact it fetches (firmware, KDK, CLT runtime) in its cache directory, so a
  rebuild does not download them again. After any change under `base/darwin/`,
  the base image and every task image need a rebuild before the change is live.
* **Variants.** Each task's `meta.json` lists its variants. `ipsw-stock` boots
  the IPSW's own kernelcache; `kdk-development` and `kdk-kasan` relink a KDK
  kernel; `custom-development` compiles the vulnerable xnu tag from source; and
  `custom-fixed` compiles that same tag with the upstream security fix from the
  task's `patches/` applied on top. `patch_check.py` boots `custom-fixed` as an
  oracle: it runs the PoC and asserts the crash is gone, exiting 0 on
  `NO_CRASH_DETECTED`, 1 if the fixed kernel still crashes, and 2 on a harness
  error.
* **Tiers of support.** [README.md](README.md) marks each host, toolchain pin
  and guest as supported (Tier 1), best effort (Tier 2), experimental (Tier 3)
  or out of scope by design (Tier 4, such as Intel Mac guests). State the tier
  of the configuration you are working on, and treat a Tier 1 failure as a bug
  to diagnose rather than a reason to switch configuration.
* **Trust the machine.** When a claim in the docs disagrees with what the
  machine actually does, trust the machine, then fix the doc.

## Prompts

### Set up a Linux host and boot the reference task

```
Read docs/README.md, docs/quickstart-docker.md and docs/quickstart-agent.md in
this checkout. Then set this machine up as a Darwin-bench host and boot the
kdk-development guest:

1. Build the base image in the background with output to a log file; poll every
   10 minutes and report the stage it is in. It takes a long time; do not give
   up on it.
2. Build the kdk-development and kdk-kasan images with
   projects/darwin/build_images.py, which fetches the firmware and the KDK.
3. Start the kdk-development guest detached, run `uname -v` and
   `sysctl -n kern.uuid` in it with projects/darwin/crash_check.sh ... exec,
   then stop the guest.
4. Report exactly what each command printed. If a boot fails, quote the relevant
   part of the console log rather than guessing.
```

### Compile a custom kernel and boot it

```
Build the custom-development kernel and boot it:

1. Run projects/darwin/build_images.py --mode custom-development --instances
   <instance_id> in the background with its output in a log, polling every 5
   minutes. It fetches the firmware, KDK and CLT runtime into its cache
   directory and compiles the kernel. If the compile ends with errors, read the
   compile log and tell me which translation units failed before doing anything
   else.
2. Record the LC_UUID of the output kernel with otool in a base-image container,
   boot the custom-development image, and confirm `sysctl -n kern.uuid` in the
   guest equals that LC_UUID.
```

### Change the kernel source and test the change

```
I want to change <describe the change> in xnu.

1. Make the change in the xnu source tree, then produce a patch file at
   projects/darwin/<instance_id>/patches/<name>.patch.
2. Re-run projects/darwin/build_images.py --mode custom-development --instances
   <instance_id>, then boot it.
3. Prove the guest runs the new kernel (kern.uuid equals the new LC_UUID), then
   exercise the change with projects/darwin/crash_check.sh <instance_id>
   custom-development exec and report observations with the console log excerpts
   that support them.
```

### Verify an upstream fix with patch_check.py

```
Confirm the upstream security fix for <instance_id> mitigates the PoC:

1. Check that projects/darwin/<instance_id>/patches/ holds the fix patch and
   that custom-fixed is in the task's meta.json variants.
2. Run projects/darwin/patch_check.py <instance_id> --build >
   output.custom-fixed.txt in the background with its log polled. --build runs
   build_images.py --mode custom-fixed first, so this compiles the fixed kernel
   and boots it in one step.
3. Report the exit code and the verdict line: exit 0 / NO_CRASH_DETECTED means
   the fix holds; exit 1 / CONFIRMED:<type> means the fixed kernel still
   crashes. The oracle only has signal where the paired custom-development build
   already CONFIRMED-crashes on the open-source kernel, so first confirm that
   baseline if you are unsure.
```

### Add a new macOS release as a task

```
Add an ipsw-stock-only task <instance_id> for macOS <version> (<build>). Read
the layout section of docs/quickstart-docker.md first.

1. Find the IPSW URL for that build on Apple's CDN (ipsw download ipsw --device
   <device> --build <build> --urls inside a base-image container) and the xnu
   tag from apple-oss-distributions/distribution-macOS for provenance.
2. Copy projects/darwin/<old_instance_id> to projects/darwin/<new_instance_id>,
   then update meta.json and the Dockerfile ARGs.
3. Build and boot it. If it panics, read the console log, compare with the
   device-tree fixes in base/darwin/patches/darwin-vm/dt_fixup.patch, and report
   the panic string and your diagnosis before changing any patch.
4. When it boots, record the transcript with projects/darwin/crash_check.sh
   <instance_id> ipsw-stock (redirected to output.ipsw-stock.txt).
```
