<div align="center">
  <h1>SEC-bench Pro</h1>
  <p>Can Language Models Solve Long-Horizon Software Security Tasks?</p>
  <p>
    <a href="https://hwiwonl.ee/" style="text-decoration: none;">Hwiwon Lee</a>,
    <a href="https://jw-liu.xyz/" style="text-decoration: none;">Jiawei Liu</a>,
    <a href="https://smlijun.github.io/" style="text-decoration: none;">Dongjun Kim</a>,
    Wubing Xia,
    <a href="https://ziqi-zhang.github.io/" style="text-decoration: none;">Ziqi Zhang</a>,
    <a href="https://steven.cs.illinois.edu/" style="text-decoration: none;">Chunqiu Steven Xia</a>,
    <a href="https://lingming.cs.illinois.edu/" style="text-decoration: none;">Lingming Zhang</a>
  </p>
  <p>University of Illinois Urbana-Champaign</p>
  <p align="center">
    <a href="https://arxiv.org/abs/2605.26548"><img src="https://img.shields.io/badge/Paper-arXiv-b31b1b?style=for-the-badge" alt="Paper"></a>
    <a href="https://sec-bench.github.io/"><img src="https://img.shields.io/badge/Leaderboard-Live-f97316?style=for-the-badge" alt="Leaderboard"></a>
    <a href="LICENSE"><img src="https://forthebadge.com/images/badges/license-mit.svg" alt="MIT License" style="height: 28px"></a>
  </p>
</div>
<br>

SEC-bench Pro is a repository for building advanced software security benchmarks from real-world bug reports, proof-of-concept inputs, and reproducible execution environments. The goal is to make difficult security cases easier to study, validate, and reuse for benchmarking research, triage workflows, and automated analysis systems.

The benchmark currently includes 344 verified cases across Chromium V8, Mozilla SpiderMonkey, and the Linux kernel. Each case packages `meta.json`, reproduction assets, Docker build files, validation logs, and fixed-image checks where applicable.

## News

- [2026-06]: 🔥 SEC-bench Pro was used in the full GPT-5.5-Cyber evaluation ([blog](https://openai.com/index/daybreak-securing-the-world/)).
- [2026-06]: The Linux leaderboard is now live ([link](https://sec-bench.github.io/linux)).
- [2026-05]: The SpiderMonkey leaderboard is now live ([link](https://sec-bench.github.io/firefox)).
- [2026-05]: SEC-bench Pro launched with the V8 leaderboard ([link](https://sec-bench.github.io/v8)).

## Quick Start: Run Evals

Prerequisites:

- Docker
- Python 3.11+
- `uv`
- Agent credentials for the config you run. Codex configs use `OPENAI_API_KEY` or `~/.codex/auth.json` with `copy_host_auth = true`; Claude and OpenCode configs use the provider credentials declared in their TOML files.

Install Python dependencies from the repo root:

```sh
uv sync
```

Run an example Codex eval for a target project:

```sh
uv run harness/eval_codex.py harness/configs/codex/v8/config.example.toml
uv run harness/eval_codex.py harness/configs/codex/sm/config.example.toml
uv run harness/eval_codex.py harness/configs/codex/linux/config.example.toml
```

Run Claude or OpenCode with the matching config tree:

```sh
uv run harness/eval_claude.py harness/configs/claude/v8/config.example.toml
uv run harness/eval_opencode.py harness/configs/opencode/v8/config.example.toml
```

Each `harness/configs/<agent>/<project>/` directory contains one
`config.example.toml`. Copy or edit that file to select another model,
provider, output directory, or instance set.

To evaluate a small target set, edit the TOML config before running:

```toml
instances = ["472139305"]        # explicit case ids
# instances = "__verified__"     # all verified cases in images_dir
outdir = "output/v8/codex/my-run"
images_dir = "../projects/v8"    # use ../projects/sm or ../projects/linux for other targets
```

Relative `outdir` values are resolved under `harness/`, so the example above writes to `harness/output/v8/codex/my-run/<timestamp>/<instance_id>/`. See `harness/README.md` for all config fields, provider options, and artifact details.

### Linux MCP Sandbox

Linux agent runs expose the KVM/QEMU harness through the vendored
`mcps/linux` package (`secb-linux-vm-mcp`). Agents write `audit/poc.c` and use
the trusted MCP tools `secb_build`, `secb_repro`, and `secb_validate`; the MCP
server runs outside the agent command sandbox so QEMU gets native KVM while the
agent shell remains network-restricted.

All Linux leaves now declare `meta.json.privilege`: `user` PoCs run as uid
1000, and `root` PoCs run as init-namespace uid 0. The Linux prompts and MCP
validator use this field so the stated attacker model matches the actual guest
execution.

The example configs harden network access per agent: Codex uses
`workspace-write` with `network_access = false` and `web_search = "disabled"`,
Claude uses its Bash sandbox with denied domains, and OpenCode routes Bash tool
calls through a network-namespace shell wrapper.

## Grade Results

`harness/grade.py` re-runs agent-produced PoCs against vulnerable, fixed, and latest images, then classifies each PoC with the project-specific judge prompt. Point `--target-dir` at one timestamped run or a parent directory containing timestamped runs:

```sh
uv run harness/grade.py --project v8 --target-dir harness/output/v8/codex/example/gpt-5.5 --benchmark-dir projects/v8 --pull-missing
uv run harness/grade.py --project sm --target-dir harness/output/sm/codex/example/gpt-5.5 --benchmark-dir projects/sm --pull-missing
uv run harness/grade.py --project linux --target-dir harness/output/linux/codex/example/gpt-5.5 --benchmark-dir projects/linux --pull-missing
```

Summary CSVs are written to `<timestamp_dir>/summary` unless `--out-dir` is set. Linux latest validation uses per-CVE images from `hwiwonlee/linux.x86_64.latest:<instance_id>`; build local copies with:

```sh
python projects/linux/build_images.py --mode latest --linux-ref origin/master -j 4
```

## Reproduce Ground Truth

Each project has a host-side oracle for checking the packaged PoC against its vulnerable image. These scripts require Docker and `jq`:

```sh
projects/v8/crash_check.sh 472139305
projects/sm/crash_check.sh 1880719
projects/linux/crash_check.sh CVE-2022-0185
```

V8 and SpiderMonkey also accept a custom PoC path:

```sh
projects/v8/crash_check.sh 472139305 /path/to/poc.js
projects/sm/crash_check.sh 1880719 /path/to/poc.js
```

Check that a fixed image mitigates the same case:

```sh
python projects/v8/patch_check.py 472139305
python projects/sm/patch_check.py 1880719
python projects/linux/patch_check.py CVE-2022-0185
```

The crash oracles read image names, binaries, and command-line options from each case's `meta.json`. `output.txt` is retained as validation context, not as the scoring oracle.

## Repository Layout

```text
base/
  chromium/    Base image definitions for Chromium-related targets
  linux/       Base/latest image definitions for Linux kernel benchmark cases
  sm/          Base/latest image definitions for SpiderMonkey benchmark cases
  v8/          Base image definitions for V8 benchmark cases
harness/
  eval_codex.py
  eval_claude.py
  eval_opencode.py
  common.py
  grade.py
  judge.py
  configs/claude/
    v8/
    sm/
    linux/
  configs/codex/
    v8/
    sm/
    linux/
  configs/opencode/
    v8/
    sm/
    linux/
prompts/
  baseline/
  judge/
mcps/
  linux/       Vendored secb Linux VM MCP server
projects/
  v8/
    <issue_id>/  103 Chromium V8 benchmark cases
  sm/
    <issue_id>/  104 Mozilla SpiderMonkey benchmark cases
  linux/
    CVE-*/       137 Linux kernel benchmark cases
    build_images.py  Build orchestrator for base/vuln/fixed/latest images
    crash_check.sh   Host-side vuln image crash oracle
    patch_check.py   Host-side fixed image mitigation oracle
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Citation

```
@article{lee2026sec,
    author    = {Lee, Hwiwon and Liu, Jiawei and Kim, Dongjun and Zhang, Ziqi and Xia, Chunqiu Steven and Zhang, Lingming},
    journal   = {arXiv preprint arXiv:2605.26548},
    title     = {{SEC-bench Pro: Can Language Models Solve Long-Horizon Software Security Tasks?}},
    year      = {2026}
}

@inproceedings{lee2025secbench,
    author    = {Hwiwon Lee and Ziqi Zhang and Hanxiao Lu and Lingming Zhang},
    booktitle = {The Thirty-ninth Annual Conference on Neural Information Processing Systems},
    title     = {{SEC-bench: Automated Benchmarking of LLM Agents on Real-World Software Security Tasks}},
    url       = {https://openreview.net/forum?id=QQhQIqons0},
    year      = {2025}
}
```
