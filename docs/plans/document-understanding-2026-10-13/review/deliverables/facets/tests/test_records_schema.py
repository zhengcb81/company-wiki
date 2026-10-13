"""du2-facet-spec/1 record schema and vocabulary invariants."""

from __future__ import annotations

import pytest

from helpers import (
    ABSSENCE_MARKERS,
    CONFUSION_KEYS,
    EXPECTED_RECORD_IDS,
    FACT_IMPORTANCE,
    FORBIDDEN_COMPANY_TOKENS,
    ID_PATTERN,
    MECHANISM_IDS,
    MISSING_BEHAVIOR,
    POSITIVE_EVIDENCE_KEYS,
    RECORD_REQUIRED_FIELDS,
    RECORD_REQUIRED_KEYS,
    REGEX_METACHAR_PATTERN,
    SCHEMA_FACET,
    SLOT_NAMES,
    UNIT_KINDS,
    VERSION_PATTERN,
    load_record,
    record_path,
)


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_record_file_exists(record_id: str) -> None:
    assert record_path(record_id).exists(), f"missing record file for {record_id}"


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_record_required_fields(record_id: str) -> None:
    record = load_record(record_id)
    missing = RECORD_REQUIRED_FIELDS - set(record)
    assert not missing, f"{record_id} missing required fields: {sorted(missing)}"


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_record_identity_fields(record_id: str) -> None:
    record = load_record(record_id)
    assert record["schema_version"] == SCHEMA_FACET
    assert record["id"] == record_id
    assert ID_PATTERN.fullmatch(record["id"]), "id must be stable ascii slug, no company names"
    assert VERSION_PATTERN.fullmatch(record["version"]), "version must be semantic x.y.z"
    assert isinstance(record["business_questions"], list) and record["business_questions"]
    assert all(isinstance(item, str) and item.strip() for item in record["business_questions"])
    assert isinstance(record["summary_focus"], list) and record["summary_focus"]
    assert all(isinstance(item, str) and item.strip() for item in record["summary_focus"])


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_record_mechanism_enum(record_id: str) -> None:
    record = load_record(record_id)
    mechanisms = record["applicable_mechanisms"]
    assert isinstance(mechanisms, list) and mechanisms, "applicable_mechanisms must be non-empty"
    assert len(set(mechanisms)) == len(mechanisms), "duplicate mechanism entries"
    unknown = set(mechanisms) - MECHANISM_IDS
    assert not unknown, f"{record_id} unknown mechanisms: {sorted(unknown)}"


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_positive_evidence_shape(record_id: str) -> None:
    record = load_record(record_id)
    entries = record["positive_evidence"]
    assert isinstance(entries, list) and entries, "positive_evidence must be non-empty"
    for entry in entries:
        assert POSITIVE_EVIDENCE_KEYS <= set(entry), f"{record_id} evidence entry keys"
        assert isinstance(entry["description"], str) and entry["description"].strip()
        assert isinstance(entry["unit_kinds"], list) and entry["unit_kinds"]
        unknown = set(entry["unit_kinds"]) - UNIT_KINDS
        assert not unknown, f"{record_id} unknown unit_kinds: {sorted(unknown)}"
        assert isinstance(entry["signals"], list)
        for signal in entry["signals"]:
            assert isinstance(signal, str) and signal.strip(), "signals are plain phrases"
            assert not REGEX_METACHAR_PATTERN.search(signal), (
                f"{record_id} signal must be a plain phrase, not regex/DSL: {signal!r}"
            )


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_confusions_shape(record_id: str) -> None:
    record = load_record(record_id)
    confusions = record["confusions"]
    assert isinstance(confusions, list) and confusions, "confusions must be non-empty"
    for entry in confusions:
        assert CONFUSION_KEYS <= set(entry), f"{record_id} confusion keys"
        for key in ("source_meaning", "wrong_assertion", "why_wrong"):
            assert isinstance(entry[key], str) and entry[key].strip(), f"{record_id} confusion.{key}"
        slots = entry["required_context_slots"]
        assert isinstance(slots, list) and slots, f"{record_id} confusion needs slots"
        unknown = set(slots) - SLOT_NAMES
        assert not unknown, f"{record_id} confusion unknown slots: {sorted(unknown)}"


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_absence_rules_cover_all_four_states(record_id: str) -> None:
    record = load_record(record_id)
    rules = record["absence_rules"]
    assert isinstance(rules, list) and rules, "absence_rules must be non-empty"
    assert all(isinstance(item, str) and item.strip() for item in rules)
    blob = "\n".join(rules)
    for state, marker in ABSSENCE_MARKERS.items():
        assert marker.search(blob), (
            f"{record_id} absence_rules must distinguish {state} "
            f"(未披露/未答/否定/未读), got: {blob!r}"
        )


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_case_ids_reference_existing_case_files(record_id: str) -> None:
    from helpers import CASE_FILE_NAMES, case_path

    record = load_record(record_id)
    case_ids = record["case_ids"]
    assert isinstance(case_ids, list) and case_ids, f"{record_id} needs anchored cases"
    assert len(set(case_ids)) == len(case_ids), f"{record_id} duplicate case_ids"
    for case_id in case_ids:
        assert case_id in CASE_FILE_NAMES, f"{record_id} references unknown case {case_id}"
        assert case_path(case_id).exists(), f"{record_id} references missing case file {case_id}"


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_summary_focus_is_phrased_as_business_questions(record_id: str) -> None:
    """INTERFACES §3: summary_focus 是原语言业务问题，不产生投资结论。"""
    record = load_record(record_id)
    for item in record["summary_focus"]:
        assert "？" in item or "?" in item, (
            f"{record_id} summary_focus must be phrased as business questions, got {item!r}"
        )


def test_mechanism_records_have_no_company_product_lists() -> None:
    from helpers import load_json, record_path

    for record_id in EXPECTED_RECORD_IDS:
        if not record_id.startswith("mechanism_"):
            continue
        raw = record_path(record_id).read_text(encoding="utf-8").lower()
        hits = [token for token in FORBIDDEN_COMPANY_TOKENS if token.lower() in raw]
        assert not hits, (
            f"{record_id} must stay generic: found company/product tokens {hits}"
        )


def test_fact_importance_vocabulary_is_the_frozen_three() -> None:
    assert FACT_IMPORTANCE == {
        "required_business",
        "disposition_context",
        "correctness_if_emitted",
    }


def test_slot_and_missing_behavior_vocab_is_frozen() -> None:
    assert "modality" in SLOT_NAMES and "stage" in SLOT_NAMES and "denominator" in SLOT_NAMES
    assert MISSING_BEHAVIOR == {"unknown", "partial", "deferred"}
