"""Complete report assembly and accounting validation (cwp-storage-footprint/1)."""

from __future__ import annotations

from .core import (
    REPORT_SCHEMA,
    serialize,
)
from .classify import (
    BUCKETS,
    BUCKET_LABELS,
    BUCKET_REASONS,
    CATEGORIES,
    CATEGORY_LABELS,
)
from .scan import ScanResult

GAIN_BASIS = {
    "keep_now": "不产生释放：零删除测量口径，无收益可计",
    "separate_disposal_review": (
        "收益口径=logical_path_bytes（逻辑字节上界；allocated_bytes=null，"
        "未做内容/重复验证，不等于已确认可删收益）"
    ),
    "undetermined": "无收益口径：只读无法证实终态，不得计入任何释放估算",
}

COST_OR_CONDITION = {
    "keep_now": "保留成本=持续占用；无处置动作，本工具不执行删除",
    "separate_disposal_review": (
        "需确认可重建且没有正在使用；本工具不实现 purge/hardlink/delete"
    ),
    "undetermined": "需可只读证实的状态证据后重评；绝不凭 mtime 判断",
}


def _duplicate_summary(result: ScanResult) -> dict:
    groups = 0
    paths = 0
    extra = 0
    for count, size in result.duplicates.values():
        if count < 2:
            continue
        groups += 1
        paths += count
        extra += (count - 1) * size
    identity_available = (
        result.files_measured > 0 and result.unknown_identity_files == 0
    )
    return {
        "method": "st_dev+st_ino metadata identity only; no file content read",
        "identity_available": identity_available,
        "identity_known_files": result.files_measured - result.unknown_identity_files,
        "groups": groups,
        "paths": paths,
        "extra_logical_bytes": extra,
        "unknown_identity_files": result.unknown_identity_files,
        "note": (
            "candidate path aliasing only: not content-verified, not confirmed "
            "reclaimable, never added to a deletion benefit"
        ),
    }


def _top_directories(result: ScanResult) -> list[dict]:
    rows = [
        {"path": path, "files": files, "logical_path_bytes": result.dir_bytes[path]}
        for path, files in result.dir_files.items()
        if path != ""
    ]
    rows.sort(key=lambda row: (-row["logical_path_bytes"], row["path"]))
    return rows


def _retention_notes(result: ScanResult) -> list[dict]:
    keys = sorted(
        result.bucket_files,
        key=lambda key: (CATEGORIES.index(key[0]), BUCKETS.index(key[1])),
    )
    notes = []
    for category, bucket in keys:
        files = result.bucket_files[(category, bucket)]
        if files <= 0:
            continue
        notes.append(
            {
                "category": category,
                "category_label": CATEGORY_LABELS[category],
                "bucket": bucket,
                "bucket_label": BUCKET_LABELS[bucket],
                "files": files,
                "logical_path_bytes": result.bucket_bytes.get((category, bucket), 0),
                "reason": BUCKET_REASONS[bucket],
                "gain_basis": GAIN_BASIS[bucket],
                "cost_or_condition": COST_OR_CONDITION[bucket],
            }
        )
    return notes


def _limitations(result: ScanResult) -> list[str]:
    limitations = [
        (
            "allocated_bytes is null: no evidenced metadata-only allocation API on "
            "this platform; logical sizes are not disk allocation and OS "
            "compressed-size or cluster estimates are not used as a substitute"
        ),
        (
            f"measurement window {result.started_at}..{result.finished_at or 'n/a'}; "
            "the tree can change concurrently (shared Git objects); this is not an "
            "atomic filesystem snapshot"
        ),
        (
            "metadata only: no file content read, no SHA-256 computed; "
            "duplicate_path_links are path-alias candidates, not content-verified "
            "duplicates and not confirmed reclaimable bytes"
        ),
        (
            "classification follows documented path/layout rules "
            "(tools/storage_footprint/README.md); git tracked status is not verified"
        ),
        (
            "only the explicit project_root is scanned; external configured roots, "
            "other worktrees and cloud roots are excluded"
        ),
    ]
    if result.stop_reason != "complete":
        limitations.append(
            f"partial scan: stop_reason={result.stop_reason}; totals cover only the "
            f"visited portion (files_measured={result.files_measured}), not a "
            "full-tree total"
        )
    if result.skipped_files:
        limitations.append(
            "reparse/symlink/cloud entries skipped without following or hydrating: "
            f"skipped_files={result.skipped_files} "
            f"(links={result.skipped_links}, cloud={result.skipped_cloud}); "
            "their disposition is undetermined"
        )
    if result.errors_total:
        limitations.append(
            f"traversal errors: total={result.errors_total}, "
            f"listed={len(result.errors)}; affected subtrees are not measured"
        )
    if result.unknown_identity_files:
        limitations.append(
            "file identity unknown (st_ino absent) for "
            f"{result.unknown_identity_files} measured files; duplicate detection "
            "covers the remaining measured files only"
        )
    return limitations


def build_report(
    result: ScanResult,
    *,
    project_root_text: str,
    limits: dict,
) -> dict:
    """Assemble the ``cwp-storage-footprint/1`` payload from a scan result."""
    logical = result.logical_path_bytes
    categories = []
    for name in CATEGORIES:
        files = result.category_files[name]
        nbytes = result.category_bytes[name]
        categories.append(
            {
                "category": name,
                "label": CATEGORY_LABELS[name],
                "files": files,
                "logical_path_bytes": nbytes,
                "share_of_logical_bytes": round(nbytes / logical, 6)
                if logical
                else 0.0,
            }
        )
    return {
        "schema_version": REPORT_SCHEMA,
        "scope": {
            "project_root": project_root_text,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "complete": result.complete,
            "stop_reason": result.stop_reason,
        },
        "limits": {
            "max_files": int(limits["max_files"]),
            "max_seconds": float(limits["max_seconds"]),
        },
        "totals": {
            "entries_seen": result.entries_seen,
            "directories_seen": result.directories_seen,
            "files_measured": result.files_measured,
            "logical_path_bytes": result.logical_path_bytes,
            "allocated_bytes": None,
            "unknown_files": result.unknown_files,
            "skipped_files": result.skipped_files,
            "skipped_links": result.skipped_links,
            "skipped_cloud_placeholders": result.skipped_cloud,
        },
        "categories": categories,
        "top_directories": _top_directories(result),
        "retention_notes": _retention_notes(result),
        "errors": list(result.errors),
        "skipped_samples": list(result.skipped_samples),
        "calls": {"original_body_reads": 0, "llm": 0, "network": 0, "deleted": 0},
        "limitations": _limitations(result),
        "duplicate_path_links": _duplicate_summary(result),
    }


def validate_report(payload: dict) -> list[str]:
    """Return structural/accounting problems; empty list means the report holds."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["payload is not an object"]
    if payload.get("schema_version") != REPORT_SCHEMA:
        problems.append("schema_version mismatch")
    required = {
        "schema_version",
        "scope",
        "limits",
        "totals",
        "categories",
        "top_directories",
        "retention_notes",
        "errors",
        "skipped_samples",
        "calls",
        "limitations",
        "duplicate_path_links",
    }
    missing = sorted(required - set(payload))
    if missing:
        problems.append(f"missing keys: {missing}")

    scope = payload.get("scope") or {}
    if scope.get("stop_reason") not in {"budget", "complete", "errors"}:
        problems.append("scope.stop_reason outside enum")
    if not isinstance(scope.get("complete"), bool):
        problems.append("scope.complete is not bool")
    if not isinstance(scope.get("project_root"), str):
        problems.append("scope.project_root is not text")

    totals = payload.get("totals") or {}
    if totals.get("allocated_bytes") is not None:
        problems.append("totals.allocated_bytes must stay null")
    for key in (
        "entries_seen",
        "files_measured",
        "logical_path_bytes",
        "unknown_files",
        "skipped_files",
        "skipped_links",
        "skipped_cloud_placeholders",
    ):
        if not isinstance(totals.get(key), int):
            problems.append(f"totals.{key} is not an int")

    categories = payload.get("categories")
    if not isinstance(categories, list):
        problems.append("categories is not a list")
        categories = []
    ids = [item.get("category") for item in categories if isinstance(item, dict)]
    if ids != list(CATEGORIES):
        problems.append(f"categories mismatch: {ids}")
    if len(set(ids)) != len(ids):
        problems.append("duplicate category entries")
    sum_files = sum(int(item.get("files", -1)) for item in categories)
    sum_bytes = sum(int(item.get("logical_path_bytes", -1)) for item in categories)
    if sum_files != totals.get("files_measured"):
        problems.append("category file count double counts or drops entries")
    if sum_bytes != totals.get("logical_path_bytes"):
        problems.append("category bytes double count or drop entries")
    if int(totals.get("skipped_links", 0)) + int(
        totals.get("skipped_cloud_placeholders", 0)
    ) != int(totals.get("skipped_files", 0)):
        problems.append("skipped entries do not add up")

    for row in payload.get("top_directories") or []:
        path = str(row.get("path", ""))
        if path.startswith("/") or path.startswith("\\") or ":" in path:
            problems.append(f"top_directories path not root-relative: {path}")

    for note in payload.get("retention_notes") or []:
        if note.get("bucket") not in BUCKETS:
            problems.append(f"unknown retention bucket: {note.get('bucket')}")
        if note.get("category") not in CATEGORIES:
            problems.append(f"unknown retention category: {note.get('category')}")

    for entry in payload.get("errors") or []:
        path = str(entry.get("path", ""))
        if path.startswith("/") or path.startswith("\\") or ":" in path:
            problems.append(f"error path not root-relative: {path}")
        if len(path) > 400:
            problems.append("error path not truncated")

    skipped_samples = payload.get("skipped_samples")
    if not isinstance(skipped_samples, list):
        problems.append("skipped_samples is not a list")
    else:
        for sample in skipped_samples:
            path = str(sample.get("path", ""))
            if path.startswith("/") or path.startswith("\\") or ":" in path:
                problems.append(f"skipped path not root-relative: {path}")
            if sample.get("kind") not in {"reparse", "cloud"}:
                problems.append(f"unknown skip kind: {sample.get('kind')}")

    duplicates = payload.get("duplicate_path_links") or {}
    if not isinstance(duplicates.get("identity_known_files"), int):
        problems.append("duplicate_path_links.identity_known_files missing")

    calls = payload.get("calls") or {}
    if set(calls) != {"original_body_reads", "llm", "network", "deleted"}:
        problems.append("calls keys mismatch")
    elif any(calls[key] != 0 for key in calls):
        problems.append("calls must stay zero")

    if not isinstance(payload.get("limitations"), list):
        problems.append("limitations is not a list")
    return problems


def enforce_report_budget(
    payload: dict, max_bytes: int | None = None
) -> tuple[dict, list[str]]:
    """Compatibility entry: validate JSON and retain the complete report.

    Presentation size is not a scan result or execution budget. max_bytes is
    accepted for old callers but cannot trim evidence or veto serialization.
    """
    serialize(payload)  # Invalid JSON values still fail before publication.
    return payload, []
