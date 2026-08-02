#!/usr/bin/env python3
"""Redacted secret audit for the working tree, local .env, and Git history."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


MAX_TEXT_BLOB_BYTES = 5 * 1024 * 1024
ASSIGNMENT_PATTERN = re.compile(
    r"\b([A-Z][A-Z0-9_]*(?:API_KEY|ACCESS_TOKEN|SECRET_KEY))"
    r"\b\s*[:=]\s*[\"']?([^\s\"'#]{8,})"
)
YAML_SECRET_PATTERN = re.compile(
    r"(?i)\b(api_key|tavily_api_key|deepseek_api_key|openai_api_key|"
    r"minimax_api_key|mimo_api_key)"
    r"\s*:\s*[\"']?([A-Za-z0-9_-]{20,})"
)
PREFIX_PATTERN = re.compile(
    r"\b(sk-[A-Za-z0-9_-]{16,}|tp-[A-Za-z0-9_-]{16,}|tvly-[A-Za-z0-9_-]{16,})\b"
)
PERMISSION_SECRET_PATTERN = re.compile(
    r"\b[A-Z][A-Z0-9_]*(?:API_KEY|ACCESS_TOKEN|SECRET_KEY)="
)
PLACEHOLDER_MARKERS = (
    "your-",
    "your_",
    "example",
    "placeholder",
    "changeme",
    "replace-me",
    "replace_me",
    "sk-test",
    "test-key",
    "test_",
    "test-",
    "env-",
    "workflow-",
    "dummy",
    "xxxx",
    "${",
)


def _git(root: Path, arguments: list[str], input_bytes: bytes | None = None) -> bytes:
    return subprocess.check_output(["git", *arguments], cwd=root, input=input_bytes)


def _classification(value: str) -> str:
    lowered = value.casefold()
    return "placeholder" if any(marker in lowered for marker in PLACEHOLDER_MARKERS) else "active_candidate"


def _finding(path: str, source: str, line: int, kind: str, value: str) -> dict[str, Any]:
    return {
        "path": path,
        "source": source,
        "line": line,
        "kind": kind,
        "classification": _classification(value),
        "length": len(value),
        "fingerprint": hashlib.sha256(value.encode("utf-8")).hexdigest()[:16],
    }


def scan_text(text: str, path: str, source: str) -> list[dict[str, Any]]:
    """Find likely credentials without ever returning their values."""
    findings: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in ASSIGNMENT_PATTERN.finditer(line):
            key, value = match.groups()
            fingerprint = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
            marker = (line_number, fingerprint)
            if marker not in seen:
                findings.append(_finding(path, source, line_number, key.upper(), value))
                seen.add(marker)
        for match in YAML_SECRET_PATTERN.finditer(line):
            key, value = match.groups()
            fingerprint = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
            marker = (line_number, fingerprint)
            if marker not in seen:
                findings.append(_finding(path, source, line_number, key.upper(), value))
                seen.add(marker)
        for match in PREFIX_PATTERN.finditer(line):
            value = match.group(1)
            fingerprint = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
            marker = (line_number, fingerprint)
            if marker not in seen:
                if value.casefold().startswith("tvly-"):
                    kind = "TAVILY_TOKEN"
                elif value.casefold().startswith("tp-"):
                    kind = "MIMO_TOKEN_PLAN_TOKEN"
                else:
                    kind = "SK_TOKEN"
                findings.append(_finding(path, source, line_number, kind, value))
                seen.add(marker)
    return findings


def _text_from_bytes(content: bytes) -> str | None:
    if b"\0" in content[:8192]:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _tracked_findings(root: Path) -> list[dict[str, Any]]:
    output = _git(root, ["ls-files", "-z"])
    findings: list[dict[str, Any]] = []
    for raw_path in output.split(b"\0"):
        if not raw_path:
            continue
        relative = os.fsdecode(raw_path).replace("\\", "/")
        path = root / Path(relative)
        if not path.is_file() or path.stat().st_size > MAX_TEXT_BLOB_BYTES:
            continue
        text = _text_from_bytes(path.read_bytes())
        if text is not None:
            findings.extend(scan_text(text, relative, "tracked_worktree"))
    return findings


def _history_objects(root: Path) -> tuple[dict[str, set[str]], dict[str, int]]:
    raw = _git(root, ["rev-list", "--objects", "--all"])
    paths: dict[str, set[str]] = collections.defaultdict(set)
    oids: list[str] = []
    for line in raw.decode("utf-8", "surrogateescape").splitlines():
        oid, _, path = line.partition(" ")
        oids.append(oid)
        if path:
            paths[oid].add(path.replace("\\", "/"))
    check = _git(
        root,
        ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        ("\n".join(oids) + "\n").encode("ascii"),
    )
    blobs: dict[str, int] = {}
    for line in check.decode("ascii", "replace").splitlines():
        fields = line.split(" ")
        if len(fields) == 3 and fields[1] == "blob":
            size = int(fields[2])
            if size <= MAX_TEXT_BLOB_BYTES:
                blobs[fields[0]] = size
    return paths, blobs


def _read_blobs(root: Path, oids: Iterable[str]) -> Iterable[tuple[str, bytes]]:
    process = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    try:
        for oid in sorted(oids):
            process.stdin.write((oid + "\n").encode("ascii"))
            process.stdin.flush()
            header = process.stdout.readline().decode("ascii", "replace").strip().split(" ")
            if len(header) != 3 or header[1] != "blob":
                raise ValueError(f"Unable to read Git object {oid}: {' '.join(header)}")
            size = int(header[2])
            content = process.stdout.read(size)
            terminator = process.stdout.read(1)
            if len(content) != size or terminator != b"\n":
                raise ValueError(f"Truncated Git object response: {oid}")
            yield oid, content
    finally:
        process.stdin.close()
        process.wait(timeout=30)
    if process.returncode != 0:
        stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
        raise RuntimeError(f"git cat-file failed: {stderr}")


def _history_findings(root: Path) -> tuple[list[dict[str, Any]], int]:
    paths, blobs = _history_objects(root)
    findings: list[dict[str, Any]] = []
    scanned = 0
    for oid, content in _read_blobs(root, blobs):
        text = _text_from_bytes(content)
        if text is None:
            continue
        scanned += 1
        display_paths = sorted(paths.get(oid) or {"<unknown>"})
        blob_findings = scan_text(text, display_paths[0], "git_history")
        for finding in blob_findings:
            finding["blob_oid"] = oid
            finding["known_paths"] = display_paths[:5]
        findings.extend(blob_findings)
    return findings, scanned


def _audit_digest(audit: dict[str, Any]) -> str:
    payload = {key: value for key, value in audit.items() if key != "audit_sha256"}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_audit(root: Path, local_env_path: Path | None = Path(".env")) -> dict[str, Any]:
    root = root.resolve()
    head = _git(root, ["rev-parse", "HEAD"]).decode("ascii").strip()
    tracked = _tracked_findings(root)
    history, scanned_history_blobs = _history_findings(root)
    local: list[dict[str, Any]] = []
    if local_env_path is not None:
        local_path = local_env_path if local_env_path.is_absolute() else root / local_env_path
        if local_path.is_file():
            text = local_path.read_text(encoding="utf-8-sig", errors="replace")
            local = scan_text(text, ".env", "ignored_local_env")

    tracked_active = sum(item["classification"] == "active_candidate" for item in tracked)
    history_active = sum(item["classification"] == "active_candidate" for item in history)
    local_active = sum(item["classification"] == "active_candidate" for item in local)
    any_active = tracked_active + history_active + local_active > 0
    remote_refs = sorted(
        ref
        for ref in _git(root, ["for-each-ref", "--format=%(refname:short)", "refs/remotes/"])
        .decode("utf-8", "replace")
        .splitlines()
        if ref and not ref.endswith("/HEAD")
    )
    if history_active and remote_refs:
        history_decision = "required_authorization_pending"
    elif history_active:
        history_decision = "required_if_blob_was_published"
    else:
        history_decision = "not_indicated"
    decision = {
        "current_repo_remediation": "required" if tracked_active else "not_indicated",
        "provider_rotation": "external_action_pending" if any_active else "not_indicated",
        "history_rewrite": history_decision,
        "remote_refs_support_publication": remote_refs,
        "secret_values_recorded": False,
    }
    result = "fail" if tracked_active else ("blocked_external" if any_active else "pass")
    audit: dict[str, Any] = {
        "schema_version": 1,
        "head": head,
        "result": result,
        "policy": {
            "redacted": True,
            "max_history_blob_bytes": MAX_TEXT_BLOB_BYTES,
            "provider_rotation_must_be_verified_externally": True,
        },
        "summary": {
            "tracked_findings": len(tracked),
            "tracked_active_candidates": tracked_active,
            "history_findings": len(history),
            "history_active_candidates": history_active,
            "history_text_blobs_scanned": scanned_history_blobs,
            "local_env_findings": len(local),
            "local_env_active_candidates": local_active,
        },
        "decision": decision,
        "findings": {
            "tracked_worktree": tracked,
            "git_history": history,
            "ignored_local_env": local,
        },
    }
    audit["audit_sha256"] = _audit_digest(audit)
    return audit


def verify_audit(root: Path, audit: dict[str, Any], local_env_path: Path | None = Path(".env")) -> list[str]:
    violations: list[str] = []
    if audit.get("schema_version") != 1:
        violations.append("unsupported secret audit schema")
    if audit.get("audit_sha256") != _audit_digest(audit):
        violations.append("secret audit digest mismatch")
    current = build_audit(root, local_env_path)

    def security_projection(value: dict[str, Any]) -> dict[str, Any]:
        active: dict[str, list[tuple[str, str, str, str]]] = {}
        for section, findings in value.get("findings", {}).items():
            active[section] = sorted(
                (
                    str(item.get("path")),
                    str(item.get("kind")),
                    str(item.get("classification")),
                    str(item.get("fingerprint")),
                )
                for item in findings
                if item.get("classification") == "active_candidate"
            )
        summary = value.get("summary", {})
        return {
            "head": value.get("head"),
            "result": value.get("result"),
            "decision": value.get("decision"),
            "active": active,
            "active_counts": {
                key: summary.get(key)
                for key in (
                    "tracked_active_candidates",
                    "history_active_candidates",
                    "local_env_active_candidates",
                    "history_text_blobs_scanned",
                )
            },
        }

    if security_projection(audit) != security_projection(current):
        violations.append("secret security projection no longer matches current inputs")
    serialized = json.dumps(audit, ensure_ascii=False)
    if '"value"' in serialized:
        violations.append("secret audit contains a forbidden value field")
    return violations


def write_audit(audit: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sanitize_claude_settings(path: Path) -> int:
    """Remove permission entries that embed secret assignments; return count."""
    data = json.loads(path.read_text(encoding="utf-8"))
    permissions = data.get("permissions", {})
    allowed = permissions.get("allow", [])
    if not isinstance(allowed, list):
        raise ValueError("permissions.allow must be a list")
    cleaned = [
        item
        for item in allowed
        if not (isinstance(item, str) and PERMISSION_SECRET_PATTERN.search(item))
    ]
    removed = len(allowed) - len(cleaned)
    if removed:
        permissions["allow"] = cleaned
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return removed


def scan_staged(root: Path) -> list[dict[str, Any]]:
    """Scan staged added/modified/renamed file contents without exposing values."""
    root = root.resolve()
    raw_paths = _git(root, ["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"])
    findings: list[dict[str, Any]] = []
    for raw_path in raw_paths.split(b"\0"):
        if not raw_path:
            continue
        relative = os.fsdecode(raw_path).replace("\\", "/")
        try:
            content = _git(root, ["show", f":{relative}"])
        except subprocess.CalledProcessError:
            continue
        if len(content) > MAX_TEXT_BLOB_BYTES:
            continue
        text = _text_from_bytes(content)
        if text is not None:
            findings.extend(scan_text(text, relative, "git_index"))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("--root", type=Path, default=Path.cwd())
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--local-env", type=Path, default=Path(".env"))
    verify = subparsers.add_parser("verify")
    verify.add_argument("--root", type=Path, default=Path.cwd())
    verify.add_argument("--audit", type=Path, required=True)
    verify.add_argument("--local-env", type=Path, default=Path(".env"))
    sanitize = subparsers.add_parser("sanitize-claude-settings")
    sanitize.add_argument("--path", type=Path, required=True)
    staged = subparsers.add_parser("scan-staged")
    staged.add_argument("--root", type=Path, default=Path.cwd())
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "sanitize-claude-settings":
        removed = sanitize_claude_settings(arguments.path)
        print(json.dumps({"integrity_result": "pass", "removed_secret_permissions": removed}, indent=2))
        return 0
    if arguments.command == "scan-staged":
        findings = scan_staged(arguments.root)
        active = [item for item in findings if item["classification"] == "active_candidate"]
        print(
            json.dumps(
                {
                    "result": "pass" if not active else "fail",
                    "staged_findings": len(findings),
                    "active_candidates": len(active),
                    "active_evidence": active,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if not active else 2
    if arguments.command == "generate":
        audit = build_audit(arguments.root, arguments.local_env)
        write_audit(audit, arguments.output)
        print(json.dumps({"integrity_result": "pass", "result": audit["result"], **audit["summary"]}, indent=2))
        return 0
    audit = json.loads(arguments.audit.read_text(encoding="utf-8"))
    violations = verify_audit(arguments.root, audit, arguments.local_env)
    print(json.dumps({"integrity_result": "pass" if not violations else "fail", "decision_result": audit.get("result"), "violations": violations}, indent=2))
    return 0 if not violations else 2


if __name__ == "__main__":
    raise SystemExit(main())
