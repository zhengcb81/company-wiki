"""Tests for the text-legibility check.

The check exists because a real PDF with a broken CID font mapping produces
9,618 units, zero quality flags and zero errors while every page is unreadable.
Its thresholds come from a measured control, and these tests pin both the firing
case and the clean cases so the threshold cannot silently drift.
"""

from __future__ import annotations

from tools.document_understanding_benchmark import evaluate
from tools.document_understanding_benchmark.checkers import (
    MAX_UNUSABLE_BLOCK_RATIO,
    UNUSABLE_BLOCKS,
)
from tools.document_understanding_benchmark.records import validate_gold, validate_observed


def _gold(language="zh-Hant"):
    return validate_gold(
        {
            "schema_version": "du-gold/1",
            "sample_id": "legibility",
            "source_sha256": "a" * 64,
            "scope": "development",
            "language": language,
            "expected_route_families": ["annual"],
            "facts": [
                {
                    "id": "f",
                    "importance": "critical",
                    "any_support_sets": [[{"page": 1, "exact_quote": "x"}]],
                }
            ],
        }
    )


def _observed(text):
    return validate_observed(
        {
            "schema_version": "du-observed/1",
            "sample_id": "legibility",
            "source_sha256": "a" * 64,
            "route": {"family": "annual"},
            "selected_locators": ["loc:v1/page:1/paragraph:1"],
            "selected_text": text,
            "semantic_units": [],
            "claims": [],
            "coverage": {"native_scan": "partial", "complete": False, "opaque_pages": []},
            "metrics": {},
            "execution": {"mode": "native", "calls": 0},
        }
    )


def _check(result, check_id="integrity.text_legibility"):
    return next(row for row in result["checks"] if row["check_id"] == check_id)


def test_clean_chinese_text_passes():
    text = "本公司截至二零二五年十二月三十一日止年度的收入為人民幣一千零三十四點六百萬元。" * 20
    assert _check(evaluate(_observed(text), _gold()))["status"] == "PASS"


def test_mojibake_from_a_broken_font_mapping_fails():
    """The real file's characters: CJK radicals, strokes, control pictures."""

    text = (
        "2025⸶\u2e68⟳␌ 昆姽灿 \u31ec况2025⸶12㛊31㖧灱᷏⋇㊮㘼傿㈍㨡˾⸵㝁 "
        "\u2f00\u2f01\u2f02\u31c0\u31c1\u2400\u2401\u2402\u4dc0\u4dc1 ䷿㓸℧ "
    ) * 30
    result = evaluate(_observed(text), _gold())
    row = _check(result)
    assert row["status"] == "FAIL", row["observed"]
    assert row["observed"]["unusable_block_ratio"] >= MAX_UNUSABLE_BLOCK_RATIO
    assert result["status"] == "FAIL"


def test_no_language_declared_is_not_evaluated():
    """Without a declared language the check must not guess."""

    text = "\u2f00\u31c0\u2400" * 200
    assert _check(evaluate(_observed(text), _gold(language=None)))["status"] == "NOT_EVALUATED"


def test_short_selection_is_not_evaluated():
    """A short or numeric-only selection is not evidence of a broken text layer."""

    assert _check(evaluate(_observed("12345"), _gold()))["status"] == "NOT_EVALUATED"


def test_empty_selection_is_not_evaluated_not_failed():
    """Nothing selected is a coverage matter, not a legibility failure."""

    assert _check(evaluate(_observed(""), _gold()))["status"] == "NOT_EVALUATED"


def test_a_few_radicals_do_not_trip_the_threshold():
    """A glossary or linguistic aside must not be reported as garbled text."""

    body = "本公司截至二零二五年十二月三十一日止年度的收入為人民幣。" * 40
    # ~0.2% unusable characters: well under the 0.5% threshold.
    text = body + ("\u2f00" * max(1, len(body) // 500))
    result = evaluate(_observed(text), _gold())
    row = _check(result)
    assert row["status"] == "PASS", row["observed"]
    assert row["observed"]["unusable_block_ratio"] < MAX_UNUSABLE_BLOCK_RATIO


def test_unusable_blocks_cover_the_measured_mojibake_blocks():
    """The block list must contain what the real garbled file actually used."""

    for code in (
        0x2E80,  # CJK radicals supplement
        0x2F00,  # Kangxi radical
        0x31C0,  # CJK stroke
        0x2400,  # control picture
        0xE000,  # private use
        0x4DC0,  # Yijing hexagram
        0x2500,  # box drawing
    ):
        assert any(low <= code <= high for low, high in UNUSABLE_BLOCKS), hex(code)


def test_parsed_text_measurement_takes_precedence_over_selection():
    """A garbled document can select almost nothing and still be unreadable.

    The real case: 415 pages, 270k unusable characters, but the selector kept
    only 195 characters. Judging the selection alone would report
    NOT_EVALUATED and the defect would stay invisible.
    """

    gold = _gold()
    observed = validate_observed(
        {
            "schema_version": "du-observed/1",
            "sample_id": "legibility",
            "source_sha256": "a" * 64,
            "route": {"family": "annual"},
            "selected_locators": ["loc:v1/page:9/paragraph:1"],
            # Short, and itself garbled: below the selection threshold.
            "selected_text": "\u2f00\u31c0\u2400\u4dc0" * 20,
            "semantic_units": [],
            "claims": [],
            "coverage": {"native_scan": "partial", "complete": False, "opaque_pages": []},
            # Measured over everything parsed.
            "metrics": {
                "read_text_dense_chars": 270005,
                "unusable_block_ratio": 0.02663,
                "unusable_block_chars": 7191,
            },
            "execution": {"mode": "native", "calls": 0},
        }
    )
    result = evaluate(observed, gold)
    row = _check(result)
    assert row["status"] == "FAIL", row["observed"]
    assert row["observed"]["basis"] == "parsed_text"
    assert row["observed"]["dense_chars"] == 270005


def test_clean_parsed_text_passes_on_the_parsed_basis():
    observed = validate_observed(
        {
            "schema_version": "du-observed/1",
            "sample_id": "legibility",
            "source_sha256": "a" * 64,
            "route": {"family": "annual"},
            "selected_locators": [],
            "selected_text": "",
            "semantic_units": [],
            "claims": [],
            "coverage": {"native_scan": "partial", "complete": False, "opaque_pages": []},
            "metrics": {
                "read_text_dense_chars": 136212,
                "unusable_block_ratio": 0.00076,
                "unusable_block_chars": 104,
            },
            "execution": {"mode": "native", "calls": 0},
        }
    )
    row = _check(evaluate(observed, _gold()))
    assert row["status"] == "PASS", row["observed"]
    assert row["observed"]["basis"] == "parsed_text"


def test_tiny_parsed_text_is_not_evaluated():
    observed = validate_observed(
        {
            "schema_version": "du-observed/1",
            "sample_id": "legibility",
            "source_sha256": "a" * 64,
            "route": {"family": "annual"},
            "selected_locators": [],
            "selected_text": "",
            "semantic_units": [],
            "claims": [],
            "coverage": {"native_scan": "partial", "complete": False, "opaque_pages": []},
            "metrics": {"read_text_dense_chars": 12, "unusable_block_ratio": 0.5},
            "execution": {"mode": "native", "calls": 0},
        }
    )
    assert _check(evaluate(observed, _gold()))["status"] == "NOT_EVALUATED"


def test_legibility_does_not_mask_a_missed_fact():
    """A passing legibility check must not rescue recall."""

    good = "本公司截至二零二五年十二月三十一日止年度的收入為人民幣一千零三十四點六百萬元。" * 20
    result = evaluate(_observed(good), _gold())
    assert _check(result)["status"] == "PASS"
    assert _check(result, "recall.f")["status"] == "FAIL"
    assert result["status"] == "FAIL"
