"""W23 OCR comparison metrics: frozen-behaviour tests (TDD, no model, no net).

Locks the comparator contracts the task card requires: strict/narrow CER and
English WER on known examples, insertion/deletion separation, timeout and
empty responses never counting as pass, duplicate lines adding no recall,
page mismatch rejection, and no heavy imports at unit level.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.ocr_comparison.metrics import (
    cer_strict,
    cer_strict_ops,
    char_error_rate,
    extract_numbers,
    number_prf,
    narrow_normalize,
    wer,
)


def test_no_heavy_imports_at_unit_level():
    heavy = [name for name in sys.modules if name.split(".")[0] in {"torch", "transformers", "rapidocr", "onnxruntime"}]
    assert heavy == []


def test_cer_strict_known_example():
    # gold: 产能约为6,300万片 ; hyp dropped the 3 -> one deletion over 10 chars
    ref = "产能约为6300万片"
    hyp = "产能约为630万片"
    distance, ops = cer_strict_ops(ref, hyp)
    assert distance == 1
    assert ops == {"insertions": 0, "deletions": 1, "substitutions": 0}
    assert char_error_rate(ref, hyp) == pytest.approx(1 / len(ref))


def test_cer_insertions_not_confused_with_deletions():
    assert cer_strict_ops("ABC", "ABXC")[1] == {"insertions": 1, "deletions": 0, "substitutions": 0}
    assert cer_strict_ops("ABXC", "ABC")[1] == {"insertions": 0, "deletions": 1, "substitutions": 0}
    assert cer_strict_ops("ABC", "AXD")[1] == {"insertions": 0, "deletions": 0, "substitutions": 2}


def test_cer_strict_keeps_real_character_differences():
    # 繁简/异体差异必须留在 strict CER 里，不得静默抵消
    assert cer_strict_ops("雲計算收入", "云计算收入")[0] == 2


def test_narrow_normalization_is_declared_and_narrow():
    # declared: NFC compose + whitespace removal only.  No script folding,
    # no synonym replacement, no case folding.
    assert narrow_normalize("A B\u3000c\r\n") == "ABc"
    assert narrow_normalize("雲") == "雲"
    assert narrow_normalize("云") == "云"
    assert narrow_normalize("Hello World") == "HelloWorld"
    with pytest.raises(ValueError):
        # normalization must not silently translate synonyms
        narrow_normalize("腾讯", fold_synonyms=True)


def test_cer_normalized_uses_declared_rules():
    ref = "總收入 2,703.7百萬元"
    hyp = "總收入2,703.7百萬元"
    strict = cer_strict(narrow_normalize(ref), narrow_normalize(hyp))
    assert strict == 0


def test_wer_known_example():
    ref = "revenues grew by 13% to RMB 21.9 billion"
    hyp = "revenues grew 13% to RMB 21.9 billion"
    distance, ops, ref_n = wer(ref, hyp)
    assert ref_n == 8
    assert distance == 1
    assert ops["deletions"] == 1


def test_wer_case_and_edge_punctuation_declared():
    # declared: lowercase + strip edge punctuation per token
    assert wer("Revenues grew.", "revenues grew")[0] == 0


def test_number_extraction_units_and_signs():
    nums = extract_numbers("總收入2,703.7百萬元（392.0百萬美元），同比+37.2%，環比-2.1%，約30億元, up 13% to RMB 21.9 billion")
    text_tokens = {n["text"] for n in nums}
    assert "2,703.7" in text_tokens
    assert "392.0" in text_tokens
    assert "+37.2%" in text_tokens
    assert "-2.1%" in text_tokens
    assert "30" in text_tokens
    assert "21.9" in text_tokens
    units = {n["value"]: n["unit"] for n in nums}
    assert units["2,703.7"] == "百萬元"
    assert units["+37.2"] == "%"
    assert units["21.9"] == "billion"


def test_number_recall_duplicates_add_nothing():
    gold = extract_numbers("产量4,281,084辆，同比41.12%")
    hyp = extract_numbers("4,281,084 4,281,084 4,281,084 41.12% 41.12%")
    prf = number_prf(gold, hyp)
    assert prf["gold_total"] == 2
    assert prf["recall_hits"] == 2
    assert prf["hyp_total"] == 2  # deduplicated, repeats add no recall
    assert prf["precision_hits"] == 2


def test_number_fabrication_counts_against_precision():
    gold = extract_numbers("产能约6,300万片")
    hyp = extract_numbers("产能约6,500万片 6,300万片")
    prf = number_prf(gold, hyp)
    assert prf["recall_hits"] == 1
    assert prf["hyp_total"] == 2
    assert prf["precision_hits"] == 1


def test_superscript_marker_not_a_number():
    # ksy gold records 392.0 (superscript footnote excluded); 392.01 is wrong
    gold = extract_numbers("（392.0百萬美元）")
    hyp = extract_numbers("（392.01百萬美元）")
    prf = number_prf(gold, hyp)
    assert prf["recall_hits"] == 0


@pytest.mark.parametrize(
    "status,expected_pass",
    [
        ("ok", True),
        ("timeout", False),
        ("truncated", False),
        ("empty_response", False),
        ("error", False),
        ("not_run", False),
        ("unsupported", False),
    ],
)
def test_timeout_truncation_empty_never_pass(status, expected_pass):
    from tools.ocr_comparison.metrics import counts_as_pass

    assert counts_as_pass(status) is expected_pass


def test_empty_response_detected_as_empty():
    from tools.ocr_comparison.backends.base import classify_raw_output

    assert classify_raw_output("   \n  ", finish_reason="stop") == "empty_response"
    assert classify_raw_output("正文", finish_reason="stop") == "ok"
    assert classify_raw_output("被截断的正文", finish_reason="length") == "truncated"


def test_page_mismatch_rejected():
    from tools.ocr_comparison.cache import cache_key

    identity = {"backend": "x1", "model_revision": "r1"}
    key_a = cache_key(identity, "page_sha_a", "prompt_sha", {"max_new_tokens": 512})
    key_b = cache_key(identity, "page_sha_b", "prompt_sha", {"max_new_tokens": 512})
    assert key_a != key_b


def test_cache_key_separates_backend_identity_axes():
    from tools.ocr_comparison.cache import cache_key

    base = {"backend": "x1", "model_revision": "r1", "precision": "bfloat16"}
    prompt_sha = "p" * 8
    params = {"max_new_tokens": 512}
    same = cache_key(base, "page", prompt_sha, params)
    assert same == cache_key(dict(base), "page", prompt_sha, params)
    for changed in (
        {**base, "model_revision": "r2"},
        {**base, "precision": "float32"},
        {**base, "prompt": "different"},
        {**base, "preprocess": "fit_image_v2"},
    ):
        assert cache_key(changed, "page", prompt_sha, params) != same
    assert cache_key(base, "page", prompt_sha, {"max_new_tokens": 256}) != same


def test_cache_hit_keeps_original_latency_not_zero():
    from tools.ocr_comparison.cache import ResultCache

    cache = ResultCache()
    record = {
        "status": "ok",
        "engine_seconds": 41.5,
        "text_sha256": "a" * 64,
        "raw_output_sha256": "b" * 64,
    }
    cache.put("k1", record)
    hit = cache.get("k1")
    assert hit is not None
    assert hit["cache_hit"] is True
    assert hit["engine_seconds"] == 41.5


def test_partial_failure_not_batch_pass():
    from tools.ocr_comparison.runner import batch_summary

    records = [
        {"page_id": "a", "status": "ok"},
        {"page_id": "b", "status": "timeout"},
        {"page_id": "c", "status": "ok"},
    ]
    summary = batch_summary(records)
    assert summary["pages_total"] == 3
    assert summary["pages_ok"] == 2
    assert summary["batch_status"] == "partial"


def test_output_cap_flags_truncation():
    from tools.ocr_comparison.backends.base import enforce_output_cap

    capped, status = enforce_output_cap("x" * 100, cap=50)
    assert len(capped) == 50
    assert status == "truncated"
    intact, status = enforce_output_cap("short", cap=50)
    assert status == "ok"
    assert intact == "short"


def test_null_locator_fields_stay_null():
    from tools.ocr_comparison.backends.base import serialize_lines

    lines = serialize_lines([{"text": "字", "bbox": None, "confidence": None}])
    assert lines[0]["bbox"] is None
    assert lines[0]["confidence"] is None
    assert "locator_quality" in lines[0]


def test_fault_injected_retry_records_inference_not_duplicate_page():
    """Recovered run must not duplicate pages or hide the extra inference."""
    from tools.ocr_comparison.runner import run_pages

    calls = {"n": 0}

    def flaky_backend(page):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("injected transient failure")
        return {"status": "ok", "engine_seconds": 1.0, "text": "内容"}

    records = run_pages(
        ["p1", "p2"],
        flaky_backend,
        max_retries=1,
        retry_on=(RuntimeError,),
    )
    assert calls["n"] == 3  # p1 fail + retry, p2 once: no duplicated page work
    assert [r["status"] for r in records] == ["ok", "ok"]
    assert records[0]["retries"] == 1
    assert records[1]["retries"] == 0
    assert len({r["page_id"] for r in records}) == 2


def test_truncation_marker_repetition_guard_flags_loops():
    from tools.ocr_comparison.backends.base import detect_repetition

    report = detect_repetition("内容" * 200, min_repeats=8)
    assert report["suspicious"] is True
    ok = detect_repetition("正常的一段话，不含循环。", min_repeats=8)
    assert ok["suspicious"] is False
