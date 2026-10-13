"""A-node RED: cross-page, role and unit integrity must hold before anything else.

Every assertion here is stated against the frozen du-input/1 fixtures in
``tests/fixtures/document_understanding_structure/inputs``.  Nothing in this
module reads the owner's catalog, a parser, the network, or the clock.
"""

from __future__ import annotations

import sys
from pathlib import Path


# ``parents[2]`` is the ``tests`` directory for this module's depth; the lane's fixtures
# live under ``tests/fixtures/document_understanding_structure``.
FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "document_understanding_structure"
if str(FIXTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(FIXTURE_ROOT))

# Imported by its unique module name, not as a bare ``fixtures``: the repository's own
# ``tests/fixtures`` directory is also on ``sys.path``, so a bare name resolves to whichever
# wins the race and collection fails when the DU unit suites run in one invocation.
from du_structure_fixtures import load_observation  # noqa: E402

from company_wiki.document_understanding.structure import build_structure  # noqa: E402


def _by_id(result: dict) -> dict[str, dict]:
    return {unit["unit_id"]: unit for unit in result["semantic_units"]}


def _members(unit: dict) -> list[str]:
    return list(unit["member_unit_ids"])


def _units_of_kind(result: dict, kind: str) -> list[dict]:
    return [unit for unit in result["semantic_units"] if unit["kind"] == kind]


# ---------------------------------------------------------------- schema


def test_output_is_du_structure_wire() -> None:
    result = build_structure(load_observation("toc_repeated_heading"))
    assert result["schema_version"] == "du-structure/1"
    assert result["source_ref"]["source_id"] == "opaque-source-toc"
    for key in ("sections", "semantic_units", "relations", "coverage", "diagnostics"):
        assert key in result


def test_source_ref_digest_is_passed_through_untouched() -> None:
    observation = load_observation("cross_page_project")
    result = build_structure(observation)
    assert result["source_ref"] == observation["source_ref"]


# ------------------------------------------------- TOC / repeated heading


def test_toc_entries_do_not_become_body_sections() -> None:
    result = build_structure(load_observation("toc_repeated_heading"))
    heading_ids = {
        unit_id
        for section in result["sections"]
        for unit_id in section["heading_unit_ids"]
    }
    assert "t2" not in heading_ids
    assert "t3" not in heading_ids
    toc_roles = {section["section_role"] for section in result["sections"]}
    assert "toc" not in toc_roles


def test_toc_and_running_header_are_reported_as_diagnostics_not_sections() -> None:
    result = build_structure(load_observation("toc_repeated_heading"))
    codes = {item["code"] for item in result["diagnostics"]}
    assert "TOC_ENTRIES_DETECTED" in codes
    assert "REPEATED_RUNNING_HEADER" in codes
    body_ids = {
        unit_id
        for section in result["sections"]
        for unit_id in section["body_unit_ids"]
    }
    assert "t6" not in body_ids  # page header
    assert "t9" not in body_ids


def test_body_heading_after_toc_still_opens_the_real_section() -> None:
    result = build_structure(load_observation("toc_repeated_heading"))
    sections = {section["section_id"]: section for section in result["sections"]}
    owner = next(
        section for section in sections.values() if "t7" in section["heading_unit_ids"]
    )
    assert "t8" in owner["body_unit_ids"]
    assert "t10" in owner["body_unit_ids"]


# --------------------------------------------------- cross-page project


def test_cross_page_project_keeps_subject_across_the_page_break() -> None:
    result = build_structure(load_observation("cross_page_project"))
    projects = _units_of_kind(result, "project")
    assert len(projects) == 1
    members = _members(projects[0])
    assert "p7" in members, "the sentence continuing onto page 63 was dropped"
    assert "p8" in members, "the continuation half on page 63 was dropped"
    assert "p5" in members, "the project table row lost its subject"


def test_cross_page_project_carries_its_header_units_and_continuation_relation() -> None:
    result = build_structure(load_observation("cross_page_project"))
    project = _units_of_kind(result, "project")[0]
    assert "p4" in _members(project)
    continuation = [
        relation for relation in result["relations"] if relation["kind"] == "continuation"
    ]
    assert continuation
    assert any("p7" in relation["from_unit_ids"] for relation in continuation)
    assert any("p8" in relation["to_unit_ids"] for relation in continuation)


def test_cross_page_project_does_not_swallow_the_next_page_section() -> None:
    result = build_structure(load_observation("cross_page_project"))
    project = _units_of_kind(result, "project")[0]
    members = _members(project)
    assert "p10" not in members, "new same-level heading must stop the continuation"
    assert "p11" not in members
    assert not any(
        "p11" in unit["member_unit_ids"]
        for unit in result["semantic_units"]
        if unit["kind"] == "project"
    )


def test_plan_and_actual_are_not_rewritten_into_each_other() -> None:
    """The project keeps plan wording; nothing asserts it is already producing."""
    result = build_structure(load_observation("cross_page_project"))
    project = _units_of_kind(result, "project")[0]
    assert project["completeness"] == "complete"
    assert not any("actual" in item["code"].lower() for item in project["diagnostics"])


# --------------------------------------------- adjacent / multi-subsection


def test_adjacent_projects_stay_separate_packages() -> None:
    result = build_structure(load_observation("adjacent_projects_multi_subsection"))
    projects = _units_of_kind(result, "project")
    member_sets = [set(_members(project)) for project in projects]
    assert len(projects) >= 2
    for left in range(len(member_sets)):
        for right in range(left + 1, len(member_sets)):
            assert not (member_sets[left] & member_sets[right]), "members leaked across projects"


def test_multi_subsection_project_absorbs_its_own_subsections() -> None:
    result = build_structure(load_observation("adjacent_projects_multi_subsection"))
    projects = _units_of_kind(result, "project")
    first = next(project for project in projects if "a2" in _members(project))
    members = set(_members(first))
    assert {"a3", "a4", "a5", "a6"} <= members
    assert "a7" not in members, "the second project's body must not join the first"
    assert "a9" not in members


# ----------------------------------------------------- bilingual columns


def test_bilingual_lanes_are_not_read_across_columns() -> None:
    result = build_structure(load_observation("bilingual_two_column"))
    chinese = next(
        section for section in result["sections"] if "b1" in section["heading_unit_ids"]
    )
    english = next(
        section for section in result["sections"] if "b2" in section["heading_unit_ids"]
    )
    assert chinese["language"] == "zh"
    assert english["language"] == "en"
    assert "b4" not in chinese["body_unit_ids"]
    assert "b3" not in english["body_unit_ids"]


def test_language_parallel_only_where_real_layout_evidence_exists() -> None:
    result = build_structure(load_observation("bilingual_two_column"))
    parallel = [
        relation for relation in result["relations"] if relation["kind"] == "language_parallel"
    ]
    assert parallel
    paired = {tuple(relation["from_unit_ids"]) + tuple(relation["to_unit_ids"]) for relation in parallel}
    assert any("b3" in pair and "b4" in pair for pair in paired)
    assert any("b5" in pair and "b7" in pair for pair in paired)


def test_language_alignment_never_deletes_source_units() -> None:
    observation = load_observation("bilingual_two_column")
    result = build_structure(observation)
    referenced = {
        unit_id
        for collection in ("sections", "semantic_units")
        for item in result[collection]
        for unit_id in (
            item["heading_unit_ids"] + item["body_unit_ids"]
            if collection == "sections"
            else item["member_unit_ids"]
        )
    }
    relations_referenced = {
        unit_id
        for relation in result["relations"]
        for unit_id in (*relation["from_unit_ids"], *relation["to_unit_ids"])
    }
    for unit in observation["units"]:
        if unit["kind"] == "header":
            continue
        assert unit["unit_id"] in referenced | relations_referenced


# ------------------------------------------------------------- QA roles


def test_qa_keeps_question_and_answer_roles_separate() -> None:
    result = build_structure(load_observation("qa_question_page_then_answer_page"))
    exchanges = _units_of_kind(result, "qa_exchange")
    assert exchanges, "no qa_exchange semantic unit was produced"
    first = next(
        exchange for exchange in exchanges if "q1" in exchange["member_unit_ids"]
    )
    assert "q2" in first["member_unit_ids"], "the question tail on the next page was dropped"
    assert "q3" in first["member_unit_ids"], "the answer on the next page was dropped"
    assert "q4" not in first["member_unit_ids"], "the second question leaked into the first exchange"


def test_qa_relation_binds_question_to_answer() -> None:
    result = build_structure(load_observation("qa_question_page_then_answer_page"))
    pairs = [
        relation for relation in result["relations"] if relation["kind"] == "question_answer"
    ]
    assert pairs
    assert any(
        {"q1", "q2"} & set(relation["from_unit_ids"]) and "q3" in relation["to_unit_ids"]
        for relation in pairs
    )


def test_management_denial_is_preserved_verbatim_in_membership() -> None:
    """The negative answer must remain a member; it must not be dropped or rewritten."""
    result = build_structure(load_observation("qa_question_page_then_answer_page"))
    exchanges = _units_of_kind(result, "qa_exchange")
    first = next(exchange for exchange in exchanges if "q1" in exchange["member_unit_ids"])
    assert "q3" in first["member_unit_ids"]
    assert not any(
        "denial_dropped" in item["code"] for item in first["diagnostics"]
    )


def test_question_without_answer_is_not_invented() -> None:
    observation = load_observation("qa_question_page_then_answer_page")
    for unit in observation["units"]:
        if unit["unit_id"] == "q5":
            unit["hints"]["speaker"] = "management"
    observation["units"] = [unit for unit in observation["units"] if unit["unit_id"] != "q5"]
    result = build_structure(observation)
    exchanges = _units_of_kind(result, "qa_exchange")
    second = next(
        (exchange for exchange in exchanges if "q4" in exchange["member_unit_ids"]), None
    )
    assert second is not None
    assert second["completeness"] == "partial"
    assert any("ANSWER_MISSING" in item["code"] for item in second["diagnostics"])


# -------------------------------------------------- operating table


def test_operating_table_requires_header_units_and_period() -> None:
    result = build_structure(load_observation("operating_table_units_years_footnote"))
    tables = _units_of_kind(result, "operating_table")
    assert tables
    capacity = next(table for table in tables if "g4" in table["member_unit_ids"])
    members = set(capacity["member_unit_ids"])
    assert "g2" in members, "the unit caption was dropped"
    assert "g3" in members, "the period header was dropped"
    assert "g5" in members, "the footnote was dropped"


def test_financial_table_rows_do_not_join_the_operating_table() -> None:
    result = build_structure(load_observation("operating_table_units_years_footnote"))
    tables = _units_of_kind(result, "operating_table")
    capacity = next(table for table in tables if "g4" in table["member_unit_ids"])
    assert "g7" not in capacity["member_unit_ids"]
    assert "g6" not in capacity["member_unit_ids"]


# ------------------------------------------------------- scanned gap


def test_scanned_gap_forces_partial_and_reports_deferred_pages() -> None:
    result = build_structure(load_observation("scanned_missing_page"))
    coverage = result["coverage"]
    assert coverage["complete"] is False
    assert 2 in coverage["opaque_pages"]
    assert 4 in coverage["deferred_unit_ids"] or coverage["native_scan"] == "partial"


def test_empty_native_text_is_not_treated_as_no_content() -> None:
    result = build_structure(load_observation("scanned_missing_page"))
    codes = {item["code"] for item in result["diagnostics"]}
    assert "OPAQUE_PAGE" in codes
