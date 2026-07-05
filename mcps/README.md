# secb MCP servers (vendored)

In-container harness exposed as MCP tools. The agent (codex) spawns these servers
OUTSIDE its per-command sandbox, so QEMU launched from them gets native KVM while
the agent's own shell stays sandboxed.

- `linux/` — `secb-linux-vm-mcp`: wraps the Linux kernel KASAN harness
  (`secb build` / `secb repro` / `secb validate`) as MCP tools.

Vendored from github.com/SEC-bench/mcps so the image build is self-contained
(no private-repo access / gh token needed).
