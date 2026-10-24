"""Replay the frozen annual14 V5 selection through the public read/model contract.

This is an offline projection check. It does not reparse the source, call a
provider, or modify the frozen selection artifact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(ROOT / "tests"))

from company_wiki.automation.narrative_contracts import NarrativeSelectResult  # noqa: E402
from company_wiki.automation.narrative_model import NarrativeModelRequest  # noqa: E402
from company_wiki.source_catalog.narrative_reading import (  # noqa: E402
    _READING_DIAGNOSTIC_SAMPLE_LIMIT,
    _reading_group_id,
)
from support.narrative_model_request_fixture import selection  # noqa: E402


HERE = Path(__file__).resolve().parent
SELECTION = HERE.parent / "selection.json"
OUTPUT = HERE / "receipt.json"
SAMPLE_KEYS = ("opaque_pages", "deferred_pages", "deferred_unit_ids", "unassigned_unit_ids")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounded_context(context: dict[str, Any]) -> tuple[dict[str, Any], int]:
    seen: set[str] = set()
    groups = []
    for row in context["groups"]:
        semantic = {key: value for key, value in row.items() if key != "group_id"}
        group_id = _reading_group_id(semantic)
        if group_id not in seen:
            seen.add(group_id)
            groups.append({**semantic, "group_id": group_id})
    context["groups"] = groups

    unread = context["unread"]
    for key in SAMPLE_KEYS:
        count = max(unread.get("counts", {}).get(key, 0), len(unread[key]))
        unread["counts"][key] = count
        unread[key] = unread[key][:_READING_DIAGNOSTIC_SAMPLE_LIMIT]
    unread["limited"] = any(unread["counts"][key] > len(unread[key]) for key in SAMPLE_KEYS)

    deferred_count = context["deferred_count"]
    context["deferred"] = context["deferred"][:_READING_DIAGNOSTIC_SAMPLE_LIMIT]
    context["deferred_limited"] = deferred_count > len(context["deferred"])
    return context, len(seen)


def main() -> None:
    artifact = json.loads(SELECTION.read_text(encoding="utf-8"))
    wire = selection(3).to_dict()
    wire["source_ref"] = artifact["source_ref"]
    wire["evidence_spans"] = artifact["selected_evidence"]
    wire["selection"].update(
        status=artifact["selection_status"],
        coverage_complete=artifact["coverage_complete"],
        source_units=artifact["units"],
        candidate_count=artifact["candidate_count"],
        selected_count=artifact["selected_count"],
        omitted_candidate_count=artifact["candidate_count"] - artifact["selected_count"],
        pages_total=artifact["physical_pages"],
        pages_read=artifact["physical_pages"],
    )
    context, unique_group_count = bounded_context(artifact["reading_context"])
    wire["reading_context"] = context
    wire["reading_dependencies"] = artifact.get("reading_dependencies")

    selected = NarrativeSelectResult.from_dict(wire)
    request = NarrativeModelRequest.from_selection(selected)
    model_data = json.loads(request.data_json)
    context_size = len(json.dumps(context, ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":")).encode("utf-8"))
    receipt = {
        "schema_version": "w08-annual14-v5-public-contract-replay/1",
        "selection_sha256": sha256_file(SELECTION),
        "selected_spans": len(selected.evidence_spans),
        "reading_context_groups": len(context["groups"]),
        "unique_group_ids": unique_group_count,
        "reading_context_bytes": context_size,
        "unread_sample_limit": _READING_DIAGNOSTIC_SAMPLE_LIMIT,
        "unread_counts_preserved": context["unread"]["counts"],
        "deferred_count": context["deferred_count"],
        "deferred_sample_count": len(context["deferred"]),
        "model_task_count": len(model_data.get("evidence_groups", [])),
        "model_payload_bytes": len(request.data_json.encode("utf-8")),
        "contract": "PASS",
        "external_model_calls": 0,
        "source_reparse": 0,
        "downloads": 0,
        "raw_copies": 0,
        "note": "Frozen selected evidence reused; only bounded reading-context projection and public DTO/model-task contracts were replayed.",
    }
    OUTPUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
