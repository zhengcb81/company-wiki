"""Complete report assembly and non-binding recommendations."""

from __future__ import annotations

import json

from .classify import Group
from .core import (
    LOCAL_PATHS_SCHEMA,
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
    entries: list[dict], *, max_rows: int | None = None, limits_hit: list[str]
) -> tuple[list[dict], int, int]:
    """Compatibility entry: all observed groups remain in the full report."""
    return entries, _detail_rows(entries), 0


def _serialized_size(report: dict) -> int:
    """Measure with the exact serializer used by ``core.write_json``."""
    return len(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True, allow_nan=False).encode("utf-8")
    )


def _detail_rows(entries: list[dict]) -> int:
    return sum(
        len(entry.get("locators", []))
        + len(entry.get("verification", {}).get("files", []))
        for entry in entries
    )


def apply_size_cap(
    report: dict, *, max_bytes: int | None = None, limits_hit: list[str]
) -> dict:
    """Compatibility name: refresh accounting without dropping any evidence."""
    groups = report.get("duplicate_groups", [])
    rows = _detail_rows(groups)
    truncated = report.setdefault("truncated", {})
    truncated.update(detail_rows=rows, max_detail_rows=None, listed_groups=len(groups),
                     max_report_bytes=None, report_bytes=0)
    for field in ("dropped_groups_by_row_cap", "dropped_groups_by_size_cap", "dropped_groups_total"):
        truncated.setdefault(field, 0)
    report.setdefault("counts", {}).update(duplicate_groups_listed=len(groups), detail_rows=rows)
    while True:
        actual = _serialized_size(report)
        if truncated["report_bytes"] == actual:
            return report
        truncated["report_bytes"] = actual


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
