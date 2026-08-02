#!/usr/bin/env python3
"""Machine-enforced Work Unit boundary checks and candidate receipts."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable


PRODUCTION_DATA_DIRS = ("companies", "sectors", "themes", ".state")
PRODUCTION_DATA_FILES = (
    "log.md",
    "index.md",
    "config.yaml",
    "companies.yaml",
    "graph.yaml",
)
CONTENT_HASH_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".csv", ".db"}
SMALL_FILE_HASH_LIMIT = 1024 * 1024
LARGE_STRUCTURED_SAMPLE_SIZE = 64 * 1024
UNTRACKED_RUNTIME_PREFIXES = (".codegraph/",)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sampled_sha256(path: Path, sample_size: int = LARGE_STRUCTURED_SAMPLE_SIZE) -> str:
    """Hash file size plus first/last samples without reading a large file fully."""
    size = path.stat().st_size
    digest = hashlib.sha256()
    digest.update(str(size).encode("ascii"))
    with path.open("rb") as handle:
        digest.update(handle.read(sample_size))
        if size > sample_size:
            handle.seek(max(0, size - sample_size))
            digest.update(handle.read(sample_size))
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _git_paths(root: Path, arguments: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return [os.fsdecode(item).replace("\\", "/") for item in result.stdout.split(b"\0") if item]


def production_data_snapshot(root: Path) -> dict[str, Any]:
    """Fingerprint tracked and ignored production data without reading large PDFs.

    Small and structured files receive a full SHA-256, so a same-size rewrite
    with a restored timestamp is still detected.  Large binaries are guarded
    by path, size, and nanosecond mtime; the full recovery baseline remains the
    authoritative byte-level backup.
    """
    root = root.resolve()
    candidates: set[Path] = set()
    for name in PRODUCTION_DATA_DIRS:
        directory = root / name
        if directory.is_dir():
            candidates.update(path for path in directory.rglob("*") if path.is_file())
    for name in PRODUCTION_DATA_FILES:
        path = root / name
        if path.is_file():
            candidates.add(path)

    entries: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    for path in sorted(candidates, key=lambda item: item.as_posix()):
        try:
            stat = path.stat()
            relative = path.relative_to(root).as_posix()
            entry: dict[str, Any] = {
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
            parts = Path(relative).parts
            content_critical = (
                relative in PRODUCTION_DATA_FILES
                or (parts and parts[0] == ".state")
                or "wiki" in parts
                or (parts and parts[0] == "themes" and "raw" not in parts)
            )
            if content_critical and stat.st_size <= SMALL_FILE_HASH_LIMIT:
                entry["sha256"] = sha256_file(path)
            elif content_critical and path.suffix.casefold() in CONTENT_HASH_SUFFIXES:
                entry["sampled_sha256"] = sampled_sha256(path)
            entries[relative] = entry
            total_bytes += stat.st_size
        except (FileNotFoundError, PermissionError, OSError) as exc:
            relative = path.relative_to(root).as_posix()
            entries[relative] = {"error": type(exc).__name__}

    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "digest": hashlib.sha256(canonical).hexdigest(),
        "files": len(entries),
        "bytes": total_bytes,
        "hash_policy": (
            f"wiki/state/root control files: full size<={SMALL_FILE_HASH_LIMIT}, "
            f"otherwise {LARGE_STRUCTURED_SAMPLE_SIZE}-byte head/tail samples; "
            "raw binaries/content: path+size+mtime_ns"
        ),
    }


def workspace_snapshot(root: Path) -> dict[str, Any]:
    """Hash every tracked and non-ignored untracked file, including deleted markers."""
    root = root.resolve()
    tracked = set(_git_paths(root, ["ls-files", "-z"]))
    untracked = {
        path
        for path in _git_paths(root, ["ls-files", "-z", "--others", "--exclude-standard"])
        if not path.startswith(UNTRACKED_RUNTIME_PREFIXES)
    }
    entries: dict[str, dict[str, Any]] = {}
    for relative in sorted(tracked | untracked):
        path = root / Path(relative)
        origin = "tracked" if relative in tracked else "untracked"
        if not path.exists():
            entries[relative] = {"origin": origin, "state": "deleted", "sha256": None, "size": None}
        elif path.is_file():
            stat = path.stat()
            entries[relative] = {
                "origin": origin,
                "state": "file",
                "sha256": sha256_file(path),
                "size": stat.st_size,
            }
        else:
            entries[relative] = {"origin": origin, "state": "non_file", "sha256": None, "size": None}
    production_data = production_data_snapshot(root)
    index_patch = subprocess.check_output(
        ["git", "diff", "--cached", "--binary", "--no-ext-diff"], cwd=root
    )
    index_digest = hashlib.sha256(index_patch).hexdigest()
    canonical = json.dumps(
        {
            "entries": entries,
            "production_data_digest": production_data["digest"],
            "git_index_digest": index_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "schema_version": 1,
        "root": str(root),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "digest": hashlib.sha256(canonical).hexdigest(),
        "entries": entries,
        "production_data": production_data,
        "git_index_digest": index_digest,
    }


def verify_lock(root: Path, lock_path: Path) -> list[str]:
    lock = load_json(lock_path)
    violations: list[str] = []
    if lock.get("algorithm") != "sha256":
        violations.append("acceptance lock algorithm must be sha256")
    files = lock.get("files")
    if not isinstance(files, dict) or not files:
        return violations + ["acceptance lock has no files"]
    for relative, expected in sorted(files.items()):
        path = root / relative
        if not path.is_file():
            violations.append(f"locked file missing: {relative}")
            continue
        actual = sha256_file(path)
        if actual.lower() != str(expected).lower():
            violations.append(f"locked file hash mismatch: {relative}")
    return violations


def _matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def boundary_violations(
    baseline: dict[str, Any],
    current: dict[str, Any],
    allowed_paths: list[str],
    reviewer_owned_paths: list[str],
) -> list[str]:
    violations: list[str] = []
    baseline_entries = baseline.get("entries", {})
    current_entries = current.get("entries", {})
    if baseline.get("git_index_digest") != current.get("git_index_digest"):
        violations.append("git index changed outside Work Unit boundary")
    for path in sorted(set(baseline_entries) | set(current_entries)):
        if baseline_entries.get(path) == current_entries.get(path):
            continue
        if _matches(path, reviewer_owned_paths):
            violations.append(f"reviewer-owned path changed: {path}")
        elif not _matches(path, allowed_paths):
            violations.append(f"path outside Work Unit allowlist: {path}")
    return violations


def _sanitized_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().endswith("_API_KEY")
        and key.upper() not in {
            "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "MINIMAX_API_KEY",
            "MIMO_API_KEY", "TAVILY_API_KEY"
        }
    }
    environment.update(
        {
            "COMPANY_WIKI_WRITE_MODE": "off",
            "COMPANY_WIKI_LEGACY_WRITERS": "deny",
            "COMPANY_WIKI_REAL_LLM": "0",
            "COMPANY_WIKI_NETWORK": "blocked",
            "PYTHON_DOTENV_DISABLED": "1",
            "NO_PROXY": "*",
        }
    )
    return environment


def run_commands(root: Path, commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
        name = str(command.get("name", "unnamed"))
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            results.append({"name": name, "exit_code": None, "error": "argv must be a non-empty string list"})
            continue
        timeout = int(command.get("timeout_s", 120))
        started = time.monotonic()
        try:
            completed = subprocess.run(
                argv,
                cwd=root,
                env=_sanitized_environment(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            results.append(
                {
                    "name": name,
                    "argv": argv,
                    "exit_code": completed.returncode,
                    "duration_s": round(time.monotonic() - started, 3),
                    "stdout_tail": completed.stdout[-4000:],
                    "stderr_tail": completed.stderr[-4000:],
                }
            )
        except subprocess.TimeoutExpired as exc:
            results.append(
                {
                    "name": name,
                    "argv": argv,
                    "exit_code": None,
                    "duration_s": round(time.monotonic() - started, 3),
                    "error": f"timeout after {timeout}s",
                    "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
                    "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
                }
            )
    return results


def evaluate_work_unit(root: Path, work_unit_path: Path, receipt_path: Path) -> dict[str, Any]:
    root = root.resolve()
    work_unit = load_json(work_unit_path)
    acceptance_path = root / work_unit.get("acceptance", "control/acceptance.json")
    acceptance = load_json(acceptance_path)
    lock_path = root / work_unit.get("acceptance_lock", "control/acceptance.lock.json")
    baseline_path = root / work_unit["baseline_snapshot"]
    baseline = load_json(baseline_path)
    current = workspace_snapshot(root)
    violations = verify_lock(root, lock_path)
    violations.extend(
        boundary_violations(
            baseline,
            current,
            list(work_unit.get("allowed_paths", [])),
            list(acceptance.get("reviewer_owned_paths", [])),
        )
    )
    baseline_production = baseline.get("production_data", {}).get("digest")
    current_production = current.get("production_data", {}).get("digest")
    if not baseline_production:
        violations.append("baseline missing production-data fingerprint")
    elif baseline_production != current_production:
        violations.append("production data changed since Work Unit baseline")
    commands = run_commands(root, list(work_unit.get("commands", []))) if not violations else []
    for result in commands:
        if result.get("exit_code") != 0:
            violations.append(f"command failed: {result.get('name')}")

    snapshot_after = workspace_snapshot(root)
    if snapshot_after["digest"] != current["digest"]:
        violations.append("workspace changed while Gate commands were running")

    result = "pass" if not violations else "fail"
    receipt = {
        "schema_version": 1,
        "work_unit": work_unit.get("id"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "head": snapshot_after["head"],
        "workspace_digest": snapshot_after["digest"],
        "baseline_digest": baseline.get("digest"),
        "production_data": snapshot_after.get("production_data"),
        "status": "candidate" if result == "pass" else "rejected",
        "result": result,
        "violations": violations,
        "commands": commands,
        "review": {"status": "pending", "reviewer": None},
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    lock_parser = subparsers.add_parser("verify-lock")
    lock_parser.add_argument("--root", type=Path, default=Path.cwd())
    lock_parser.add_argument("--lock", type=Path, default=Path("control/acceptance.lock.json"))

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--root", type=Path, default=Path.cwd())
    snapshot_parser.add_argument("--output", type=Path, required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--root", type=Path, default=Path.cwd())
    run_parser.add_argument("--work-unit", type=Path, required=True)
    run_parser.add_argument("--receipt", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    if args.command == "verify-lock":
        lock_path = args.lock if args.lock.is_absolute() else root / args.lock
        violations = verify_lock(root, lock_path)
        print(json.dumps({"result": "pass" if not violations else "fail", "violations": violations}, indent=2))
        return 0 if not violations else 2
    if args.command == "snapshot":
        snapshot = workspace_snapshot(root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"digest": snapshot["digest"], "files": len(snapshot["entries"])}, indent=2))
        return 0
    if args.command == "run":
        receipt = evaluate_work_unit(root, args.work_unit, args.receipt)
        print(json.dumps({"result": receipt["result"], "violations": receipt["violations"]}, indent=2))
        return 0 if receipt["result"] == "pass" else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
