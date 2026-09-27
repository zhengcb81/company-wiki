from __future__ import annotations

import pytest

from scripts.narrative_summary_review_pilot import build_report


def _inputs(
    *,
    scope: str = "selected_span_window",
    role: str = "management",
    claim_type: str = "company_statement",
) -> tuple[dict, dict, dict]:
    span_id = "urn:company-wiki:evidence-span:sha256:" + "a" * 64
    source_sha = "b" * 64
    metrics = {
        "samples": [
            {
                "sample_id": "T01",
                "source_sha256": source_sha,
                "document_kind": "investor_call_transcript",
                "anchor_checks": [
                    {
                        "check_id": "C10",
                        "passed": True,
                        "match_scope": scope,
                        "matched_evidence_ids": [span_id],
                    }
                ],
                "selected_evidence_preview": [
                    {
                        "span_id": span_id,
                        "locator_v1": "loc:v1/paragraph:1/chars:0-20",
                        "source_role": role,
                        "quality_flags": [],
                        "excerpt": "Demand exceeds available supply.",
                    }
                ],
            }
        ]
    }
    manifest = {
        "samples": [
            {
                "id": "T01",
                "sha256_prefix": source_sha[:12],
                "language": "en",
            }
        ]
    }
    claims = {
        "authorship": "test fixture",
        "claims": [
            {
                "id": "C10-summary",
                "sample_id": "T01",
                "anchor_check_ids": ["C10"],
                "text": "Management said demand exceeds supply.",
                "claim_type": claim_type,
                "modality": "question" if claim_type == "analyst_question" else "actual",
            }
        ],
    }
    return metrics, claims, manifest


def test_summary_review_pilot_keeps_drafts_in_review_state() -> None:
    report = build_report(*_inputs())

    assert report["status"] == "citation_and_role_checks_passed"
    assert report["semantic_review"] == "not_performed; all drafts remain needs_review"
    assert report["drafts"][0]["draft_status"] == "needs_review"
    assert report["drafts"][0]["claims"][0]["evidence"][0]["source_role"] == "management"


def test_summary_review_pilot_rejects_page_only_anchor_match() -> None:
    with pytest.raises(ValueError, match="precise selected span"):
        build_report(*_inputs(scope="page_or_role_context_only"))


def test_summary_review_pilot_rejects_analyst_question_as_company_statement() -> None:
    with pytest.raises(ValueError, match="non-company evidence"):
        build_report(*_inputs(role="analyst"))


def test_summary_review_pilot_accepts_question_as_analyst_question_only() -> None:
    report = build_report(*_inputs(role="investor_question", claim_type="analyst_question"))

    assert report["drafts"][0]["claims"][0]["claim_type"] == "analyst_question"
    assert report["drafts"][0]["claims"][0]["modality"] == "question"


def test_summary_review_pilot_rejects_response_link_to_missing_question() -> None:
    metrics, claims, manifest = _inputs()
    claims["claims"][0]["response_to_claim_id"] = "missing-question"

    with pytest.raises(ValueError, match="target an analyst question"):
        build_report(metrics, claims, manifest)


def test_summary_review_pilot_rejects_translation_of_english_source() -> None:
    metrics, claims, manifest = _inputs()
    claims["claims"][0]["text"] = "管理层表示需求超过供应。"

    with pytest.raises(ValueError, match="language does not match source"):
        build_report(metrics, claims, manifest)


def test_summary_review_pilot_rejects_english_draft_for_chinese_source() -> None:
    metrics, claims, manifest = _inputs()
    manifest["samples"][0]["language"] = "zh"
    claims["claims"][0]["text"] = "Management said demand exceeded supply."

    with pytest.raises(ValueError, match="language does not match source"):
        build_report(metrics, claims, manifest)


def _question_answer_inputs() -> tuple[dict, dict, dict]:
    metrics, claims, manifest = _inputs()
    sample = metrics["samples"][0]
    answer = sample["selected_evidence_preview"][0]
    answer["qa_group_id"] = "qa-7"
    question_id = "urn:company-wiki:evidence-span:sha256:" + "c" * 64
    sample["selected_evidence_preview"].append(
        {
            "span_id": question_id,
            "locator_v1": "loc:v1/page:2/table:0/row:0/column:1",
            "source_role": "investor_question",
            "qa_group_id": "qa-7",
            "quality_flags": [],
            "excerpt": "The question asks about the product.",
        }
    )
    sample["anchor_checks"].append(
        {
            "check_id": "Q01",
            "passed": True,
            "match_scope": "selected_span_window",
            "matched_evidence_ids": [question_id],
        }
    )
    answer_claim = claims["claims"][0]
    answer_claim["response_to_claim_id"] = "Q01-summary"
    question_claim = {
        "id": "Q01-summary",
        "sample_id": "T01",
        "anchor_check_ids": ["Q01"],
        "text": "The investor asked about the product.",
        "claim_type": "analyst_question",
        "modality": "question",
    }
    claims["claims"].insert(0, question_claim)
    return metrics, claims, manifest


def test_summary_review_pilot_requires_same_qa_group_for_response_link() -> None:
    report = build_report(*_question_answer_inputs())

    answer = report["drafts"][0]["claims"][1]
    assert answer["response_to_claim_id"] == "Q01-summary"
    assert answer["qa_group_link_verified"] is True


def test_summary_review_pilot_rejects_cross_question_answer_link() -> None:
    metrics, claims, manifest = _question_answer_inputs()
    metrics["samples"][0]["selected_evidence_preview"][0]["qa_group_id"] = "qa-8"

    with pytest.raises(ValueError, match="do not share a qa_group_id"):
        build_report(metrics, claims, manifest)
