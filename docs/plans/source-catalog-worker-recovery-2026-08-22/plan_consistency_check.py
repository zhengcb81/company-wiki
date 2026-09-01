#!/usr/bin/env python3
"""Read-only mechanical consistency checks for the frozen worker recovery plan.

This helper deliberately performs no writes, opens no production database, touches
no registry key, starts no process, and makes no network request.  It checks the
plan artifacts that must agree before a revision may be frozen for review.
"""

from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover - fail closed in an unprepared host
    print(f"FAIL DEPENDENCY: jsonschema is required: {exc}")
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parent

SCHEMA_FILES = (
    "gate_dag.schema.json",
    "operation_contracts.schema.json",
    "gate_ledger_validator_vectors.schema.json",
    "test_id_registry.schema.json",
    "gate_ledger.schema.json",
    "operation_contract.schema.json",
    "authorization_manifest.schema.json",
    "review_result.schema.json",
    "review_confirmation.schema.json",
    "parser_route_manifest.schema.json",
    "operation_intent_manifest.schema.json",
    "journal_manifest.schema.json",
    "evidence_manifest.schema.json",
    "validator_fixture_manifest.schema.json",
    "validator_release_manifest.schema.json",
    "plan_manifest.schema.json",
)

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
    "D12C_FREEZES_EXACT_INTENT_BEFORE_FINAL_USER_AUTHORIZATION",
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
    elif isinstance(value, list):
        for child in value:
            yield from iter_refs(child)


def resolve_ref(owner_name: str, owner: Any, ref: str) -> None:
    try:
        if ref.startswith("#"):
            json_pointer(owner, ref)
            return
        file_part, marker, fragment = ref.partition("#")
        check(bool(file_part), "SCHEMA-REF", f"{owner_name}: empty external reference")
        target = load_json(file_part)
        check(target is not None, "SCHEMA-REF", f"{owner_name}: missing {file_part}")
        if target is not None and marker:
            json_pointer(target, f"#{fragment}")
    except (KeyError, IndexError, ValueError) as exc:
        ERRORS.append(f"SCHEMA-REF: {owner_name}: unresolved {ref!r}: {exc}")


def schema_checks() -> None:
    for name in SCHEMA_FILES:
        schema = load_json(name)
        if schema is None:
            continue
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
        for malformed in ({}, [], "shape-negative"):
            check(
                not Draft202012Validator(schema).is_valid(malformed),
                "SCHEMA-SHAPE",
                f"{name}: accepts malformed top-level {malformed!r}",
            )
        for ref in iter_refs(schema):
            resolve_ref(name, schema, ref)

    for instance_name, schema_name in INSTANCE_PAIRS:
        instance = load_json(instance_name)
        schema = load_json(schema_name)
        if instance is None or schema is None:
            continue
        errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
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
    check(
        "optional_external_successor" not in by_id.get("G12B-POST", {})
        and by_id.get("D12C", {}).get("optional_external_successor", {}).get("node")
        == "G12C-PRE",
        "DAG-12C-AUTH-ORDER",
        "D12C must freeze intent before final user approval",
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
            "VERIFY_ABSENT_OR_CONDITIONAL_DELETE_EXACT_OWNED_PRESERVE_CONFLICT",
            "VERIFY_OR_PRESERVE_CONFLICT",
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
    check(
        ["ARMED_PRELOGIN/OFF", "PAUSED/REGISTRY_CONFLICT"]
        in by_node.get("OP12B-RB", {}).get("state_sequence_options", []),
        "OP-12B-CONFLICT",
        "pre-CAS ARM rollback lacks a registry-conflict terminal state",
    )
    check(
        ["ENABLED_IDLE/ON", "PAUSED/REGISTRY_CONFLICT"]
        in by_node.get("OP12C-RB", {}).get("state_sequence_options", []),
        "OP-12C-CONFLICT",
        "final-activation rollback lacks a registry-conflict terminal state",
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


def registry_checks(fixed_ids: set[str]) -> None:
    registry = load_json("test_id_registry.v4.json")
    if not isinstance(registry, dict):
        return
    check(registry.get("plan_revision") == EXPECTED_PLAN_REVISION, "TEST-REV", "not v4")
    tests = registry.get("tests", [])
    test_ids = [test.get("id") for test in tests]
    concrete_ids = {test_id for test_id in test_ids if isinstance(test_id, str)}
    check(len(test_ids) == 286, "TEST-COUNT", f"expected 286, got {len(test_ids)}")
    check(len(test_ids) == len(concrete_ids), "TEST-ID", "duplicate/non-string test ID")

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
    required_new_codes = {"GLV-E030", "GLV-E031", "GLV-E032", "GLV-E033", "GLV-E034"}
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
        == "/base_fixtures/0/fixture_id"
        and by_case.get("GL-F04-H", {}).get("mutation", {}).get("target_pointer")
        == "/base_fixtures/0/expected_result",
        "VECTOR-FIXTURE-POINTER",
        "fixture-catalog mutations do not match validator_fixture_manifest schema",
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


def main() -> int:
    schema_checks()
    nodes, fixed_ids = dag_checks()
    operation_checks(nodes)
    registry_checks(fixed_ids)
    vector_checks()
    catalog_pointer_checks()

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
