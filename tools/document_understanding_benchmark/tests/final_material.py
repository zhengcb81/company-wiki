"""Shared synthetic builders for the DU3 final-material / paired-comparison tests.

Everything here is synthetic, small and offline: no original is read, no network
and no model call happens. The builders exist so that the *new* entry points
(``observe_final_material``, ``compare_runs``) can be exercised against a real
``ModelRequest``-shaped envelope without a production selector run, and so that
every counterexample the DU3/1 card names has an explicit fixture.

Two shapes matter and are deliberately kept apart:

``final_material(...)``
    the decode of an actual ``NarrativeModelRequest.data_json``: ``evidence``
    rows addressed by *alias*, ``evidence_groups`` addressed by *group alias*.
    This is what the model actually receives, so it is what the observer must
    measure.

``originals(...)``
    the already-verified source side: alias -> real unit text/locator/role. The
    observer may only copy text from here. A fixture that expects the observer
    to take wording from the material or from gold is a bug in the test, not a
    feature of the observer.
"""

from __future__ import annotations

from typing import Any

SHA_FINAL = "1" * 64

# ---------------------------------------------------------------------------
# originals: the already-verified source side
# ---------------------------------------------------------------------------

ORIGINAL_UNITS: dict[str, dict[str, Any]] = {
    "u-no-vc": {
        "locator": "loc:v1/page:3/paragraph:12",
        "page": 3,
        "text": "公司现无生产VC（碳酸亚乙烯酯）的情况。",
        "source_role": "management_answer",
        "language": "zh",
        "period": "2026Q2",
        "scope_id": "project-vc",
    },
    "u-stores": {
        "locator": "loc:v1/page:12/table:1/row:3",
        "page": 12,
        "text": "门店总数7,504家（截至2024年12月31日）。",
        "source_role": "company_filing",
        "language": "zh",
        "period": "2024-12-31",
        "scope_id": "stores",
    },
    "u-capex": {
        "locator": "loc:v1/page:62/table:2/row:1",
        "page": 62,
        "text": "本项目总投资为28,000万元，建设期两期。",
        "source_role": "company_filing",
        "language": "zh",
        "period": "2020",
        "scope_id": "project-alpha",
    },
    "u-question": {
        "locator": "loc:v1/page:3/paragraph:9",
        "page": 3,
        "text": "有没有能推动与宁德时代达成VC带量采购等具体业务？",
        "source_role": "analyst_question",
        "language": "zh",
        "period": "2026Q2",
        "scope_id": "qa-1",
    },
    "u-answer": {
        "locator": "loc:v1/page:3/paragraph:10",
        "page": 3,
        "text": "公司现无生产VC的情况，控股股东中国节能与宁德时代已建立联系，并希望建立业务协同。",
        "source_role": "management_answer",
        "language": "zh",
        "period": "2026Q2",
        "scope_id": "qa-1",
    },
}

#: source groups the caller declares as semantic closures, by member unit id.
ORIGINAL_GROUPS: dict[str, list[str]] = {
    "stores": ["u-stores"],
    "project-alpha": ["u-capex"],
    "project-vc": ["u-no-vc"],
    "qa-1": ["u-question", "u-answer"],
}


def originals(alias_to_unit: dict[str, str] | None = None) -> dict[str, Any]:
    """Build the ``originals`` argument of ``observe_final_material``.

    ``alias_to_unit`` maps an *actual* material alias to a unit id. The default
    is the honest one-to-one mapping. A test that wants to prove the observer
    refuses fabricated text changes the unit binding, never the original.
    """

    table = dict(alias_to_unit or {
        "e1": "u-no-vc",
        "e2": "u-stores",
        "e3": "u-capex",
        "e4": "u-question",
        "e5": "u-answer",
    })
    units: dict[str, dict[str, Any]] = {}
    for alias, unit_id in table.items():
        source = ORIGINAL_UNITS[unit_id]
        units[alias] = {
            "unit_id": unit_id,
            "source_id": "urn:company-wiki:source:sha256:" + SHA_FINAL,
            "source_sha256": SHA_FINAL,
            **source,
        }
    return {
        "schema_version": "du-final-originals/1",
        "source_id": "urn:company-wiki:source:sha256:" + SHA_FINAL,
        "source_sha256": SHA_FINAL,
        "units": units,
        "groups": {alias: list(members) for alias, members in ORIGINAL_GROUPS.items()},
    }


# ---------------------------------------------------------------------------
# material: the decoded final ModelRequest
# ---------------------------------------------------------------------------

def material(
    *,
    evidence: list[list[Any]] | None = None,
    groups: list[list[Any]] | None = None,
    source_sha256: str = SHA_FINAL,
    default_role: str = "unknown",
    columns: list[str] | None = None,
    group_columns: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """A decoded ``NarrativeModelRequest.data_json`` envelope.

    Row shape follows the *real* builder in
    ``company_wiki.automation.narrative_model``: ``[alias, raw_text]`` plus
    optional trailing role / quality-flag entries governed by
    ``evidence_columns``. Group rows follow ``evidence_group_columns``:
    ``[group_alias, [member_alias, ...]]``.
    """

    rows = evidence if evidence is not None else [
        ["e1", "公司现无生产VC（碳酸亚乙烯酯）的情况。"],
        ["e2", "门店总数7,504家（截至2024年12月31日）。"],
        ["e3", "本项目总投资为28,000万元，建设期两期。"],
        ["e4", "有没有能推动与宁德时代达成VC带量采购等具体业务？", "analyst_question"],
        ["e5", "公司现无生产VC的情况，控股股东中国节能与宁德时代已建立联系，并希望建立业务协同。", "management_answer"],
    ]
    group_rows = groups if groups is not None else [
        ["g1", ["e1"]],
        ["g2", ["e2"]],
        ["g3", ["e3"]],
        ["g4", ["e4", "e5"]],
    ]
    envelope: dict[str, Any] = {
        "schema_version": "du-model-request/1",
        "source": {
            "source_id": "urn:company-wiki:source:sha256:" + source_sha256,
            "source_sha256": source_sha256,
            "language": "zh",
            "title": "synthetic-final-material",
            "document_kind": "investor_relations",
        },
        "default_source_role": default_role,
        "default_quality_flags": [],
        "evidence_columns": columns or ["id", "raw_text", "source_role"],
        "evidence": rows,
        "evidence_group_columns": group_columns or ["id", "evidence_ids"],
        "evidence_groups": group_rows,
        "output_plan": {"max_claims": 20, "coverage": "selected_excerpts_only"},
        "selection": {"status": "selected", "coverage_complete": False,
                      "omitted_candidate_count": 3},
    }
    envelope.update(extra)
    return envelope


def execution(**extra: Any) -> dict[str, Any]:
    """Real execution facts for a synthetic run: measured, never assumed."""

    payload: dict[str, Any] = {
        "entry_point": "company_wiki.automation.narrative_model.NarrativeModelRequest.from_selection",
        "selector_version": "narrative-selector/1.0.0",
        "parser_version": "narrative-parser/1.0.0",
        "prompt_version": "du-narrative-prompt/1",
        "mode": "synthetic-final-material",
        "calls": 0,
        "elapsed_seconds": 0.01,
        "assessment": "synthetic fixture equivalent to a frozen final material",
    }
    payload.update(extra)
    return payload


def originals_with_unread(**extra: Any) -> dict[str, Any]:
    base = originals()
    base["unread"] = {
        "native_scan": "partial",
        "opaque_pages": [9],
        "deferred_pages": [],
        "deferred_unit_ids": [],
        "unassigned_unit_ids": [],
        "structure_complete": False,
    }
    base.update(extra)
    return base
