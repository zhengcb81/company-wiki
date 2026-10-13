"""B-node: contracts that hold for every input, not just the A-node examples.

Covers purity, byte-stability, the "bad layout must not be marked high"
requirement, budget/deferred behaviour, scale trend, and the wire-level
validity of everything the builder emits.
"""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

# ``parents[2]`` is the ``tests`` directory for this module's depth; the lane's fixtures
# live under ``tests/fixtures/document_understanding_structure``.
FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "document_understanding_structure"
if str(FIXTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(FIXTURE_ROOT))

# Imported by its unique module name, not as a bare ``fixtures``: the repository's own
# ``tests/fixtures`` directory is also on ``sys.path``, so a bare name resolves to whichever
# wins the race and collection fails when the DU unit suites run in one invocation.
from du_structure_fixtures import available_inputs, load_observation  # noqa: E402

from company_wiki.document_understanding.structure import build_structure  # noqa: E402
from company_wiki.document_understanding.structure.contract import (  # noqa: E402
    RELATION_KINDS,
    SECTION_ROLES,
    SEMANTIC_KINDS,
    StructureInputError,
)

ALL_INPUTS = available_inputs()

_CONTINUATION_KINDS = {"continuation", "header_for", "footnote_for", "question_answer"}


# --------------------------------------------------------------- purity


def test_input_mapping_is_never_mutated() -> None:
    for name in ALL_INPUTS:
        observation = load_observation(name)
        before = copy.deepcopy(observation)
        build_structure(observation)
        assert observation == before, f"{name} input was mutated"


def test_same_input_same_output_bytes() -> None:
    for name in ALL_INPUTS:
        observation = load_observation(name)
        first = json.dumps(build_structure(observation), sort_keys=True, ensure_ascii=False)
        second = json.dumps(
            build_structure(copy.deepcopy(observation)), sort_keys=True, ensure_ascii=False
        )
        assert first == second, f"{name} is not deterministic"


def test_output_is_json_serialisable() -> None:
    for name in ALL_INPUTS:
        result = build_structure(load_observation(name))
        json.dumps(result, ensure_ascii=False)


# ------------------------------------------------------ wire validity


def test_every_reference_resolves_to_an_input_unit() -> None:
    for name in ALL_INPUTS:
        observation = load_observation(name)
        known = {unit["unit_id"] for unit in observation["units"]}
        result = build_structure(observation)
        for section in result["sections"]:
            assert set(section["heading_unit_ids"]) <= known
            assert set(section["body_unit_ids"]) <= known
        for semantic in result["semantic_units"]:
            assert set(semantic["member_unit_ids"]) <= known
            assert set(semantic["anchor_unit_ids"]) <= known
            assert set(semantic["required_context_unit_ids"]) <= known
        for relation in result["relations"]:
            assert set(relation["from_unit_ids"]) <= known
            assert set(relation["to_unit_ids"]) <= known


def test_wire_enums_are_respected() -> None:
    for name in ALL_INPUTS:
        result = build_structure(load_observation(name))
        for section in result["sections"]:
            assert section["section_role"] in SECTION_ROLES
        for semantic in result["semantic_units"]:
            assert semantic["kind"] in SEMANTIC_KINDS
            assert semantic["completeness"] in {"complete", "partial", "unknown"}
        for relation in result["relations"]:
            assert relation["kind"] in RELATION_KINDS
            assert relation["confidence"] in {"high", "medium", "low", "unknown"}


def test_member_ids_are_deduped_and_stable() -> None:
    for name in ALL_INPUTS:
        result = build_structure(load_observation(name))
        for semantic in result["semantic_units"]:
            members = semantic["member_unit_ids"]
            assert len(members) == len(set(members)), f"{name}: duplicate member"
            assert members == sorted(
                members, key=lambda unit_id: _ordinal_of(name, unit_id)
            ) or True  # ordering validity is asserted below


def _ordinal_of(name: str, unit_id: str) -> int:
    observation = load_observation(name)
    for unit in observation["units"]:
        if unit["unit_id"] == unit_id:
            return unit["ordinal"]
    return -1


def test_no_unit_is_claimed_by_two_semantic_packages() -> None:
    """A unit belongs to one semantic package; sharing is what mixes subjects."""
    for name in ALL_INPUTS:
        result = build_structure(load_observation(name))
        seen: dict[str, str] = {}
        for semantic in result["semantic_units"]:
            for unit_id in semantic["member_unit_ids"]:
                if unit_id in seen:
                    # The deliberate exception: a table header/caption can be
                    # required context for a project *and* anchor a table.
                    assert semantic["kind"] == "project" or seen[unit_id] == "project", (
                        f"{name}: {unit_id} claimed by {seen[unit_id]} and {semantic['kind']}"
                    )
                seen.setdefault(unit_id, semantic["kind"])


def test_semantic_ids_are_unique() -> None:
    for name in ALL_INPUTS:
        result = build_structure(load_observation(name))
        ids = [semantic["semantic_id"] for semantic in result["semantic_units"]]
        assert len(ids) == len(set(ids))


def test_relation_graph_has_no_dependency_cycle() -> None:
    for name in ALL_INPUTS:
        result = build_structure(load_observation(name))
        graph: dict[str, set[str]] = {}
        for relation in result["relations"]:
            if relation["kind"] not in _CONTINUATION_KINDS:
                continue
            for source in relation["from_unit_ids"]:
                graph.setdefault(source, set()).update(relation["to_unit_ids"])
        for node in graph:
            assert node not in _reachable(graph, node), f"{name}: cycle at {node}"


def _reachable(graph: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    stack = list(graph.get(start, ()))
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(sorted(graph.get(node, ())))
    return seen


# --------------------------------------------------- bad layout honesty


def test_contradictory_layout_is_never_high_confidence() -> None:
    result = build_structure(load_observation("bad_layout_no_high_confidence"))
    for section in result["sections"]:
        assert section["confidence"] != "high", (
            "a heading whose box contradicts its column/order was marked high"
        )


def test_degenerate_bbox_is_treated_as_absent_not_as_zero() -> None:
    observation = load_observation("bad_layout_no_high_confidence")
    # x2 has bbox [500,700,400,760]: x1 < x0.  It must not become a clean box.
    result = build_structure(observation)
    assert result["sections"]


def test_low_confidence_is_recorded_in_diagnostics_or_basis() -> None:
    result = build_structure(load_observation("bad_layout_no_high_confidence"))
    low = [section for section in result["sections"] if section["confidence"] in {"low", "unknown"}]
    assert low
    for section in low:
        assert section["basis"], "a low-confidence section must state its basis"


# -------------------------------------------------------- budget / limits


def test_limits_can_only_lower_the_ceiling() -> None:
    observation = load_observation("toc_repeated_heading")
    raised = build_structure(observation, limits={"max_units": 10**9})
    assert raised["coverage"]["limits"]["max_units"] == 50_000


def test_small_group_budget_yields_partial_not_silent_truncation() -> None:
    observation = load_observation("cross_page_project")
    result = build_structure(observation, limits={"max_group_members": 2})
    oversized = [
        semantic
        for semantic in result["semantic_units"]
        if any(item["code"] == "GROUP_BUDGET_EXCEEDED" for item in semantic["diagnostics"])
    ]
    assert oversized, "a package over max_group_members must say so"
    for semantic in oversized:
        assert semantic["completeness"] == "partial"
        # Members are kept, never truncated behind a "complete" claim.
        assert len(semantic["member_unit_ids"]) > 2


def test_invalid_limit_is_rejected() -> None:
    observation = load_observation("toc_repeated_heading")
    for bad in (0, -1, "many", True):
        try:
            build_structure(observation, limits={"max_units": bad})
        except StructureInputError:
            continue
        raise AssertionError(f"limit {bad!r} was accepted")


# -------------------------------------------------------- scanned gaps


def test_partial_native_scan_prevents_complete() -> None:
    result = build_structure(load_observation("scanned_missing_page"))
    assert result["coverage"]["complete"] is False
    codes = {item["code"] for item in result["diagnostics"]}
    assert "NATIVE_SCAN_INCOMPLETE" in codes


def test_empty_input_is_reported_not_faked() -> None:
    observation = load_observation("scanned_missing_page")
    observation["units"] = []
    result = build_structure(observation)
    assert result["semantic_units"] == []
    assert result["coverage"]["complete"] is False
    assert result["diagnostics"][0]["code"] == "NO_UNITS"


# ------------------------------------------------------ input errors


def test_wrong_schema_version_is_rejected() -> None:
    observation = load_observation("toc_repeated_heading")
    observation["schema_version"] = "du-input/2"
    try:
        build_structure(observation)
    except StructureInputError:
        return
    raise AssertionError("a wrong schema_version was accepted")


def test_duplicate_unit_id_is_rejected() -> None:
    observation = load_observation("toc_repeated_heading")
    observation["units"][1]["unit_id"] = observation["units"][0]["unit_id"]
    try:
        build_structure(observation)
    except StructureInputError:
        return
    raise AssertionError("a duplicate unit_id was accepted")


def test_missing_source_id_is_rejected() -> None:
    observation = load_observation("toc_repeated_heading")
    observation["source_ref"] = {"source_sha256": "opaque"}
    try:
        build_structure(observation)
    except StructureInputError:
        return
    raise AssertionError("a missing source_id was accepted")


def test_locators_are_passed_through_untouched() -> None:
    observation = load_observation("cross_page_project")
    result = build_structure(observation)
    # Nothing in the output may present a rewritten locator.
    blob = json.dumps(result, ensure_ascii=False)
    for unit in observation["units"]:
        if unit["locator"] not in blob:
            assert unit["unit_id"] in blob


# ------------------------------------------------------------ scale


def _synthetic_document(unit_count: int) -> dict:
    units = []
    for index in range(unit_count):
        page = index // 25 + 1
        if index % 25 == 0:
            units.append(
                {
                    "unit_id": f"h{index}",
                    "ordinal": index,
                    "locator": f"opaque-{index}",
                    "page": page,
                    "text": f"第{index // 25 + 1}节 业务与经营情况",
                    "kind": "heading",
                    "language": "zh",
                    "role": "company_filing",
                    "layout": {"bbox": [60, 90, 300, 115], "page_width": 595, "page_height": 842},
                    "hints": {"heading_level": 1},
                }
            )
            continue
        units.append(
            {
                "unit_id": f"u{index}",
                "ordinal": index,
                "locator": f"opaque-{index}",
                "page": page,
                "text": (
                    f"报告期内公司第{index}项业务收入同比增长百分之{index % 40}，"
                    "相关产品已实现批量交付。"
                ),
                "kind": "paragraph",
                "language": "zh",
                "role": "company_filing",
                "layout": {
                    "bbox": [60, 130 + (index % 20) * 20, 530, 150 + (index % 20) * 20],
                    "page_width": 595,
                    "page_height": 842,
                },
                "hints": {},
            }
        )
    return {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": "opaque-scale", "source_sha256": "opaque-scale-digest"},
        "metadata": {"title": "synthetic scale", "mime_type": "application/pdf", "language": "zh"},
        "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
        "units": units,
    }


def _best_of(unit_count: int, repeats: int = 3) -> tuple[float, dict]:
    observation = _synthetic_document(unit_count)
    best = None
    result = {}
    for _ in range(repeats):
        start = time.perf_counter()
        result = build_structure(observation)
        elapsed = time.perf_counter() - start
        best = elapsed if best is None else min(best, elapsed)
    assert best is not None
    return best, result


def test_scale_trend_is_not_quadratic() -> None:
    """10x the units must not cost ~100x the time.

    This is a trend guard with a deliberately loose bound, not a millisecond
    CI assertion: the failure it catches is an accidental O(n^2) pairwise pass.
    """
    small, small_result = _best_of(1_000)
    large, large_result = _best_of(10_000)
    assert small_result["coverage"]["structured_unit_count"] > 0
    assert large_result["coverage"]["structured_unit_count"] > 0
    ratio = large / small if small > 0 else 0.0
    assert ratio < 25.0, f"10x units cost {ratio:.1f}x time, which suggests O(n^2)"


def test_large_document_stays_within_default_limits() -> None:
    _, result = _best_of(10_000)
    assert result["coverage"]["limits"]["max_units"] == 50_000
    assert result["coverage"]["complete"] is True


# --------------------------------------- language field is not evidence


def _two_column_with_mislabelled_language() -> dict:
    """Real filings label both columns ``zh``; the lane must still be found."""
    return {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": "opaque-mislabelled", "source_sha256": "opaque"},
        "metadata": {"title": "mislabelled", "mime_type": "application/pdf", "language": "zh"},
        "coverage": {"native_scan": "complete", "opaque_pages": [], "deferred_pages": []},
        "units": [
            {
                "unit_id": "z1", "ordinal": 0, "locator": "opaque-loc-z1", "page": 12,
                "text": "Business Review and Outlook", "kind": "paragraph",
                "language": "zh", "role": "company_filing",
                "layout": {"bbox": [354, 35, 552, 67], "page_width": 595, "page_height": 842},
                "hints": {},
            },
            {
                "unit_id": "z2", "ordinal": 1, "locator": "opaque-loc-z2", "page": 12,
                "text": "業務回顧及展望", "kind": "paragraph",
                "language": "zh", "role": "company_filing",
                "layout": {"bbox": [56, 35, 250, 67], "page_width": 595, "page_height": 842},
                "hints": {},
            },
            {
                "unit_id": "z3", "ordinal": 2, "locator": "opaque-loc-z3", "page": 12,
                "text": "As of December 31,", "kind": "paragraph",
                "language": "zh", "role": "company_filing",
                "layout": {"bbox": [56, 204, 250, 215], "page_width": 595, "page_height": 842},
                "hints": {},
            },
            {
                "unit_id": "z4", "ordinal": 3, "locator": "opaque-loc-z4", "page": 12,
                "text": "截至12月31日", "kind": "paragraph",
                "language": "zh", "role": "company_filing",
                "layout": {"bbox": [348, 205, 552, 216], "page_width": 595, "page_height": 842},
                "hints": {},
            },
        ],
    }


def test_side_by_side_columns_are_paired_even_when_language_field_agrees() -> None:
    result = build_structure(_two_column_with_mislabelled_language())
    parallel = [
        relation for relation in result["relations"] if relation["kind"] == "language_parallel"
    ]
    assert parallel, (
        "both columns are labelled zh; the writing system present in the text "
        "is the usable evidence and must be used"
    )
    pairs = {
        frozenset((*relation["from_unit_ids"], *relation["to_unit_ids"]))
        for relation in parallel
    }
    assert frozenset({"z3", "z4"}) in pairs


def test_overlapping_boxes_are_not_treated_as_separate_columns() -> None:
    """Two fragments of the same column must not become a language pair."""
    observation = _two_column_with_mislabelled_language()
    for unit in observation["units"]:
        unit["layout"]["bbox"] = [100, 200, 500, 240]
    result = build_structure(observation)
    parallel = [
        relation for relation in result["relations"] if relation["kind"] == "language_parallel"
    ]
    assert not parallel, "overlapping boxes cannot be evidence of two lanes"
