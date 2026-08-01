"""Independent evaluator for the RR-12.2d synthetic gold corpus.

The evaluator is deliberately test-internal and pure stdlib.  It validates the
gold package before scoring predictions and never imports production scoring
helpers, so a production bug cannot silently become the expected answer.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


EVALUATOR_VERSION = "1.0.0"
RECEIPT_SCHEMA_VERSION = 1
MATERIAL = {"high", "medium"}
NUMERIC_FIELDS = ("metric", "value", "unit", "currency", "period", "scope")
VALID_CLAIM_TYPES = {"fact", "opinion", "prediction"}
DEFAULT_THRESHOLD_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "gold_corpus"
    / "expected"
    / "quality_metrics.json"
)


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON document must be an object: {path}")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _load_threshold_rules(path: Path) -> dict[str, dict]:
    document = _read_json(path)
    if document.get("schema_version") != 1:
        raise ValueError("threshold schema_version must be 1")
    rules = document.get("thresholds")
    if not isinstance(rules, dict) or not rules:
        raise ValueError("thresholds must be a non-empty object")
    normalized: dict[str, dict] = {}
    for name, rule in rules.items():
        if not isinstance(rule, dict):
            raise ValueError(f"threshold {name} must be an object")
        operator = rule.get("operator")
        value = rule.get("value")
        critical = rule.get("critical")
        if operator not in {">=", "<="}:
            raise ValueError(f"threshold {name} has invalid operator")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"threshold {name} has invalid value")
        if not isinstance(critical, bool):
            raise ValueError(f"threshold {name} has invalid critical flag")
        normalized[name] = {
            "operator": operator,
            "value": float(value),
            "critical": critical,
        }
    return normalized


# Public compatibility export.  Values come from the reviewer-owned file; this
# module contains no second hard-coded threshold table.
THRESHOLD_RULES = _load_threshold_rules(DEFAULT_THRESHOLD_PATH)
THRESHOLDS = {name: rule["value"] for name, rule in THRESHOLD_RULES.items()}


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


def claim_key(claim: dict) -> tuple[str, str, str]:
    """Stable semantic identity that does not hide numeric-field mutations."""
    return (
        str(claim.get("source_id", "")),
        str(claim.get("entity_id", "")),
        _norm(str(claim.get("text", ""))),
    )


def _ratio(num: float, den: float, *, empty: float = 1.0) -> float:
    return num / den if den else empty


def _f1(precision: float, recall: float) -> float:
    return _ratio(2 * precision * recall, precision + recall, empty=0.0)


def _parse_frontmatter_body(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    return parts[2] if len(parts) == 3 else text


def _ensure_unique(items: list[dict], field: str) -> None:
    values = [item.get(field) for item in items]
    if any(not value for value in values):
        raise ValueError(f"manifest revision missing {field}")
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate {field}: {duplicates}")


def _safe_manifest_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if not relative or rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe manifest source path: {relative}")
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"unsafe manifest source path: {relative}") from exc
    return candidate


def load_gold(corpus_dir: str | Path) -> dict:
    """Load and validate a gold corpus package.

    Structural corruption is rejected before any metric is computed.  This is
    essential for the fixed CLI: a self-consistent predictions file must never
    make a damaged gold package appear valid.
    """
    root = Path(corpus_dir).resolve()
    manifest_path = root / "corpus_manifest.json"
    claims_path = root / "annotations" / "material_claims.json"
    spans_path = root / "annotations" / "evidence_spans.json"
    routes_path = root / "annotations" / "routing_targets.json"
    contradictions_path = root / "annotations" / "contradictions.json"
    thresholds_path = root / "expected" / "quality_metrics.json"

    manifest = _read_json(manifest_path)
    revisions = manifest.get("revisions")
    if not isinstance(revisions, list) or not revisions:
        raise ValueError("manifest revisions must be a non-empty list")
    _ensure_unique(revisions, "revision_id")
    _ensure_unique(revisions, "source_id")

    source_ids = {revision["source_id"] for revision in revisions}
    manifest_files: set[str] = set()
    source_bodies: dict[str, str] = {}
    for revision in revisions:
        relative = revision.get("path", "")
        source = _safe_manifest_path(root, relative)
        if not source.is_file():
            raise ValueError(f"manifest source missing: {relative}")
        manifest_files.add(source.relative_to(root).as_posix())
        text = source.read_text(encoding="utf-8")
        body = _parse_frontmatter_body(text)
        actual_hash = _sha256_bytes(body.encode("utf-8"))
        if actual_hash != revision.get("content_sha256"):
            raise ValueError(
                f"content_sha256 mismatch for manifest source {revision['source_id']}"
            )
        source_bodies[revision["source_id"]] = body

    disk_files = {
        path.relative_to(root).as_posix()
        for path in (root / "sources").rglob("*.md")
        if path.is_file()
    }
    extras = sorted(disk_files - manifest_files)
    if extras:
        raise ValueError(f"unregistered source files: {extras}")

    claims_document = _read_json(claims_path)
    claims = claims_document.get("claims")
    if not isinstance(claims, list):
        raise ValueError("material claims must be a list")
    claim_ids = [claim.get("claim_id") for claim in claims]
    if any(not claim_id for claim_id in claim_ids):
        raise ValueError("claim missing claim_id")
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("duplicate claim_id")
    claim_id_set = set(claim_ids)
    for claim in claims:
        if claim.get("source_id") not in source_ids:
            raise ValueError(f"claim source reference missing: {claim.get('source_id')}")
        if claim.get("claim_type") not in VALID_CLAIM_TYPES:
            raise ValueError(f"invalid claim_type: {claim.get('claim_type')}")

    spans_document = _read_json(spans_path)
    span_groups = spans_document.get("spans")
    if not isinstance(span_groups, dict):
        raise ValueError("evidence spans must be grouped by source_id")
    span_by_id: dict[str, dict] = {}
    for source_id, span_list in span_groups.items():
        if source_id not in source_ids:
            raise ValueError(f"span source reference missing: {source_id}")
        if not isinstance(span_list, list):
            raise ValueError(f"span group must be a list: {source_id}")
        body = source_bodies[source_id]
        for raw_span in span_list:
            span = dict(raw_span)
            span_id = span.get("span_id")
            if not span_id or span_id in span_by_id:
                raise ValueError(f"duplicate or missing span_id: {span_id}")
            if span.get("claim_id") not in claim_id_set:
                raise ValueError(
                    f"span claim reference missing: {span.get('claim_id')}"
                )
            start, end, text = span.get("start"), span.get("end"), span.get("text")
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or start < 0
                or end < start
                or body[start:end] != text
            ):
                raise ValueError(f"span offset mismatch: {span_id}")
            span["source_id"] = source_id
            span_by_id[span_id] = span

    for claim in claims:
        for span_id in claim.get("evidence_spans", []):
            span = span_by_id.get(span_id)
            if span is None:
                raise ValueError(f"claim span reference missing: {span_id}")
            if span["claim_id"] != claim["claim_id"]:
                raise ValueError(
                    f"claim/span reverse reference mismatch: {claim['claim_id']} / {span_id}"
                )
            if span["source_id"] != claim["source_id"]:
                raise ValueError(
                    f"claim/span source reference mismatch: {claim['claim_id']} / {span_id}"
                )

    routes_document = _read_json(routes_path)
    routes = routes_document.get("routing")
    if not isinstance(routes, list):
        raise ValueError("routing annotations must be a list")
    route_ids = [route.get("source_id") for route in routes]
    if len(route_ids) != len(set(route_ids)):
        raise ValueError("duplicate routing source_id")
    for route in routes:
        if route.get("source_id") not in source_ids:
            raise ValueError(f"routing source reference missing: {route.get('source_id')}")

    contradictions = _read_json(contradictions_path)
    for item in contradictions.get("contradictions", []):
        for field in ("original_claim", "correcting_claim"):
            reference = item.get(field, {}).get("claim_id")
            if reference not in claim_id_set:
                raise ValueError(f"contradiction claim reference missing: {reference}")
    for item in contradictions.get("supersedes", []):
        for field in ("newer_claim", "supersedes"):
            reference = item.get(field)
            if reference not in claim_id_set:
                raise ValueError(f"supersedes claim reference missing: {reference}")

    threshold_rules = _load_threshold_rules(thresholds_path)
    return {
        "root": root,
        "manifest": manifest,
        "manifest_sha256": _sha256_bytes(manifest_path.read_bytes()),
        "source_ids": source_ids,
        "claims": claims,
        "routes": routes,
        "span_by_id": span_by_id,
        "span_text": {span_id: span["text"] for span_id, span in span_by_id.items()},
        "threshold_rules": threshold_rules,
        "thresholds": {
            name: rule["value"] for name, rule in threshold_rules.items()
        },
        "thresholds_sha256": _sha256_bytes(thresholds_path.read_bytes()),
    }


def gold_to_perfect_predictions(gold: dict) -> dict:
    """Build a ceiling prediction artifact from validated gold annotations."""
    claims = []
    for claim in gold["claims"]:
        evidence = None
        evidence_ids = claim.get("evidence_spans", [])
        if evidence_ids:
            span = gold["span_by_id"][evidence_ids[0]]
            evidence = {
                "start": span["start"],
                "end": span["end"],
                "text": span["text"],
            }
        claims.append(
            {
                "claim_id": claim.get("claim_id"),
                "source_id": claim["source_id"],
                "claim_type": claim.get("claim_type"),
                "text": claim.get("text", ""),
                "entity_id": claim.get("entity_id"),
                "materiality": claim.get("materiality", "medium"),
                "evidence": evidence,
                "numeric": claim.get("numeric"),
                "corrects": claim.get("corrects"),
                "supersedes": claim.get("supersedes"),
                "published_at": claim.get("published_at", ""),
                "canonical_source_id": claim.get("canonical_source_id"),
            }
        )
    routes = []
    for route in gold["routes"]:
        targets = (
            []
            if route.get("is_irrelevant")
            else [
                {
                    "entity_id": target["entity_id"],
                    "confidence": target.get("confidence", "medium"),
                }
                for target in route.get("expected_targets", [])
            ]
        )
        routes.append(
            {
                "source_id": route["source_id"],
                "targets": targets,
                "has_ambiguity": bool(route.get("has_ambiguity")),
                "is_irrelevant": bool(route.get("is_irrelevant")),
                "canonical_source_id": route.get("canonical_source_id"),
            }
        )
    return {"claims": claims, "routes": routes}


def _predicted_evidence_items(claim: dict) -> list[dict]:
    evidence = claim.get("evidence")
    if evidence is None:
        return []
    if isinstance(evidence, dict):
        return [evidence]
    if isinstance(evidence, list) and all(isinstance(item, dict) for item in evidence):
        return evidence
    return []


def _threshold_passes(value: float, rule: dict) -> bool:
    if rule["operator"] == ">=":
        return value >= rule["value"]
    return value <= rule["value"]


def evaluate(predictions: dict, gold: dict, as_of: str | None = None) -> dict:
    """Compute a deterministic metric receipt from predictions and validated gold."""
    if not isinstance(predictions, dict):
        raise ValueError("predictions must be a JSON object")
    predicted_claims = predictions.get("claims", [])
    predicted_routes = predictions.get("routes", [])
    if not isinstance(predicted_claims, list) or not isinstance(predicted_routes, list):
        raise ValueError("predictions claims/routes must be lists")

    gold_claims = [
        claim for claim in gold["claims"] if claim.get("materiality") in MATERIAL
    ]
    scored_predictions = [
        claim
        for claim in predicted_claims
        if isinstance(claim, dict) and claim.get("materiality") in MATERIAL
    ]
    gold_counter = Counter(claim_key(claim) for claim in gold_claims)
    predicted_counter = Counter(claim_key(claim) for claim in scored_predictions)
    matched_count = sum((gold_counter & predicted_counter).values())
    recall = _ratio(matched_count, sum(gold_counter.values()), empty=1.0)
    precision = _ratio(matched_count, sum(predicted_counter.values()), empty=1.0)

    predicted_by_key: dict[tuple[str, str, str], dict] = {}
    for claim in scored_predictions:
        predicted_by_key.setdefault(claim_key(claim), claim)

    evidence_total = evidence_ok = 0
    numeric_total = numeric_ok = 0
    type_total = type_ok = 0
    for gold_claim in gold_claims:
        predicted = predicted_by_key.get(claim_key(gold_claim))

        type_total += 1
        if predicted and predicted.get("claim_type") == gold_claim.get("claim_type"):
            type_ok += 1

        evidence_ids = gold_claim.get("evidence_spans", [])
        if evidence_ids:
            evidence_total += 1
            expected = {
                (
                    gold["span_by_id"][span_id]["start"],
                    gold["span_by_id"][span_id]["end"],
                    gold["span_by_id"][span_id]["text"],
                )
                for span_id in evidence_ids
            }
            actual = {
                (item.get("start"), item.get("end"), item.get("text"))
                for item in _predicted_evidence_items(predicted or {})
            }
            if expected == actual:
                evidence_ok += 1

        if gold_claim.get("numeric") is not None:
            numeric_total += 1
            predicted_numeric = predicted.get("numeric") if predicted else None
            if isinstance(predicted_numeric, dict) and all(
                gold_claim["numeric"].get(field) == predicted_numeric.get(field)
                for field in NUMERIC_FIELDS
            ):
                numeric_ok += 1

    evidence_exactness = _ratio(evidence_ok, evidence_total, empty=1.0)
    numeric_exactness = _ratio(numeric_ok, numeric_total, empty=1.0)
    claim_type_accuracy = _ratio(type_ok, type_total, empty=1.0)

    valid_provenance = sum(
        1 for claim in predicted_claims if claim.get("source_id") in gold["source_ids"]
    )
    provenance_coverage = _ratio(
        valid_provenance, len(predicted_claims), empty=1.0
    )

    gold_routes = {route["source_id"]: route for route in gold["routes"]}
    prediction_routes = {
        route["source_id"]: route
        for route in predicted_routes
        if isinstance(route, dict) and route.get("source_id")
    }
    true_positive = false_positive = false_negative = 0
    macro_precision_values: list[float] = []
    macro_recall_values: list[float] = []
    macro_f1_values: list[float] = []
    irrelevant_total = irrelevant_ok = 0
    ambiguity_total = ambiguity_ok = 0

    for source_id, gold_route in gold_routes.items():
        predicted_route = prediction_routes.get(
            source_id,
            {
                "targets": [],
                "has_ambiguity": False,
                "is_irrelevant": False,
                "canonical_source_id": None,
            },
        )
        predicted_targets = {
            target.get("entity_id")
            for target in predicted_route.get("targets", [])
            if isinstance(target, dict) and target.get("entity_id")
        }
        if gold_route.get("is_irrelevant"):
            irrelevant_total += 1
            if predicted_route.get("is_irrelevant") is True and not predicted_targets:
                irrelevant_ok += 1
            false_positive += len(predicted_targets)
            continue

        gold_targets = {
            target["entity_id"] for target in gold_route.get("expected_targets", [])
        }
        tp_source = len(gold_targets & predicted_targets)
        fp_source = len(predicted_targets - gold_targets)
        fn_source = len(gold_targets - predicted_targets)
        true_positive += tp_source
        false_positive += fp_source
        false_negative += fn_source
        source_precision = _ratio(
            tp_source, len(predicted_targets), empty=0.0 if gold_targets else 1.0
        )
        source_recall = _ratio(
            tp_source, len(gold_targets), empty=1.0
        )
        macro_precision_values.append(source_precision)
        macro_recall_values.append(source_recall)
        macro_f1_values.append(_f1(source_precision, source_recall))

        if gold_route.get("has_ambiguity"):
            ambiguity_total += 1
            if (
                predicted_route.get("has_ambiguity") is True
                and predicted_targets == gold_targets
            ):
                ambiguity_ok += 1

    for source_id, route in prediction_routes.items():
        if source_id not in gold_routes:
            false_positive += len(route.get("targets", []))

    routing_micro_precision = _ratio(
        true_positive,
        true_positive + false_positive,
        empty=1.0,
    )
    routing_micro_recall = _ratio(
        true_positive,
        true_positive + false_negative,
        empty=1.0,
    )
    routing_macro_precision = _ratio(
        sum(macro_precision_values), len(macro_precision_values), empty=1.0
    )
    routing_macro_recall = _ratio(
        sum(macro_recall_values), len(macro_recall_values), empty=1.0
    )
    routing_macro_f1 = _ratio(
        sum(macro_f1_values), len(macro_f1_values), empty=1.0
    )
    irrelevant_rejection = _ratio(
        irrelevant_ok, irrelevant_total, empty=1.0
    )
    ambiguity_detection = _ratio(ambiguity_ok, ambiguity_total, empty=1.0)

    correction_total = correction_ok = 0
    for gold_claim in gold["claims"]:
        corrects = gold_claim.get("corrects")
        supersedes = gold_claim.get("supersedes")
        if not corrects and not supersedes:
            continue
        correction_total += 1
        predicted = predicted_by_key.get(claim_key(gold_claim))
        if predicted and (
            predicted.get("corrects") == corrects
            and predicted.get("supersedes") == supersedes
        ):
            correction_ok += 1
    correction_accuracy = _ratio(correction_ok, correction_total, empty=1.0)

    if as_of:
        leaking = sum(
            1
            for claim in predicted_claims
            if claim.get("published_at") and claim["published_at"] > as_of
        )
        as_of_leakage = _ratio(leaking, len(predicted_claims), empty=0.0)
    else:
        as_of_leakage = 0.0

    dedup_total = dedup_ok = 0
    for source_id, gold_route in gold_routes.items():
        canonical = gold_route.get("canonical_source_id")
        if not canonical:
            continue
        dedup_total += 1
        predicted = prediction_routes.get(source_id)
        if predicted and predicted.get("canonical_source_id") == canonical:
            dedup_ok += 1
    dedup_accuracy = _ratio(dedup_ok, dedup_total, empty=1.0)

    raw_metrics = {
        "material_claim_recall": recall,
        "material_claim_precision": precision,
        "material_claim_f1": _f1(precision, recall),
        "evidence_exactness": evidence_exactness,
        "provenance_coverage": provenance_coverage,
        "numeric_exactness": numeric_exactness,
        "claim_type_accuracy": claim_type_accuracy,
        "routing_micro_precision": routing_micro_precision,
        "routing_micro_recall": routing_micro_recall,
        "routing_macro_precision": routing_macro_precision,
        "routing_macro_recall": routing_macro_recall,
        "routing_macro_f1": routing_macro_f1,
        "irrelevant_rejection": irrelevant_rejection,
        "ambiguity_detection_recall": ambiguity_detection,
        "correction_supersedes_accuracy": correction_accuracy,
        "as_of_leakage_rate": as_of_leakage,
        "aggregation_dedup_accuracy": dedup_accuracy,
    }

    failures = []
    for name, rule in gold["threshold_rules"].items():
        value = raw_metrics.get(name)
        if value is None:
            raise ValueError(f"threshold references unknown metric: {name}")
        if not _threshold_passes(value, rule):
            failures.append(
                {
                    "metric": name,
                    "operator": rule["operator"],
                    "threshold": rule["value"],
                    "actual": round(value, 4),
                    "critical": rule["critical"],
                }
            )

    critical_failures = [failure for failure in failures if failure["critical"]]
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "evaluator_version": EVALUATOR_VERSION,
        "manifest_sha256": gold["manifest_sha256"],
        "thresholds_sha256": gold["thresholds_sha256"],
        "predictions_sha256": _sha256_json(predictions),
        "metrics": {name: round(value, 4) for name, value in raw_metrics.items()},
        "thresholds": gold["thresholds"],
        "threshold_policy": gold["threshold_rules"],
        "failures": failures,
        "all_critical_pass": not critical_failures,
        "as_of": as_of,
        "counts": {
            "predicted_claims": len(predicted_claims),
            "gold_material_claims": len(gold_claims),
            "gold_routes": len(gold_routes),
            "evidence_cases": evidence_total,
            "numeric_cases": numeric_total,
            "correction_cases": correction_total,
            "ambiguity_cases": ambiguity_total,
            "irrelevant_cases": irrelevant_total,
            "aggregation_cases": dedup_total,
        },
    }


def receipt_sha256(receipt: dict) -> str:
    """Return the canonical SHA-256 of a receipt object."""
    return _sha256_json(receipt)
