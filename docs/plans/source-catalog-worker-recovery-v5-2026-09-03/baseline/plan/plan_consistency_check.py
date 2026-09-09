#!/usr/bin/env python3
"""Read-only mechanical consistency checks for the frozen worker recovery plan.

This helper deliberately performs no writes, opens no production database, touches
no registry key, starts no process, and makes no network request.  It checks the
plan artifacts that must agree before a revision may be frozen for review.
"""

from __future__ import annotations

import json
import hashlib
import re
from collections import deque
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError as exc:  # pragma: no cover - fail closed in an unprepared host
    print(f"FAIL DEPENDENCY: jsonschema and referencing are required: {exc}")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parent

SCHEMA_FILES = tuple(sorted(path.name for path in ROOT.glob("*.schema.json")))
REQUIRED_SCHEMA_IDS = {
    "authorization_manifest.schema.json": "urn:company-wiki:source-catalog-worker-recovery:authorization-manifest:v4",
    "authorization_revalidation_receipt.schema.json": "urn:company-wiki:source-catalog-worker-recovery:authorization-revalidation-receipt:v1",
    "bootstrap_verifier_manifest.schema.json": "urn:company-wiki:source-catalog-worker-recovery:bootstrap-verifier-manifest:v1",
    "budget_reservation_bundle.schema.json": "urn:company-wiki:source-catalog-worker-recovery:budget-reservation-bundle:v1",
    "budget_settlement_receipt.schema.json": "urn:company-wiki:source-catalog-worker-recovery:budget-settlement-receipt:v1",
    "evidence_manifest.schema.json": "urn:company-wiki:source-catalog-worker-recovery:evidence-manifest:v4",
    "gate_dag.schema.json": "urn:company-wiki:source-catalog-worker-recovery:gate-dag-instance:v4",
    "gate_ledger.schema.json": "urn:company-wiki:source-catalog-worker-recovery:gate-ledger:v4",
    "gate_ledger_transcript.schema.json": "urn:company-wiki:source-catalog-worker-recovery:gate-ledger-transcript:v1",
    "gate_ledger_validator_vectors.schema.json": "urn:company-wiki:source-catalog-worker-recovery:validator-vectors-instance:v4",
    "journal_manifest.schema.json": "urn:company-wiki:source-catalog-worker-recovery:journal-manifest:v5",
    "journal_record.schema.json": "urn:company-wiki:source-catalog-worker-recovery:journal-record:v1",
    "ledger_head_anchor.schema.json": "urn:company-wiki:source-catalog-worker-recovery:ledger-head-anchor:v1",
    "operation_contract.schema.json": "urn:company-wiki:source-catalog-worker-recovery:operation-contract:v4",
    "operation_contracts.schema.json": "urn:company-wiki:source-catalog-worker-recovery:operation-policy-instance:v4",
    "operation_execution_receipt.schema.json": "urn:company-wiki:source-catalog-worker-recovery:operation-execution-receipt:v1",
    "operation_intent_manifest.schema.json": "urn:company-wiki:source-catalog-worker-recovery:operation-intent-manifest:v4",
    "operation_intent_template.schema.json": "urn:company-wiki:source-catalog-worker-recovery:operation-intent-template:v4",
    "parser_route_manifest.schema.json": "urn:company-wiki:source-catalog-worker-recovery:parser-route-manifest:v4",
    "plan_manifest.schema.json": "urn:company-wiki:source-catalog-worker-recovery:plan-manifest:v4",
    "review_confirmation.schema.json": "urn:company-wiki:source-catalog-worker-recovery:review-storage-confirmation:v4",
    "review_result.schema.json": "urn:company-wiki:source-catalog-worker-recovery:review-result:v4",
    "schema_registry.schema.json": "urn:company-wiki:source-catalog-worker-recovery:schema-registry:v1",
    "test_id_registry.schema.json": "urn:company-wiki:source-catalog-worker-recovery:test-id-registry-instance:v4",
    "user_approval_receipt.schema.json": "urn:company-wiki:source-catalog-worker-recovery:user-approval-receipt:v1",
    "validator_fixture_manifest.schema.json": "urn:company-wiki:source-catalog-worker-recovery:validator-fixture-manifest:v5",
    "validator_release_manifest.schema.json": "urn:company-wiki:source-catalog-worker-recovery:validator-release-manifest:v2",
    "validator_request.schema.json": "urn:company-wiki:source-catalog-worker-recovery:validator-request:v1",
    "validator_scenario_fixture.schema.json": "urn:company-wiki:source-catalog-worker-recovery:validator-scenario-fixture:v1",
}
REQUIRED_SCHEMA_FILES = frozenset(REQUIRED_SCHEMA_IDS)
IMMUTABLE_HISTORY_SHA256 = {
    "plan_manifest.v3.json": "9ee84acdbe65a294925de004125f37b62b9e4b1c95655a04cd2344bc6bd270cc",
}

ACTIVE_PROSE_FILES = (
    "README.md",
    "task_plan.md",
    "execution_playbook.md",
    "test_acceptance_plan.md",
    "agent_review_gates.md",
    "gate_state_machine.md",
    "acceptance_thresholds.md",
    "rollout_rollback_runbook.md",
    "traceability_matrix.md",
    "implementation_agent_prompts.md",
    "ledger_validator_contract.md",
)

EXPECTED_NORMATIVE_FILES = tuple(
    sorted(
        {
            *REQUIRED_SCHEMA_FILES,
            *ACTIVE_PROSE_FILES,
            "findings.md",
            "plan_review_findings.md",
            "gate_dag.v4.json",
            "operation_contracts.v4.json",
            "gate_ledger_validator_vectors.v4.json",
            "test_id_registry.v4.json",
            "plan_consistency_check.py",
            "plan_freeze_check.v4.txt",
        },
        key=str.casefold,
    )
)

EXPECTED_MANIFEST_EXCLUSIONS = {
    "plan_manifest.v4.json",
    "plan_manifest.v3.json",
    "plan_review_revision.md",
    "progress.md",
    "gate_ledger.jsonl",
    "evidence/",
    "reviews/",
    "decisions/",
}

INSTANCE_PAIRS = (
    ("gate_dag.v4.json", "gate_dag.schema.json"),
    ("operation_contracts.v4.json", "operation_contracts.schema.json"),
    (
        "gate_ledger_validator_vectors.v4.json",
        "gate_ledger_validator_vectors.schema.json",
    ),
    ("test_id_registry.v4.json", "test_id_registry.schema.json"),
)

EXPECTED_VECTOR_IDS = {
    *(f"GL-S{i:02d}" for i in range(1, 7)),
    *(f"GL-F{i:02d}" for i in range(1, 13)),
}

EXPECTED_PLAN_REVISION = "v4"
REQUIRED_DAG_INVARIANTS = {
    "UNSELECTED_BRANCH_HAS_NO_LEDGER_RECORD",
    "G10C_HAS_ONLY_D11A_SUCCESSOR",
    "G10R_HAS_ONLY_D12A_SUCCESSOR",
    "EVERY_PRODUCTION_OP_HAS_DISTINCT_PRE_AND_POST_REVIEW",
    "TWELVEB_COMPENSATION_CONTRACT_REVIEWED_BEFORE_ARM_AND_REACHABLE_AFTER_EACH_WRITING_STEP",
    "FAILED_POST_ARM_OR_FINAL_ACTIVATION_USES_EXPLICIT_COMPENSATION_OP_AND_REVIEW",
    "ROLLBACK_GATE_INHERITS_EXACT_COMPENSATION_TERMINAL_STATE",
    "D12C_RT_FREEZES_RUNTIME_TEMPLATE_BEFORE_DISTINCT_TEMPLATE_USER_AUTHORIZATION",
    "D12C_FREEZES_EXACT_INTENT_AFTER_G12C_RT_AND_BEFORE_DISTINCT_FINAL_USER_AUTHORIZATION",
    "RUNTIME_TEMPLATE_AND_FINAL_ACTIVATION_APPROVAL_IDS_HASHES_PURPOSES_AND_RECEIPTS_ARE_DISTINCT",
    "EVERY_POST_G12C_CYCLE_SEALS_EXACT_INTENT_CONTRACT_AND_JOURNAL_BEFORE_SIDE_EFFECTS",
    "RESET_NEVER_AUTHORIZES_RESUME_ARM_LOGIN_OR_ACTIVATION",
    "VALIDATOR_COMPUTES_ELIGIBLE_NODES_AND_REJECTS_AUTHORED_NEXT_EDGE",
}


class DuplicateKeyError(ValueError):
    """Raised when a JSON object silently overwrites a duplicate key."""


def object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate object key {key!r}")
        result[key] = value
    return result


ERRORS: list[str] = []
CHECKS = 0
DOCUMENTS: dict[str, Any] = {}


def check(condition: bool, code: str, message: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        ERRORS.append(f"{code}: {message}")


def load_json(name: str) -> Any:
    if name in DOCUMENTS:
        return DOCUMENTS[name]
    path = ROOT / name
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text, object_pairs_hook=object_without_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        ERRORS.append(f"JSON-LOAD: {name}: {exc}")
        value = None
    DOCUMENTS[name] = value
    return value


def json_pointer(document: Any, fragment: str) -> Any:
    if fragment in ("", "#"):
        return document
    pointer = fragment[1:] if fragment.startswith("#") else fragment
    if not pointer.startswith("/"):
        raise KeyError(f"unsupported JSON pointer {fragment!r}")
    current = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    return current


def iter_refs(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            yield ref
        for child in value.values():
            yield from iter_refs(child)


def iter_reference_keywords(value: Any) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for keyword in ("$ref", "$dynamicRef", "$recursiveRef"):
            ref = value.get(keyword)
            if isinstance(ref, str):
                yield keyword, ref
        for child in value.values():
            yield from iter_reference_keywords(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_reference_keywords(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_refs(child)


def resolve_ref(
    owner_name: str,
    owner: Any,
    ref: str,
    schemas_by_id: dict[str, Any],
) -> None:
    try:
        if ref.startswith("#"):
            json_pointer(owner, ref)
            return
        resource_id, marker, fragment = ref.partition("#")
        check(bool(resource_id), "SCHEMA-REF", f"{owner_name}: empty external reference")
        if not resource_id.startswith("urn:company-wiki:source-catalog-worker-recovery:"):
            check(
                False,
                "SCHEMA-REF-RELATIVE",
                f"{owner_name}: external reference must use a closed $id URN: {ref!r}",
            )
            return
        target = schemas_by_id.get(resource_id)
        check(
            target is not None,
            "SCHEMA-REF-CLOSURE",
            f"{owner_name}: external resource is outside the closed registry: {resource_id!r}",
        )
        if target is not None and marker:
            json_pointer(target, f"#{fragment}")
    except (KeyError, IndexError, ValueError) as exc:
        ERRORS.append(f"SCHEMA-REF: {owner_name}: unresolved {ref!r}: {exc}")


def schema_checks() -> None:
    check(
        set(SCHEMA_FILES) == REQUIRED_SCHEMA_FILES,
        "SCHEMA-CLOSED-SET",
        "schema set differs from the required normative closure; "
        f"missing={sorted(REQUIRED_SCHEMA_FILES - set(SCHEMA_FILES))}, "
        f"extra={sorted(set(SCHEMA_FILES) - REQUIRED_SCHEMA_FILES)}",
    )
    try:
        readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        ERRORS.append(f"README-LOAD: {exc}")
        readme_text = ""
    readme_schema_rows = set(
        re.findall(r"^\| `([^`]+\.schema\.json)` \|", readme_text, flags=re.MULTILINE)
    )
    check(
        readme_schema_rows == set(SCHEMA_FILES),
        "SCHEMA-README-CLOSED-SET",
        "README normative schema table differs from disk; "
        f"missing_rows={sorted(set(SCHEMA_FILES) - readme_schema_rows)}, "
        f"stale_rows={sorted(readme_schema_rows - set(SCHEMA_FILES))}",
    )
    schemas_by_id: dict[str, Any] = {}
    schema_names_by_id: dict[str, str] = {}
    for name in SCHEMA_FILES:
        schema = load_json(name)
        if schema is None:
            continue
        schema_id = schema.get("$id")
        check(
            isinstance(schema_id, str) and schema_id.startswith(
                "urn:company-wiki:source-catalog-worker-recovery:"
            ),
            "SCHEMA-ID",
            f"{name}: missing or out-of-namespace $id: {schema_id!r}",
        )
        if isinstance(schema_id, str):
            check(
                schema_id == REQUIRED_SCHEMA_IDS.get(name),
                "SCHEMA-ID-BINDING",
                f"{name}: expected {REQUIRED_SCHEMA_IDS.get(name)!r}, got {schema_id!r}",
            )
            previous = schema_names_by_id.get(schema_id)
            check(
                previous is None,
                "SCHEMA-ID-UNIQUE",
                f"{name}: duplicate $id {schema_id!r} already owned by {previous!r}",
            )
            if previous is None:
                schema_names_by_id[schema_id] = name
                schemas_by_id[schema_id] = schema
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # jsonschema exposes several schema exceptions
            ERRORS.append(f"SCHEMA-META: {name}: {exc}")
            continue
        check(
            schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
            "SCHEMA-DIALECT",
            f"{name}: must declare draft 2020-12",
        )

    registry = Registry().with_resources(
        (
            schema_id,
            Resource.from_contents(schema, default_specification=DRAFT202012),
        )
        for schema_id, schema in schemas_by_id.items()
    )

    for name in SCHEMA_FILES:
        schema = load_json(name)
        if schema is None:
            continue
        for malformed in ({}, [], "shape-negative"):
            try:
                is_valid = Draft202012Validator(schema, registry=registry).is_valid(malformed)
            except Exception as exc:
                ERRORS.append(f"SCHEMA-REGISTRY: {name}: shape validation failed: {exc}")
                is_valid = True
            check(not is_valid, "SCHEMA-SHAPE", f"{name}: accepts malformed top-level {malformed!r}")
        schema_id = schema.get("$id")
        for keyword, ref in iter_reference_keywords(schema):
            check(
                keyword == "$ref",
                "SCHEMA-REF-KEYWORD",
                f"{name}: {keyword} is not permitted in the closed static registry",
            )
            if keyword != "$ref":
                continue
            resolve_ref(name, schema, ref, schemas_by_id)
            if isinstance(schema_id, str):
                try:
                    resolved = registry.resolver(schema_id).lookup(ref).contents
                    check(
                        isinstance(resolved, (dict, bool)),
                        "SCHEMA-REF-TARGET",
                        f"{name}: {ref!r} resolves to non-schema {type(resolved).__name__}",
                    )
                except Exception as exc:
                    ERRORS.append(f"SCHEMA-REGISTRY-LOOKUP: {name}: {ref!r}: {exc}")

    for instance_name, schema_name in INSTANCE_PAIRS:
        instance = load_json(instance_name)
        schema = load_json(schema_name)
        if instance is None or schema is None:
            continue
        errors = sorted(
            Draft202012Validator(
                schema,
                registry=registry,
                format_checker=FormatChecker(),
            ).iter_errors(instance),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
        for error in errors[:20]:
            location = "/".join(str(part) for part in error.absolute_path) or "$"
            ERRORS.append(
                f"INSTANCE-SCHEMA: {instance_name}:{location}: {error.message}"
            )
        check(
            not errors,
            "INSTANCE-SCHEMA",
            f"{instance_name}: {len(errors)} schema violation(s)",
        )


def node_dependencies(requirement: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(requirement, list):
        for item in requirement:
            result.update(node_dependencies(item))
    elif isinstance(requirement, dict):
        for key, value in requirement.items():
            if key in {"all", "exactly_one", "then_all"} and isinstance(value, list):
                result.update(item for item in value if isinstance(item, str))
            elif key in {"any", "conditional"}:
                result.update(node_dependencies(value))
    return result


def dag_checks() -> tuple[dict[str, Any], set[str]]:
    dag = load_json("gate_dag.v4.json")
    if not isinstance(dag, dict):
        return {}, set()
    check(dag.get("plan_revision") == EXPECTED_PLAN_REVISION, "DAG-REV", "not v4")
    nodes = dag.get("nodes", [])
    ids = [node.get("id") for node in nodes]
    fixed_ids = {node_id for node_id in ids if isinstance(node_id, str)}
    by_id = {node["id"]: node for node in nodes if isinstance(node.get("id"), str)}
    check(len(ids) == len(fixed_ids), "DAG-ID", "duplicate or non-string fixed node ID")
    check(dag.get("entry_node") in fixed_ids, "DAG-ENTRY", "entry node does not exist")
    check(
        "NOT_SELECTED" not in json.dumps(dag, ensure_ascii=False),
        "DAG-NOT-SELECTED",
        "NOT_SELECTED appears in the normative DAG",
    )
    check(
        REQUIRED_DAG_INVARIANTS <= set(dag.get("global_invariants", [])),
        "DAG-INVARIANTS",
        "one or more required fail-closed invariants are absent",
    )

    expected_type_prefix = {"T": "T", "D": "D", "I": "I", "G": "G", "OP": "OP"}
    dependencies: dict[str, set[str]] = {}
    for node in nodes:
        node_id = node.get("id")
        node_type = node.get("type")
        if not isinstance(node_id, str):
            continue
        check(
            node_type in expected_type_prefix
            and node_id.startswith(expected_type_prefix[node_type]),
            "DAG-TYPE",
            f"{node_id}: type/prefix mismatch ({node_type!r})",
        )
        reviewers = node.get("reviewers_on_pass")
        if node_type in {"D", "G"}:
            check(
                isinstance(reviewers, int) and 1 <= reviewers <= 3,
                "DAG-REVIEW-COUNT",
                f"{node_id}: D/G needs 1..3 reviewers",
            )
        else:
            check(reviewers == 0, "DAG-REVIEW-COUNT", f"{node_id}: non-D/G must be 0")

        deps = node_dependencies(node.get("requires", {}))
        dependencies[node_id] = deps
        for dependency in deps:
            check(
                dependency in fixed_ids,
                "DAG-DANGLING",
                f"{node_id}: requires missing {dependency}",
            )
        for key in ("only_successor",):
            target = node.get(key)
            if target is not None:
                check(target in fixed_ids, "DAG-DANGLING", f"{node_id}: {key}={target}")
        for target in node.get("failure_successors", []):
            check(target in fixed_ids, "DAG-DANGLING", f"{node_id}: failure->{target}")
        optional = node.get("optional_external_successor")
        if isinstance(optional, dict):
            target = optional.get("node")
            check(target in fixed_ids, "DAG-DANGLING", f"{node_id}: optional->{target}")

    indegree = {node_id: 0 for node_id in fixed_ids}
    successors: dict[str, set[str]] = {node_id: set() for node_id in fixed_ids}
    for node_id, deps in dependencies.items():
        for dependency in deps & fixed_ids:
            indegree[node_id] += 1
            successors[dependency].add(node_id)
    ready = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
    visited = 0
    while ready:
        current = ready.popleft()
        visited += 1
        for successor in sorted(successors[current]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    check(visited == len(fixed_ids), "DAG-CYCLE", "fixed-node dependency graph is cyclic")

    decisions = dag.get("branch_decisions", {})
    for decision_id, decision in decisions.items():
        check(
            decision.get("node") in fixed_ids,
            "DAG-DECISION",
            f"{decision_id}: decision gate missing",
        )
        check(
            len(decision.get("allowed_values", [])) == 2
            and decision.get("exactly_one") is True,
            "DAG-DECISION",
            f"{decision_id}: must freeze exactly one of two values",
        )
    query_contract = decisions.get("ADR-02", {}).get("query_acceptance_contract", {})
    check(
        query_contract
        == {
            "pre_migration_gate": "G11A",
            "no_index_required_outcome": "QUERY_BUDGET_MET",
            "index_allowed_outcome": "INDEX_REQUIRED",
            "index_allowed_only_if": [
                "SEMANTIC_ORACLE_MATCH",
                "BOUNDED_READ_ONLY_DIAGNOSTIC",
                "QUERY_PLAN_PROVES_INDEX_REQUIRED",
                "NO_PRODUCTION_MUTATION",
            ],
            "post_migration_gate": "G11M",
            "post_migration_required_outcome": "QUERY_BUDGET_MET",
            "deadline_seconds": 10,
        },
        "DAG-INDEX-ACCEPTANCE",
        "ADR-02 must prevent the G11A/D11M index deadlock",
    )

    expected_12b_predecessors = {
        "D12B-ARM": {"G12B-PRE"},
        "D12B-RB": {"D12B-ARM"},
        "OP12B-ARM": {"D12B-RB"},
        "G12B-ARM": {"OP12B-ARM"},
        "D12B-CAS": {"G12B-ARM"},
    }
    for node_id, expected in expected_12b_predecessors.items():
        check(
            dependencies.get(node_id) == expected,
            "DAG-12B-ORDER",
            f"{node_id}: got {sorted(dependencies.get(node_id, set()))}, expected {sorted(expected)}",
        )
    for node_id in (
        "OP12B-ARM",
        "G12B-ARM",
        "D12B-CAS",
        "OP12B-CAS",
        "G12B-CAS",
        "D12B-LOGIN",
        "OP12B-LOGIN",
        "G12B-POST",
    ):
        check(
            by_id.get(node_id, {}).get("failure_successors") == ["OP12B-RB"],
            "DAG-12B-ROLLBACK",
            f"{node_id}: no exact rollback edge",
        )
    check(
        by_id.get("OP12B-RB", {}).get("requires", {}).get("external")
        == ["ROLLBACK_TRIGGER_12B"],
        "DAG-12B-ROLLBACK",
        "OP12B-RB must use the closed generic 12B rollback trigger",
    )
    for node_id in ("G12B-RB", "G12C-RB"):
        check(
            by_id.get(node_id, {}).get("pass_production_state_source")
            == "BOUND_OPERATION_TERMINAL_STATE",
            "DAG-ROLLBACK-STATE",
            f"{node_id}: must inherit the operation terminal state",
        )
    runtime_approval = "USER_APPROVAL_RUNTIME_TEMPLATE_AUTHORIZATION"
    activation_approval = "USER_APPROVAL_FINAL_AUTOSTART_ACTIVATION"
    check(
        "optional_external_successor" not in by_id.get("G12B-POST", {})
        and dependencies.get("D12C-RT") == {"G12B-POST"}
        and by_id.get("D12C-RT", {}).get("optional_external_successor")
        == {
            "node": "G12C-RT",
            "external": runtime_approval,
            "absence_state": "SAFE_PAUSED_WAITING_USER",
            "absence_is_blocked": False,
        }
        and dependencies.get("G12C-RT") == {"D12C-RT"}
        and by_id.get("G12C-RT", {}).get("requires", {}).get("external")
        == [runtime_approval]
        and by_id.get("G12C-RT", {}).get("only_successor") == "D12C"
        and dependencies.get("D12C") == {"G12C-RT"}
        and by_id.get("D12C", {}).get("optional_external_successor")
        == {
            "node": "G12C-PRE",
            "external": activation_approval,
            "absence_state": "SAFE_PAUSED_WAITING_USER",
            "absence_is_blocked": False,
        }
        and dependencies.get("G12C-PRE") == {"D12C"}
        and by_id.get("G12C-PRE", {}).get("requires", {}).get("external")
        == [activation_approval]
        and runtime_approval != activation_approval,
        "DAG-12C-DUAL-AUTH-ORDER",
        "runtime-template and final-activation approvals are not distinct reviewed chains",
    )
    role_overrides = dag.get("reviewer_rules", {}).get("node_role_overrides", {})
    check(
        role_overrides.get("D12C-RT", {}).get("roles")
        == ["llm_data_governance", "runtime_operations"]
        and role_overrides.get("G12C-RT", {}).get("roles")
        == ["llm_data_governance", "control_security", "release_security"]
        and role_overrides.get("G12C-RT", {}).get("disjoint_from") == ["D12C-RT"]
        and role_overrides.get("D12C", {}).get("disjoint_from") == ["G12C-RT"]
        and role_overrides.get("G12C-PRE", {}).get("disjoint_from") == ["D12C"],
        "DAG-12C-DUAL-AUTH-REVIEW",
        "dual-authorization nodes lack exact reviewer roles/disjointness",
    )
    check(
        {"G09P", "G09"} <= dependencies.get("G10R", set()),
        "DAG-G10R-JOIN",
        "G10R is missing G09P/G09",
    )

    ledger_schema = load_json("gate_ledger.schema.json")
    try:
        node_pattern = ledger_schema["$defs"]["nodeId"]["pattern"]
        node_regex = re.compile(node_pattern)
    except (KeyError, TypeError, re.error) as exc:
        ERRORS.append(f"LEDGER-NODE-REGEX: cannot compile: {exc}")
        node_regex = re.compile(r"(?!)")
    for node_id in fixed_ids:
        check(
            node_regex.fullmatch(node_id) is not None,
            "LEDGER-NODE-REGEX",
            f"fixed DAG ID rejected: {node_id}",
        )
    for sample in ("D11B-BF01", "OP11B-BF01", "G11B-BF01", "D05R01", "OP05R01", "G05R01"):
        check(
            node_regex.fullmatch(sample) is not None,
            "LEDGER-NODE-REGEX",
            f"valid family sample rejected: {sample}",
        )
    for forbidden in ("D11B-BF00", "OP11B-BF00", "G11B-BF00", "D05R00", "OP02A", "NOT_SELECTED"):
        check(
            node_regex.fullmatch(forbidden) is None,
            "LEDGER-NODE-REGEX",
            f"forbidden node token accepted: {forbidden}",
        )

    evidence_schema = load_json("evidence_manifest.schema.json")
    try:
        evidence_node_pattern = evidence_schema["$defs"]["nodeId"]["pattern"]
        evidence_node_regex = re.compile(evidence_node_pattern)
    except (KeyError, TypeError, re.error) as exc:
        ERRORS.append(f"EVIDENCE-NODE-REGEX: cannot compile: {exc}")
        evidence_node_regex = re.compile(r"(?!)")
    for node_id in fixed_ids:
        check(
            evidence_node_regex.fullmatch(node_id) is not None,
            "EVIDENCE-NODE-REGEX",
            f"fixed DAG ID rejected: {node_id}",
        )
    for forbidden in ("D11B-BF00", "OP11B-BF00", "G11B-BF00", "D05R00", "OP02A", "NOT_SELECTED"):
        check(
            evidence_node_regex.fullmatch(forbidden) is None,
            "EVIDENCE-NODE-REGEX",
            f"forbidden node token accepted: {forbidden}",
        )

    review_rules = dag.get("reviewer_rules", {})
    allowed_roles = set(review_rules.get("allowed_roles", []))
    defaults = review_rules.get("default_roles_on_pass", {})
    overrides = review_rules.get("node_role_overrides", {})
    check(review_rules.get("distinct_agent_ids") is True, "REVIEW-RULE", "agent IDs")
    check(review_rules.get("distinct_roles") is True, "REVIEW-RULE", "roles")
    check(
        review_rules.get("exclude_implementer_and_operator") is True,
        "REVIEW-RULE",
        "implementer/operator exclusion",
    )
    check(
        review_rules.get("storage_hash_confirmation_required") is True,
        "REVIEW-RULE",
        "detached storage confirmation",
    )
    for override_id in overrides:
        check(override_id in fixed_ids, "REVIEW-OVERRIDE", f"unknown node {override_id}")
    for node_id, node in by_id.items():
        if node.get("type") not in {"D", "G"}:
            continue
        policy = overrides.get(node_id, {})
        roles = policy.get("roles", defaults.get(node["type"], []))
        check(
            len(roles) == node.get("reviewers_on_pass"),
            "REVIEW-CARDINALITY",
            f"{node_id}: DAG={node.get('reviewers_on_pass')} roles={roles}",
        )
        check(len(roles) == len(set(roles)), "REVIEW-ROLE", f"{node_id}: duplicate role")
        check(set(roles) <= allowed_roles, "REVIEW-ROLE", f"{node_id}: unapproved role")
        for ref in policy.get("disjoint_from", []):
            check(ref in fixed_ids, "REVIEW-DISJOINT", f"{node_id}: unknown {ref}")
        min_not_in = policy.get("min_not_in")
        if isinstance(min_not_in, dict):
            for ref in min_not_in.get("nodes", []):
                check(ref in fixed_ids, "REVIEW-DISJOINT", f"{node_id}: unknown {ref}")

    for family_name, family in dag.get("families", {}).items():
        family_review = review_rules.get("family_role_overrides", {}).get(family_name)
        check(family_review is not None, "REVIEW-FAMILY", f"{family_name}: no role rule")
        if not isinstance(family_review, dict):
            continue
        counts = family.get("reviewers_on_pass", {})
        for node_type in ("D", "G"):
            roles = family_review.get(node_type, [])
            check(
                len(roles) == counts.get(node_type),
                "REVIEW-FAMILY",
                f"{family_name}/{node_type}: count/role mismatch",
            )
            check(set(roles) <= allowed_roles, "REVIEW-FAMILY", f"{family_name}: role")
    return by_id, fixed_ids


def policy_matches(policy: dict[str, Any], node_id: str) -> bool:
    if policy.get("node") == node_id:
        return True
    pattern = policy.get("node_pattern")
    return isinstance(pattern, str) and re.fullmatch(pattern, node_id) is not None


def check_policy_shape(policy: dict[str, Any], label: str) -> None:
    deltas = policy.get("generation_deltas", [])
    sequences = []
    if "state_sequence" in policy:
        sequences.append(policy["state_sequence"])
    sequences.extend(policy.get("state_sequence_options", []))
    for sequence in sequences:
        check(
            len(sequence) == len(deltas) + 1,
            "OP-STATE-SEQUENCE",
            f"{label}: {len(sequence)} states vs {len(deltas)} deltas",
        )
    transition_options = policy.get("state_transition_options", [])
    for option in transition_options:
        check(
            isinstance(option, dict)
            and set(option) == {"from", "to", "generation_delta"}
            and option.get("generation_delta") in {0, 1},
            "OP-STATE-TRANSITION-OPTION",
            f"{label}: malformed explicit transition option {option!r}",
        )
    check(policy.get("dynamic_contract_required") is True, "OP-CONTRACT", label)
    check(policy.get("evidence_manifest_required") is True, "OP-EVIDENCE", label)
    check(
        policy.get("intent_policy")
        in {"REQUIRED_READ_ONLY", "REQUIRED_MUTATION", "REQUIRED_COMPENSATION", "REQUIRED_RESET"},
        "OP-INTENT",
        label,
    )
    check(
        policy.get("journal_policy")
        in {"NOT_APPLICABLE", "INITIALIZE", "REQUIRED_INTENT_FINALIZE"},
        "OP-JOURNAL",
        label,
    )
    check(
        policy.get("registry_contract_mode")
        in {
            "NONE",
            "VERIFY_ONLY_EXACT_OWNED_VALUE",
            "EXACT_CAS_CREATE_ABSENT",
            "VERIFY_ABSENT_OR_PRESERVE_OWNED_OR_CONFLICT",
            "VERIFY_ABSENT_EXACT_OR_PRESERVE_CONFLICT",
        },
        "OP-REGISTRY-MODE",
        label,
    )
    authorization = policy.get("authorization_policy")
    authorization_kind = policy.get("required_authorization_kind")
    reasons = policy.get("allowed_na_reasons", [])
    if authorization == "N_A_ALLOWED":
        check(bool(reasons), "OP-AUTH", f"{label}: missing closed N/A reason")
        check(
            authorization_kind == "NOT_APPLICABLE_LOCAL_READ_ONLY",
            "OP-AUTH-KIND",
            label,
        )
    elif authorization == "BOUND_COMPENSATION":
        check(
            authorization_kind == "BOUND_COMPENSATION",
            "OP-AUTH-KIND",
            label,
        )
        check(
            policy.get("journal_policy") == "REQUIRED_INTENT_FINALIZE",
            "OP-JOURNAL",
            f"{label}: compensation must be journaled",
        )
    else:
        check(not reasons, "OP-AUTH", f"{label}: unexpected N/A reason")


def operation_checks(nodes: dict[str, Any]) -> None:
    catalog = load_json("operation_contracts.v4.json")
    if not isinstance(catalog, dict):
        return
    check(catalog.get("plan_revision") == EXPECTED_PLAN_REVISION, "OP-REV", "not v4")
    operations = catalog.get("operations", [])
    families = catalog.get("families", [])
    for policy in [*operations, *families]:
        check_policy_shape(policy, policy.get("node", policy.get("node_pattern", "?")))

    fixed_op_ids = {node_id for node_id, node in nodes.items() if node.get("type") == "OP"}
    for node_id in sorted(fixed_op_ids):
        matches = [policy for policy in operations if policy_matches(policy, node_id)]
        check(len(matches) == 1, "OP-COVERAGE", f"{node_id}: {len(matches)} matches")
        if len(matches) == 1:
            check(
                matches[0].get("operation") == nodes[node_id].get("operation"),
                "OP-NAME",
                f"{node_id}: DAG={nodes[node_id].get('operation')} catalog={matches[0].get('operation')}",
            )
    for policy in operations:
        if "node" in policy:
            check(policy["node"] in fixed_op_ids, "OP-ORPHAN", policy["node"])

    dag = load_json("gate_dag.v4.json")
    dag_families = dag.get("families", {}) if isinstance(dag, dict) else {}
    samples = (
        ("OP11B-BF01", operations, "G11B-BFnn"),
        ("OP05R01", families, "05Rnn"),
    )
    for sample, policies, family_name in samples:
        matches = [policy for policy in policies if policy_matches(policy, sample)]
        check(len(matches) == 1, "OP-FAMILY-COVERAGE", f"{sample}: {len(matches)}")
        if len(matches) == 1:
            check(
                matches[0].get("operation") == dag_families[family_name].get("operation"),
                "OP-FAMILY-NAME",
                f"{sample}: catalog/DAG family mismatch",
            )
    for forbidden, policies in (("OP11B-BF00", operations), ("OP05R00", families)):
        check(
            not any(policy_matches(policy, forbidden) for policy in policies),
            "OP-FAMILY-RANGE",
            f"forbidden family member accepted: {forbidden}",
        )

    by_node = {policy.get("node"): policy for policy in operations if policy.get("node")}
    def has_transition(node_id: str, source: str, target: str, delta: int) -> bool:
        return {
            "from": source,
            "to": target,
            "generation_delta": delta,
        } in by_node.get(node_id, {}).get("state_transition_options", [])

    check(
        has_transition("OP12B-RB", "ARMED_PRELOGIN/OFF", "PAUSED/REGISTRY_CONFLICT", 1),
        "OP-12B-CONFLICT",
        "pre-CAS ARM rollback lacks a registry-conflict terminal state",
    )
    check(
        has_transition("OP12C-RB", "ENABLED_IDLE/ON", "PAUSED/REGISTRY_CONFLICT", 1),
        "OP-12C-CONFLICT",
        "final-activation rollback lacks a registry-conflict terminal state",
    )
    check(
        has_transition("OP12B-RB", "PAUSED/OFF", "PAUSED/OFF", 0),
        "OP-12B-PRE-EFFECT-NOOP",
        "pre-effect 12B rollback lacks an explicit zero-generation no-op",
    )
    check(
        has_transition("OP12C-RB", "LOGIN_VALIDATED_PAUSED/ON", "LOGIN_VALIDATED_PAUSED/ON", 0),
        "OP-12C-PRE-EFFECT-NOOP",
        "pre-control-write 12C rollback lacks an explicit zero-generation no-op",
    )
    check(
        has_transition("OP12C-RB", "ENABLED_IDLE/ON", "PAUSED/OFF", 1),
        "OP-12C-REGISTRY-ABSENT",
        "final activation rollback lacks a registry-absent safe-off branch",
    )
    check(
        by_node.get("OP12B-CAS", {}).get("registry_contract_mode")
        == "EXACT_CAS_CREATE_ABSENT",
        "OP-REGISTRY-CAS",
        "OP12B-CAS is not bound to exact create-if-absent semantics",
    )
    reset_requires = set(families[0].get("contract_requires", [])) if families else set()
    check(
        {
            "active_latch",
            "budget_states",
            "history_state",
            "reset_authorization_token_sha256",
            "control_state_before",
            "control_state_after",
            "forbidden_combined_actions",
        }
        <= reset_requires,
        "OP-RESET-CONTRACT",
        "reset family lacks exact latch/budget/history/forbidden-action fields",
    )
    runtime_policy = catalog.get("runtime_cycle_policy", {})
    check(
        runtime_policy.get("applies_after_gate") == "G12C"
        and runtime_policy.get("operation_policy_id") == "OP-RUNTIME-CYCLE"
        and runtime_policy.get("seal_before_any_side_effect") is True
        and runtime_policy.get("journal_policy") == "REQUIRED_INTENT_FINALIZE"
        and runtime_policy.get("failure_actions")
        == ["OPEN_CIRCUIT", "SET_PAUSED", "ENSURE_PROCESS_ZERO", "FINALIZE_OR_RECONCILE_JOURNAL"]
        and runtime_policy.get("process_count_after") == 0,
        "OP-RUNTIME-CYCLE",
        "post-G12C cycle policy is incomplete",
    )
    default_invariants = catalog.get("default_invariants", {})
    check(
        default_invariants.get("final_activation_requires_distinct_purpose_bound_user_approvals") is True
        and default_invariants.get("runtime_cycle_requires_runtime_template_user_approval") is True,
        "OP-DUAL-AUTH-INVARIANTS",
        "operation catalog does not fail closed on the two purpose-bound approvals",
    )
    op12c_requires = set(by_node.get("OP12C", {}).get("contract_requires", []))
    check(
        {
            "runtime_template_gate_evidence",
            "runtime_template_user_approval_receipt",
            "final_activation_user_approval_receipt",
            "distinct_user_approval_receipts",
            "dual_authorization_binding",
        }
        <= op12c_requires,
        "OP-12C-DUAL-AUTH-CONTRACT",
        "OP12C static policy lacks the complete dual-authorization contract",
    )
    check(
        {"RUNTIME_TEMPLATE_USER_APPROVAL_RECEIPT", "G12C_RT_EVIDENCE"}
        <= set(runtime_policy.get("required_bindings", []))
        and {"RUNTIME_TEMPLATE_USER_APPROVAL_VALID", "G12C_RT_EVIDENCE_MATCH"}
        <= set(runtime_policy.get("revalidate_before_each_cycle", [])),
        "OP-RUNTIME-TEMPLATE-APPROVAL",
        "runtime-cycle policy does not bind and revalidate the approved runtime template",
    )
    check(
        "DUAL_ACTIVATION_AUTHORITY_CHAIN"
        in catalog.get("ordinary_autostart_transition", {}).get("requires", []),
        "OP-AUTOSTART-DUAL-AUTH",
        "ordinary autostart transition lacks dual-activation provenance",
    )

    authorization_schema = load_json("authorization_manifest.schema.json")
    authorization_text = json.dumps(authorization_schema, sort_keys=True)
    authorization_required = set(authorization_schema.get("required", []))
    approval_requirement = authorization_schema.get("$defs", {}).get("approvalRequirement", {})
    approval_purposes = set(
        approval_requirement.get("properties", {}).get("purpose", {}).get("enum", [])
    )
    check(
        "approval_requirement" in authorization_required
        and {"RUNTIME_TEMPLATE_AUTHORIZATION", "FINAL_AUTOSTART_ACTIVATION"}
        <= approval_purposes,
        "AUTH-PREAPPROVAL-PROPOSAL",
        "authorization manifest does not freeze both approval purposes",
    )
    check(
        "user_approval_receipt_sha256" not in authorization_text,
        "AUTH-RECEIPT-HASH-CYCLE",
        "pre-approval authorization manifest points to a future user receipt",
    )

    approval_schema = load_json("user_approval_receipt.schema.json")
    final_binding_required = set(
        approval_schema.get("$defs", {}).get("finalActivationBinding", {}).get("required", [])
    )
    check(
        {
            "final_activation_authorization_id",
            "final_activation_authorization_manifest_sha256",
            "final_approval_subject_digest_sha256",
            "runtime_template_approval_id",
            "runtime_template_approval_receipt_sha256",
        }
        <= final_binding_required,
        "USER-APPROVAL-FINAL-BINDING",
        "final user approval does not bind both the final authorization and prior runtime approval",
    )

    operation_contract_schema = load_json("operation_contract.schema.json")
    contract_required = set(operation_contract_schema.get("required", []))
    authority_binding = operation_contract_schema.get("$defs", {}).get(
        "activationAuthorityBinding", {}
    )
    check(
        "activation_authority_binding" in contract_required
        and set(authority_binding.get("properties", {}).get("phase", {}).get("enum", []))
        == {"RUNTIME_ONLY", "DUAL_APPROVED"}
        and "runtime_template_user_approval_receipt"
        in set(authority_binding.get("required", []))
        and "final_activation_user_approval_receipt"
        in set(authority_binding.get("required", [])),
        "CONTRACT-DUAL-AUTH-BINDING",
        "dynamic operation contract lacks exact runtime/final approval phases",
    )

    evidence_schema = load_json("evidence_manifest.schema.json")
    evidence_chain = evidence_schema.get("$defs", {}).get("activationAuthorityChain", {})
    evidence_phase_enum = set(
        evidence_chain.get("properties", {}).get("phase", {}).get("enum", [])
    )
    phase_by_node: dict[str, str] = {}
    for conditional in evidence_schema.get("allOf", []):
        node_rule = conditional.get("if", {}).get("properties", {}).get("node_id", {})
        node_id = node_rule.get("const")
        chain_rule = conditional.get("then", {}).get("properties", {}).get(
            "activation_authority_chain", {}
        )
        for clause in chain_rule.get("allOf", []):
            phase = clause.get("properties", {}).get("phase", {}).get("const")
            if isinstance(node_id, str) and isinstance(phase, str):
                phase_by_node[node_id] = phase
    check(
        evidence_phase_enum
        == {"RUNTIME_PREPARED", "RUNTIME_APPROVED", "FINAL_PREPARED", "DUAL_APPROVED"}
        and phase_by_node.get("D12C-RT") == "RUNTIME_PREPARED"
        and phase_by_node.get("G12C-RT") == "RUNTIME_APPROVED"
        and phase_by_node.get("D12C") == "FINAL_PREPARED",
        "EVIDENCE-DUAL-AUTH-PHASES",
        "evidence manifest can skip or mislabel a dual-authorization phase",
    )

    execution_receipt_schema = load_json("operation_execution_receipt.schema.json")
    execution_required = set(execution_receipt_schema.get("required", []))
    check(
        {
            "runtime_template_authorization_manifest_sha256",
            "runtime_template_authorization_revalidation_receipt_sha256",
            "runtime_template_user_approval_receipt_sha256",
            "g12c_rt_evidence_sha256",
            "final_activation_user_approval_receipt_sha256",
            "final_approval_subject_digest_sha256",
            "dual_approval_distinctness_verified",
        }
        <= execution_required,
        "EXECUTION-RECEIPT-DUAL-AUTH",
        "post-operation receipt does not preserve the activation authority chain",
    )


def registry_checks(fixed_ids: set[str]) -> None:
    registry = load_json("test_id_registry.v4.json")
    if not isinstance(registry, dict):
        return
    check(registry.get("plan_revision") == EXPECTED_PLAN_REVISION, "TEST-REV", "not v4")
    tests = registry.get("tests", [])
    test_ids = [test.get("id") for test in tests]
    concrete_ids = {test_id for test_id in test_ids if isinstance(test_id, str)}
    check(len(test_ids) == 315, "TEST-COUNT", f"expected 315, got {len(test_ids)}")
    check(len(test_ids) == len(concrete_ids), "TEST-ID", "duplicate/non-string test ID")
    required_v4_test_ids = {
        "BOOT-S01", "SCH-S01", "ARV-S01", "JRN-S01", "JRN-S02", "JRN-S03",
        "BUD-S01", "BUD-S02", "PROC-S01", "FIX-S01",
        "ACT-S11", "ACT-S12", "ACT-S13", "ACT-S14", "ACT-S15", "START-S11",
        "ZR1005-C1", "ZR1005-C2", "ZR1005-C3", "ZR1005-C4",
        "ZR1006-C1", "ZR1006-C2A", "ZR1006-C2B", "ZR1006-C3",
        "ZR1006-C4A", "ZR1006-C4B", "ZR1006-C4C", "ZR1006-C5A", "ZR1006-C5B",
    }
    check(
        required_v4_test_ids <= concrete_ids,
        "TEST-V4-CLOSURE",
        f"missing v4 hardening IDs: {sorted(required_v4_test_ids - concrete_ids)}",
    )
    by_test_id = {test.get("id"): test for test in tests if isinstance(test.get("id"), str)}
    baseline_ids = {test_id for test_id in required_v4_test_ids if test_id.startswith("ZR100")}
    check(
        all(by_test_id[test_id].get("expected_red_at") == [] for test_id in baseline_ids),
        "TEST-BASELINE-LIFECYCLE",
        "existing ZR1005/ZR1006 baselines must be explicitly never-red",
    )
    check(
        all(by_test_id[test_id].get("required_green_at") == ["G11A"] for test_id in baseline_ids)
        and all("G11J" in by_test_id[test_id].get("required_green_at", []) for test_id in {"JRN-S01", "JRN-S02", "JRN-S03"}),
        "TEST-PRODUCTION-DUE-NODES",
        "G11A/G11J have no explicit stable-test obligations",
    )

    condition_contract = registry.get("condition_contract", {})
    definitions = registry.get("condition_definitions", {})
    expected_condition_ids = {
        "MEASUREMENT_VM_STEP_EXACT",
        "ADR02_SELECTED_BRANCH_LIFECYCLE",
        "ADR02_NO_INDEX",
        "ADR02_INDEX",
        "ADR11_LLM_ENABLED",
        "ADR11_SELECTED_PROFILE_LIFECYCLE",
        "ADR11_LLM_ENABLED_ADR13_REVALIDATION",
        "PARSER_ROUTE_MEDIUM_ENABLED",
    }
    check(
        set(definitions) == expected_condition_ids,
        "TEST-CONDITION-CATALOG",
        f"condition IDs drifted: {sorted(definitions)}",
    )
    check(
        condition_contract
        == {
            "free_text_conditions_allowed": False,
            "undefined_condition_ids_allowed": False,
            "null_means_unconditional": True,
            "branch_definition_arrays_are_exact_case_union": True,
            "selected_case_is_only_runtime_lifecycle": True,
            "unselected_case_ledger_records_allowed": False,
            "evaluation_inputs_and_hashes_must_be_evidence": True,
        },
        "TEST-CONDITION-CONTRACT",
        "condition contract is not fail closed",
    )
    for test in tests:
        condition_id = test.get("condition_id")
        check(
            condition_id is None or condition_id in definitions,
            "TEST-CONDITION-REF",
            f"{test.get('id')}: {condition_id!r}",
        )
        check("condition" not in test, "TEST-FREE-TEXT-CONDITION", str(test.get("id")))

    for condition_id in (
        "ADR02_SELECTED_BRANCH_LIFECYCLE",
        "ADR11_SELECTED_PROFILE_LIFECYCLE",
    ):
        definition = definitions.get(condition_id, {})
        cases = definition.get("cases", {})
        check(
            set(cases) == set(definition.get("allowed_values", [])),
            "TEST-BRANCH-CASES",
            f"{condition_id}: cases/allowed values differ",
        )
        for test in (item for item in tests if item.get("condition_id") == condition_id):
            for field in (
                "introduced_at",
                "variant_at",
                "expected_red_at",
                "required_green_at",
                "revalidate_at",
            ):
                expected_union: list[str] = []
                for case_name in definition.get("allowed_values", []):
                    for node_id in cases.get(case_name, {}).get(field, []):
                        if node_id not in expected_union:
                            expected_union.append(node_id)
                check(
                    test.get(field, []) == expected_union,
                    "TEST-BRANCH-UNION",
                    f"{test.get('id')}/{field}: got {test.get(field, [])}, expected {expected_union}",
                )
    check(
        definitions.get("ADR11_LLM_ENABLED", {}).get("allowed_values")
        == ["LLM_ENABLED", "LLM_OFF"]
        and definitions.get("ADR11_SELECTED_PROFILE_LIFECYCLE", {}).get("allowed_values")
        == ["LLM_ENABLED", "LLM_OFF"],
        "TEST-ADR11-VOCABULARY",
        "condition catalog does not match gate_dag ADR-11 values",
    )
    try:
        route_test_pattern = re.compile(
            definitions["PARSER_ROUTE_MEDIUM_ENABLED"]["test_id_pattern"]
        )
    except (KeyError, re.error) as exc:
        ERRORS.append(f"TEST-ROUTE-CONDITION: invalid route pattern: {exc}")
        route_test_pattern = re.compile(r"(?!)")
    for test in (item for item in tests if item.get("condition_id") == "PARSER_ROUTE_MEDIUM_ENABLED"):
        check(
            route_test_pattern.fullmatch(test.get("id", "")) is not None,
            "TEST-ROUTE-CONDITION",
            f"{test.get('id')}: route predicate does not derive a route",
        )

    dag = load_json("gate_dag.v4.json")
    family_node_templates: set[str] = set()
    if isinstance(dag, dict):
        for family in dag.get("families", {}).values():
            family_node_templates.update(family.get("nodes_per_instance", []))
    allowed_lifecycle_nodes = fixed_ids | family_node_templates
    for test in tests:
        for field in (
            "introduced_at",
            "variant_at",
            "expected_red_at",
            "required_green_at",
            "revalidate_at",
        ):
            for node_id in test.get(field, []):
                check(
                    node_id in allowed_lifecycle_nodes,
                    "TEST-LIFECYCLE-NODE",
                    f"{test.get('id')}/{field}: {node_id}",
                )

    parser_schema = load_json("parser_route_manifest.schema.json")
    try:
        route_fields = set(parser_schema["$defs"]["supportedRoute"]["properties"])
    except (KeyError, TypeError):
        route_fields = set()
    try:
        route_keys = set(parser_schema["properties"]["routes"]["properties"])
    except (KeyError, TypeError):
        route_keys = set()
    check(
        route_keys
        == {"01", "02", "03H", "03T", "04P", "04D", "05", "06", "07", "08", "09", "10J", "10X", "99"},
        "TEST-PARSER-ROUTES",
        f"parser route keys drifted: {sorted(route_keys)}",
    )
    template_patterns: list[re.Pattern[str]] = []
    for template in registry.get("templates", []):
        try:
            template_patterns.append(re.compile(template["pattern"]))
        except (KeyError, re.error) as exc:
            ERRORS.append(f"TEST-TEMPLATE: {template.get('template_id')}: {exc}")
        check(
            template.get("minimum_samples_field") in route_fields,
            "TEST-PARSER-FIELD",
            f"{template.get('template_id')}: {template.get('minimum_samples_field')}",
        )

    extraction = registry.get("reference_extraction", {})
    try:
        token_regex = re.compile(extraction["token_regex"])
    except (KeyError, re.error) as exc:
        ERRORS.append(f"TEST-TOKEN-REGEX: {exc}")
        return
    sample_text = "GL-S01 Q-P02 P-FMT01-S P-FMT00-ROUTE"
    check(
        token_regex.findall(sample_text)
        == ["GL-S01", "Q-P02", "P-FMT01-S", "P-FMT00-ROUTE"],
        "TEST-TOKEN-REGEX",
        f"sample extraction failed: {token_regex.findall(sample_text)!r}",
    )
    range_regex = re.compile(
        r"`?(?<![A-Z0-9])([A-Z][A-Z0-9-]*[0-9]{2})`?[ \t]*[–—][ \t]*"
        r"`?(?:[A-Z][A-Z0-9-]*)?[0-9]{2}`?"
    )
    for source_name in extraction.get("active_sources", []):
        source_path = ROOT / source_name
        check(source_path.is_file(), "TEST-SOURCE", f"missing {source_name}")
        if not source_path.is_file():
            continue
        source_text = source_path.read_text(encoding="utf-8")
        for token in token_regex.findall(source_text):
            resolved = token in concrete_ids or any(
                pattern.fullmatch(token) is not None for pattern in template_patterns
            )
            check(resolved, "TEST-UNRESOLVED", f"{source_name}: {token}")
        for match in range_regex.finditer(source_text):
            first = match.group(1)
            if token_regex.fullmatch(first):
                ERRORS.append(
                    f"TEST-RANGE: {source_name}: expand abbreviated reference {match.group(0)!r}"
                )


def vector_checks() -> None:
    vectors_document = load_json("gate_ledger_validator_vectors.v4.json")
    if not isinstance(vectors_document, dict):
        return
    check(
        vectors_document.get("plan_revision") == EXPECTED_PLAN_REVISION,
        "VECTOR-REV",
        "not v4",
    )
    vectors = vectors_document.get("vectors", [])
    reason_mappings = vectors_document.get("reason_rule_mappings", {})
    vector_ids = [vector.get("id") for vector in vectors]
    check(set(vector_ids) == EXPECTED_VECTOR_IDS, "VECTOR-ID", f"got {sorted(vector_ids)}")
    check(len(vector_ids) == len(set(vector_ids)), "VECTOR-ID", "duplicate vector ID")
    case_ids: list[str] = []
    for vector in vectors:
        kind = vector.get("kind")
        for case in vector.get("cases", []):
            case_ids.append(case.get("case_id"))
            mapping = reason_mappings.get(case.get("reason_rule_id"), {})
            check(
                bool(mapping),
                "VECTOR-REASON-RULE",
                f"{case.get('case_id')}: missing {case.get('reason_rule_id')}",
            )
            if mapping:
                check(
                    mapping.get("primary_code") == case.get("expected_primary_code")
                    and mapping.get("validation_stage") == case.get("validation_stage"),
                    "VECTOR-REASON-RULE",
                    f"{case.get('case_id')}: case/mapping mismatch",
                )
                prefix = mapping.get("pointer_prefix")
                pointer = case.get("expected_pointer")
                check(
                    prefix is None
                    or (isinstance(pointer, str) and pointer.startswith(prefix)),
                    "VECTOR-REASON-POINTER",
                    f"{case.get('case_id')}: {pointer!r} not beneath {prefix!r}",
                )
            if kind == "positive":
                check(
                    case.get("expected_exit") == 0
                    and case.get("expected_primary_code") == "OK",
                    "VECTOR-OUTCOME",
                    f"{case.get('case_id')}: positive must be exit=0/OK",
                )
            elif kind == "negative":
                check(
                    case.get("expected_exit") == 1
                    and re.fullmatch(r"GLV-E[0-9]{3}", case.get("expected_primary_code", ""))
                    is not None,
                    "VECTOR-OUTCOME",
                    f"{case.get('case_id')}: negative exit/code mismatch",
                )
            else:
                check(False, "VECTOR-KIND", f"{vector.get('id')}: {kind!r}")
    check(len(case_ids) == len(set(case_ids)), "VECTOR-CASE-ID", "duplicate case ID")
    shape_cases = {
        case.get("case_id"): case.get("expected_primary_code")
        for vector in vectors
        for case in vector.get("cases", [])
        if case.get("case_id") in {"GL-F04-C", "GL-F04-D", "GL-F04-E"}
    }
    check(
        shape_cases
        == {
            "GL-F04-C": "GLV-E002",
            "GL-F04-D": "GLV-E002",
            "GL-F04-E": "GLV-E002",
        },
        "VECTOR-PRECEDENCE",
        f"shape-invalid cases must fail at schema boundary E002: {shape_cases}",
    )
    required_new_codes = {*(f"GLV-E{i:03d}" for i in range(30, 46))}
    observed_codes = {
        case.get("expected_primary_code")
        for vector in vectors
        for case in vector.get("cases", [])
    }
    check(
        required_new_codes <= observed_codes,
        "VECTOR-NEW-CONTRACT-CODES",
        f"missing {sorted(required_new_codes - observed_codes)}",
    )
    by_case = {
        case.get("case_id"): case
        for vector in vectors
        for case in vector.get("cases", [])
    }
    check(
        by_case.get("GL-F03-D", {}).get("mutation", {}).get("source_pointer")
        == "/records/0/executor_agent_id"
        and by_case.get("GL-F03-D", {}).get("expected_primary_code") == "GLV-E020",
        "VECTOR-F03-D",
        "executor-reuse case does not target a prior executor record",
    )
    check(
        by_case.get("GL-F04-G", {}).get("mutation", {}).get("source_pointer")
        == "/base_scenarios/0/scenario_id"
        and by_case.get("GL-F04-H", {}).get("mutation", {}).get("target_pointer")
        == "/base_scenarios/0/expected_result",
        "VECTOR-FIXTURE-POINTER",
        "fixture-catalog mutations do not match validator_fixture_manifest schema",
    )
    fixture_contract = vectors_document.get("fixture_contract", {})
    check(
        fixture_contract.get("manifest_instance_path") == "validator_fixture_manifest.v2.json"
        and fixture_contract.get("scenario_schema_path")
        == "validator_scenario_fixture.schema.json"
        and fixture_contract.get("base_fixture_field_semantics")
        == "COMPOSITE_SCENARIO_ID_LEGACY_WIRE_NAME"
        and fixture_contract.get("case_to_mutation_id_policy")
        == "MUTATION_ID_EQUALS_CASE_ID"
        and fixture_contract.get("materialized_mutation_required") is True
        and fixture_contract.get("pointer_and_type_checked_before_execution") is True
        and fixture_contract.get("derived_recompute_closure_required") is True,
        "VECTOR-COMPOSITE-FIXTURE",
        "vectors are not bound to materialized composite scenarios and recomputation closure",
    )


def catalog_pointer_checks() -> None:
    dag = load_json("gate_dag.v4.json")
    catalog = load_json("operation_contracts.v4.json")
    if isinstance(dag, dict):
        pointer = dag.get("operation_policy_catalog")
        check(isinstance(pointer, str) and (ROOT / pointer).is_file(), "POINTER", str(pointer))
    if isinstance(catalog, dict):
        for field in (
            "dynamic_contract_schema",
            "operation_intent_schema",
            "authorization_schema",
            "journal_manifest_schema",
            "evidence_manifest_schema",
        ):
            pointer = catalog.get(field)
            check(
                isinstance(pointer, str) and (ROOT / pointer).is_file(),
                "POINTER",
                f"{field}={pointer}",
            )


def immutable_history_checks() -> None:
    for name, expected_sha256 in IMMUTABLE_HISTORY_SHA256.items():
        path = ROOT / name
        try:
            actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            ERRORS.append(f"IMMUTABLE-HISTORY: {name}: {exc}")
            continue
        check(
            actual_sha256 == expected_sha256,
            "IMMUTABLE-HISTORY",
            f"{name}: expected {expected_sha256}, got {actual_sha256}",
        )


def active_prose_semantic_checks() -> None:
    texts: dict[str, str] = {}
    for name in ACTIVE_PROSE_FILES:
        try:
            texts[name] = (ROOT / name).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            ERRORS.append(f"PROSE-LOAD: {name}: {exc}")
            texts[name] = ""

    combined = "\n".join(texts.values())
    forbidden_fragments = {
        "PROSE-OLD-VALIDATOR-RELEASE": "validator_release_manifest.v1.json",
        "PROSE-STDLIB-ONLY": "stdlib-only",
        "PROSE-CONDITIONAL-DELETE-EN": "conditional delete",
        "PROSE-CONDITIONAL-DELETE-HYPHEN": "conditional-delete",
        "PROSE-CONDITIONAL-DELETE-ZH": "条件删除",
        "PROSE-IMPOSSIBLE-ARM-STATE": "ARMED_ON_PRELOGIN/OFF",
        "PROSE-OLD-COUNT-TESTS": "283个concrete test ID",
        "PROSE-OLD-COUNT-SCHEMAS": "10个schema",
    }
    for code, fragment in forbidden_fragments.items():
        check(fragment not in combined, code, f"active prose contains {fragment!r}")

    for name in ACTIVE_PROSE_FILES:
        text = texts[name]
        check(
            "D12C-RT" in text and "G12C-RT" in text,
            "PROSE-DUAL-AUTH",
            f"{name}: missing runtime-template authorization nodes",
        )

    validator_text = texts["ledger_validator_contract.md"]
    for token in (
        "-I -S -B",
        "--schema-registry",
        "--release-manifest",
        "--fixture-manifest",
        "--scenario",
        "--vector-schema",
        "--head-anchor",
        "--clock",
    ):
        check(token in validator_text, "PROSE-VALIDATOR-CLI", f"missing {token}")

    rollback_text = "\n".join(
        texts[name]
        for name in (
            "task_plan.md",
            "execution_playbook.md",
            "test_acceptance_plan.md",
            "agent_review_gates.md",
            "gate_state_machine.md",
            "acceptance_thresholds.md",
            "rollout_rollback_runbook.md",
            "implementation_agent_prompts.md",
        )
    )
    for token in (
        "VERIFY_ABSENT",
        "VERIFY_OWNED_PRESERVE",
        "VERIFY_CONFLICT_PRESERVE",
        "PAUSED/ON",
        "PAUSED/REGISTRY_CONFLICT",
    ):
        check(token in rollback_text, "PROSE-ROLLBACK-BRANCH", f"missing {token}")


def has_reparse_component(relative_name: str) -> bool:
    candidate = ROOT
    for component in Path(relative_name).parts:
        candidate = candidate / component
        try:
            stat_result = candidate.lstat()
        except OSError:
            return True
        if candidate.is_symlink():
            return True
        if getattr(stat_result, "st_file_attributes", 0) & 0x400:
            return True
    return False


def current_coverage_counts(fixed_ids: set[str]) -> dict[str, int]:
    vectors = load_json("gate_ledger_validator_vectors.v4.json")
    tests = load_json("test_id_registry.v4.json")
    try:
        traceability = (ROOT / "traceability_matrix.md").read_text(encoding="utf-8")
        review_findings = (ROOT / "plan_review_findings.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        ERRORS.append(f"MANIFEST-COVERAGE-LOAD: {exc}")
        traceability = ""
        review_findings = ""
    vector_groups = vectors.get("vectors", []) if isinstance(vectors, dict) else []
    test_entries = tests.get("tests", []) if isinstance(tests, dict) else []
    return {
        "fixed_dag_nodes": len(fixed_ids),
        "stable_test_ids": len(test_entries),
        "validator_vector_groups": len(vector_groups),
        "validator_vector_cases": sum(
            len(group.get("cases", [])) for group in vector_groups if isinstance(group, dict)
        ),
        "schemas": len(SCHEMA_FILES),
        "requirements": len(set(re.findall(r"\bRQ-[0-9]{3}\b", traceability))),
        "risks": len(set(re.findall(r"\bRK-[0-9]{2}\b", traceability))),
        "plan_review_findings": len(set(re.findall(r"\bPR-[0-9]{3}\b", review_findings))),
    }


def pre_freeze_output_checks() -> tuple[bytes, int | None]:
    path = ROOT / "plan_freeze_check.v4.txt"
    try:
        payload = path.read_bytes()
    except OSError as exc:
        ERRORS.append(f"PREFREEZE-OUTPUT: {exc}")
        payload = b""
    check(bool(payload), "PREFREEZE-OUTPUT", "missing/empty plan_freeze_check.v4.txt")
    check(b"\r" not in payload, "PREFREEZE-OUTPUT", "must use LF without CR")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        ERRORS.append(f"PREFREEZE-OUTPUT: invalid UTF-8: {exc}")
        text = ""
    match = re.fullmatch(
        r"PASS: ([0-9]+) checks; \{\"fixed_nodes\": 115, \"schemas\": 29, "
        r"\"tests\": 315, \"vectors\": 18\}\n"
        r"READ_ONLY: no production database, registry, process, source, config, or network access\n",
        text,
    )
    check(match is not None, "PREFREEZE-OUTPUT", "unexpected pre-freeze stdout")
    return payload, int(match.group(1)) if match else None


def plan_manifest_checks(fixed_ids: set[str], prefreeze_payload: bytes, prefreeze_count: int | None) -> None:
    manifest_path = ROOT / "plan_manifest.v4.json"
    manifest_present = manifest_path.is_file()
    manifest = load_json("plan_manifest.v4.json") if manifest_present else {}
    manifest_valid = isinstance(manifest, dict)
    if manifest_present and manifest_valid:
        schema = load_json("plan_manifest.schema.json")
        errors = list(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(manifest)
        ) if isinstance(schema, dict) else ["missing schema"]
        if errors:
            for error in errors[:20]:
                if isinstance(error, str):
                    ERRORS.append(f"MANIFEST-SCHEMA: {error}")
                else:
                    location = "/".join(str(part) for part in error.absolute_path) or "$"
                    ERRORS.append(f"MANIFEST-SCHEMA: {location}: {error.message}")
        schema_valid = not errors
    else:
        schema_valid = not manifest_present
    check(schema_valid, "MANIFEST-SCHEMA", "plan_manifest.v4.json is invalid")

    entries = manifest.get("normative_files", []) if manifest_valid else []
    entry_paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
    expected_set = set(EXPECTED_NORMATIVE_FILES)
    actual_set = {path for path in entry_paths if isinstance(path, str)}
    check(
        (not manifest_present)
        or (manifest.get("normative_file_count") == len(EXPECTED_NORMATIVE_FILES)
            and len(entries) == len(EXPECTED_NORMATIVE_FILES)),
        "MANIFEST-COUNT",
        f"expected {len(EXPECTED_NORMATIVE_FILES)} normative files",
    )
    check(
        (not manifest_present) or actual_set == expected_set,
        "MANIFEST-FILE-SET",
        f"missing={sorted(expected_set - actual_set)}, extra={sorted(actual_set - expected_set)}",
    )
    check(
        (not manifest_present)
        or len(entry_paths) == len({path.casefold() for path in entry_paths if isinstance(path, str)}),
        "MANIFEST-PATH-UNIQUE",
        "normative paths collide after Windows case-folding",
    )
    check(
        (not manifest_present) or "plan_manifest.v4.json" not in actual_set,
        "MANIFEST-SELF",
        "manifest must not include itself",
    )

    by_path = {
        entry.get("path"): entry for entry in entries if isinstance(entry, dict)
    }
    for name in EXPECTED_NORMATIVE_FILES:
        entry = by_path.get(name)
        candidate = ROOT / name
        check((not manifest_present) or isinstance(entry, dict), "MANIFEST-ENTRY", name)
        check((not manifest_present) or candidate.is_file(), "MANIFEST-FILE", name)
        safe = False
        try:
            safe = (
                candidate.resolve(strict=True).parent == ROOT.resolve(strict=True)
                and not has_reparse_component(name)
            )
        except OSError:
            safe = False
        check((not manifest_present) or safe, "MANIFEST-PATH-SAFETY", name)
        if manifest_present and isinstance(entry, dict) and candidate.is_file():
            payload = candidate.read_bytes()
            matches_bytes = (
                entry.get("size_bytes") == len(payload)
                and entry.get("sha256") == hashlib.sha256(payload).hexdigest()
            )
        else:
            matches_bytes = not manifest_present
        check(matches_bytes, "MANIFEST-BYTES", name)

    expected_coverage = current_coverage_counts(fixed_ids)
    check(
        (not manifest_present) or manifest.get("coverage_counts") == expected_coverage,
        "MANIFEST-COVERAGE",
        f"expected {expected_coverage}",
    )
    check(
        (not manifest_present)
        or set(manifest.get("excluded_dynamic_or_historical_paths", []))
        == EXPECTED_MANIFEST_EXCLUSIONS,
        "MANIFEST-EXCLUSIONS",
        "dynamic/historical exclusions differ",
    )

    source_path = ROOT.parents[1] / "worker-investigation-2026-08-20.md"
    try:
        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    except OSError:
        source_hash = None
    check(
        (not manifest_present)
        or (
            manifest.get("investigation_source", {}).get("sha256") == source_hash
            == "8e6166ba063bc281ca1fa5da3c0743b895e4d93b6f2957de3cbd0b6938a95be6"
        ),
        "MANIFEST-SOURCE",
        f"source hash={source_hash}",
    )

    prefreeze = manifest.get("pre_freeze_check", {}) if manifest_valid else {}
    check(
        (not manifest_present)
        or prefreeze.get("stdout_sha256") == hashlib.sha256(prefreeze_payload).hexdigest(),
        "MANIFEST-PREFREEZE-HASH",
        "stored stdout hash differs",
    )
    check(
        (not manifest_present)
        or prefreeze.get("reported_check_count") == prefreeze_count,
        "MANIFEST-PREFREEZE-COUNT",
        f"stored={prefreeze.get('reported_check_count')}, file={prefreeze_count}",
    )


def main() -> int:
    schema_checks()
    nodes, fixed_ids = dag_checks()
    operation_checks(nodes)
    registry_checks(fixed_ids)
    vector_checks()
    catalog_pointer_checks()
    immutable_history_checks()
    active_prose_semantic_checks()
    prefreeze_payload, prefreeze_count = pre_freeze_output_checks()
    plan_manifest_checks(fixed_ids, prefreeze_payload, prefreeze_count)

    if ERRORS:
        print(f"FAIL: {len(ERRORS)} error(s) after {CHECKS} checks")
        for error in ERRORS:
            print(f"- {error}")
        return 1
    counts = {
        "fixed_nodes": len(fixed_ids),
        "tests": len(load_json("test_id_registry.v4.json")["tests"]),
        "vectors": len(load_json("gate_ledger_validator_vectors.v4.json")["vectors"]),
        "schemas": len(SCHEMA_FILES),
    }
    print(f"PASS: {CHECKS} checks; {json.dumps(counts, sort_keys=True)}")
    print("READ_ONLY: no production database, registry, process, source, config, or network access")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
