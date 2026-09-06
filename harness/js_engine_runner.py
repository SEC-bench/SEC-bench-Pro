#!/usr/bin/env python3
"""Run one JavaScript engine process and persist authoritative launch state.

The grader executes this helper as the container's foreground process.  Python's
Popen reports exec failures to the parent, so an engine that deliberately exits
124-127 can be distinguished from a binary that never started.  A small status
file also distinguishes a real exit 124 from this helper's timeout exit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
from pathlib import Path

MAX_INPUT_FILES = 1_000
MAX_INPUT_DIRECTORIES = 1_000
MAX_INPUT_BYTES = 128 * 1024 * 1024
MAX_INPUT_DEPTH = 64
SKIP_INPUT_DIRECTORIES = {"result", "results", "similarity", "summary"}


class InputIntegrityError(ValueError):
    """The selected PoC no longer matches the grader's accepted snapshot."""


def _write_status(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _normalise_returncode(returncode: int) -> int:
    return returncode if returncode >= 0 else 128 + (-returncode)


def _prepare_status_path(status_file: Path) -> None:
    if not status_file.is_absolute():
        raise ValueError("status file must use an absolute path")
    state_dir = status_file.parent
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    state_dir.chmod(0o700)
    status_file.unlink(missing_ok=True)


def _open_absolute_directory(path: Path, flags: int) -> int:
    """Open every absolute-path component without following a symlink."""
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError(f"input root is not an absolute safe path: {path}")

    descriptor = -1
    try:
        descriptor = os.open("/", flags)
        for part in path.parts[1:]:
            if part in ("", "."):
                continue
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise ValueError(f"input root is not a safe directory: {path}: {exc}") from exc


def _copy_input_tree(
    source_root: Path,
    destination_root: Path,
    required_relative_path: str | None = None,
) -> str:
    """Copy regular audit inputs and return a canonical staged-tree digest.

    Production execution supplies ``required_relative_path`` so only the
    selected PoC is executable evidence.  Sibling files are deliberately not
    staged: otherwise a small visible PoC could delegate its behavior to an
    unvalidated, judge-invisible helper.
    """
    if not source_root.is_absolute():
        raise ValueError(f"input root is not a directory: {source_root}")
    destination_root.mkdir(mode=0o755, parents=True, exist_ok=False)
    files = 0
    directories = 1
    total_bytes = 0
    records: list[tuple[bytes, bytes, int, bytes]] = []
    required_parts: tuple[str, ...] | None = None
    if required_relative_path is not None:
        required = Path(required_relative_path)
        if (
            required.is_absolute()
            or not required.parts
            or any(part in ("", ".", "..") for part in required.parts)
        ):
            raise InputIntegrityError(
                "required input is not a safe relative path: "
                f"{required_relative_path}"
            )
        required_parts = tuple(required.parts)

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_NOFOLLOW
    root_descriptor = _open_absolute_directory(source_root, directory_flags)

    def copy_directory(
        source_descriptor: int,
        destination: Path,
        relative_parts: tuple[str, ...],
        depth: int,
    ) -> None:
        nonlocal files, directories, total_bytes
        if depth > MAX_INPUT_DEPTH:
            raise ValueError("audit input tree exceeds the grader depth limit")
        destination.chmod(0o755)
        try:
            entries = os.scandir(source_descriptor)
        except OSError as exc:
            raise ValueError(f"could not enumerate audit input directory: {exc}") from exc
        with entries:
            for entry in entries:
                name = entry.name
                entry_parts = (*relative_parts, name)
                try:
                    source_stat = os.stat(
                        name, dir_fd=source_descriptor, follow_symlinks=False
                    )
                except OSError:
                    continue
                if stat.S_ISDIR(source_stat.st_mode):
                    if required_parts is not None and required_parts[: len(entry_parts)] != entry_parts:
                        continue
                    if name in SKIP_INPUT_DIRECTORIES:
                        continue
                    try:
                        child_descriptor = os.open(
                            name, directory_flags, dir_fd=source_descriptor
                        )
                    except OSError:
                        continue
                    try:
                        if not stat.S_ISDIR(os.fstat(child_descriptor).st_mode):
                            continue
                        directories += 1
                        if directories > MAX_INPUT_DIRECTORIES:
                            raise ValueError(
                                "audit input tree exceeds the grader directory limit"
                            )
                        child_destination = destination / name
                        child_destination.mkdir(mode=0o755, exist_ok=False)
                        child_parts = entry_parts
                        records.append((b"d", os.fsencode("/".join(child_parts)), 0, b""))
                        copy_directory(
                            child_descriptor,
                            child_destination,
                            child_parts,
                            depth + 1,
                        )
                    finally:
                        os.close(child_descriptor)
                    continue
                if not stat.S_ISREG(source_stat.st_mode):
                    continue
                if required_parts is not None and entry_parts != required_parts:
                    continue

                try:
                    descriptor = os.open(
                        name, file_flags, dir_fd=source_descriptor
                    )
                except OSError:
                    continue
                try:
                    source_stat = os.fstat(descriptor)
                    if not stat.S_ISREG(source_stat.st_mode):
                        continue
                    files += 1
                    total_bytes += source_stat.st_size
                    if files > MAX_INPUT_FILES or total_bytes > MAX_INPUT_BYTES:
                        raise ValueError("audit input tree exceeds the grader copy limit")
                    target = destination / name
                    bytes_read = 0
                    file_digest = hashlib.sha256()
                    with target.open("xb") as target_file:
                        while chunk := os.read(descriptor, 1024 * 1024):
                            bytes_read += len(chunk)
                            observed_total = total_bytes - source_stat.st_size + bytes_read
                            if observed_total > MAX_INPUT_BYTES:
                                raise ValueError(
                                    "audit input tree exceeds the grader copy limit"
                                )
                            target_file.write(chunk)
                            file_digest.update(chunk)
                    total_bytes = total_bytes - source_stat.st_size + bytes_read
                    target.chmod(0o444)
                    records.append(
                        (
                            b"f",
                            os.fsencode("/".join(entry_parts)),
                            bytes_read,
                            file_digest.digest(),
                        )
                    )
                finally:
                    os.close(descriptor)

    try:
        if not stat.S_ISDIR(os.fstat(root_descriptor).st_mode):
            raise ValueError(f"input root is not a directory: {source_root}")
        copy_directory(root_descriptor, destination_root, (), 0)
    finally:
        os.close(root_descriptor)

    digest = hashlib.sha256()
    digest.update(b"SEC-bench staged input tree v1\0")
    for kind, relative_path, size, content_digest in sorted(
        records, key=lambda record: (record[1], record[0])
    ):
        digest.update(kind)
        digest.update(len(relative_path).to_bytes(8, "big"))
        digest.update(relative_path)
        digest.update(size.to_bytes(8, "big"))
        digest.update(content_digest)
    return digest.hexdigest()


def _verify_input_tree_digest(observed_sha256: str, expected_sha256: str) -> None:
    if not expected_sha256:
        return
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("required input tree SHA-256 is malformed")
    if observed_sha256 != expected_sha256:
        raise InputIntegrityError(
            "staged input tree does not match the vulnerable execution snapshot: "
            f"expected={expected_sha256}, observed={observed_sha256}"
        )


def _verify_required_input(
    staged_root: Path, relative_path: str, expected_sha256: str
) -> str:
    """Require the selected PoC to survive secure staging as a regular file."""
    relative = Path(relative_path)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        raise InputIntegrityError(
            f"required input is not a safe relative path: {relative_path}"
        )
    candidate = staged_root / relative
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("required input SHA-256 is malformed")
    descriptor = -1
    try:
        descriptor = os.open(candidate, os.O_RDONLY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise InputIntegrityError(
            f"required input was not copied into the trusted staging tree: "
            f"{relative_path}: {exc}"
        ) from exc
    try:
        if not stat.S_ISREG(metadata.st_mode):
            raise InputIntegrityError(
                f"required staged input is not a regular file: {relative_path}"
            )
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        observed_sha256 = digest.hexdigest()
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if observed_sha256 != expected_sha256:
        raise InputIntegrityError(
            "required staged input does not match the accepted PoC snapshot: "
            f"expected={expected_sha256}, observed={observed_sha256}"
        )
    return observed_sha256


def _relocate_execution_input(
    trusted_input_root: Path,
    required_input: str,
    execution_root: Path,
    execution_relative_path: str,
) -> Path:
    """Expose the verified inode at the submitted relative path.

    Keep the grader's fixed internal filename outside ``execution_root``.  A
    submitted path is otherwise allowed to start with that same filename (for
    example ``secb-selected-poc.js/nested/poc.js``), and placing both in one
    tree would turn the internal file into a parent-path collision.
    """
    relative = Path(execution_relative_path)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        raise InputIntegrityError(
            "execution input is not a safe relative path: "
            f"{execution_relative_path}"
        )
    source = trusted_input_root / required_input
    execution_root.mkdir(mode=0o755, parents=True, exist_ok=False)
    target = execution_root / relative
    if target.parent != execution_root:
        target.parent.mkdir(mode=0o755, parents=True, exist_ok=False)
    os.link(source, target, follow_symlinks=False)
    source.unlink()
    target.chmod(0o444)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--status-file", required=True, type=Path)
    parser.add_argument("--timeout-sec", required=True, type=float)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--staged-input-root", required=True, type=Path)
    parser.add_argument("--required-input", required=True)
    parser.add_argument("--required-input-sha256", required=True)
    parser.add_argument("--required-input-tree-sha256", default="")
    parser.add_argument("--execution-input-relative-path", required=True)
    parser.add_argument("--run-uid", type=int, default=65534)
    parser.add_argument("--run-gid", type=int, default=65534)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("an engine command is required after --")

    input_tree_sha256 = ""
    try:
        _prepare_status_path(args.status_file)
        trusted_input_root = (
            args.staged_input_root.parent / ".secb-trusted-selected-input"
        )
        try:
            input_tree_sha256 = _copy_input_tree(
                args.input_root,
                trusted_input_root,
                args.required_input,
            )
        except (OSError, ValueError) as exc:
            raise InputIntegrityError(
                f"could not stage the accepted input tree: {exc}"
            ) from exc
        _verify_input_tree_digest(
            input_tree_sha256, args.required_input_tree_sha256
        )
        input_sha256 = _verify_required_input(
            trusted_input_root,
            args.required_input,
            args.required_input_sha256,
        )
        execution_input = _relocate_execution_input(
            trusted_input_root,
            args.required_input,
            args.staged_input_root,
            args.execution_input_relative_path,
        )
        private_input = str(args.input_root / args.required_input)
        command = [
            str(execution_input)
            if item == private_input
            else item
            for item in command
        ]
        os.chdir(args.cwd)
        engine_environment = os.environ.copy()
        engine_environment.update(
            {
                "HOME": "/tmp",
                "TMPDIR": "/tmp",
                "XDG_CACHE_HOME": "/tmp/.cache",
            }
        )
        process = subprocess.Popen(
            command,
            start_new_session=True,
            user=args.run_uid,
            group=args.run_gid,
            extra_groups=(),
            env=engine_environment,
        )
    except (OSError, ValueError) as exc:
        _write_status(
            args.status_file,
            {
                "engine_started": False,
                "timed_out": False,
                "exit_code": None,
                "raw_returncode": None,
                "infrastructure_error": f"could not launch engine: {exc}",
                "input_integrity_error": isinstance(exc, InputIntegrityError),
                "input_tree_sha256": input_tree_sha256,
            },
        )
        return 126

    timed_out = False
    try:
        raw_returncode = process.wait(timeout=args.timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        raw_returncode = process.wait()

    # Do not let descendants outlive the engine and race the trusted status
    # write.  The engine runs as an unprivileged uid and cannot enter the
    # root-owned 0700 status directory.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    exit_code = _normalise_returncode(raw_returncode)
    _write_status(
        args.status_file,
        {
            "engine_started": True,
            "timed_out": timed_out,
            "exit_code": exit_code,
            "raw_returncode": raw_returncode,
            "infrastructure_error": "",
            "input_integrity_error": False,
            "input_sha256": input_sha256,
            "input_tree_sha256": input_tree_sha256,
        },
    )
    return 124 if timed_out else exit_code


if __name__ == "__main__":
    sys.exit(main())
