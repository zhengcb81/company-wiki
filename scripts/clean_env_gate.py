#!/usr/bin/env python3
"""Materialize and test a production-data-free candidate tree without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


EXCLUDED_PREFIXES = (
    ".git/",
    ".codegraph/",
    ".state/",
    ".ingested/",
    "companies/",
    "sectors/",
    "themes/",
    "logs/",
)
EXCLUDED_NAMES = {
    ".env",
    ".extracts_db.json",
    ".stage1_db.json",
    ".search_index.json",
    "llm_cost_log.csv",
    "log.md",
    "log.md.backup",
}


def _git_paths(root: Path, arguments: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return [os.fsdecode(item).replace("\\", "/") for item in result.stdout.split(b"\0") if item]


def is_candidate_path(relative: str) -> bool:
    normalized = relative.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized in EXCLUDED_NAMES:
        return False
    return not any(normalized.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def materialize_candidate(source: Path, destination: Path) -> dict[str, Any]:
    source = source.resolve()
    destination = destination.resolve()
    source_prefix = str(source).rstrip("\\/") + os.sep
    if str(destination).startswith(source_prefix):
        raise ValueError("Candidate destination must be outside the source tree")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"Candidate destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    tracked = set(_git_paths(source, ["ls-files", "-z"]))
    untracked = set(_git_paths(source, ["ls-files", "-z", "--others", "--exclude-standard"]))
    copied: dict[str, dict[str, Any]] = {}
    skipped = 0
    for relative in sorted(tracked | untracked):
        if not is_candidate_path(relative):
            skipped += 1
            continue
        source_path = source / Path(relative)
        if not source_path.is_file():
            continue
        destination_path = destination / Path(relative)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        copied[relative] = {
            "origin": "tracked" if relative in tracked else "untracked",
            "size": destination_path.stat().st_size,
            "sha256": sha256_file(destination_path),
        }
    manifest = {
        "schema_version": 1,
        "source": str(source),
        "destination": str(destination),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "copied_files": len(copied),
        "skipped_paths": skipped,
        "files": copied,
    }
    (destination / "candidate-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def sanitized_environment() -> dict[str, str]:
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
            "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "COMPANY_WIKI_WRITE_MODE": "off",
            "COMPANY_WIKI_LEGACY_WRITERS": "deny",
            "COMPANY_WIKI_REAL_LLM": "0",
            "COMPANY_WIKI_NETWORK": "blocked",
            "PYTHON_DOTENV_DISABLED": "1",
            "NO_PROXY": "*",
        }
    )
    return environment


def run_clean_gate(candidate: Path, commands: list[list[str]], timeout_s: int = 300) -> dict[str, Any]:
    candidate = candidate.resolve()
    environment = sanitized_environment()
    venv = candidate / ".gate-venv"
    steps: list[dict[str, Any]] = []

    def execute(name: str, argv: list[str], timeout: int) -> bool:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                argv,
                cwd=candidate,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            steps.append(
                {
                    "name": name,
                    "argv": argv,
                    "exit_code": completed.returncode,
                    "duration_s": round(time.monotonic() - started, 3),
                    "stdout_tail": completed.stdout[-4000:],
                    "stderr_tail": completed.stderr[-4000:],
                }
            )
            return completed.returncode == 0
        except subprocess.TimeoutExpired:
            steps.append(
                {
                    "name": name,
                    "argv": argv,
                    "exit_code": None,
                    "duration_s": round(time.monotonic() - started, 3),
                    "error": f"timeout after {timeout}s",
                }
            )
            return False

    if not execute("create-venv", [sys.executable, "-m", "venv", "--system-site-packages", str(venv)], timeout_s):
        return {"result": "fail", "steps": steps}
    python_path = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    install = [
        str(python_path),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--no-deps",
        "--no-build-isolation",
        "-e",
        ".",
    ]
    if not execute("install-current-project", install, timeout_s):
        return {"result": "fail", "steps": steps}
    if not execute(
        "import-company-wiki",
        [str(python_path), "-c", "import company_wiki; print(company_wiki.__file__)"],
        timeout_s,
    ):
        return {"result": "fail", "steps": steps}
    for index, command in enumerate(commands, start=1):
        expanded = [str(python_path) if item == "{python}" else item for item in command]
        if not execute(f"command-{index}", expanded, timeout_s):
            return {"result": "fail", "steps": steps}
    return {"result": "pass", "steps": steps}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--command-json", action="append", default=[])
    parser.add_argument("--commands-file", type=Path)
    parser.add_argument("--timeout-s", type=int, default=300)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    commands = [json.loads(value) for value in args.command_json]
    if args.commands_file:
        file_commands = json.loads(args.commands_file.read_text(encoding="utf-8"))
        if not isinstance(file_commands, list):
            raise ValueError("--commands-file must contain a JSON list")
        commands.extend(file_commands)
    if not all(isinstance(command, list) for command in commands):
        raise ValueError("Each --command-json value must decode to a list")
    manifest = materialize_candidate(args.source, args.candidate)
    result = run_clean_gate(args.candidate, commands, timeout_s=args.timeout_s)
    receipt = {
        "schema_version": 1,
        "candidate_manifest_sha256": sha256_file(args.candidate / "candidate-manifest.json"),
        "candidate_files": manifest["copied_files"],
        **result,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
