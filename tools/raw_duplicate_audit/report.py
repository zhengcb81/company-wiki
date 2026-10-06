"""Report assembly, truncation and non-binding recommendations."""

from __future__ import annotations

import json

from .classify import Group
from .core import (
    LIMIT_HIT_DETAIL_ROWS,
    LIMIT_HIT_REPORT_BYTES,
    LOCAL_PATHS_SCHEMA,
    MAX_DETAIL_ROWS_DEFAULT,
    MAX_REPORT_BYTES,
    RECOMMENDATION_MIN_BENEFIT_BYTES,
    utc_now_text,
)


def group_entry(group: Group) -> dict:
    """Git-safe group row: identifiers, hash, size and root-relative locators only."""
    entry = dict(group.account)
    entry["locators"] = [
        {
            "location_id": member.record.location_id,
            "source_id": member.record.source_id,
            "document_id": member.record.document_id,
            "root_id": member.record.root_id,
            "relative_path": member.record.relative_path,
            "location_status": member.record.location_status,
            "role": member.record.role,
        }
        for member in group.members
    ]
    entry["verification"] = group.verification
    return entry


def sort_groups(groups: list[Group]) -> list[Group]:
    def key(group: Group):
        value = group.account.get("logical_duplicate_bytes")
        if value is None:
            return (1, 0, group.group_id)
        return (0, -int(value), group.group_id)

    return sorted(groups, key=key)


def apply_detail_row_cap(
    entries: list[dict], *, max_rows: int, limits_hit: list[str]
) -> tuple[list[dict], int, int]:
    kept: list[dict] = []
    rows = 0
    for entry in entries:
        width = len(entry.get("locators", [])) + len(
            entry.get("verification", {}).get("files", [])
        )
        if rows + width > max_rows:
            if LIMIT_HIT_DETAIL_ROWS not in limits_hit:
                limits_hit.append(LIMIT_HIT_DETAIL_ROWS)
            break
        kept.append(entry)
        rows += width
    return kept, rows, len(entries) - len(kept)


def _serialized_size(report: dict) -> int:
    """Measure with the exact serializer used by ``core.write_json``."""
    return len(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    )


def _detail_rows(entries: list[dict]) -> int:
    return sum(
        len(entry.get("locators", []))
        + len(entry.get("verification", {}).get("files", []))
        for entry in entries
    )


_REPORT_BYTES_PLACEHOLDER = 9999999999999


def apply_size_cap(
    report: dict, *, max_bytes: int = MAX_REPORT_BYTES, limits_hit: list[str]
) -> dict:
    """Trim the Git report to ``max_bytes`` and refresh the truncation counters.

    Runs as the final mutation before serialisation, so every derived field is
    part of the measured size.  ``report_bytes`` is probed with a
    13-digit placeholder so writing the real value can only shrink the report.
    """
    truncated = report.setdefault("truncated", {})
    reasons = truncated.setdefault("reasons", [])
    for key, value in (
        ("detail_rows", 0),
        ("max_detail_rows", truncated.get("max_detail_rows", MAX_DETAIL_ROWS_DEFAULT)),
        ("dropped_groups_by_row_cap", truncated.get("dropped_groups_by_row_cap", 0)),
        ("dropped_groups_by_size_cap", 0),
        ("dropped_groups_total", 0),
        ("listed_groups", 0),
        ("report_bytes", _REPORT_BYTES_PLACEHOLDER),
        ("max_report_bytes", max_bytes),
    ):
        truncated.setdefault(key, value)
    truncated["report_bytes"] = _REPORT_BYTES_PLACEHOLDER
    counts = report.setdefault("counts", {})

    groups = list(report.get("duplicate_groups", []))
    listed_before = len(groups)

    def build(keep: int) -> None:
        report["duplicate_groups"] = groups[:keep]
        rows = _detail_rows(report["duplicate_groups"])
        truncated["detail_rows"] = rows
        truncated["dropped_groups_by_size_cap"] = listed_before - keep
        truncated["dropped_groups_total"] = int(
            truncated.get("dropped_groups_by_row_cap", 0)
        ) + (listed_before - keep)
        truncated["listed_groups"] = keep
        counts["duplicate_groups_listed"] = keep
        counts["detail_rows"] = rows

    build(listed_before)
    keep = listed_before
    if _serialized_size(report) > max_bytes:
        if LIMIT_HIT_REPORT_BYTES not in limits_hit:
            limits_hit.append(LIMIT_HIT_REPORT_BYTES)
        if (
            "report_bytes_cap" not in reasons
            and "report_bytes_floor_reached" not in reasons
        ):
            reasons.append("report_bytes_cap")
        low, high, best = 0, listed_before, 0
        while low <= high:
            mid = (low + high) // 2
            build(mid)
            if _serialized_size(report) <= max_bytes:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        keep = best
        build(keep)
        if keep == 0 and listed_before:
            reasons.append("report_bytes_floor_reached")

    # Group truncation alone cannot bound diagnostics or similar-file rows.
    # Keep summary totals, and truncate optional lists with explicit counters.
    for field in ("diagnostics", "similar_groups", "notes"):
        values = report.get(field, [])
        if not isinstance(values, list) or _serialized_size(report) <= max_bytes:
            continue
        dropped_key = f"dropped_{field}"
        truncated[dropped_key] = 0
        low, high, best = 0, len(values), 0
        while low <= high:
            mid = (low + high) // 2
            report[field] = values[:mid]
            truncated[dropped_key] = len(values) - mid
            if _serialized_size(report) <= max_bytes:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        report[field] = values[:best]
        truncated[dropped_key] = len(values) - best
    if _serialized_size(report) > max_bytes:
        # Invalid/unbounded header data must not force a giant report onto disk.
        report.clear()
        report.update({"schema_version": "raw-duplicate-assessment/1",
                       "status": "refused", "error_code": "report_header_too_large",
                       "deleted_bytes": 0, "written": True,
                       "truncated": {"max_report_bytes": max_bytes, "report_bytes": 0}})
        truncated = report["truncated"]
    for _ in range(5):
        actual = _serialized_size(report)
        if truncated.get("report_bytes") == actual:
            break
        truncated["report_bytes"] = actual
    truncated["max_report_bytes"] = max_bytes
    return report


def build_local_paths(inputs, groups: list[Group]) -> dict:
    """Machine-absolute paths live only in this non-Git side file."""
    return {
        "schema_version": LOCAL_PATHS_SCHEMA,
        "generated_at": utc_now_text(),
        "project_root": str(inputs.project_root),
        "config_path": str(inputs.config_path),
        "database_path": str(inputs.database_path),
        "roots": [
            {"root_id": root.root_id, "path": str(root.path)} for root in inputs.roots
        ],
        "groups": [
            {
                "group_id": group.group_id,
                "content_sha256": group.content_sha256,
                "byte_size": group.byte_size,
                "members": [
                    {
                        "location_id": member.record.location_id,
                        "root_id": member.record.root_id,
                        "relative_path": member.record.relative_path,
                        "absolute_path": str(member.path) if member.path else None,
                    }
                    for member in group.members
                ],
            }
            for group in groups
        ],
    }


def build_recommendations(
    *,
    upper_bound: int,
    verified_bytes: int,
    physical_allocated_bytes: int | None,
    candidate_groups: int,
    verified_groups: int,
    registered_bytes: int,
    threshold: int = RECOMMENDATION_MIN_BENEFIT_BYTES,
) -> dict:
    """Non-binding comparison of three options; no architecture is modified."""
    share = (upper_bound / registered_bytes) if registered_bytes else 0.0
    options = [
        {
            "option": "keep_as_is",
            "summary": "维持现状：原件按路径重复存放，不做任何结构调整。",
            "source_version_impact": "none",
            "move_impact": "none",
            "reference_impact": "none",
            "recoverability_impact": "none",
            "implementation_risk": "none",
        },
        {
            "option": "sha_objectification",
            "summary": "按 SHA-256 内容寻址保存单份字节，路径退化为对 digest 的引用。",
            "source_version_impact": "digest 即版本身份，注册的 content_sha256 不变，但"
            " source 与物理文件的一对一假设被打破，需要新的引用解析层。",
            "move_impact": "移动变为引用重写；原件不再随目录搬迁，需要显式材料化才能导出原件。",
            "reference_impact": "所有以 path 为准的下游读取、清理、审计必须改为 SourceRef/digest 解析；"
            " 属于跨仓合同变更，只能由 MAIN 决策。",
            "recoverability_impact": "内容寻址 + 校验和可恢复性最好，可按 digest 重建，但需要"
            " 额外的第二存储与保留策略。",
            "implementation_risk": "高：需要迁移、双写期与回滚方案。",
        },
        {
            "option": "filesystem_hardlinks",
            "summary": "在支持的文件系统上用硬链接让多个名字共享一份物理字节。",
            "source_version_impact": "最小：不改 schema，不改 digest，路径仍然有效。",
            "move_impact": "同一卷内移动只是改目录项；跨卷复制会重新占用空间，链接数会被打断。",
            "reference_impact": "path 与 digest 假设都保持不变，引用无需改写。",
            "recoverability_impact": "删除一个名字不释放空间（链接计数），删除最后一个名字才释放，"
            " 部分备份/同步工具会把链接展开成副本。",
            "implementation_risk": "中：仅限本地同卷，云同步目录可能不保链接，且会改变不可变原件的"
            " 物理呈现。",
        },
    ]
    benefit = verified_bytes if verified_groups else upper_bound
    if upper_bound < threshold:
        verdict = "keep_as_is"
        reason = (
            f"逻辑重复字节上界 {upper_bound} 低于建议阈值 {threshold}"
            f"（占已登记原件 {share:.1%}），收益过小，建议不做去重。"
        )
    else:
        verdict = "needs_main_decision"
        reason = (
            f"逻辑重复字节上界 {upper_bound}（已实读确认 {verified_bytes}，"
            f" 占已登记原件 {share:.1%}）达到阈值 {threshold}，"
            " 值得由 MAIN 结合引用兼容性决定是否实施；本工具不改架构、不删文件。"
        )
    return {
        "verdict": verdict,
        "reason": reason,
        "threshold_bytes": threshold,
        "benefit_basis_bytes": benefit,
        "candidate_groups": candidate_groups,
        "verified_groups": verified_groups,
        "registered_bytes": registered_bytes,
        "upper_bound_share_of_registered": round(share, 6),
        "physical_allocated_bytes": physical_allocated_bytes,
        "options": options,
        "binding": False,
    }


def report_contains_forbidden_claims(report: dict) -> list[str]:
    """Guard rail: estimates must never read as space already reclaimed."""
    text = json.dumps(report, ensure_ascii=False)
    banned = ["已释放", "freed ", "reclaimed "]
    found = [token for token in banned if token in text]
    if report.get("deleted_bytes") != 0:
        found.append("deleted_bytes!=0")
    return found
