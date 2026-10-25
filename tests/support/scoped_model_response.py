"""Deterministic offline response for the task-scoped summary protocol."""

from __future__ import annotations

from typing import Any


def source_grounded_scoped_reply(data: dict[str, Any]) -> dict[str, Any]:
    """Return one bounded clause copied from its actual task-local support.

    This fixture proves wire, citation, cache and recovery behavior only; the
    uncertain modality deliberately prevents it from claiming semantic review.
    """
    if data.get("schema_version") != "narrative-model-request/5":
        raise AssertionError("scoped fixture received a different request protocol")
    material = data["material"]
    task = material["tasks"][0]
    support = task.get("support_parts", material["task_defaults"]["support_parts"])
    key = task["parts"][0]["key"] if support == "all_parts" else support[0]
    part = next(row for row in task["parts"] if row["key"] == key)
    if "shared_ref" in part:
        part = next(row for row in material["shared_fragments"]
                    if row["source_key"] == part["shared_ref"])
    return {"drafts_by_task": {task["key"]: [{
        "text": part["text"][:200], "basis_parts": [key], "modality": "uncertain",
    }]}}
