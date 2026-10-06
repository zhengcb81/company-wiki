"""Read-only end-to-end orchestration for the raw duplicate assessment."""

from __future__ import annotations

import time
from pathlib import Path

from . import catalog as catalog_mod
from .classify import (
    CLASS_DISTINCT_COPIES,
    CLASS_UNCERTAIN,
    account_group,
    build_groups,
    enforce_containment,
    fill_allocations,
    observe,
    upper_bound_bytes,
)
from .core import (
    DEADLINE_SECONDS_DEFAULT,
    LOCAL_PATHS_SCHEMA,
    MAX_DETAIL_ROWS_DEFAULT,
    MAX_GROUPS_DEFAULT,
    MAX_READ_BYTES_DEFAULT,
    REPORT_SCHEMA,
    Budget,
    error_label,
    paths_overlap,
    report_is_ours,
    utc_now_text,
    write_json,
)
from .report import (
    apply_detail_row_cap,
    apply_size_cap,
    build_local_paths,
    build_recommendations,
    group_entry,
    report_contains_forbidden_claims,
    sort_groups,
)
from .verify import STATUS_VERIFIED_GROUP, init_verifications, verify_groups

ERROR_CONFIG = "config_unavailable"
ERROR_DATABASE = "catalog_database_unavailable"
ERROR_OVERLAP = "report_path_overlaps_data"
ERROR_OUTPUT_EXISTS = "output_exists_unknown"
ERROR_SQL = "catalog_read_failed"

STOPPING_LIMITS = ("deadline", "read_bytes")


def _base_report(operation: str, started_at: str) -> dict:
    return {
        "schema_version": REPORT_SCHEMA,
        "operation": operation,
        "status": "succeeded",
        "error_code": None,
        "started_at": started_at,
        "elapsed_seconds": 0.0,
        "catalog": {},
        "scan_scope": {},
        "limits": {},
        "limits_hit": [],
        "counts": {},
        "read_bytes": 0,
        "read_files": 0,
        "duplicate_groups": [],
        "similar_groups": [],
        "diagnostics": [],
        "logical_duplicate_bytes_upper_bound": 0,
        "verified_duplicate_bytes": 0,
        "physical_allocated_bytes": None,
        "physical_allocated_bytes_available": False,
        "physical_allocated_bytes_partial": None,
        "deleted_bytes": 0,
        "protected_before": {},
        "protected_after": {},
        "protected_unchanged": True,
        "truncated": {},
        "recommendations": {},
        "notes": [],
        "written": False,
    }


def _refuse(report: dict, error_code: str, notes: list[str]) -> dict:
    report["status"] = "refused"
    report["error_code"] = error_code
    report["notes"] = list(notes)
    return report


def _write_report(report: dict, target: Path, *, overwrite: bool) -> bool:
    if target.exists() and (not overwrite or not report_is_ours(target)):
        report["written"] = False
        report["write_refusal"] = ERROR_OUTPUT_EXISTS
        return False
    report["written"] = True
    apply_size_cap(report, limits_hit=report.setdefault("limits_hit", []))
    write_json(target, report, overwrite=True)
    return True


def _write_local(payload: dict, target: Path, *, overwrite: bool) -> bool:
    if (
        target.exists()
        and (not overwrite or not report_is_ours(target, LOCAL_PATHS_SCHEMA))
    ):
        return False
    write_json(target, payload, overwrite=True)
    return True


def run_assessment(
    *,
    config_path: Path,
    output_path: Path,
    mode: str = "scan",
    project_root: Path | None = None,
    max_groups: int = MAX_GROUPS_DEFAULT,
    max_read_bytes: int = MAX_READ_BYTES_DEFAULT,
    deadline_seconds: float = DEADLINE_SECONDS_DEFAULT,
    max_detail_rows: int = MAX_DETAIL_ROWS_DEFAULT,
    max_similar_groups: int = 100,
    location_status: str = "all",
    hash_catalog: bool = False,
    overwrite: bool = False,
    local_output_path: Path | None = None,
) -> dict:
    started_at = utc_now_text()
    clock0 = time.monotonic()
    target = Path(output_path)
    report = _base_report(mode, started_at)
    limits_hit: list[str] = []
    report["limits"] = {
        "max_groups": int(max_groups),
        "max_read_bytes": int(max_read_bytes),
        "deadline_seconds": float(deadline_seconds),
        "max_detail_rows": int(max_detail_rows),
        "max_similar_groups": int(max_similar_groups),
    }

    outputs = [(target, REPORT_SCHEMA)]
    if local_output_path is not None:
        outputs.append((Path(local_output_path), LOCAL_PATHS_SCHEMA))
    if any(path.exists() and (not overwrite or not report_is_ours(path, schema))
           for path, schema in outputs):
        _refuse(
            report,
            ERROR_OUTPUT_EXISTS,
            ["existing output is unknown or explicit overwrite was not requested"],
        )
        report["elapsed_seconds"] = round(time.monotonic() - clock0, 3)
        report["limits_hit"] = limits_hit
        report["written"] = False
        return report

    try:
        inputs = catalog_mod.load_inputs(config_path, project_root=project_root)
    except Exception as exc:  # noqa: BLE001 - surfaced as an explicit refusal
        _refuse(report, ERROR_CONFIG, [error_label(exc)])
        report["elapsed_seconds"] = round(time.monotonic() - clock0, 3)
        _write_report(report, target, overwrite=overwrite)
        return report

    protected_paths = [
        Path(inputs.config_path),
        Path(inputs.database_path),
        Path(inputs.catalog_dir),
        *[Path(root.path) for root in inputs.roots],
    ]
    overlapping = [
        str(candidate)
        for candidate in protected_paths
        if any(paths_overlap(path, candidate) for path, _ in outputs)
    ]
    if local_output_path is not None and paths_overlap(target, Path(local_output_path)):
        overlapping.append("output_paths_overlap")
    if overlapping:
        _refuse(
            report,
            ERROR_OVERLAP,
            [
                f"output path overlaps a protected data path: {len(overlapping)} match(es)"
            ],
        )
        report["elapsed_seconds"] = round(time.monotonic() - clock0, 3)
        report["limits_hit"] = limits_hit
        report["written"] = False
        return report

    try:
        reader = catalog_mod.open_reader(inputs)
    except Exception as exc:  # noqa: BLE001
        _refuse(report, ERROR_DATABASE, [error_label(exc)])
        report["elapsed_seconds"] = round(time.monotonic() - clock0, 3)
        _write_report(report, target, overwrite=overwrite)
        return report

    budget = Budget(max_read_bytes=max_read_bytes, deadline_seconds=deadline_seconds)
    try:
        try:
            schema = reader.schema_version()
            report["catalog"] = catalog_mod.catalog_identity(
                inputs, schema, hash_database=hash_catalog
            )
            protected_before = catalog_mod.protected_snapshot(inputs, reader)
            records = catalog_mod.read_locations(
                reader, location_status=location_status
            )
            similar = catalog_mod.similar_source_groups(
                reader, limit=max_similar_groups
            )
            root_rows = catalog_mod.roots_report(inputs, reader)
            totals = catalog_mod.registered_totals(reader)
        except Exception as exc:  # noqa: BLE001
            _refuse(report, ERROR_SQL, [error_label(exc)])
            report["elapsed_seconds"] = round(time.monotonic() - clock0, 3)
            _write_report(report, target, overwrite=overwrite)
            return report

        members, diagnostics = observe(records, inputs.roots, budget=budget)
        groups, conflicts = build_groups(members)
        dropped_by_containment = enforce_containment(groups, inputs.roots)
        if dropped_by_containment:
            diagnostics.append(
                {
                    "kind": "resolved_outside_configured_root",
                    "members": int(dropped_by_containment),
                    "note": "junction/reparse resolved outside a configured root; not read",
                }
            )
        for group in groups:
            group.account = account_group(group)
        fill_allocations(groups)
        for group in groups:
            if group.account.get("classification") == CLASS_DISTINCT_COPIES:
                group.account = account_group(group)

        if mode == "verify":
            attempted = verify_groups(groups, budget, max_groups=int(max_groups))
        else:
            init_verifications(groups, scan_mode=True)
            attempted = 0

        protected_after = catalog_mod.protected_snapshot(inputs, reader)
    finally:
        reader.close()

    limits_hit.extend(budget.limits_hit())
    accounts = [group.account for group in groups]
    sorted_groups = sort_groups(groups)
    entries = [group_entry(group) for group in sorted_groups]
    kept, detail_rows, dropped_rows = apply_detail_row_cap(
        entries, max_rows=int(max_detail_rows), limits_hit=limits_hit
    )

    upper_bound = upper_bound_bytes(accounts)
    verified_groups = [
        group
        for group in groups
        if group.verification.get("status") == STATUS_VERIFIED_GROUP
    ]
    verified_bytes = sum(
        int(group.account.get("logical_duplicate_bytes") or 0)
        for group in verified_groups
    )
    uncertain_groups = [
        group
        for group in groups
        if group.account.get("classification") == CLASS_UNCERTAIN
    ]
    unresolved_groups = [
        group
        for group in groups
        if group.account.get("classification") == "unresolved"
        or group.verification.get("status")
        in {"missing", "acl_denied", "open_error", "changed", "metadata_sha_mismatch"}
    ]
    accounted = [
        group
        for group in groups
        if group.account.get("logical_duplicate_bytes") is not None
    ]
    allocated_values = [
        group.account.get("physical_allocated_bytes") for group in accounted
    ]
    if accounted and all(value is not None for value in allocated_values):
        physical_allocated: int | None = int(
            sum(int(value) for value in allocated_values)
        )
        physical_available = True
    else:
        physical_allocated = None
        physical_available = False
    physical_partial = int(
        sum(int(value) for value in allocated_values if value is not None)
    )

    report["scan_scope"] = {
        "mode": mode,
        "location_status_filter": location_status,
        "location_rows_considered": len(records),
        "location_rows_observed": len(members),
        "roots": root_rows,
        "filesystem_sweep": False,
        "filesystem_sweep_note": (
            "只对 catalog 已登记的 location 做 stat/实读，不做任何全盘扫描；"
            " 未知外部目录不追随，云占位文件不打开。"
        ),
        "candidate_rule": (
            "按已登记 content_sha256/byte_size 分组，组内成员 >=2 才是候选；"
            " 只有不同物理身份的副本才计入逻辑重复字节。"
        ),
        "verification_rule": (
            "对每个不同物理身份开一次流式 SHA-256（1MiB 块），"
            " 与已登记 digest 比对后才可称 exact duplicate。"
        ),
    }
    report["limits_hit"] = limits_hit
    report["read_bytes"] = budget.read_bytes
    report["read_files"] = budget.read_files
    report["duplicate_groups"] = kept
    report["similar_groups"] = similar
    report["diagnostics"] = diagnostics + conflicts
    report["logical_duplicate_bytes_upper_bound"] = upper_bound
    report["verified_duplicate_bytes"] = verified_bytes
    report["physical_allocated_bytes"] = physical_allocated
    report["physical_allocated_bytes_available"] = physical_available
    report["physical_allocated_bytes_partial"] = (
        physical_partial if not physical_available else physical_allocated
    )
    report["physical_allocated_bytes_unavailable_groups"] = int(
        sum(1 for value in allocated_values if value is None)
    )
    report["counts"] = {
        "location_rows_considered": len(records),
        "location_rows_observed": len(members),
        "candidate_groups": len(groups),
        "similar_groups": len(similar),
        "duplicate_groups_listed": len(kept),
        "duplicate_groups_full": len(groups),
        "detail_rows": detail_rows,
        "verified_groups": len(verified_groups),
        "uncertain_groups": len(uncertain_groups),
        "unresolved_groups": len(unresolved_groups),
        "attempted_verification_groups": attempted,
        "registered_sources": totals["sources"],
        "registered_bytes": totals["registered_bytes"],
    }
    report["truncated"] = {
        "detail_rows": detail_rows,
        "max_detail_rows": int(max_detail_rows),
        "dropped_groups_by_row_cap": dropped_rows,
        "reasons": [],
    }
    report["protected_before"] = protected_before
    report["protected_after"] = protected_after
    report["protected_unchanged"] = catalog_mod.protected_equal(
        protected_before, protected_after
    )
    report["recommendations"] = build_recommendations(
        upper_bound=upper_bound,
        verified_bytes=verified_bytes,
        physical_allocated_bytes=physical_allocated,
        candidate_groups=len(groups),
        verified_groups=len(verified_groups),
        registered_bytes=totals["registered_bytes"],
    )
    report["notes"] = [
        "logical_duplicate_bytes_upper_bound 是按已登记 digest 与实测物理身份推算的、"
        " 未来可能减少的逻辑副本字节上界，不是已经收回的空间。",
        "本次 deleted_bytes=0：未删除、未移动、未硬链接、未复制任何原件。",
        "physical_allocated_bytes 取不到时为 null，另给 physical_allocated_bytes_partial。",
        "Windows普通文件大小不等于簇分配量；此平台physical_allocated_bytes为null，不声称实测磁盘节省。",
        "未实读、ACL 拒绝、文件消失或变更中的组单独列在 duplicate_groups 的 verification 里，"
        " 不计入 verified_duplicate_bytes。",
        "本机绝对路径不写入本报告；需要时用 --local-output 输出独立非 Git 文件。",
        "limits_hit 含 scope 类上限（max_groups/detail_rows/report_bytes）；"
        " status=partial 仅表示 deadline 或 read_bytes 预算被截断。",
    ]

    report["limits_hit"] = limits_hit
    report["elapsed_seconds"] = round(time.monotonic() - clock0, 3)
    if any(limit in STOPPING_LIMITS for limit in limits_hit):
        report["status"] = "partial"

    forbidden = report_contains_forbidden_claims(report)
    if forbidden:
        report["status"] = "refused"
        report["error_code"] = "report_contains_reclaimed_space_claim"
        report["notes"] = forbidden

    _write_report(report, target, overwrite=overwrite)
    if local_output_path is not None:
        _write_local(
            build_local_paths(inputs, sorted_groups),
            Path(local_output_path),
            overwrite=overwrite,
        )
    return report


def exit_code(report: dict) -> int:
    return 2 if report.get("status") == "refused" else 0
