"""Validation for ``du-gold/1`` and ``du-observed/1`` records.

Validation rejects real structural errors (wrong schema version, duplicate fact
ids, unknown enums, malformed quote anchors). It never demands an authorization
file, an expected Git HEAD, a policy hash or a fresh source-identity check.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .schema import (
    CRITICAL,
    DEVELOPMENT,
    FACT_SCOPES,
    GOLD_SCHEMA_VERSION,
    IMPORTANCES,
    MODALITY_VALUES,
    NATIVE_SCAN_VALUES,
    OBSERVED_SCHEMA_VERSION,
    QUANTITY_BASIS_VALUES,
    ROLE_VALUES,
    SCOPES,
    BenchmarkSchemaError,
    _optional_sequence,
    _optional_text,
    _require_enum,
    _require_mapping,
    _require_sequence,
    _require_sha256,
    _require_text,
)
# ---------------------------------------------------------------------------
# gold
# ---------------------------------------------------------------------------


def _validate_quote_anchor(anchor: Any, where: str) -> dict[str, Any]:
    mapping = _require_mapping(anchor, where)
    page = mapping.get("page")
    line = mapping.get("line")
    if page is None and line is None:
        raise BenchmarkSchemaError(f"{where} needs either page or line")
    if page is not None and (isinstance(page, bool) or not isinstance(page, int) or page < 1):
        raise BenchmarkSchemaError(f"{where}.page must be a positive integer")
    if line is not None and (isinstance(line, bool) or not isinstance(line, int) or line < 1):
        raise BenchmarkSchemaError(f"{where}.line must be a positive integer")
    quote = _require_text(mapping.get("exact_quote"), f"{where}.exact_quote")
    return {
        "page": page,
        "line": line,
        "exact_quote": quote,
        "locator": _optional_text(mapping.get("locator"), f"{where}.locator"),
    }


def validate_gold(gold: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one ``du-gold/1`` record."""

    record = _require_mapping(gold, "gold")
    version = record.get("schema_version")
    if version != GOLD_SCHEMA_VERSION:
        raise BenchmarkSchemaError(f"gold schema_version must be {GOLD_SCHEMA_VERSION}")

    fact_ids: set[str] = set()
    facts: list[dict[str, Any]] = []
    total_quote_chars = 0
    for index, raw_fact in enumerate(_require_sequence(record.get("facts"), "gold.facts")):
        where = f"gold.facts[{index}]"
        fact = _require_mapping(raw_fact, where)
        fact_id = _require_text(fact.get("id"), f"{where}.id")
        if fact_id in fact_ids:
            raise BenchmarkSchemaError(f"duplicate gold fact id: {fact_id}")
        fact_ids.add(fact_id)
        importance = _require_enum(fact.get("importance"), IMPORTANCES, f"{where}.importance")
        support_sets = []
        for set_index, raw_set in enumerate(
            _require_sequence(fact.get("any_support_sets"), f"{where}.any_support_sets")
        ):
            set_where = f"{where}.any_support_sets[{set_index}]"
            anchors = [
                _validate_quote_anchor(anchor, f"{set_where}[{anchor_index}]")
                for anchor_index, anchor in enumerate(_require_sequence(raw_set, set_where))
            ]
            if not anchors:
                raise BenchmarkSchemaError(f"{set_where} must contain at least one anchor")
            total_quote_chars += sum(len(anchor["exact_quote"]) for anchor in anchors)
            support_sets.append(anchors)
        if not support_sets:
            raise BenchmarkSchemaError(f"{where}.any_support_sets must not be empty")
        facts.append(
            {
                "id": fact_id,
                "importance": importance,
                "any_support_sets": support_sets,
                "must_preserve": [
                    _require_text(item, f"{where}.must_preserve")
                    for item in _optional_sequence(fact.get("must_preserve"), f"{where}.must_preserve")
                ],
                "must_not_assert": [
                    _require_text(item, f"{where}.must_not_assert")
                    for item in _optional_sequence(
                        fact.get("must_not_assert"), f"{where}.must_not_assert"
                    )
                ],
                "reason": _optional_text(fact.get("reason"), f"{where}.reason") or "",
                "key_fact": bool(fact.get("key_fact", importance == CRITICAL)),
                "quantity_basis": _require_enum(
                    fact.get("quantity_basis", "unknown"),
                    QUANTITY_BASIS_VALUES,
                    f"{where}.quantity_basis",
                ),
                "modality": _require_enum(
                    fact.get("modality", "unknown"),
                    MODALITY_VALUES,
                    f"{where}.modality",
                ),
                "role": _require_enum(
                    fact.get("role", "unknown"), ROLE_VALUES, f"{where}.role"
                ),
                "fact_scope": _require_enum(
                    fact.get("fact_scope", "narrative"),
                    FACT_SCOPES,
                    f"{where}.fact_scope",
                ),
            }
        )

    families = [
        _require_text(item, "gold.expected_route_families")
        for item in _optional_sequence(
            record.get("expected_route_families"), "gold.expected_route_families"
        )
    ]

    return {
        "schema_version": GOLD_SCHEMA_VERSION,
        "sample_id": _require_text(record.get("sample_id"), "gold.sample_id"),
        "source_sha256": _require_sha256(record.get("source_sha256"), "gold.source_sha256"),
        "scope": _require_enum(record.get("scope"), SCOPES, "gold.scope"),
        "language": _optional_text(record.get("language"), "gold.language"),
        "expected_route_families": families,
        "facts": facts,
        "notes": _optional_text(record.get("notes"), "gold.notes") or "",
        "gold_quote_chars": total_quote_chars,
    }


def gold_is_holdout(gold: Mapping[str, Any]) -> bool:
    return gold.get("scope") != DEVELOPMENT


# ---------------------------------------------------------------------------
# observed
# ---------------------------------------------------------------------------


def _validate_route(route: Any, where: str) -> dict[str, Any] | None:
    if route is None:
        return None
    mapping = _require_mapping(route, where)
    return {
        "family": _optional_text(mapping.get("family"), f"{where}.family"),
        "subtype": _optional_text(mapping.get("subtype"), f"{where}.subtype"),
        "regime": _optional_text(mapping.get("regime"), f"{where}.regime"),
        "confidence": _optional_text(mapping.get("confidence"), f"{where}.confidence"),
        "document_kind": _optional_text(mapping.get("document_kind"), f"{where}.document_kind"),
        "profile_id": _optional_text(mapping.get("profile_id"), f"{where}.profile_id"),
        "raw": dict(mapping),
    }


def _validate_claim(claim: Any, where: str) -> dict[str, Any]:
    mapping = _require_mapping(claim, where)
    quantities = []
    for index, raw_quantity in enumerate(_optional_sequence(mapping.get("quantities"), f"{where}.quantities")):
        q_where = f"{where}.quantities[{index}]"
        quantity = _require_mapping(raw_quantity, q_where)
        value = quantity.get("value")
        if value is not None and isinstance(value, bool):
            raise BenchmarkSchemaError(f"{q_where}.value must be a number, string or null")
        if value is not None and not isinstance(value, (int, float, str)):
            raise BenchmarkSchemaError(f"{q_where}.value must be a number, string or null")
        quantities.append(
            {
                "value": value,
                "unit": _optional_text(quantity.get("unit"), f"{q_where}.unit"),
                "currency": _optional_text(quantity.get("currency"), f"{q_where}.currency"),
                "period": _optional_text(quantity.get("period"), f"{q_where}.period"),
                "basis": _require_enum(
                    quantity.get("basis", "unknown"), QUANTITY_BASIS_VALUES, f"{q_where}.basis"
                ),
            }
        )
    return {
        "text": _require_text(mapping.get("text"), f"{where}.text"),
        "evidence_locators": [
            _require_text(item, f"{where}.evidence_locators")
            for item in _optional_sequence(
                mapping.get("evidence_locators"), f"{where}.evidence_locators"
            )
        ],
        "role": _require_enum(mapping.get("role", "unknown"), ROLE_VALUES, f"{where}.role"),
        "modality": _require_enum(
            mapping.get("modality", "unknown"), MODALITY_VALUES, f"{where}.modality"
        ),
        "quantities": quantities,
        "language": _optional_text(mapping.get("language"), f"{where}.language"),
    }


def _validate_coverage(coverage: Any, where: str) -> dict[str, Any]:
    if coverage is None:
        return {"native_scan": None, "complete": None, "raw": {}}
    mapping = _require_mapping(coverage, where)
    native_scan = mapping.get("native_scan")
    if native_scan is not None:
        native_scan = _require_enum(native_scan, NATIVE_SCAN_VALUES, f"{where}.native_scan")
    return {
        "native_scan": native_scan,
        "complete": mapping.get("complete"),
        "structured_unit_count": mapping.get("structured_unit_count"),
        "unassigned_unit_ids": [
            _require_text(item, f"{where}.unassigned_unit_ids")
            for item in _optional_sequence(mapping.get("unassigned_unit_ids"), f"{where}.unassigned_unit_ids")
        ],
        "deferred_unit_ids": [
            _require_text(item, f"{where}.deferred_unit_ids")
            for item in _optional_sequence(mapping.get("deferred_unit_ids"), f"{where}.deferred_unit_ids")
        ],
        "opaque_pages": [
            int(item) for item in _optional_sequence(mapping.get("opaque_pages"), f"{where}.opaque_pages")
        ],
        "raw": dict(mapping),
    }


def validate_observed(observed: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one ``du-observed/1`` record."""

    record = _require_mapping(observed, "observed")
    version = record.get("schema_version")
    if version != OBSERVED_SCHEMA_VERSION:
        raise BenchmarkSchemaError(f"observed schema_version must be {OBSERVED_SCHEMA_VERSION}")

    claims = [
        _validate_claim(claim, f"observed.claims[{index}]")
        for index, claim in enumerate(_optional_sequence(record.get("claims"), "observed.claims"))
    ]

    semantic_units = []
    for index, raw_unit in enumerate(
        _optional_sequence(record.get("semantic_units"), "observed.semantic_units")
    ):
        where = f"observed.semantic_units[{index}]"
        unit = _require_mapping(raw_unit, where)
        semantic_units.append(
            {
                "semantic_id": _require_text(unit.get("semantic_id"), f"{where}.semantic_id"),
                "kind": _optional_text(unit.get("kind"), f"{where}.kind"),
                "locators": [
                    _require_text(item, f"{where}.locators")
                    for item in _optional_sequence(unit.get("locators"), f"{where}.locators")
                ],
                "completeness": _optional_text(unit.get("completeness"), f"{where}.completeness"),
                "diagnostics": [
                    _require_text(item, f"{where}.diagnostics")
                    for item in _optional_sequence(unit.get("diagnostics"), f"{where}.diagnostics")
                ],
            }
        )

    execution = _require_mapping(record.get("execution") or {}, "observed.execution")
    metrics = _require_mapping(record.get("metrics") or {}, "observed.metrics")

    return {
        "schema_version": OBSERVED_SCHEMA_VERSION,
        "sample_id": _require_text(record.get("sample_id"), "observed.sample_id"),
        "source_sha256": _require_sha256(record.get("source_sha256"), "observed.source_sha256"),
        "route": _validate_route(record.get("route"), "observed.route"),
        "selected_locators": [
            _require_text(item, "observed.selected_locators")
            for item in _optional_sequence(
                record.get("selected_locators"), "observed.selected_locators"
            )
        ],
        "selected_text": _require_text(
            record.get("selected_text", ""),
            "observed.selected_text",
            allow_empty=True,
        ),
        "semantic_units": semantic_units,
        "claims": claims,
        "coverage": _validate_coverage(record.get("coverage"), "observed.coverage"),
        "metrics": dict(metrics),
        "execution": {
            "entry_point": _optional_text(execution.get("entry_point"), "observed.execution.entry_point"),
            "parser_version": _optional_text(
                execution.get("parser_version"), "observed.execution.parser_version"
            ),
            "selector_version": _optional_text(
                execution.get("selector_version"), "observed.execution.selector_version"
            ),
            "calls": execution.get("calls"),
            "elapsed_seconds": execution.get("elapsed_seconds"),
            "mode": _optional_text(execution.get("mode"), "observed.execution.mode"),
            "raw": dict(execution),
        },
    }
