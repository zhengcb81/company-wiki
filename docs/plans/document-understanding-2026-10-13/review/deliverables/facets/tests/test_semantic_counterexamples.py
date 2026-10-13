"""Counter-pair semantics handed to ROOT, marked NOT_RUN_ROOT_INTEGRATION.

This package cannot execute production semantic checks (no second summary
generator, no NL entailment checker). The paired counterexamples therefore
carry explicit inputs/expectations for ROOT and an execution_status that says
the production semantic run did NOT happen here. These tests enforce that
honesty marker and the mutation-dimension coverage of the pairing design.
"""

from __future__ import annotations

import pytest

from helpers import EXPECTED_CASE_IDS, load_case

NOT_RUN = "NOT_RUN_ROOT_INTEGRATION"

# The card requires paired cases that change 主体/时间/单位/范围/语态 or delete
# conditions, plus the three named semantic error classes (缺否定、错项目、未来当实际).
REQUIRED_DIMENSIONS = {
    "subject",
    "period",
    "unit",
    "scope",
    "modality",
    "condition",
    "negation",
    "project",
}


def _mutation_dimensions() -> set:
    covered = set()
    for case_id in EXPECTED_CASE_IDS:
        for mutation in load_case(case_id).get("mutations", []):
            covered.add(mutation["dimension"])
    return covered


def test_mutation_dimensions_cover_the_required_change_axes() -> None:
    covered = _mutation_dimensions()
    missing = REQUIRED_DIMENSIONS - covered
    assert not missing, f"paired cases must vary these axes: {sorted(missing)}"


def test_three_named_semantic_error_classes_are_paired() -> None:
    dims = _mutation_dimensions()
    for error_class, dimension in (
        ("缺否定/删否定", "negation"),
        ("错项目", "project"),
        ("未来当实际", "modality"),
    ):
        assert dimension in dims, f"missing paired counterexample for {error_class}"


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_semantic_execution_is_not_claimed_locally(case_id: str) -> None:
    case = load_case(case_id)
    has_semantic_payload = bool(case.get("mutations")) or "candidate_claim" in case
    if has_semantic_payload:
        assert case.get("execution_status") == NOT_RUN, (
            f"{case_id}: semantic counterexamples must record execution_status={NOT_RUN}; "
            f"this package does not run production semantics"
        )


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_real_cases_hand_meaning_checks_to_root_node_c(case_id: str) -> None:
    case = load_case(case_id)
    if case["kind"] != "real_excerpt":
        return
    assert case.get("execution_status") == NOT_RUN
    not_evaluated = " ".join(case["expectations"]["not_evaluated"])
    assert not_evaluated.strip(), "real cases must list what stays untested here"


def test_paired_cases_share_one_original_text() -> None:
    """Mutations change fields, never swap in a different source document."""
    for case_id in EXPECTED_CASE_IDS:
        case = load_case(case_id)
        mutations = case.get("mutations", [])
        if not mutations:
            continue
        source_pinned = case["source"]["source_sha256"] is not None or case["kind"] == "synthetic"
        assert source_pinned, f"{case_id}: counter-pair must keep one source (sha pinned)"
        for mutation in mutations:
            assert mutation["change"].strip(), "mutation must describe the field change"
