#!/usr/bin/env python3
"""Standalone test for the LLM judge on pre-existing grading results.

Reads edge_cases.csv from a grading run, reconstructs JudgeInput objects from
on-disk result logs and benchmark metadata, then invokes the judge and writes
output alongside the existing summary.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import judge as judge_module
from judge import JudgeInput, JudgeVerdict


def read_edge_csv(csv_path: Path) -> list[dict[str, str]]:
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    return rows


def extract_source_file(image: str, work_dir: str, rel_path: str) -> str:
    """Extract a source file from a Docker image."""
    full_path = f"{work_dir}/{rel_path}"
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", image, "cat", full_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        return f"[file not found in image: {full_path}]"
    except (subprocess.TimeoutExpired, OSError) as e:
        return f"[extraction error: {e}]"


def find_log(result_dir: Path, image_kind: str, stream: str, rel_path: str) -> str:
    """Find and read the last attempt log for a file."""
    log_dir = result_dir / image_kind / stream
    if not log_dir.is_dir():
        return "<no log directory>"
    candidates = sorted(log_dir.glob(f"{rel_path}.attempt*.log"))
    if not candidates:
        return "<no log file>"
    last = candidates[-1]
    try:
        content = last.read_text(encoding="utf-8", errors="replace")
        return content if content.strip() else "<empty>"
    except OSError:
        return "<read error>"


def find_exit_code_from_log(result_dir: Path, image_kind: str, rel_path: str, edge_row: dict) -> str:
    """Infer exit code from available CSV data or log presence."""
    if image_kind == "latest":
        val = edge_row.get("last_latest_exit_code", "")
        return val if val else "N/A"
    return "N/A"


def build_inputs_from_results(
    *,
    run_dir: Path,
    benchmark_dir: Path,
    edge_rows: list[dict[str, str]],
    extract_sources: bool = True,
) -> list[JudgeInput]:
    """Build JudgeInput objects from pre-existing grading results."""
    inputs: list[JudgeInput] = []

    for row in edge_rows:
        instance_id = row["instance_id"]
        rel_path = row["js_rel_path"]

        instance_dir = run_dir / instance_id
        result_dir = instance_dir / "result"
        if not result_dir.is_dir():
            print(f"  [skip] {instance_id}/{rel_path}: no result dir", flush=True)
            continue

        meta_path = benchmark_dir / instance_id / "meta.json"
        if not meta_path.is_file():
            print(f"  [skip] {instance_id}/{rel_path}: no meta.json", flush=True)
            continue

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        target_source_files = meta.get("target_source_files", [])
        if isinstance(target_source_files, str):
            target_source_files = [target_source_files]
        target_vulnerability_type = meta.get("target_vulnerability_type", "")
        error_type = meta.get("error_type", "")
        command_options = meta.get("command_options", "")
        work_dir = meta.get("work_dir", "/src/v8")
        image_name = meta.get("image_name", f"hwiwonlee/v8.x86_64:{instance_id}")

        source_file_contents: list[dict[str, str]] = []
        if extract_sources and target_source_files:
            for src_path in target_source_files:
                content = extract_source_file(image_name, work_dir, src_path)
                if len(content) > judge_module.MAX_SOURCE_FILE_CHARS:
                    content = judge_module._truncate(content, judge_module.MAX_SOURCE_FILE_CHARS)
                source_file_contents.append({"path": src_path, "content": content})
        else:
            source_file_contents = [
                {"path": p, "content": "[source extraction disabled]"}
                for p in target_source_files
            ]

        poc_path = instance_dir / rel_path
        poc_source = ""
        if poc_path.is_file():
            poc_source = poc_path.read_text(encoding="utf-8", errors="replace")
            if len(poc_source) > judge_module.MAX_POC_CHARS:
                poc_source = judge_module._truncate(poc_source, judge_module.MAX_POC_CHARS)

        vuln_stderr = find_log(result_dir, "vuln", "stderr", rel_path)
        vuln_stdout = find_log(result_dir, "vuln", "stdout", rel_path)
        fixed_stderr = find_log(result_dir, "fixed", "stderr", rel_path)
        fixed_stdout = find_log(result_dir, "fixed", "stdout", rel_path)
        latest_stderr = find_log(result_dir, "latest", "stderr", rel_path)
        latest_stdout = find_log(result_dir, "latest", "stdout", rel_path)

        latest_exit_code = row.get("last_latest_exit_code", "N/A")

        last_fixed_alert = row.get("last_fixed_alert", "")
        last_latest_alert = row.get("last_latest_alert", "")

        inputs.append(JudgeInput(
            project="v8",
            instance_id=instance_id,
            target_source_files=target_source_files,
            target_vulnerability_type=target_vulnerability_type,
            error_type=error_type,
            command_options=command_options,
            poc_rel_path=rel_path,
            poc_source=poc_source,
            source_file_contents=source_file_contents,
            vuln_exit_code="non-zero (crash)",
            vuln_alert_type=row.get("expected_type", error_type),
            vuln_stderr=judge_module._truncate(vuln_stderr, judge_module.MAX_STDERR_CHARS),
            vuln_stdout=judge_module._truncate(vuln_stdout, judge_module.MAX_STDOUT_CHARS),
            fixed_exit_code="non-zero (crash)",
            fixed_alert_type=last_fixed_alert,
            fixed_stderr=judge_module._truncate(fixed_stderr, judge_module.MAX_STDERR_CHARS),
            fixed_stdout=judge_module._truncate(fixed_stdout, judge_module.MAX_STDOUT_CHARS),
            latest_exit_code=latest_exit_code,
            latest_alert_type=last_latest_alert,
            latest_stderr=judge_module._truncate(latest_stderr, judge_module.MAX_STDERR_CHARS),
            latest_stdout=judge_module._truncate(latest_stdout, judge_module.MAX_STDOUT_CHARS),
        ))

    return inputs


def print_verdicts_table(verdicts: list[JudgeVerdict], edge_rows: list[dict[str, str]]) -> None:
    """Print a summary table comparing judge verdicts with original decisions."""
    original_map = {(r["instance_id"], r["js_rel_path"]): r for r in edge_rows}
    width = 130
    print("\n" + "=" * width, flush=True)
    print(
        f"{'Instance':<12} {'PoC':<40} {'Tgt':>4} {'Vul':>4} {'Mit':>4}  {'Verdict':<22} {'Orig':<5} {'OK'}",
        flush=True,
    )
    print("-" * width, flush=True)

    agreements = 0
    total = 0
    for v in verdicts:
        orig = original_map.get((v.instance_id, v.poc_rel_path), {})
        orig_accepted = orig.get("accepted", "?")
        judge_would_accept = v.verdict == "verified"
        ok = "YES" if (judge_would_accept and orig_accepted == "yes") or (not judge_would_accept and orig_accepted == "no") else "NO"
        if ok == "YES":
            agreements += 1
        total += 1
        poc_short = v.poc_rel_path[-39:] if len(v.poc_rel_path) > 39 else v.poc_rel_path
        tgt_str = "T" if v.target_aligned else "F"
        vul_str = "T" if v.vuln_matched else "F"
        mit_str = "T" if v.latest_mitigated else "F"
        print(
            f"{v.instance_id:<12} {poc_short:<40} {tgt_str:>4} {vul_str:>4} {mit_str:>4}  {v.verdict:<22} {orig_accepted:<5} {ok}",
            flush=True,
        )

    print("-" * width, flush=True)
    print(f"Agreement with ground truth: {agreements}/{total} ({agreements/total*100:.0f}%)" if total else "No verdicts", flush=True)
    print("=" * width, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test LLM judge on pre-existing edge case results")
    parser.add_argument("--run-dir", required=True, type=Path,
                        help="Path to trajectory run directory (e.g., trajectories/v8/claude_opus-4.6_source-files)")
    parser.add_argument("--benchmark-dir", type=Path, default=None,
                        help="Path to benchmark ground truth (default: ROOT/v8/)")
    parser.add_argument("--model", default=None,
                        help="LLM model to use (default: auto-detect from env)")
    parser.add_argument("--reasoning-effort", default=judge_module.DEFAULT_REASONING_EFFORT,
                        help=f"Reasoning effort (default: {judge_module.DEFAULT_REASONING_EFFORT})")
    parser.add_argument("--workers", type=int, default=judge_module.DEFAULT_JUDGE_WORKERS,
                        help="Parallel workers for LLM calls")
    parser.add_argument("--samples", type=int, default=judge_module.DEFAULT_JUDGE_SAMPLES,
                        help=f"Majority-vote samples per case (default: {judge_module.DEFAULT_JUDGE_SAMPLES})")
    parser.add_argument("--no-source-extract", action="store_true",
                        help="Skip extracting source files from Docker images")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Output directory for judge results (default: run-dir/summary/)")
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    benchmark_dir = (args.benchmark_dir or ROOT / "v8").expanduser().resolve()

    if not run_dir.is_dir():
        print(f"ERROR: run directory not found: {run_dir}", file=sys.stderr)
        return 1
    if not benchmark_dir.is_dir():
        print(f"ERROR: benchmark directory not found: {benchmark_dir}", file=sys.stderr)
        return 1

    model = args.model or judge_module.get_default_model()
    if not judge_module.check_api_key(model):
        judge_module.warn_missing_api_key(model)
        return 1

    edge_csv = run_dir / "summary" / "edge_cases.csv"
    if not edge_csv.is_file():
        print(f"ERROR: edge_cases.csv not found: {edge_csv}", file=sys.stderr)
        return 1

    print(f"Reading edge cases from: {edge_csv}", flush=True)
    edge_rows = read_edge_csv(edge_csv)
    print(f"Found {len(edge_rows)} edge-candidate PoC rows", flush=True)

    print(f"\nBuilding judge inputs (source extraction: {'disabled' if args.no_source_extract else 'enabled'})...", flush=True)
    inputs = build_inputs_from_results(
        run_dir=run_dir,
        benchmark_dir=benchmark_dir,
        edge_rows=edge_rows,
        extract_sources=not args.no_source_extract,
    )
    print(f"Built {len(inputs)} judge inputs", flush=True)

    if not inputs:
        print("No inputs to judge. Done.", flush=True)
        return 0

    print(f"\nRunning judge with model={model}, reasoning_effort={args.reasoning_effort}, workers={args.workers}, samples={args.samples}", flush=True)
    start = time.monotonic()
    verdicts = judge_module.judge_edge_cases(
        inputs,
        model=model,
        reasoning_effort=args.reasoning_effort,
        workers=args.workers,
        samples=args.samples,
    )
    elapsed = time.monotonic() - start
    print(f"\nJudge completed in {elapsed:.1f}s", flush=True)

    print_verdicts_table(verdicts, edge_rows)

    out_dir = args.out_dir or (run_dir / "summary")
    csv_path = judge_module.write_judge_csv(verdicts, out_dir)
    json_path = judge_module.write_judge_details_json(verdicts, out_dir)
    usage_path = judge_module.write_judge_usage(verdicts, out_dir)
    print(f"\nWrote: {csv_path}", flush=True)
    print(f"Wrote: {json_path}", flush=True)
    print(f"Wrote: {usage_path}", flush=True)

    verified = sum(1 for v in verdicts if v.verdict == "verified")
    misaligned = sum(1 for v in verdicts if v.verdict in ("misaligned", "mitigated_but_misaligned"))
    not_mitigated = sum(1 for v in verdicts if v.verdict == "not_mitigated")
    errors = sum(1 for v in verdicts if v.verdict == "error")
    total_cost = sum(v.cost_usd for v in verdicts)
    total_tokens = sum(v.total_tokens for v in verdicts)
    print(f"\nSummary: {verified} verified, {misaligned} misaligned, {not_mitigated} not_mitigated, {errors} errors", flush=True)
    print(f"Usage: {total_tokens:,} tokens, ${total_cost:.4f} USD", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
