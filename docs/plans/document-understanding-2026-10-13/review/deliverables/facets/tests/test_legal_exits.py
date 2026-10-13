"""Legal exits and the correctness_if_emitted policy.

The benchmark must not force the engine to bloat: low-information documents,
documents with no business content, and questions management did not answer all
have legal exits. Pure financial numbers are never required selections; if the
engine emits them they must be right (correctness_if_emitted).
"""

from __future__ import annotations

from helpers import load_case


def test_low_information_exit() -> None:
    case = load_case("syn_exit_low_information")
    expectations = case["expectations"]
    assert expectations["disposition"] in {"generic_read", "eligible_skip_after_read"}
    required = [
        fact for fact in expectations["facts"] if fact["importance"] == "required_business"
    ]
    assert not required, "low-information documents must not conjure required business facts"
    assert expectations["not_evaluated"], "the exit must state what stays unevaluated"
    assert case.get("execution_status") == "NOT_RUN_ROOT_INTEGRATION"


def test_no_business_exit() -> None:
    case = load_case("syn_exit_no_business")
    expectations = case["expectations"]
    assert expectations["disposition"] == "eligible_skip_after_read"
    assert expectations["facts"] == [], "a no-business document exits without business facts"
    assert expectations["not_evaluated"], "explain the exit instead of inventing content"
    assert case["observation"]["units"], "the document was still read before the exit"


def test_no_answer_exit_keeps_question_and_denial_apart() -> None:
    case = load_case("syn_exit_no_answer")
    expectations = case["expectations"]
    assert expectations["disposition"] in {"read", "generic_read"}
    must_not = " ".join(
        entry for fact in expectations["facts"] for entry in fact["must_not_assert"]
    )
    assert must_not.strip(), "an unanswered question must pin what may not be asserted"
    assert "不回答" in must_not or "未回答" in must_not or "回避" in must_not, (
        "the exit must forbid upgrading non-answer into fact or denial"
    )


def test_financial_numbers_are_correctness_if_emitted_only() -> None:
    case = load_case("syn_financial_numbers")
    expectations = case["expectations"]
    importances = {fact["importance"] for fact in expectations["facts"]}
    assert "correctness_if_emitted" in importances, (
        "pure financial numbers belong to correctness_if_emitted"
    )
    route_text = " ".join(expectations["routing_notes"])
    assert "不要求" in route_text, (
        "routing notes must say selecting plain financial numbers is not required"
    )
    for fact in expectations["facts"]:
        if fact["importance"] == "correctness_if_emitted":
            assert fact["must_not_assert"] or fact["must_preserve"], (
                "if a financial number is emitted, its period/unit/subject must be pinned"
            )
