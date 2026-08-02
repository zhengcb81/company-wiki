"""Machine-readable compatibility and deprecation policy for source contracts."""

from collections.abc import Mapping, Sequence
from datetime import date
import hashlib
from importlib.resources import files
import json
import re
from typing import Any
import unicodedata

from .evidence_span import EVIDENCE_SPAN_SCHEMA_VERSION
from .source_export import SOURCE_EXPORT_SCHEMA_VERSION
from .source_manifest import SOURCE_MANIFEST_SCHEMA_VERSION


SOURCE_CONTRACT_COMPATIBILITY_POLICY_VERSION = "1.0.0"
SOURCE_CONTRACT_NAMES = (
    "evidence_span",
    "source_export",
    "source_manifest",
)
MINIMUM_DEPRECATION_NOTICE_DAYS = 180
MINIMUM_MINOR_OVERLAP_RELEASES = 2

_CURRENT_VERSIONS = {
    "evidence_span": EVIDENCE_SPAN_SCHEMA_VERSION,
    "source_export": SOURCE_EXPORT_SCHEMA_VERSION,
    "source_manifest": SOURCE_MANIFEST_SCHEMA_VERSION,
}
_POLICY_FIELDS = {
    "policy_schema_version",
    "contracts",
    "compatible_version_sets",
    "compatibility",
    "deprecation_notices",
}
_CONTRACT_FIELDS = {"current_version", "supported_versions"}
_COMPATIBILITY_FIELDS = {
    "negotiation",
    "stable_versions_only",
    "unknown_fields_fail_closed",
    "breaking_changes_require_new_major",
    "minimum_deprecation_notice_days",
    "minimum_minor_overlap_releases",
}
_NOTICE_FIELDS = {
    "contract",
    "version",
    "status",
    "announced_on",
    "sunset_on",
    "replacement_version",
    "reason",
    "migration_guide",
}
_STABLE_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)


class SourceContractCompatibilityError(ValueError):
    """Raised when a compatibility policy violates the published contract."""


class ContractNegotiationError(SourceContractCompatibilityError):
    """Raised when producer and consumer contract versions cannot be negotiated."""


def _require_exact_fields(
    value: Any,
    expected: set[str],
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SourceContractCompatibilityError(f"{label} must be an object")
    supplied = set(value)
    if supplied != expected:
        missing = sorted(expected - supplied)
        unknown = sorted(supplied - expected)
        raise SourceContractCompatibilityError(
            f"{label} fields are invalid; missing={missing}, unknown={unknown}"
        )
    return value


def _stable_semver_key(
    value: Any,
    label: str,
    *,
    error_type: type[SourceContractCompatibilityError] = SourceContractCompatibilityError,
) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise error_type(f"{label} must be a stable semantic version")
    match = _STABLE_SEMVER_RE.fullmatch(value)
    if match is None:
        raise error_type(f"{label} must be a stable semantic version")
    return tuple(int(part) for part in match.groups())


def _require_sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SourceContractCompatibilityError(f"{label} must be an array")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SourceContractCompatibilityError(
            f"{label} must be non-empty trimmed text"
        )
    if unicodedata.normalize("NFC", value) != value:
        raise SourceContractCompatibilityError(f"{label} must use Unicode NFC")
    if any(ord(character) < 32 for character in value):
        raise SourceContractCompatibilityError(
            f"{label} must not contain control characters"
        )
    return value


def _require_date(value: Any, label: str) -> date:
    if not isinstance(value, str):
        raise SourceContractCompatibilityError(f"{label} must be YYYY-MM-DD text")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SourceContractCompatibilityError(
            f"{label} must be a valid YYYY-MM-DD date"
        ) from exc
    if parsed.isoformat() != value:
        raise SourceContractCompatibilityError(
            f"{label} must be canonical YYYY-MM-DD text"
        )
    return parsed


def _require_minimum_integer(value: Any, minimum: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SourceContractCompatibilityError(
            f"{label} must be an integer greater than or equal to {minimum}"
        )
    return value


def validate_compatibility_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached, canonical-shape policy value."""

    policy = _require_exact_fields(policy, _POLICY_FIELDS, "compatibility policy")
    if (
        policy["policy_schema_version"]
        != SOURCE_CONTRACT_COMPATIBILITY_POLICY_VERSION
    ):
        raise SourceContractCompatibilityError(
            "policy_schema_version is not supported"
        )

    contracts = policy["contracts"]
    if not isinstance(contracts, Mapping) or set(contracts) != set(
        SOURCE_CONTRACT_NAMES
    ):
        raise SourceContractCompatibilityError(
            "contracts must contain the exact published contract names"
        )

    normalized_contracts: dict[str, dict[str, Any]] = {}
    version_keys: dict[str, dict[str, tuple[int, int, int]]] = {}
    for contract_name in SOURCE_CONTRACT_NAMES:
        entry = _require_exact_fields(
            contracts[contract_name],
            _CONTRACT_FIELDS,
            f"contracts.{contract_name}",
        )
        current_version = entry["current_version"]
        current_key = _stable_semver_key(
            current_version, f"contracts.{contract_name}.current_version"
        )
        if current_version != _CURRENT_VERSIONS[contract_name]:
            raise SourceContractCompatibilityError(
                f"contracts.{contract_name}.current_version does not match runtime"
            )

        supported = _require_sequence(
            entry["supported_versions"],
            f"contracts.{contract_name}.supported_versions",
        )
        if not supported:
            raise SourceContractCompatibilityError(
                f"contracts.{contract_name}.supported_versions must not be empty"
            )
        keys: dict[str, tuple[int, int, int]] = {}
        for index, version in enumerate(supported):
            key = _stable_semver_key(
                version,
                f"contracts.{contract_name}.supported_versions[{index}]",
            )
            if version in keys:
                raise SourceContractCompatibilityError(
                    f"contracts.{contract_name}.supported_versions must be unique"
                )
            keys[version] = key
        if list(supported) != sorted(supported, key=keys.__getitem__):
            raise SourceContractCompatibilityError(
                f"contracts.{contract_name}.supported_versions must be ascending"
            )
        if current_version not in keys or keys[current_version] != max(keys.values()):
            raise SourceContractCompatibilityError(
                f"contracts.{contract_name}.current_version must be the newest supported version"
            )
        if keys[current_version] != current_key:
            raise SourceContractCompatibilityError(
                f"contracts.{contract_name}.current_version is inconsistent"
            )
        normalized_contracts[contract_name] = {
            "current_version": current_version,
            "supported_versions": list(supported),
        }
        version_keys[contract_name] = keys

    compatible_version_sets = _require_sequence(
        policy["compatible_version_sets"], "compatible_version_sets"
    )
    if not compatible_version_sets:
        raise SourceContractCompatibilityError(
            "compatible_version_sets must not be empty"
        )
    normalized_version_sets: list[dict[str, str]] = []
    covered_versions = {name: set() for name in SOURCE_CONTRACT_NAMES}
    seen_version_sets: set[tuple[str, ...]] = set()
    previous_version_set_key: tuple[tuple[int, int, int], ...] | None = None
    for index, raw_version_set in enumerate(compatible_version_sets):
        if not isinstance(raw_version_set, Mapping) or set(raw_version_set) != set(
            SOURCE_CONTRACT_NAMES
        ):
            raise SourceContractCompatibilityError(
                f"compatible_version_sets[{index}] must contain exact contract names"
            )
        normalized_version_set: dict[str, str] = {}
        identity: list[str] = []
        sort_parts: list[tuple[int, int, int]] = []
        for contract_name in SOURCE_CONTRACT_NAMES:
            version = raw_version_set[contract_name]
            key = _stable_semver_key(
                version,
                f"compatible_version_sets[{index}].{contract_name}",
            )
            if version not in version_keys[contract_name]:
                raise SourceContractCompatibilityError(
                    f"compatible_version_sets[{index}].{contract_name} is not supported"
                )
            normalized_version_set[contract_name] = version
            identity.append(version)
            sort_parts.append(key)
            covered_versions[contract_name].add(version)
        identity_tuple = tuple(identity)
        if identity_tuple in seen_version_sets:
            raise SourceContractCompatibilityError(
                "compatible version sets must be unique"
            )
        seen_version_sets.add(identity_tuple)
        sort_key = tuple(sort_parts)
        if previous_version_set_key is not None and sort_key <= previous_version_set_key:
            raise SourceContractCompatibilityError(
                "compatible version sets must be ascending"
            )
        previous_version_set_key = sort_key
        normalized_version_sets.append(normalized_version_set)

    current_version_set = tuple(
        normalized_contracts[name]["current_version"]
        for name in SOURCE_CONTRACT_NAMES
    )
    if current_version_set not in seen_version_sets:
        raise SourceContractCompatibilityError(
            "compatible version sets must include the current contract set"
        )
    for contract_name in SOURCE_CONTRACT_NAMES:
        if covered_versions[contract_name] != set(version_keys[contract_name]):
            raise SourceContractCompatibilityError(
                f"every supported {contract_name} version must appear in a compatible version set"
            )

    compatibility = _require_exact_fields(
        policy["compatibility"],
        _COMPATIBILITY_FIELDS,
        "compatibility",
    )
    if compatibility["negotiation"] != "exact_highest":
        raise SourceContractCompatibilityError(
            "compatibility.negotiation must be exact_highest"
        )
    for field_name in (
        "stable_versions_only",
        "unknown_fields_fail_closed",
        "breaking_changes_require_new_major",
    ):
        if compatibility[field_name] is not True:
            raise SourceContractCompatibilityError(
                f"compatibility.{field_name} must be true"
            )
    notice_days = _require_minimum_integer(
        compatibility["minimum_deprecation_notice_days"],
        MINIMUM_DEPRECATION_NOTICE_DAYS,
        "compatibility.minimum_deprecation_notice_days",
    )
    overlap_releases = _require_minimum_integer(
        compatibility["minimum_minor_overlap_releases"],
        MINIMUM_MINOR_OVERLAP_RELEASES,
        "compatibility.minimum_minor_overlap_releases",
    )
    normalized_compatibility = {
        "negotiation": "exact_highest",
        "stable_versions_only": True,
        "unknown_fields_fail_closed": True,
        "breaking_changes_require_new_major": True,
        "minimum_deprecation_notice_days": notice_days,
        "minimum_minor_overlap_releases": overlap_releases,
    }

    notices = _require_sequence(policy["deprecation_notices"], "deprecation_notices")
    normalized_notices: list[dict[str, Any]] = []
    seen_notices: set[tuple[str, str]] = set()
    previous_sort_key: tuple[str, tuple[int, int, int]] | None = None
    for index, raw_notice in enumerate(notices):
        notice = _require_exact_fields(
            raw_notice,
            _NOTICE_FIELDS,
            f"deprecation_notices[{index}]",
        )
        contract_name = notice["contract"]
        if contract_name not in SOURCE_CONTRACT_NAMES:
            raise SourceContractCompatibilityError(
                f"deprecation_notices[{index}].contract is unknown"
            )
        version = notice["version"]
        version_key = _stable_semver_key(
            version, f"deprecation_notices[{index}].version"
        )
        notice_identity = (contract_name, version)
        if notice_identity in seen_notices:
            raise SourceContractCompatibilityError(
                "deprecation notices must be unique by contract and version"
            )
        seen_notices.add(notice_identity)
        sort_key = (contract_name, version_key)
        if previous_sort_key is not None and sort_key <= previous_sort_key:
            raise SourceContractCompatibilityError(
                "deprecation notices must be sorted by contract and version"
            )
        previous_sort_key = sort_key

        if version not in version_keys[contract_name]:
            raise SourceContractCompatibilityError(
                f"deprecation_notices[{index}].version must remain supported"
            )
        if version == normalized_contracts[contract_name]["current_version"]:
            raise SourceContractCompatibilityError(
                f"deprecation_notices[{index}] cannot deprecate the current version"
            )
        if notice["status"] != "deprecated":
            raise SourceContractCompatibilityError(
                f"deprecation_notices[{index}].status must be deprecated"
            )

        replacement = notice["replacement_version"]
        replacement_key = _stable_semver_key(
            replacement,
            f"deprecation_notices[{index}].replacement_version",
        )
        if replacement not in version_keys[contract_name]:
            raise SourceContractCompatibilityError(
                f"deprecation_notices[{index}].replacement_version must be supported"
            )
        if replacement_key <= version_key:
            raise SourceContractCompatibilityError(
                f"deprecation_notices[{index}].replacement_version must be newer"
            )

        announced = _require_date(
            notice["announced_on"],
            f"deprecation_notices[{index}].announced_on",
        )
        sunset = _require_date(
            notice["sunset_on"],
            f"deprecation_notices[{index}].sunset_on",
        )
        if (sunset - announced).days < notice_days:
            raise SourceContractCompatibilityError(
                f"deprecation_notices[{index}] is shorter than the notice window"
            )
        normalized_notices.append(
            {
                "contract": contract_name,
                "version": version,
                "status": "deprecated",
                "announced_on": notice["announced_on"],
                "sunset_on": notice["sunset_on"],
                "replacement_version": replacement,
                "reason": _require_text(
                    notice["reason"], f"deprecation_notices[{index}].reason"
                ),
                "migration_guide": _require_text(
                    notice["migration_guide"],
                    f"deprecation_notices[{index}].migration_guide",
                ),
            }
        )

    return {
        "policy_schema_version": SOURCE_CONTRACT_COMPATIBILITY_POLICY_VERSION,
        "contracts": normalized_contracts,
        "compatible_version_sets": normalized_version_sets,
        "compatibility": normalized_compatibility,
        "deprecation_notices": normalized_notices,
    }


def load_compatibility_policy() -> dict[str, Any]:
    """Load and validate a fresh copy of the packaged compatibility policy."""

    resource = files("company_wiki.source_contract.schemas").joinpath(
        "source_contract_compatibility.v1.json"
    )
    value = json.loads(resource.read_text(encoding="utf-8"))
    return validate_compatibility_policy(value)


def canonical_compatibility_policy_json(
    policy: Mapping[str, Any] | None = None,
) -> str:
    """Return canonical JSON for policy pinning and transport."""

    normalized = (
        validate_compatibility_policy(policy)
        if policy is not None
        else load_compatibility_policy()
    )
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def compatibility_policy_sha256(policy: Mapping[str, Any] | None = None) -> str:
    """Return the SHA-256 of the canonical compatibility policy JSON."""

    return hashlib.sha256(
        canonical_compatibility_policy_json(policy).encode("utf-8")
    ).hexdigest()


def negotiate_contract_versions(
    consumer_support: Mapping[str, Sequence[str]],
    *,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Select the highest exact supported version for every source contract."""

    normalized_policy = (
        validate_compatibility_policy(policy)
        if policy is not None
        else load_compatibility_policy()
    )
    if not isinstance(consumer_support, Mapping) or set(consumer_support) != set(
        SOURCE_CONTRACT_NAMES
    ):
        raise ContractNegotiationError(
            "consumer contract names must exactly match the published contract names"
        )

    consumer_versions: dict[str, set[str]] = {}
    for contract_name in SOURCE_CONTRACT_NAMES:
        raw_versions = consumer_support[contract_name]
        if isinstance(raw_versions, (str, bytes, bytearray)) or not isinstance(
            raw_versions, Sequence
        ):
            raise ContractNegotiationError(
                f"consumer {contract_name} versions must be a non-empty array"
            )
        if not raw_versions:
            raise ContractNegotiationError(
                f"consumer {contract_name} versions must be a non-empty array"
            )
        version_keys: dict[str, tuple[int, int, int]] = {}
        for index, version in enumerate(raw_versions):
            key = _stable_semver_key(
                version,
                f"consumer {contract_name} versions[{index}]",
                error_type=ContractNegotiationError,
            )
            if version in version_keys:
                raise ContractNegotiationError(
                    f"consumer {contract_name} versions must be unique"
                )
            version_keys[version] = key

        consumer_versions[contract_name] = set(version_keys)

    candidates = [
        version_set
        for version_set in normalized_policy["compatible_version_sets"]
        if all(
            version_set[name] in consumer_versions[name]
            for name in SOURCE_CONTRACT_NAMES
        )
    ]
    if not candidates:
        raise ContractNegotiationError(
            "no mutually supported compatible version set"
        )
    return dict(candidates[-1])
