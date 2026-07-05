# MCP servers

In-container harness exposed as MCP tools. The agent (codex) spawns these servers
OUTSIDE its per-command sandbox, so QEMU launched from them gets native KVM while
the agent's own shell stays sandboxed.

- `linux/` - `secb-linux-vm-mcp`: wraps the Linux kernel KASAN harness
  (`secb build` / `secb repro` / `secb validate`) as MCP tools.

