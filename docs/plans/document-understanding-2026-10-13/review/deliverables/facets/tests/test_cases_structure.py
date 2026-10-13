"""du2-reading-case/1 structural invariants (support sets, anchors, mutations)."""

from __future__ import annotations

import pytest

from helpers import (
    CASE_REQUIRED_FIELDS,
    DISPOSITIONS,
    EXPECTED_CASE_IDS,
    FACT_IMPORTANCE,
    FACT_KEYS,
    MUTATION_DIMENSIONS,
    MUTATION_KEYS,
    SCHEMA_CASE,
    SHA256_PATTERN,
    SLOT_NAMES,
    UNIT_KEYS,
    case_path,
    load_case,
)


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_case_file_exists(case_id: str) -> None:
    assert case_path(case_id).exists(), f"missing case file for {case_id}"


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_case_required_fields(case_id: str) -> None:
    case = load_case(case_id)
    assert case["schema_version"] == SCHEMA_CASE
    missing = CASE_REQUIRED_FIELDS - set(case)
    assert not missing, f"{case_id} missing fields: {sorted(missing)}"
    assert case["case_id"] == case_id
    assert case["kind"] in {"synthetic", "real_excerpt"}


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_source_shape(case_id: str) -> None:
    case = load_case(case_id)
    source = case["source"]
    assert {"sample_id", "source_sha256", "origin", "local_binding_key"} <= set(source)
    assert isinstance(source["sample_id"], str) and source["sample_id"].strip()
    if case["kind"] == "real_excerpt":
        assert isinstance(source["source_sha256"], str), "real excerpts pin the original SHA"
        assert SHA256_PATTERN.fullmatch(source["source_sha256"]), f"{case_id} bad sha256"
        assert isinstance(source["local_binding_key"], str) and source["local_binding_key"].strip()
        assert isinstance(source["origin"], dict) and source["origin"], "origin carries 资料属性"
        assert "synthetic" not in source["origin"]
    else:
        assert source["source_sha256"] is None, "synthetic cases must not fake a source SHA"
        assert source["origin"].get("synthetic") is True


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_observation_units_and_anchors(case_id: str) -> None:
    case = load_case(case_id)
    observation = case["observation"]
    assert {"metadata", "units"} <= set(observation)
    assert isinstance(observation["metadata"], dict)
    units = observation["units"]
    assert isinstance(units, list) and units, f"{case_id} needs observed units"
    unit_ids = [unit["unit_id"] for unit in units]
    assert len(set(unit_ids)) == len(unit_ids), f"{case_id} duplicate unit_id"
    for unit in units:
        assert UNIT_KEYS <= set(unit), f"{case_id} unit keys"
        assert isinstance(unit["unit_id"], str) and unit["unit_id"].strip()
        assert isinstance(unit["text"], str) and unit["text"].strip(), f"{case_id} unit text"
        assert isinstance(unit["role"], str) and unit["role"].strip(), f"{case_id} unit role"
        assert isinstance(unit["hints"], dict)
        locator = unit["locator"]
        anchor = unit["anchor"]
        if locator is None:
            assert anchor is not None, (
                f"{case_id}: locator=null requires an exact_quote anchor"
            )
            assert isinstance(anchor["exact_quote"], str) and anchor["exact_quote"].strip()
            carrier = observation["metadata"].get("carrier", "pdf")
            if carrier not in {"html", "htm", "txt"}:
                assert anchor["physical_page"] is not None or anchor["line"] is not None, (
                    f"{case_id}: paged sources need page/line with the quote anchor"
                )
        else:
            assert isinstance(locator, str) and locator.strip()
        if anchor is not None:
            assert set(anchor) == {"physical_page", "line", "exact_quote"}
            assert isinstance(anchor["exact_quote"], str) and anchor["exact_quote"].strip()
            assert anchor["physical_page"] is None or isinstance(anchor["physical_page"], int)
            assert anchor["line"] is None or isinstance(anchor["line"], int)


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_expectations_and_facts(case_id: str) -> None:
    case = load_case(case_id)
    expectations = case["expectations"]
    assert {"routing_notes", "facts", "disposition", "not_evaluated"} <= set(expectations)
    assert isinstance(expectations["routing_notes"], list)
    assert expectations["disposition"] in DISPOSITIONS, f"{case_id} disposition"
    assert isinstance(expectations["not_evaluated"], list), (
        f"{case_id} must name what this package does not evaluate"
    )

    unit_ids = {unit["unit_id"] for unit in case["observation"]["units"]}
    fact_ids = [fact["id"] for fact in expectations["facts"]]
    assert len(set(fact_ids)) == len(fact_ids), f"{case_id} duplicate fact id"
    for fact in expectations["facts"]:
        assert FACT_KEYS <= set(fact), f"{case_id} fact keys"
        assert isinstance(fact["objective"], str) and fact["objective"].strip()
        assert fact["importance"] in FACT_IMPORTANCE, f"{case_id} fact importance"
        support_sets = fact["any_support_sets"]
        assert isinstance(support_sets, list) and support_sets, (
            f"{case_id}/{fact['id']} needs at least one support set (outer OR, inner AND)"
        )
        for support_set in support_sets:
            assert isinstance(support_set, list) and support_set, "inner AND set must be non-empty"
            unknown = set(support_set) - unit_ids
            assert not unknown, f"{case_id}/{fact['id']} support set references unknown units {unknown}"
        assert isinstance(fact["must_preserve"], list)
        assert isinstance(fact["must_not_assert"], list)
        if fact["importance"] == "required_business":
            assert fact["must_preserve"], (
                f"{case_id}/{fact['id']} required_business facts must name the "
                f"conditions that travel with the assertion"
            )


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_mutations_shape(case_id: str) -> None:
    case = load_case(case_id)
    mutations = case.get("mutations", [])
    assert isinstance(mutations, list)
    mutation_ids = [mutation["id"] for mutation in mutations]
    assert len(set(mutation_ids)) == len(mutation_ids), f"{case_id} duplicate mutation id"
    for mutation in mutations:
        assert MUTATION_KEYS <= set(mutation), f"{case_id} mutation keys"
        assert mutation["dimension"] in MUTATION_DIMENSIONS, (
            f"{case_id} mutation dimension {mutation['dimension']}"
        )
        for key in ("change", "expected_failure", "reason"):
            assert isinstance(mutation[key], str) and mutation[key].strip(), (
                f"{case_id} mutation {mutation['id']} needs {key}"
            )


@pytest.mark.parametrize("case_id", EXPECTED_CASE_IDS)
def test_candidate_claim_is_explicit_structural_fields(case_id: str) -> None:
    case = load_case(case_id)
    claim = case.get("candidate_claim")
    expected_missing = case.get("expected_missing_slots")
    if claim is None and expected_missing is None:
        return
    assert isinstance(claim, dict) and expected_missing is not None, (
        f"{case_id}: expected_missing_slots requires candidate_claim"
    )
    unknown_keys = set(claim) - SLOT_NAMES
    assert not unknown_keys, f"{case_id} candidate_claim unknown keys: {sorted(unknown_keys)}"
    unknown_slots = set(expected_missing) - SLOT_NAMES
    assert not unknown_slots, f"{case_id} expected_missing_slots unknown: {sorted(unknown_slots)}"
    for slot in expected_missing:
        assert claim.get(slot) is None, (
            f"{case_id}: expected_missing slot {slot!r} must be null/absent in candidate_claim, "
            f"got {claim.get(slot)!r}"
        )
