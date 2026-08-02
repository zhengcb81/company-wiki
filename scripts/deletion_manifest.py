#!/usr/bin/env python3
"""Build and verify a deterministic manifest for tracked worktree deletions."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

DERIVED_CATEGORIES = {"derived_extract", "company_wiki", "wiki_archive"}
AUTHORIZED_DECISION = "user_authorized_derived_cleanup"

def _git(root: Path, arguments: list[str]) -> bytes:
    return subprocess.check_output(["git", *arguments], cwd=root)


def tracked_deletion_records(root: Path) -> dict[str, str]:
    """Return path -> two-column porcelain status for tracked deletions."""
    records = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=no"]).split(b"\0")
    deleted: dict[str, str] = {}
    index = 0
    while index < len(records) and records[index]:
        record = records[index]
        status = record[:2].decode("ascii", "replace")
        path = os.fsdecode(record[3:]).replace("\\", "/")
        if status[0] in {"R", "C"} or status[1] in {"R", "C"}:
            index += 1  # porcelain -z emits the second rename/copy path next
        if "D" in status:
            deleted[path] = status
        index += 1
    return dict(sorted(deleted.items()))


def tracked_deletions(root: Path) -> list[str]:
    return list(tracked_deletion_records(root))


def classify_path(relative: str) -> str:
    parts = PurePosixPath(relative).parts
    if "extracts" in parts:
        return "derived_extract"
    if "wiki" in parts and "archive" in parts:
        return "wiki_archive"
    if "wiki" in parts:
        return "company_wiki"
    return "other"


def _head_tree(root: Path, head: str) -> dict[str, dict[str, str]]:
    output = _git(root, ["ls-tree", "-r", "-z", head])
    result: dict[str, dict[str, str]] = {}
    for record in output.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split(" ")
        path = os.fsdecode(raw_path).replace("\\", "/")
        result[path] = {"mode": mode, "type": object_type, "oid": oid}
    return result


def _blob_metadata(root: Path, oids: Iterable[str]) -> dict[str, dict[str, Any]]:
    unique_oids = sorted(set(oids))
    process = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    result: dict[str, dict[str, Any]] = {}
    try:
        for oid in unique_oids:
            process.stdin.write((oid + "\n").encode("ascii"))
            process.stdin.flush()
            header = process.stdout.readline().decode("ascii", "replace").strip()
            fields = header.split(" ")
            if len(fields) != 3 or fields[1] != "blob":
                raise ValueError(f"Unable to read Git blob {oid}: {header}")
            size = int(fields[2])
            content = process.stdout.read(size)
            terminator = process.stdout.read(1)
            if len(content) != size or terminator != b"\n":
                raise ValueError(f"Truncated Git blob response: {oid}")
            result[oid] = {
                "size": size,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
    finally:
        process.stdin.close()
        process.wait(timeout=30)
    if process.returncode != 0:
        stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
        raise RuntimeError(f"git cat-file failed: {stderr}")
    return result


def _manifest_digest(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_manifest(root: Path, head: str = "HEAD", backup_id: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    head_oid = _git(root, ["rev-parse", head]).decode("ascii").strip()
    tree = _head_tree(root, head_oid)
    deleted = tracked_deletions(root)
    missing_from_head = [path for path in deleted if path not in tree]
    if missing_from_head:
        raise ValueError(f"Deleted paths missing from {head_oid}: {missing_from_head[:5]}")
    non_blob = [path for path in deleted if tree[path]["type"] != "blob"]
    if non_blob:
        raise ValueError(f"Deleted paths are not Git blobs: {non_blob[:5]}")
    non_derived = [path for path in deleted if classify_path(path) not in DERIVED_CATEGORIES]
    if non_derived:
        raise ValueError(
            "Refusing deletion manifest containing original or unclassified content: "
            f"{non_derived[:5]}"
        )
    blobs = _blob_metadata(root, (tree[path]["oid"] for path in deleted))

    entries: list[dict[str, Any]] = []
    for path in deleted:
        object_info = tree[path]
        blob = blobs[object_info["oid"]]
        parts = PurePosixPath(path).parts
        entries.append(
            {
                "path": path,
                "entity": parts[1] if len(parts) > 1 and parts[0] == "companies" else None,
                "category": classify_path(path),
                "git_status": "worktree_deleted_unstaged",
                "head_blob_oid": object_info["oid"],
                "head_mode": object_info["mode"],
                "content_bytes": blob["size"],
                "content_sha256": blob["sha256"],
                "decision_state": AUTHORIZED_DECISION,
                "recovery": {
                    "git_head": [
                        "git",
                        "restore",
                        f"--source={head_oid}",
                        "--worktree",
                        "--",
                        path,
                    ],
                    "backup_id": backup_id,
                },
            }
        )

    categories = dict(sorted(collections.Counter(entry["category"] for entry in entries).items()))
    manifest: dict[str, Any] = {
        "schema_version": 2,
        "head": head_oid,
        "policy": {
            "commit_blocked": True,
            "decision_state": AUTHORIZED_DECISION,
            "user_authorized": True,
            "independent_review_required": True,
            "original_source_entries": 0,
            "bulk_restore_blocked": True,
            "bulk_delete_blocked": True,
        },
        "summary": {
            "total": len(entries),
            "content_bytes": sum(entry["content_bytes"] for entry in entries),
            "categories": categories,
        },
        "entries": entries,
    }
    manifest["manifest_sha256"] = _manifest_digest(manifest)
    return manifest


def verify_manifest(root: Path, manifest: dict[str, Any]) -> list[str]:
    root = root.resolve()
    violations: list[str] = []
    if manifest.get("schema_version") != 2:
        violations.append("unsupported deletion manifest schema")
    if manifest.get("manifest_sha256") != _manifest_digest(manifest):
        violations.append("manifest digest mismatch")

    head = str(manifest.get("head", ""))
    current_head = _git(root, ["rev-parse", "HEAD"]).decode("ascii").strip()
    if head != current_head:
        violations.append(f"HEAD mismatch: manifest={head} current={current_head}")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return violations + ["entries must be a list"]
    manifest_paths = [str(entry.get("path", "")) for entry in entries]
    current_records = tracked_deletion_records(root)
    current_deleted = list(current_records)
    if manifest_paths != current_deleted:
        violations.append("deleted path set differs from manifest")
    staged = [path for path, status in current_records.items() if status != " D"]
    if staged:
        violations.append(f"deletion is staged while review is pending: {staged[:5]}")

    tree = _head_tree(root, head or "HEAD")
    for entry in entries:
        path = str(entry.get("path", ""))
        if not path.startswith("companies/"):
            violations.append(f"deleted path outside companies/: {path}")
        if (root / Path(path)).exists():
            violations.append(f"manifest path is no longer deleted: {path}")
        if entry.get("category") != classify_path(path):
            violations.append(f"category mismatch: {path}")
        if tree.get(path, {}).get("oid") != entry.get("head_blob_oid"):
            violations.append(f"HEAD blob mismatch: {path}")
        if entry.get("decision_state") != AUTHORIZED_DECISION:
            violations.append(f"deletion is not user-authorized derived cleanup: {path}")
        if classify_path(path) not in DERIVED_CATEGORIES:
            violations.append(f"original or unclassified deletion is forbidden: {path}")

    categories = dict(sorted(collections.Counter(classify_path(path) for path in manifest_paths).items()))
    summary = manifest.get("summary", {})
    if summary.get("total") != len(entries):
        violations.append("summary total mismatch")
    if summary.get("categories") != categories:
        violations.append("summary category counts mismatch")
    policy = manifest.get("policy", {})
    if policy.get("commit_blocked") is not True:
        violations.append("deletion commit is not blocked")
    if policy.get("decision_state") != AUTHORIZED_DECISION:
        violations.append("manifest decision state is not user-authorized derived cleanup")
    if policy.get("user_authorized") is not True:
        violations.append("derived cleanup lacks explicit user authorization")
    if policy.get("independent_review_required") is not True:
        violations.append("independent review requirement was removed")
    if policy.get("original_source_entries") != 0:
        violations.append("manifest claims non-zero original source entries")
    return violations


def write_manifest(manifest: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("--root", type=Path, default=Path.cwd())
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--head", default="HEAD")
    generate.add_argument("--backup-id")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--root", type=Path, default=Path.cwd())
    verify.add_argument("--manifest", type=Path, required=True)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "generate":
        manifest = build_manifest(arguments.root, arguments.head, arguments.backup_id)
        write_manifest(manifest, arguments.output)
        print(json.dumps({"result": "pass", **manifest["summary"]}, ensure_ascii=False, indent=2))
        return 0
    manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    violations = verify_manifest(arguments.root, manifest)
    print(json.dumps({"result": "pass" if not violations else "fail", "violations": violations}, ensure_ascii=False, indent=2))
    return 0 if not violations else 2


if __name__ == "__main__":
    raise SystemExit(main())
