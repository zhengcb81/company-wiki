"""index.json / coverage / C-verification cross references."""

from __future__ import annotations

from helpers import (
    C_CHECKS_PATH,
    CASE_FILE_NAMES,
    EVIDENCE_STATUS,
    EXPECTED_CASE_IDS,
    EXPECTED_RECORD_IDS,
    INDEX_PATH,
    MECHANISM_IDS,
    SCHEMA_C_CHECKS,
    SCHEMA_INDEX,
    SPEC_STATUS,
    load_case,
    load_json,
    load_record,
    normalized_quote,
)


def test_index_schema_and_record_paths() -> None:
    assert INDEX_PATH.exists(), "index.json (du2-facet-index/1) is a required deliverable"
    index = load_json(INDEX_PATH)
    assert index["schema_version"] == SCHEMA_INDEX
    assert set(index) == {"schema_version", "records", "coverage"}
    assert isinstance(index["records"], list) and index["records"]
    for rel_path in index["records"]:
        assert not rel_path.startswith(("/", "\\")) and ":" not in rel_path, (
            f"records entries must be relative portable paths, got {rel_path}"
        )
        assert (INDEX_PATH.parent / rel_path).exists(), f"index lists missing file {rel_path}"


def test_index_lists_every_record_exactly_once() -> None:
    index = load_json(INDEX_PATH)
    listed = sorted(index["records"])
    expected = sorted(f"records/{record_id}.json" for record_id in EXPECTED_RECORD_IDS)
    assert listed == expected, "index.json must list exactly the delivered record files"


def test_coverage_rows_are_valid_and_closed() -> None:
    index = load_json(INDEX_PATH)
    coverage = index["coverage"]
    assert isinstance(coverage, list) and coverage
    known_case_ids = set(CASE_FILE_NAMES)
    covered_facets = set()
    for row in coverage:
        assert set(row) == {
            "facet",
            "mechanism",
            "spec_status",
            "evidence_status",
            "integration_status",
            "case_ids",
            "gaps",
        }, f"coverage row keys fixed by contract, got {sorted(row)}"
        assert row["facet"] in EXPECTED_RECORD_IDS, f"unknown facet {row['facet']}"
        assert row["mechanism"] in MECHANISM_IDS, f"unknown mechanism {row['mechanism']}"
        assert row["spec_status"] in SPEC_STATUS
        assert row["evidence_status"] in EVIDENCE_STATUS
        assert row["integration_status"] == "not_integrated", (
            "this package never claims production integration"
        )
        unknown = set(row["case_ids"]) - known_case_ids
        assert not unknown, f"coverage references unknown cases {sorted(unknown)}"
        assert isinstance(row["gaps"], list)
        if row["evidence_status"] == "real":
            assert row["case_ids"], "real evidence rows must cite their anchoring cases"
            kinds = {case_id: load_case(case_id)["kind"] for case_id in row["case_ids"]}
            assert "real_excerpt" in set(kinds.values()), (
                f"row {row['facet']}/{row['mechanism']} claims real evidence but cites "
                f"no real_excerpt case: {kinds}"
            )
        if row["evidence_status"] == "synthetic_only":
            kinds = {case_id: load_case(case_id)["kind"] for case_id in row["case_ids"]}
            wrong = [case_id for case_id, kind in kinds.items() if kind != "synthetic"]
            assert not wrong, (
                f"row {row['facet']}/{row['mechanism']} is synthetic_only but cites "
                f"real cases {wrong}; record the gap instead"
            )
        if row["evidence_status"] == "missing":
            assert not row["case_ids"], "missing-evidence rows must not cite cases"
        covered_facets.add(row["facet"])
    missing = set(EXPECTED_RECORD_IDS) - covered_facets
    assert not missing, f"coverage rows missing for records: {sorted(missing)}"


def test_every_case_is_referenced_by_a_record_or_coverage() -> None:
    referenced = set()
    for record_id in EXPECTED_RECORD_IDS:
        referenced.update(load_record(record_id)["case_ids"])
    index = load_json(INDEX_PATH)
    for row in index["coverage"]:
        referenced.update(row["case_ids"])
    orphan = set(EXPECTED_CASE_IDS) - referenced
    assert not orphan, f"orphan cases (no record/coverage reference): {sorted(orphan)}"


def test_c_verification_records_exist_and_are_machine_readable() -> None:
    assert C_CHECKS_PATH.exists(), "C-node human-vs-original checks must be listed separately"
    payload = load_json(C_CHECKS_PATH)
    assert payload["schema_version"] == SCHEMA_C_CHECKS
    assert {"schema_version", "method_notes", "checks"} <= set(payload)
    assert isinstance(payload["checks"], list) and payload["checks"]
    for check in payload["checks"]:
        assert {
            "check_id",
            "sample_id",
            "source_sha256",
            "page",
            "quote",
            "method",
            "normalized_match",
            "sha256_verified",
        } <= set(check)
        assert check["normalized_match"] is True, "unverified quotes must not be recorded as matched"
        assert check["sha256_verified"] is True


def test_every_real_case_quote_is_covered_by_a_c_check() -> None:
    payload = load_json(C_CHECKS_PATH)
    verified = {(check["sample_id"], normalized_quote(check["quote"])) for check in payload["checks"]}
    for case_id in EXPECTED_CASE_IDS:
        case = load_case(case_id)
        if case["kind"] != "real_excerpt":
            continue
        sample_id = case["source"]["sample_id"]
        for unit in case["observation"]["units"]:
            anchor = unit["anchor"]
            if anchor is None:
                continue
            key = (sample_id, normalized_quote(anchor["exact_quote"]))
            assert key in verified, (
                f"{case_id} quote not verified against the original document: "
                f"{anchor['exact_quote'][:40]!r}"
            )


def test_real_case_sha_matches_c_checks() -> None:
    payload = load_json(C_CHECKS_PATH)
    sha_by_sample = {check["sample_id"]: check["source_sha256"] for check in payload["checks"]}
    for case_id in EXPECTED_CASE_IDS:
        case = load_case(case_id)
        if case["kind"] != "real_excerpt":
            continue
        sample_id = case["source"]["sample_id"]
        assert sha_by_sample[sample_id] == case["source"]["source_sha256"], (
            f"{case_id}: case sha must equal the C-verified original sha"
        )
