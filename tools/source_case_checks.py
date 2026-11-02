"""Pure engineering receipt checks; never accesses a catalog or original."""

from __future__ import annotations


def compare_storage_observations(before: dict, after: dict) -> dict:
    """Keep originals/DB/WAL strict; SHM may refresh mtime without byte change.

    Caller supplies actual file observations. Missing observations cannot be
    invented. A SHM size/hash/existence change remains a failure, as does any
    other file's metadata change; no timestamps are restored to hide evidence.
    """
    paths = sorted(set(before) | set(after))
    rows = []
    for path in paths:
        left, right = before.get(path), after.get(path)
        if left is None or right is None:
            rows.append({"path": path, "observed_both": False, "passed": False})
            continue
        same_content = all(
            left.get(k) == right.get(k) for k in ("exists", "bytes", "sha256")
        )
        same_stat = left == right
        shm = path.endswith("-shm")
        same_except_mtime = {k: v for k, v in left.items() if k != "mtime_ns"} == {
            k: v for k, v in right.items() if k != "mtime_ns"
        }
        rows.append(
            {
                "path": path,
                "observed_both": True,
                "role": "sqlite_shm" if shm else "strict_file",
                "content_unchanged": same_content,
                "all_metadata_unchanged": same_stat,
                "shm_mtime_only": shm and same_except_mtime and not same_stat,
                "passed": same_except_mtime if shm else same_stat,
            }
        )
    return {
        "all_supplied_files_content_unchanged": all(
            r.get("content_unchanged", False) for r in rows
        ),
        "strict_files_and_shm_bytes_pass": bool(paths)
        and all(r["passed"] for r in rows),
        "all_file_stats_unchanged": all(
            r.get("all_metadata_unchanged", False) for r in rows
        ),
        "files": rows,
        "scope": "Only supplied observations; this does not manufacture original-file mtime proof.",
    }


def original_member_index(span_index: list[dict]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for span in span_index:
        for member in span.get("native_members", []):
            if member.get("valid_slice"):
                result.setdefault(member["unit_id"], []).append(span["span_id"])
        for unit_id in span.get("direct_original_unit_ids", []):
            result.setdefault(unit_id, []).append(span["span_id"])
    return result


def compare_context_original_members(
    oracle: dict, span_index: list[dict] | None, view_index: list[dict] | None
) -> dict:
    """Map original IDs through current carriers before inspecting view roles.

    This detects a previously wrong pair; it cannot prove new actor semantics.
    An absent material index remains OPEN rather than treating an unmatched
    old composite quotation as an absent current support statement.
    """
    result = {
        "oracle_id": oracle["oracle_id"],
        "expected_actor_and_scope": oracle["expected_actor_and_scope"],
        "original_support_unit_ids": oracle.get("original_support_unit_ids", []),
        "original_forbidden_context_unit_ids": oracle.get(
            "original_forbidden_context_unit_ids", []
        ),
    }
    if span_index is None or view_index is None:
        return {
            **result,
            "status": "OPEN_CURRENT_MEMBER_OR_VIEW_INDEX_NOT_RETAINED",
            "previous_bad_context_observed": None,
        }
    members = original_member_index(span_index)
    required = set(oracle.get("original_support_unit_ids", []))
    forbidden = set(oracle.get("original_forbidden_context_unit_ids", []))
    if not required or not forbidden:
        return {
            **result,
            "status": "OPEN_ORIGINAL_MEMBER_LINEAGE_UNAVAILABLE",
            "previous_bad_context_observed": None,
        }
    support_spans = {sid for uid in required for sid in members.get(uid, [])}
    bad_spans = {sid for uid in forbidden for sid in members.get(uid, [])}
    relevant = [
        view
        for view in view_index
        if support_spans & set(view.get("support_evidence_ids", []))
    ]
    wrong = [
        view.get("view_id")
        for view in relevant
        if bad_spans & set(view.get("context_evidence_ids", []))
    ]
    return {
        **result,
        "status": "PREVIOUS_WRONG_PAIR_REPRODUCED"
        if wrong
        else "OPEN_SEMANTIC_REVIEW_REQUIRED",
        "mapped_support_span_ids": sorted(support_spans),
        "unmapped_support_unit_ids": sorted(required - set(members)),
        "mapped_forbidden_context_span_ids": sorted(bad_spans),
        "relevant_view_count": len(relevant),
        "wrong_view_ids": wrong,
        "previous_bad_context_observed": bool(wrong),
        "scope": "No match is not proof of repaired attribution or complete processing.",
    }
