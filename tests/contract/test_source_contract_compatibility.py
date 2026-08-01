"""CW-1 consumer contracts for source-contract compatibility and deprecation."""

from copy import deepcopy
from datetime import date
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_NAMES = ("evidence_span", "source_export", "source_manifest")
CURRENT_VERSIONS = {
    "evidence_span": "1.0.0",
    "source_export": "1.0.0",
    "source_manifest": "1.0.0",
}
POLICY_FIELDS = {
    "policy_schema_version",
    "contracts",
    "compatible_version_sets",
    "compatibility",
    "deprecation_notices",
}
COMPATIBILITY_FIELDS = {
    "negotiation",
    "stable_versions_only",
    "unknown_fields_fail_closed",
    "breaking_changes_require_new_major",
    "minimum_deprecation_notice_days",
    "minimum_minor_overlap_releases",
}
NOTICE_FIELDS = {
    "contract",
    "version",
    "status",
    "announced_on",
    "sunset_on",
    "replacement_version",
    "reason",
    "migration_guide",
}


def _contract():
    module_name = "company_wiki.source_contract"
    assert importlib.util.find_spec(module_name) is not None
    return importlib.import_module(module_name)


def _policy(module):
    return module.load_compatibility_policy()


def _consumer_support(*, manifest=("1.0.0",), span=("1.0.0",), export=("1.0.0",)):
    return {
        "source_manifest": list(manifest),
        "evidence_span": list(span),
        "source_export": list(export),
    }


def _policy_with_retiring_manifest(module):
    policy = _policy(module)
    policy["contracts"]["source_manifest"]["supported_versions"] = [
        "0.9.0",
        "1.0.0",
    ]
    policy["compatible_version_sets"].insert(
        0,
        {
            "evidence_span": "1.0.0",
            "source_export": "1.0.0",
            "source_manifest": "0.9.0",
        },
    )
    policy["deprecation_notices"] = [
        {
            "contract": "source_manifest",
            "version": "0.9.0",
            "status": "deprecated",
            "announced_on": "2026-01-01",
            "sunset_on": "2026-06-30",
            "replacement_version": "1.0.0",
            "reason": "The v1 source identity is now the canonical upstream contract.",
            "migration_guide": "docs/contracts/source-contract-compatibility-v1.md#migration",
        }
    ]
    return policy


def test_published_policy_is_packaged_strict_and_matches_runtime_versions():
    module = _contract()
    policy = _policy(module)

    assert module.SOURCE_CONTRACT_COMPATIBILITY_POLICY_VERSION == "1.0.0"
    assert module.SOURCE_CONTRACT_NAMES == CONTRACT_NAMES
    assert set(policy) == POLICY_FIELDS
    assert policy["policy_schema_version"] == "1.0.0"
    assert tuple(policy["contracts"]) == CONTRACT_NAMES
    assert policy["compatible_version_sets"] == [CURRENT_VERSIONS]
    assert set(policy["compatibility"]) == COMPATIBILITY_FIELDS
    assert policy["deprecation_notices"] == []

    actual = {
        "source_manifest": module.SOURCE_MANIFEST_SCHEMA_VERSION,
        "evidence_span": module.EVIDENCE_SPAN_SCHEMA_VERSION,
        "source_export": module.SOURCE_EXPORT_SCHEMA_VERSION,
    }
    assert actual == CURRENT_VERSIONS
    assert {
        name: entry["current_version"]
        for name, entry in policy["contracts"].items()
    } == CURRENT_VERSIONS
    assert all(
        entry["supported_versions"] == [entry["current_version"]]
        for entry in policy["contracts"].values()
    )


def test_policy_loader_returns_fresh_validated_values():
    module = _contract()
    first = _policy(module)
    first["contracts"]["source_manifest"]["supported_versions"].append("9.9.9")

    second = _policy(module)
    assert second["contracts"]["source_manifest"]["supported_versions"] == [
        "1.0.0"
    ]
    assert module.validate_compatibility_policy(second) == second


def test_policy_canonical_json_and_hash_are_deterministic():
    module = _contract()
    policy = _policy(module)
    text = module.canonical_compatibility_policy_json(policy)

    assert text == json.dumps(
        policy,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    assert module.compatibility_policy_sha256(policy) == hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()
    assert module.canonical_compatibility_policy_json() == text
    assert module.compatibility_policy_sha256() == module.compatibility_policy_sha256()


def test_json_schemas_and_export_references_match_the_policy():
    module = _contract()
    policy = _policy(module)
    manifest_schema = module.load_source_manifest_schema()
    span_schema = module.load_evidence_span_schema()

    assert manifest_schema["properties"]["schema_version"]["const"] == policy[
        "contracts"
    ]["source_manifest"]["current_version"]
    assert span_schema["properties"]["schema_version"]["const"] == policy[
        "contracts"
    ]["evidence_span"]["current_version"]
    assert module.SOURCE_EXPORT_SCHEMA_VERSION == policy["contracts"][
        "source_export"
    ]["current_version"]


def test_negotiation_selects_current_exact_versions_independent_of_input_order():
    module = _contract()
    consumer = {
        "source_export": ["2.0.0", "1.0.0"],
        "source_manifest": ["1.0.0", "2.0.0"],
        "evidence_span": ["1.0.0"],
    }

    assert module.negotiate_contract_versions(consumer) == CURRENT_VERSIONS


def test_negotiation_selects_highest_exact_intersection():
    module = _contract()
    policy = _policy_with_retiring_manifest(module)

    negotiated = module.negotiate_contract_versions(
        _consumer_support(manifest=("0.9.0", "1.0.0")), policy=policy
    )
    assert negotiated["source_manifest"] == "1.0.0"


def test_negotiation_can_use_an_older_version_still_in_the_window():
    module = _contract()
    policy = _policy_with_retiring_manifest(module)

    negotiated = module.negotiate_contract_versions(
        _consumer_support(manifest=("0.9.0",)), policy=policy
    )
    assert negotiated == {
        "evidence_span": "1.0.0",
        "source_export": "1.0.0",
        "source_manifest": "0.9.0",
    }


def test_negotiation_rejects_a_cross_product_that_has_no_published_version_set():
    module = _contract()
    policy = _policy_with_retiring_manifest(module)
    policy["contracts"]["evidence_span"]["supported_versions"] = [
        "0.9.0",
        "1.0.0",
    ]
    policy["compatible_version_sets"].insert(
        0,
        {
            "evidence_span": "0.9.0",
            "source_export": "1.0.0",
            "source_manifest": "1.0.0",
        },
    )

    with pytest.raises(module.ContractNegotiationError, match="version set"):
        module.negotiate_contract_versions(
            _consumer_support(manifest=("0.9.0",), span=("0.9.0",)),
            policy=policy,
        )


@pytest.mark.parametrize(
    "consumer",
    (
        _consumer_support(manifest=("2.0.0",)),
        _consumer_support(span=("2.0.0",)),
        _consumer_support(export=("2.0.0",)),
    ),
)
def test_negotiation_fails_the_whole_contract_set_when_any_contract_has_no_overlap(
    consumer,
):
    module = _contract()
    with pytest.raises(module.ContractNegotiationError, match="no mutually supported"):
        module.negotiate_contract_versions(consumer)


@pytest.mark.parametrize(
    "consumer",
    (
        {"source_manifest": ["1.0.0"], "evidence_span": ["1.0.0"]},
        {
            **_consumer_support(),
            "research_report": ["1.0.0"],
        },
    ),
)
def test_negotiation_rejects_missing_or_unknown_contracts(consumer):
    module = _contract()
    with pytest.raises(module.ContractNegotiationError, match="contract names"):
        module.negotiate_contract_versions(consumer)


@pytest.mark.parametrize(
    "version",
    ("1.x", "^1.0.0", "latest", "1.0", "1.0.0-rc.1", "1.0.0+local"),
)
def test_negotiation_rejects_non_exact_or_non_stable_versions(version):
    module = _contract()
    with pytest.raises(module.ContractNegotiationError, match="stable semantic version"):
        module.negotiate_contract_versions(
            _consumer_support(manifest=(version,))
        )


@pytest.mark.parametrize("versions", ([], "1.0.0", ["1.0.0", "1.0.0"]))
def test_negotiation_rejects_empty_scalar_or_duplicate_version_lists(versions):
    module = _contract()
    consumer = _consumer_support()
    consumer["source_manifest"] = versions
    with pytest.raises(module.ContractNegotiationError):
        module.negotiate_contract_versions(consumer)


@pytest.mark.parametrize("field", tuple(POLICY_FIELDS))
def test_policy_rejects_missing_top_level_fields(field):
    module = _contract()
    policy = _policy(module)
    del policy[field]
    with pytest.raises(module.SourceContractCompatibilityError):
        module.validate_compatibility_policy(policy)


def test_policy_rejects_unknown_fields_at_every_level():
    module = _contract()
    cases = []
    top = _policy(module)
    top["research_rating"] = "buy"
    cases.append(top)
    contract = _policy(module)
    contract["contracts"]["source_manifest"]["target_price"] = 100
    cases.append(contract)
    rules = _policy(module)
    rules["compatibility"]["position_size"] = 0.1
    cases.append(rules)

    for policy in cases:
        with pytest.raises(module.SourceContractCompatibilityError, match="fields"):
            module.validate_compatibility_policy(policy)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("minimum_deprecation_notice_days", 179),
        ("minimum_deprecation_notice_days", True),
        ("minimum_minor_overlap_releases", 1),
        ("minimum_minor_overlap_releases", True),
        ("stable_versions_only", False),
        ("unknown_fields_fail_closed", False),
        ("breaking_changes_require_new_major", False),
        ("negotiation", "same_major"),
    ),
)
def test_policy_rejects_weakened_compatibility_commitments(field, value):
    module = _contract()
    policy = _policy(module)
    policy["compatibility"][field] = value
    with pytest.raises(module.SourceContractCompatibilityError):
        module.validate_compatibility_policy(policy)


@pytest.mark.parametrize(
    "supported",
    (
        ["1.0.0", "0.9.0"],
        ["1.0.0", "1.0.0"],
        ["1.0.0-rc.1", "1.0.0"],
        ["0.9.0"],
    ),
)
def test_policy_rejects_noncanonical_or_currentless_support_windows(supported):
    module = _contract()
    policy = _policy(module)
    policy["contracts"]["source_manifest"]["supported_versions"] = supported
    with pytest.raises(module.SourceContractCompatibilityError):
        module.validate_compatibility_policy(policy)


def test_policy_rejects_supported_versions_without_a_compatible_version_set():
    module = _contract()
    policy = _policy(module)
    policy["contracts"]["source_manifest"]["supported_versions"] = [
        "0.9.0",
        "1.0.0",
    ]
    with pytest.raises(module.SourceContractCompatibilityError, match="version set"):
        module.validate_compatibility_policy(policy)


def test_policy_rejects_invalid_duplicate_or_unsorted_compatible_version_sets():
    module = _contract()
    invalid = []

    missing = _policy(module)
    del missing["compatible_version_sets"][0]["source_manifest"]
    invalid.append(missing)

    unsupported = _policy(module)
    unsupported["compatible_version_sets"][0]["source_manifest"] = "2.0.0"
    invalid.append(unsupported)

    duplicate = _policy(module)
    duplicate["compatible_version_sets"].append(
        deepcopy(duplicate["compatible_version_sets"][0])
    )
    invalid.append(duplicate)

    unsorted = _policy_with_retiring_manifest(module)
    unsorted["compatible_version_sets"].reverse()
    invalid.append(unsorted)

    for policy in invalid:
        with pytest.raises(module.SourceContractCompatibilityError):
            module.validate_compatibility_policy(policy)


def test_valid_deprecation_notice_is_machine_readable_and_meets_the_window():
    module = _contract()
    policy = _policy_with_retiring_manifest(module)

    assert (
        date.fromisoformat(policy["deprecation_notices"][0]["sunset_on"])
        - date.fromisoformat(policy["deprecation_notices"][0]["announced_on"])
    ).days == module.MINIMUM_DEPRECATION_NOTICE_DAYS
    assert set(policy["deprecation_notices"][0]) == NOTICE_FIELDS
    assert module.validate_compatibility_policy(policy) == policy


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("sunset_on", "2026-06-29"),
        ("sunset_on", "not-a-date"),
        ("replacement_version", "2.0.0"),
        ("replacement_version", "0.8.0"),
        ("status", "removed"),
        ("reason", ""),
        ("migration_guide", " latest "),
    ),
)
def test_policy_rejects_invalid_or_incomplete_deprecation_notices(field, value):
    module = _contract()
    policy = _policy_with_retiring_manifest(module)
    policy["deprecation_notices"][0][field] = value
    with pytest.raises(module.SourceContractCompatibilityError):
        module.validate_compatibility_policy(policy)


def test_policy_rejects_deprecating_the_current_version_or_duplicate_notices():
    module = _contract()
    current = _policy_with_retiring_manifest(module)
    notice = current["deprecation_notices"][0]
    notice["version"] = "1.0.0"
    notice["replacement_version"] = "1.0.0"
    with pytest.raises(module.SourceContractCompatibilityError):
        module.validate_compatibility_policy(current)

    duplicate = _policy_with_retiring_manifest(module)
    duplicate["deprecation_notices"].append(
        deepcopy(duplicate["deprecation_notices"][0])
    )
    with pytest.raises(module.SourceContractCompatibilityError):
        module.validate_compatibility_policy(duplicate)


def test_policy_resource_and_consumer_documentation_are_published():
    policy_path = (
        ROOT
        / "src"
        / "company_wiki"
        / "source_contract"
        / "schemas"
        / "source_contract_compatibility.v1.json"
    )
    document_path = ROOT / "docs" / "contracts" / "source-contract-compatibility-v1.md"

    assert policy_path.is_file()
    assert json.loads(policy_path.read_text(encoding="utf-8"))[
        "policy_schema_version"
    ] == "1.0.0"
    assert document_path.is_file()
    document = document_path.read_text(encoding="utf-8").lower()
    for phrase in (
        "exact_highest",
        "180",
        "two subsequent minor releases",
        "deprecation_notices",
        "fail closed",
        "stockwiki",
    ):
        assert phrase in document


def test_policy_and_document_do_not_publish_investment_state():
    module = _contract()
    text = module.canonical_compatibility_policy_json().lower()
    document = (
        ROOT / "docs" / "contracts" / "source-contract-compatibility-v1.md"
    ).read_text(encoding="utf-8").lower()
    forbidden = (
        "target_price",
        "position_size",
        "buy_rating",
        "sell_rating",
        "research_acceptance",
        "investment_conclusion",
    )
    assert not any(term in text for term in forbidden)
    assert not any(term in document for term in forbidden)
