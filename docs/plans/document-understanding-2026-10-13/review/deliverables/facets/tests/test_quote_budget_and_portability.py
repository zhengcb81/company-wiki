"""Quote budgets, portability and persistent-size limits.

Contracts: every source's excerpts across all cases stay <= 8 KiB; fixtures stay
portable (no absolute paths, no raw copies); the package's persistent data stays
within the suggested 512 KiB.
"""

from __future__ import annotations

from helpers import (
    CASES_DIR,
    EXPECTED_CASE_IDS,
    FACETS_ROOT,
    INDEX_PATH,
    PERSISTENT_BUDGET_BYTES,
    QUOTE_BUDGET_BYTES_PER_SOURCE,
    RECORDS_DIR,
    load_case,
    load_json,
    utf8_len,
)

ABSOLUTE_PATH_MARKERS = ("C:\\", "C:/", "D:\\", "D:/", "/Users/", "/home/", "\\\\?\\")


def _real_case_quote_bytes_by_source() -> dict:
    totals: dict = {}
    for case_id in EXPECTED_CASE_IDS:
        case = load_case(case_id)
        if case["kind"] != "real_excerpt":
            continue
        sample_id = case["source"]["sample_id"]
        total = totals.setdefault(sample_id, 0)
        for unit in case["observation"]["units"]:
            total += utf8_len(unit["text"])
            if unit["anchor"] is not None:
                total += utf8_len(unit["anchor"]["exact_quote"])
        totals[sample_id] = total
    return totals


def test_quote_budget_per_source() -> None:
    totals = _real_case_quote_bytes_by_source()
    assert totals, "expected real excerpt cases"
    over = {
        sample_id: total
        for sample_id, total in totals.items()
        if total > QUOTE_BUDGET_BYTES_PER_SOURCE
    }
    assert not over, f"excerpt budget exceeded (<=8KiB per source): {over}"


def test_fixtures_carry_no_absolute_paths() -> None:
    offenders = []
    for directory in (RECORDS_DIR, CASES_DIR, FACETS_ROOT / "c_verification"):
        for path in sorted(directory.glob("*.json")):
            raw = path.read_text(encoding="utf-8")
            for marker in ABSOLUTE_PATH_MARKERS:
                if marker in raw:
                    offenders.append(f"{path.name}: {marker}")
    index_raw = INDEX_PATH.read_text(encoding="utf-8")
    for marker in ABSOLUTE_PATH_MARKERS:
        if marker in index_raw:
            offenders.append(f"index.json: {marker}")
    assert not offenders, f"portable fixtures must not embed absolute paths: {offenders}"


def test_no_raw_original_bytes_are_copied() -> None:
    """The package stores excerpts only; no PDF/HTML/HTM/TXT originals inside."""
    banned_suffixes = {".pdf", ".htm", ".html", ".txt", ".docx", ".pptx"}
    copied = [
        path.name
        for path in FACETS_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in banned_suffixes
    ]
    assert not copied, f"raw originals must not be copied into the package: {copied}"


def test_persistent_data_within_budget() -> None:
    total = 0
    for directory in (RECORDS_DIR, CASES_DIR, FACETS_ROOT / "c_verification"):
        for path in directory.glob("*.json"):
            total += path.stat().st_size
    total += INDEX_PATH.stat().st_size
    assert total <= PERSISTENT_BUDGET_BYTES, (
        f"persistent data {total} bytes exceeds the suggested 512 KiB budget"
    )


def test_synthetic_cases_never_embed_source_like_sha() -> None:
    for case_id in EXPECTED_CASE_IDS:
        case = load_case(case_id)
        if case["kind"] != "synthetic":
            continue
        assert case["source"]["source_sha256"] is None
        raw = (CASES_DIR / f"{case_id}.json").read_text(encoding="utf-8").lower()
        assert "source_ref" not in raw, "synthetic cases must not fabricate SourceRef structures"
