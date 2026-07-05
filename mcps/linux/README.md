# secb-linux-vm-mcp

The SEC-bench **Linux** kernel PoC harness, exposed as MCP tools.

It wraps the in-container `secb` harness (`/usr/local/bin/secb`) so an agent can
build a PoC, boot the pinned kernel under QEMU, run the PoC, and read the verdict
— all through MCP tool calls instead of shell commands.

## Why an MCP server

The agent runs under a sandbox (e.g. Codex's bubblewrap `workspace-write`), which
gives the guest a minimal `/dev` without `/dev/kvm`. QEMU launched from inside the
sandbox therefore falls back to slow TCG emulation.

An MCP server is spawned by the agent host **outside** that per-command sandbox, so
QEMU launched from it gets **native KVM** (the container exposes `/dev/kvm`) while
the agent's own shell commands stay sandboxed. As a bonus, the agent never touches
`secb`, the kernel image, or QEMU directly — it only submits `audit/poc.c` and
receives a verdict — which makes the harness tamper-proof (stronger anti-cheat).

```
[ sandboxed agent ]  --(MCP tool call)-->  [ secb-linux-vm-mcp server, unsandboxed ]
   writes audit/poc.c                          secb build + QEMU(KVM) repro
                                               -> { verdict, serial_log, guest_uid }
```

## Tools

| Tool | Description |
|------|-------------|
| `secb_validate(audit_dir="/src/linux/audit")` | Stage the audit dir, rebuild the initramfs, boot the kernel under QEMU (KVM), run the PoC at the instance's declared privilege, return the verdict. Primary tool. |
| `secb_repro()` | Re-run the already-built PoC under QEMU (no rebuild). |
| `secb_build()` | Rebuild the PoC + initramfs without running. |

Each returns `{ verdict, crashed, guest_uid, serial_log, ... }`. The PoC is run as
the privilege declared by the instance config (`user` => uid 1000, `root` =>
uid 0); `guest_uid` reports the uid it actually ran as.

## Install

```bash
pip install .          # provides the `secb-linux-vm-mcp` console script
# or:  uv pip install --system .
```

Requires Python ≥ 3.10 and `fastmcp`. Intended to run **inside** a per-CVE
SEC-bench Linux image (which provides `/usr/local/bin/secb`, `/src/linux/audit`,
`/run/secb/config.json`, QEMU, and `/dev/kvm`).

## Use from Codex

Register it as an MCP server in the Codex config; keep the agent sandboxed:

```toml
[mcp_servers.secb]
command = "secb-linux-vm-mcp"
# Auto-run the harness tools (they run outside the sandbox; with
# approval_policy=never they would otherwise be cancelled in headless exec).
default_tools_approval_mode = "approve"
startup_timeout_sec = 60
```

## Configuration (env)

| Var | Default | Meaning |
|-----|---------|---------|
| `SECB_BIN` | `/usr/local/bin/secb` | Path to the secb harness. |
| `SECB_AUDIT_DIR` | `/src/linux/audit` | Canonical staged audit dir. |
| `SERIAL_LOG` | `/tmp/serial.log` | QEMU serial log path. |
| `SECB_BUILD_TIMEOUT` / `SECB_REPRO_TIMEOUT` | `1800` / `600` | Subprocess timeouts (s). |
| `SECB_TAIL_CHARS` | `16000` | Max serial-log chars returned. |
