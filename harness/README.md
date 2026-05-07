# SEC-bench Pro Harness

End-to-end evaluation pipeline for SEC-bench Pro:

1. **Drive an agent** (Claude Code, Codex, or OpenCode) inside per-instance
   Docker containers to produce PoCs.
2. **Grade the PoCs** by executing them against vuln/fixed/latest images
   and classifying each one with an LLM-as-a-judge.

The two stages are independent: agent runs drop artifacts into
`output/<project>/.../<ts>/<instance_id>/`, and `grade.py` operates on those
artifacts (or any other directory tree that follows the same layout).

## Layout

```
harness/
├── common.py                   Shared Docker helpers, prompt rendering, progress UI,
│                               project registry, interrupt handling, eval loop
├── eval_claude.py              Run Claude Code agent per instance
├── eval_codex.py               Run Codex agent per instance
├── eval_opencode.py            Run OpenCode agent per instance
├── grade.py                    Execute PoCs against vuln/fixed/latest and aggregate verdicts
├── judge.py                    LLM-as-a-judge (litellm wrapper with robust retry/parse)
├── GRADING.md                  Deep dive on the grading design & judge prompt contract
├── configs/
│   ├── claude/<project>/*.toml
│   ├── codex/<project>/*.toml
│   └── opencode/<project>/*.toml
├── router/                     Live-stream formatters for each agent's stdout
│   ├── fmt_claude.py
│   ├── fmt_codex.py
│   ├── fmt_opencode.py
│   ├── render.py
│   └── ansi.py
└── output/                     Default drop location for agent runs (gitignored)
    └── <project>/<agent>/.../<YYYYMMDD_HHMMSS>/
        └── <instance_id>/
            ├── audit/          Agent-produced artifacts (poc.js, Report.md, ...)
            ├── prompt.txt      Rendered task prompt
            ├── AGENTS.md       (optional) rendered AGENTS.md for the agent
            ├── result/         Grading artifacts, populated by grade.py
            │   ├── run_config.txt
            │   ├── files.csv
            │   ├── {vuln,fixed,latest}/{stdout,stderr}/<rel>.attempt<N>.log
            │   └── judge/<stem>.{prompt.txt,verdict.json}
            └── (agent-specific logs, sessions, telemetry)
```

Agent-run metadata (claude_projects, codex sessions, opencode sqlite, etc.)
also lands under `<instance_id>/`. Each eval script documents its own
layout.

## Prerequisites

- **Docker** with access to the project's image repos
  (`hwiwonlee/v8.x86_64`, `hwiwonlee/v8.x86_64.fixed`, `hwiwonlee/sm.x86_64`,
  ...). Images are per-instance tags, and `--pull-missing` will pull them on
  demand during grading.
- **Python 3.11+** with the project's dependencies installed from the
  repository root (`uv sync`; dependencies are declared in `pyproject.toml`).
- **Agent CLI binaries** for whichever evaluator(s) you run
  (`claude`, `codex`, `opencode`) and/or their Docker images.
- **LLM credentials for the judge**, in order of precedence:
  1. AWS Bedrock: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
     `AWS_REGION_NAME`, `CLAUDE_CODE_USE_BEDROCK` (default model:
     `us.anthropic.claude-sonnet-4-6`).
  2. Anthropic direct: `ANTHROPIC_API_KEY` (default: `claude-sonnet-4-6`).
  3. OpenAI fallback: `OPENAI_API_KEY` (default: `gpt-5.4`).

## Running an agent

All three evaluators take a TOML config as their only positional argument:

```bash
uv run harness/eval_claude.py   harness/configs/claude/v8/baseline_sonnet-4.6.toml
uv run harness/eval_codex.py    harness/configs/codex/v8/baseline_gpt-5.4.toml
uv run harness/eval_opencode.py harness/configs/opencode/v8/baseline_sonnet-4.6.toml
```

Add `--no-tui` to disable the pinned Rich progress bar (useful for CI).

A config (see `harness/configs/*`) specifies at minimum:

```toml
model           = "us.anthropic.claude-sonnet-4-6-v1"
provider        = "bedrock"                                 # agent-specific
instances       = ["41494611", "324596281"]                 # instance ids to evaluate
outdir          = "output/path"
timeout         = 5400                                      # per-instance agent timeout, seconds
prompt_template = "../prompts/baseline/task_prompt_v8.j2"
agents_md       = "../prompts/baseline/AGENTS_v8.j2"        # optional
images_dir      = "../v8"                                   # benchmark ground-truth dir
```

The evaluator renders `prompt_template` with per-instance `meta.json`, spins
up the instance's Docker container, runs the agent with the rendered prompt,
and harvests `audit/`, session logs, and tracking artifacts into
`<outdir>/<ts>/<instance_id>/`.

Resulting per-instance directory is self-contained: anything the grader
needs (the `audit/*.js` PoCs) is inside `audit/`.

## Grading agent output

Once an agent run has finished, point `grade.py` at the timestamped
directory:

```bash
uv run harness/grade.py \
    --project v8 \
    --target-dir harness/output/v8/claude/baseline/sonnet-4.6/no-skills \
    --pull-missing
```

- `--project {v8,sm,spidermonkey}` selects the Jinja judge template
  (`prompts/judge/<project>.j2`) and the image triple in
  `common.PROJECT_SPECS`.
- `--target-dir` can be either a single timestamped run (`…/20260506_020150/`)
  or a parent directory containing multiple runs (each matching
  `YYYYMMDD_HHMMSS`), in which case all runs are graded sequentially.
- `--attempts N` (default 3) re-runs each PoC against each image up to N
  times, exiting early on the first crash. Reliably catches flaky
  reproductions without wasting Docker cycles when the first attempt
  crashes.
- `--timeout SEC` (default 300) is the per-attempt wallclock budget.
- `--workers N` (default 20) runs instances in parallel.
- `--judge-model`, `--judge-workers`, `--judge-samples` override the LLM
  side (default: auto-detect provider, 5 workers, 1 sample).

Useful flags for large benchmark sweeps:

- `--pull-missing` to pull container images on demand.
- `--benchmark-dir PATH` when the benchmark ground truth isn't at
  `./{v8,sm}/`.
- `--out-dir PATH` to write the summary CSVs somewhere other than
  `<ts>/summary/`.

### Outputs

Per instance, under `<instance_id>/result/`:

| Path | Contents |
|---|---|
| `run_config.txt` | vuln/fixed/latest images, binary, options, timeout, attempts |
| `files.csv` | per-PoC outcome table (`verified`/`unsure`/`illegal`/`invalid`) |
| `{vuln,fixed,latest}/{stdout,stderr}/<rel>.attempt<N>.log` | raw execution logs |
| `judge/<stem>.prompt.txt` | exact prompt sent to the LLM |
| `judge/<stem>.verdict.json` | structured verdict + token usage + cost |

Across instances, under `<ts>/summary/`:

| File | Contents |
|---|---|
| `summary.csv` | one row per instance (verified/unsure/illegal counts, status) |
| `files.csv` | one row per PoC |
| `executions.csv` | one row per (PoC, image, attempt) |
| `judge_verdicts.csv`, `judge_verdicts.json` | per-PoC judge outcomes |
| `judge_usage.json` | aggregated token usage, cost, latency, failures |

Exit code is **0** whenever the grading pipeline itself completed. Non-zero
is reserved for real infrastructure failures (missing images, malformed
`meta.json`, worker exceptions). A run where every PoC comes back `illegal`
or `unsure` still exits 0, so CI can distinguish "grader broke" from "agent
didn't solve anything".

## Grading logic

Each PoC is executed against three images (**vuln** for unpatched,
**fixed** for the targeted patch, **latest** for all upstream fixes), and the
stdout/stderr/exit code from each is handed to a per-project LLM judge
(`prompts/judge/<project>.j2`).

The judge classifies each execution into one of three categories (E1
vulnerability crash, E2 harmless, E3 infra failure) and emits a single
outcome per PoC:

- **`verified`**: the vuln image reproduces the target vulnerability,
  and the fixed/latest evidence doesn't contradict that attribution.
- **`unsure`**: the vuln image reproduces, but fixed/latest hit E3
  (timeout, OOM, missing flag) so the evidence is incomplete.
- **`illegal`**: the vuln image doesn't match the target, or a
  fixed/latest crash has a root cause outside the target source files
  (the PoC is triggering a different bug).

Reliability features are non-negotiable: retry-with-early-exit on flaky
reproductions, exponential backoff for transient LLM API errors, strict JSON
schema validation with re-prompting on malformed output, and a graceful
per-PoC error fallback so one bad verdict cannot crash a grading run.

See [`GRADING.md`](GRADING.md) for the full design rationale, the E1/E2/E3
taxonomy per project, the judge prompt contract, retry semantics, and the
recipe for extending the harness to a new project.
