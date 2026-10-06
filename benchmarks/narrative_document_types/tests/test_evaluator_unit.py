"""Counterexample-first unit tests for the N5-DOCSET evaluator.

Every test below encodes a way a quality report can be wrong. They exist to
prove the evaluator rejects (or refuses to credit) each one, so the benchmark's
standards cannot drift into an all-green run.
"""

from __future__ import annotations

import hashlib

import pytest

from company_wiki.source_contract import (
    EvidenceCoordinates,
    EvidenceSpan,
    ParseStatus,
    source_id_for_sha256,
)
from evaluator import (
    GoldenValidationError,
    ReportValidationError,
    SCHEMA_VERSION,
    evaluate,
    quote_sha256,
    validate_report,
)


BASELINE = "e46108b4f30d5b7e47bfc712e360f173c00b702c"
PARSER = {"name": "selective_narrative_parser", "version": "0.1.0"}
SELECTOR = {"name": "select_narrative_evidence", "version": "0.3.1"}

SAMPLE_SHA = "b" * 64
SAMPLE = {
    "sample_id": "T01",
    "doc_type": "quarterly_report",
    "language": "zh",
    "sha256": SAMPLE_SHA,
    "byte_size": 4096,
    "metadata_is_fixture": True,
    "parser_options": {},
}


def _point(
    golden_id: str,
    quote: str,
    *,
    polarity: str = "positive",
    priority: str = "required",
    page: int = 1,
    expected_role: str = "company_statement",
    modality: str = "actual",
    negative_kind: str | None = None,
    quote_digest: str | None = None,
) -> dict:
    point = {
        "golden_id": golden_id,
        "topic": "主营进展" if polarity == "positive" else "负例",
        "polarity": polarity,
        "priority": priority,
        "expected_role": expected_role,
        "modality": modality,
        "locator": {"page_number": page},
        "quote": quote,
        "quote_sha256": quote_digest if quote_digest is not None else quote_sha256(quote),
        "reason": "unit fixture",
    }
    if negative_kind is not None:
        point["negative_kind"] = negative_kind
    return point


def _span(
    text: str,
    *,
    page: int = 1,
    paragraph: int = 0,
    role: str = "company_filing",
    line_start: int | None = None,
    span_id: str | None = None,
) -> EvidenceSpan:
    coordinates = (
        EvidenceCoordinates(page_number=page, paragraph_index=paragraph)
        if line_start is None
        else EvidenceCoordinates(paragraph_index=line_start - 1)
    )
    structured: dict = {
        "language": "zh",
        "selection_reasons": [],
        "source_role": role,
        "topics": [],
        "unit_kind": "pdf_text_block",
    }
    if line_start is not None:
        structured["line_start"] = line_start
        structured["line_end"] = line_start
    span = EvidenceSpan.create(
        source_id=source_id_for_sha256(SAMPLE_SHA),
        coordinates=coordinates,
        raw_text=text,
        structured_value=structured,
        parser_name=PARSER["name"],
        parser_version=PARSER["version"],
        parse_status=ParseStatus.PARSED,
        quality_flags=(),
    )
    if span_id is None:
        return span
    return span


def _golden(points: list[dict], *, scope: dict | None = None) -> dict:
    return {
        "schema_version": "narrative-document-quality-golden/1",
        "samples": {
            "T01": {
                "read_scope": scope
                if scope is not None
                else {
                    "unit": "pdf_page",
                    "pages_read": [1, 2, 3],
                    "pages_total": 3,
                    "uncovered": "unit fixture",
                    "ambiguities": [],
                },
                "points": points,
            }
        },
    }


def _default_points() -> list[dict]:
    return [
        _point("G1", "刻蚀设备已通过客户端验证", page=1),
        _point("G2", "新工厂预计明年投产", page=1, modality="planned"),
        _point("G3", "行业规模同比增长20%", page=2, modality="forecast"),
        _point("G4", "投资者提问关于产能", page=2, priority="optional",
               expected_role="question", modality="question"),
        _point("G5", "营业收入 1,234.56", polarity="negative", priority="reference",
               page=3, negative_kind="pure_financial_table"),
        _point("G6", "目录 第三节 管理层讨论与分析", polarity="negative",
               priority="reference", page=3, negative_kind="table_of_contents"),
    ]


def _selection(spans: list[EvidenceSpan], *, sha: str = SAMPLE_SHA) -> dict:
    return {
        "source_sha256": sha,
        "spans": spans,
        "parse": {"page_count": 3, "pages_read": 3, "coverage_complete": True},
        "status": "selected",
        "document_kind": "quarterly_report",
        "selection_limit": 96,
        "candidate_count": len(spans),
        "source_units": len(spans),
        "omitted_candidate_count": 0,
        "dropped_financial_count": 0,
        "selected_span_count": len(spans),
        "locator_roundtrip_verified": len(spans),
        "locator_roundtrip_failed": 0,
        "coverage_complete": True,
        "elapsed_seconds": 0.01,
    }


def _report(samples, golden, selections, *, locator_check=None) -> dict:
    partial = evaluate(
        samples=samples,
        golden=golden,
        selections=selections,
        locator_check=locator_check or (lambda sample, point: True),
    )
    partial.update(
        {
            "baseline": BASELINE,
            "parser": dict(PARSER),
            "selector": dict(SELECTOR),
            "scope": {
                "definition": "unit fixture scope",
                "denominators": {"required_coverage": "verified required positive points"},
            },
            "output_scope": "source-only",
        }
    )
    return partial


def _validate(report: dict, golden: dict) -> None:
    validate_report(
        report,
        samples=[SAMPLE],
        golden=golden,
        baseline=BASELINE,
        parser=PARSER,
        selector=SELECTOR,
    )


# --- 1. off-by-one page -----------------------------------------------------
def test_off_by_one_page_is_not_a_hit():
    quote = "刻蚀设备已通过客户端验证"
    golden = _golden(_default_points())
    wrong_page_span = _span(f"公司说：{quote}。", page=2, paragraph=1)
    report = _report([SAMPLE], golden, {"T01": _selection([wrong_page_span])})
    rows = {row["golden_id"]: row for row in report["samples"][0]["golden_results"]}
    assert rows["G1"]["result"] == "miss"
    assert rows["G1"]["matched_span_ids"] == []
    assert report["samples"][0]["required_coverage"]["numerator"] == 0
    assert report["samples"][0]["required_coverage"]["rate"] == 0.0
    _validate(report, golden)


# --- 2. similar paragraph must not be credited ------------------------------
def test_similar_paragraph_is_not_a_hit():
    golden = _golden(_default_points())
    near_miss = _span("公司说：刻蚀设备已通过客户端小批量验证阶段。", page=1, paragraph=0)
    report = _report([SAMPLE], golden, {"T01": _selection([near_miss])})
    rows = {row["golden_id"]: row for row in report["samples"][0]["golden_results"]}
    assert rows["G1"]["result"] != "full"
    assert report["samples"][0]["required_coverage"]["numerator"] == 0
    _validate(report, golden)


# --- 3. unknown golden reference -------------------------------------------
def test_unknown_golden_reference_is_rejected():
    golden = _golden(_default_points())
    report = _report([SAMPLE], golden, {"T01": _selection([])})
    report["samples"][0]["golden_results"].append(
        dict(report["samples"][0]["golden_results"][0], golden_id="G-DOES-NOT-EXIST")
    )
    with pytest.raises(ReportValidationError, match="unknown golden references"):
        _validate(report, golden)


# --- 4. wrong SHA -----------------------------------------------------------
def test_selection_with_wrong_sha_is_rejected():
    golden = _golden(_default_points())
    with pytest.raises(GoldenValidationError, match="sha"):
        evaluate(
            samples=[SAMPLE],
            golden=golden,
            selections={"T01": _selection([], sha="c" * 64)},
            locator_check=lambda sample, point: True,
        )


def test_report_with_wrong_sha_is_rejected():
    golden = _golden(_default_points())
    report = _report([SAMPLE], golden, {"T01": _selection([])})
    report["samples"][0]["source_sha256"] = "d" * 64
    with pytest.raises(ReportValidationError, match="sha does not match samples.json"):
        _validate(report, golden)


# --- 5. missing annotation scope -------------------------------------------
def test_missing_annotation_scope_is_rejected():
    golden = _golden(_default_points(), scope={"unit": "pdf_page", "pages_read": []})
    with pytest.raises(GoldenValidationError, match="pages_read is empty"):
        evaluate(
            samples=[SAMPLE],
            golden=golden,
            selections={"T01": _selection([])},
            locator_check=lambda sample, point: True,
        )


def test_report_without_declared_scope_denominators_is_rejected():
    golden = _golden(_default_points())
    report = _report([SAMPLE], golden, {"T01": _selection([])})
    report["scope"].pop("denominators")
    with pytest.raises(ReportValidationError, match="scope.denominators"):
        _validate(report, golden)


# --- 6. role / modality confusion ------------------------------------------
def test_statement_golden_matched_by_question_role_is_confusion():
    golden = _golden(_default_points())
    span = _span("公司说：刻蚀设备已通过客户端验证。", page=1, role="investor_question")
    report = _report([SAMPLE], golden, {"T01": _selection([span])})
    row = report["samples"][0]["golden_results"][0]
    assert row["result"] == "full"
    assert row["role_confusion"] is True
    assert row["modality_confusion"] is True
    assert report["samples"][0]["role_confusion"]["count"] == 1
    assert report["samples"][0]["modality_confusion"]["count"] == 1
    _validate(report, golden)


def test_question_golden_matched_by_company_filing_is_confusion():
    golden = _golden(_default_points())
    span = _span("投资者提问关于产能的完整句子。", page=2, role="company_filing")
    report = _report([SAMPLE], golden, {"T01": _selection([span])})
    row = next(
        item for item in report["samples"][0]["golden_results"] if item["golden_id"] == "G4"
    )
    assert row["result"] == "full"
    assert row["role_confusion"] is True
    assert row["modality_confusion"] is True


def test_matching_role_is_not_confusion():
    golden = _golden(_default_points())
    span = _span("投资者提问关于产能的完整句子。", page=2, role="investor_question")
    report = _report([SAMPLE], golden, {"T01": _selection([span])})
    row = next(
        item for item in report["samples"][0]["golden_results"] if item["golden_id"] == "G4"
    )
    assert row["result"] == "full"
    assert row["role_confusion"] is False
    assert row["modality_confusion"] is False
    _validate(report, golden)


# --- 7. quote integrity -----------------------------------------------------
def test_tampered_quote_hash_is_rejected():
    points = _default_points()
    points[0]["quote"] = "刻蚀设备已通过客户端复验"
    golden = _golden(points)
    with pytest.raises(GoldenValidationError, match="quote_sha256 does not match"):
        evaluate(
            samples=[SAMPLE],
            golden=golden,
            selections={"T01": _selection([])},
            locator_check=lambda sample, point: True,
        )


def test_unlocated_quote_is_marked_unverified_and_leaves_denominator():
    points = _default_points()
    golden = _golden(points)
    report = _report(
        [SAMPLE], golden, {"T01": _selection([])},
        locator_check=lambda sample, point: point["golden_id"] != "G1",
    )
    rows = {row["golden_id"]: row for row in report["samples"][0]["golden_results"]}
    assert rows["G1"]["verified"] is False
    assert report["samples"][0]["required_coverage"]["denominator"] == 2
    assert report["samples"][0]["required_coverage"]["unverified_required_excluded"] == 1
    _validate(report, golden)


def test_required_rate_is_null_when_no_required_points_are_verified():
    points = _default_points()
    golden = _golden(points)
    report = _report(
        [SAMPLE], golden, {"T01": _selection([])},
        locator_check=lambda sample, point: point["polarity"] != "positive",
    )
    coverage = report["samples"][0]["required_coverage"]
    assert coverage["denominator"] == 0
    assert coverage["rate"] is None
    _validate(report, golden)


# --- 8. noise and duplicate arithmetic -------------------------------------
def test_negative_match_counts_as_noise_and_reports_denominator():
    golden = _golden(_default_points())
    noise_span = _span("营业收入 1,234.56 与上期对比", page=3, paragraph=0)
    kept = _span("刻蚀设备已通过客户端验证。", page=1, paragraph=1)
    report = _report([SAMPLE], golden, {"T01": _selection([noise_span, kept])})
    noise = report["samples"][0]["noise"]
    assert noise["negative_points_hit"] == 1
    assert noise["noise_spans"] == 1
    assert noise["judged_in_scope"] == 2
    assert noise["selected_noise_rate"] == {
        "numerator": 1,
        "denominator": 2,
        "rate": 0.5,
        "definition": noise["selected_noise_rate"]["definition"],
    }
    _validate(report, golden)


def test_duplicate_ratio_counts_repeated_selected_text():
    golden = _golden(_default_points())
    duplicate = "刻蚀设备已通过客户端验证。"
    report = _report(
        [SAMPLE], golden, {"T01": _selection([_span(duplicate, page=1), _span(duplicate, page=1)])}
    )
    duplicate_row = report["samples"][0]["duplicate"]
    assert duplicate_row["duplicate_span_count"] == 1
    assert duplicate_row["total_selected"] == 2
    assert duplicate_row["duplicate_ratio"] == 0.5
    _validate(report, golden)


def test_spans_outside_annotation_scope_are_not_judged():
    golden = _golden(_default_points())
    outside = _span("营业收入 1,234.56", page=30, paragraph=0)
    report = _report([SAMPLE], golden, {"T01": _selection([outside])})
    noise = report["samples"][0]["noise"]
    assert noise["selected_span_count"] == 1
    assert noise["selected_in_scope"] == 0
    assert noise["judged_in_scope"] == 0
    assert noise["selected_noise_rate"]["rate"] is None
    _validate(report, golden)


# --- 9. the report cannot be tuned to all-green ----------------------------
def test_inflated_required_numerator_is_rejected():
    golden = _golden(_default_points())
    report = _report([SAMPLE], golden, {"T01": _selection([])})
    report["samples"][0]["required_coverage"]["numerator"] = 2
    report["totals"]["required_matched"] = 2
    with pytest.raises(ReportValidationError, match="required numerator"):
        _validate(report, golden)


def test_dropped_golden_point_is_rejected():
    golden = _golden(_default_points())
    report = _report([SAMPLE], golden, {"T01": _selection([])})
    report["samples"][0]["golden_results"].pop()
    with pytest.raises(ReportValidationError, match="must cover every annotated point"):
        _validate(report, golden)


def test_wrong_schema_or_baseline_is_rejected():
    golden = _golden(_default_points())
    report = _report([SAMPLE], golden, {"T01": _selection([])})
    report["schema_version"] = "narrative-document-quality/0"
    with pytest.raises(ReportValidationError, match="schema_version"):
        _validate(report, golden)
    report["schema_version"] = SCHEMA_VERSION
    report["baseline"] = "not-a-sha"
    with pytest.raises(ReportValidationError, match="baseline"):
        _validate(report, golden)


# --- 10. control: an honest report validates -------------------------------
def test_honest_report_validates_and_full_match_counts():
    points = _default_points()
    golden = _golden(points)
    spans = [
        _span("公司说：刻蚀设备已通过客户端验证。", page=1, paragraph=0),
        _span("新工厂预计明年投产。", page=1, paragraph=1),
        _span("行业规模同比增长20%。", page=2, paragraph=0),
        _span("投资者提问关于产能的完整句子。", page=2, paragraph=1, role="investor_question"),
        _span("别的内容", page=3, paragraph=0),
    ]
    report = _report([SAMPLE], golden, {"T01": _selection(spans)})
    coverage = report["samples"][0]["required_coverage"]
    assert coverage == {
        "numerator": 3,
        "denominator": 3,
        "rate": 1.0,
        "unverified_required_excluded": 0,
        "definition": coverage["definition"],
    }
    assert report["totals"]["required_coverage_rate"] == 1.0
    _validate(report, golden)


def test_evaluate_requires_golden_points_floor():
    points = _default_points()[:3]
    with pytest.raises(GoldenValidationError, match="at least 6 annotated points"):
        evaluate(
            samples=[SAMPLE],
            golden=_golden(points),
            selections={"T01": _selection([])},
            locator_check=lambda sample, point: True,
        )


def test_quote_hash_helper_matches_hashlib():
    quote = "刻蚀设备已通过客户端验证"
    assert quote_sha256(quote) == hashlib.sha256(quote.encode("utf-8")).hexdigest()
