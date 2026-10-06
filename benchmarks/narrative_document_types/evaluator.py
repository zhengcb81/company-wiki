"""N5-DOCSET document-quality evaluator.

Compares the runtime selector's selected evidence spans against human-read
golden annotation points and emits the ``narrative-document-quality/1`` report
row set.  The evaluator never parses documents and never calls a model: the
runner supplies the selected spans, and a ``locator_check`` callback proves
each golden quote is still readable at its cited locator in the original file.

Deliberate non-goals: no thresholds are tuned to make a run pass, no
investment judgement is produced, and an unannotated scope can never be
silently converted into a covered one.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
import hashlib
import re
from typing import Any


SCHEMA_VERSION = "narrative-document-quality/1"
EVALUATOR_VERSION = "1.0.0"

STATEMENT_ROLES = frozenset({"company_filing", "management"})
QUESTION_ROLES = frozenset({"analyst", "investor_question"})

PARTIAL_COVERAGE_FLOOR = 0.6
SHORT_SPAN_MIN_CHARS = 8

class GoldenValidationError(ValueError):
    """Raised when golden/selection inputs cannot support an honest evaluation."""


class ReportValidationError(ValueError):
    """Raised when a report does not match its samples, golden and own arithmetic."""


def normalize_text(text: str) -> str:
    """Whitespace-insensitive, table-separator-insensitive comparison form."""
    return re.sub(r"\s+", "", str(text).replace("|", " ")).casefold()


def quote_sha256(quote: str) -> str:
    return hashlib.sha256(quote.encode("utf-8")).hexdigest()


def role_class(source_role: str | None) -> str:
    role = str(source_role or "")
    if role in STATEMENT_ROLES:
        return "statement"
    if role in QUESTION_ROLES:
        return "question"
    return "other"


def expected_role_class(point: Mapping[str, Any]) -> str:
    return role_class(
        "analyst" if point.get("expected_role") == "question" else "company_filing"
    )


def longest_common_substring_length(left: str, right: str) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    best = 0
    for char_left in left:
        current = [0] * (len(right) + 1)
        for index, char_right in enumerate(right, start=1):
            if char_left == char_right:
                current[index] = previous[index - 1] + 1
                if current[index] > best:
                    best = current[index]
        previous = current
    return best


def _point_in_location(point: Mapping[str, Any], span: Any) -> bool:
    locator = point["locator"]
    coordinates = span.coordinates
    if "page_number" in locator:
        return coordinates.page_number == locator["page_number"]
    start = int(locator["line_start"])
    end = int(locator.get("line_end", start))
    metadata = span.structured_value or {}
    span_start = metadata.get("line_start")
    span_end = metadata.get("line_end")
    if span_start is None and coordinates.paragraph_index is not None:
        span_start = int(coordinates.paragraph_index) + 1
        span_end = int(span_end) if span_end is not None else span_start
    if span_start is None:
        return False
    span_start = int(span_start)
    span_end = int(span_end) if span_end is not None else span_start
    return span_start <= end and start <= span_end


def spans_in_location(point: Mapping[str, Any], spans: Sequence[Any]) -> list[Any]:
    return [span for span in spans if _point_in_location(point, span)]


def match_positive(point: Mapping[str, Any], spans: Sequence[Any]) -> dict[str, Any]:
    """Full match needs the whole quote inside the located selected text."""
    quote = normalize_text(point["quote"])
    ordered = sorted(
        spans_in_location(point, spans),
        key=lambda span: (
            span.coordinates.page_number or 0,
            span.coordinates.paragraph_index or 0,
            span.coordinates.table_index or 0,
            span.coordinates.row_index or 0,
            span.coordinates.column_index or 0,
            span.coordinates.char_start or 0,
        ),
    )
    texts = [normalize_text(span.raw_text or "") for span in ordered]
    if not ordered:
        return {
            "result": "miss",
            "matched_span_ids": [],
            "matched_roles": [],
            "coverage_ratio": 0.0,
        }
    contributors: list[int] = []
    if quote:
        if any(quote in text for text in texts):
            contributors = [
                index
                for index, text in enumerate(texts)
                if quote in text or text in quote
            ]
        elif quote in "".join(texts):
            contributors = _contributor_window(texts, quote)
    if contributors:
        matched = [ordered[index] for index in contributors]
        return {
            "result": "full",
            "matched_span_ids": [span.span_id for span in matched],
            "matched_roles": sorted(
                {
                    str(span.structured_value.get("source_role", "unknown"))
                    for span in matched
                }
            ),
            "coverage_ratio": 1.0,
        }
    ratio = 0.0
    if quote:
        longest = max(
            (longest_common_substring_length(quote, text) for text in texts),
            default=0,
        )
        ratio = round(longest / len(quote), 4)
    if ratio >= PARTIAL_COVERAGE_FLOOR:
        matched = [
            span
            for span, text in zip(ordered, texts, strict=True)
            if longest_common_substring_length(quote, text) / max(1, len(quote))
            >= PARTIAL_COVERAGE_FLOOR
        ]
        return {
            "result": "partial",
            "matched_span_ids": [span.span_id for span in matched],
            "matched_roles": sorted(
                {
                    str(span.structured_value.get("source_role", "unknown"))
                    for span in matched
                }
            ),
            "coverage_ratio": ratio,
        }
    return {
        "result": "miss",
        "matched_span_ids": [],
        "matched_roles": [],
        "coverage_ratio": ratio,
    }


def _contributor_window(texts: Sequence[str], quote: str) -> list[int]:
    """Smallest contiguous run of ordered span texts whose join contains the quote."""
    best: tuple[int, int] | None = None
    for start in range(len(texts)):
        joined = ""
        for end in range(start, len(texts)):
            joined += texts[end]
            if quote in joined:
                if best is None or end - start < best[1] - best[0]:
                    best = (start, end)
                break
    if best is None:
        return []
    return list(range(best[0], best[1] + 1))


def match_negative(point: Mapping[str, Any], spans: Sequence[Any]) -> dict[str, Any]:
    """A negative fires when one located span carries (most of) the quote."""
    quote = normalize_text(point["quote"])
    hits = []
    for span in spans_in_location(point, spans):
        text = normalize_text(span.raw_text or "")
        if not text:
            continue
        if quote in text or (len(text) >= SHORT_SPAN_MIN_CHARS and text in quote):
            hits.append(span)
    return {
        "result": "noise" if hits else "clean",
        "matched_span_ids": [span.span_id for span in hits],
        "matched_roles": sorted(
            {str(span.structured_value.get("source_role", "unknown")) for span in hits}
        ),
        "coverage_ratio": 1.0 if hits else 0.0,
    }


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _span_in_scope(scope: Mapping[str, Any]) -> Callable[[Any], bool]:
    unit = scope.get("unit")
    if unit == "pdf_page":
        pages = set(scope.get("pages_read") or [])
        return lambda span: span.coordinates.page_number in pages
    ranges = [(int(item[0]), int(item[1])) for item in (scope.get("lines_read") or [])]

    def check(span: Any) -> bool:
        metadata = span.structured_value or {}
        start = metadata.get("line_start")
        end = metadata.get("line_end")
        if start is None and span.coordinates.paragraph_index is not None:
            start = int(span.coordinates.paragraph_index) + 1
            end = int(end) if end is not None else start
        if start is None:
            return False
        start = int(start)
        end = int(end) if end is not None else start
        return any(start <= high and low <= end for low, high in ranges)

    return check


def _duplicates(spans: Sequence[Any]) -> tuple[int, int, float]:
    seen: dict[str, int] = {}
    for span in spans:
        key = normalize_text(span.raw_text or "")
        seen[key] = seen.get(key, 0) + 1
    duplicate_count = sum(count - 1 for count in seen.values() if count > 1)
    total = len(spans)
    return duplicate_count, total, _rate(duplicate_count, total) or 0.0


def _golden_row(
    point: Mapping[str, Any],
    spans: Sequence[Any],
    *,
    locator_verified: bool,
) -> dict[str, Any]:
    polarity = point["polarity"]
    if polarity == "negative":
        outcome = match_negative(point, spans)
    else:
        outcome = match_positive(point, spans)
    expected_class = expected_role_class(point)
    matched_roles = outcome["matched_roles"]
    role_confusion = False
    modality_confusion = False
    if outcome["matched_span_ids"]:
        classes = {role_class(role) for role in matched_roles}
        role_confusion = any(cls != expected_class for cls in classes)
        want = "question" if point.get("modality") == "question" else "statement"
        modality_confusion = any(cls != want for cls in classes)
    row = {
        "golden_id": point["golden_id"],
        "topic": point.get("topic"),
        "polarity": polarity,
        "priority": point.get("priority"),
        "negative_kind": point.get("negative_kind"),
        "expected_role_class": expected_class,
        "modality": point.get("modality"),
        "locator": dict(point["locator"]),
        "quote_sha256": point.get("quote_sha256"),
        "verified": bool(locator_verified and bool(point.get("quote_sha256"))),
        "result": outcome["result"],
        "matched_span_ids": outcome["matched_span_ids"],
        "matched_roles": matched_roles,
        "coverage_ratio": outcome["coverage_ratio"],
        "role_confusion": role_confusion,
        "modality_confusion": modality_confusion,
    }
    return row


def _validate_golden_sample(sample_id: str, entry: Mapping[str, Any]) -> None:
    scope = entry.get("read_scope")
    if not isinstance(scope, Mapping) or not scope:
        raise GoldenValidationError(f"{sample_id}: missing read_scope annotation range")
    unit = scope.get("unit")
    if unit == "pdf_page":
        pages = scope.get("pages_read")
        if not isinstance(pages, list) or not pages:
            raise GoldenValidationError(f"{sample_id}: read_scope.pages_read is empty")
        if int(scope.get("pages_total") or 0) < max(int(page) for page in pages):
            raise GoldenValidationError(f"{sample_id}: pages_read exceeds pages_total")
    elif unit == "txt_line":
        ranges = scope.get("lines_read")
        if not isinstance(ranges, list) or not ranges:
            raise GoldenValidationError(f"{sample_id}: read_scope.lines_read is empty")
    else:
        raise GoldenValidationError(
            f"{sample_id}: unsupported read_scope.unit {unit!r}"
        )
    points = entry.get("points")
    if not isinstance(points, list) or len(points) < 6:
        raise GoldenValidationError(f"{sample_id}: needs at least 6 annotated points")
    seen: set[str] = set()
    for point in points:
        golden_id = str(point.get("golden_id") or "")
        if not golden_id:
            raise GoldenValidationError(f"{sample_id}: point without golden_id")
        if golden_id in seen:
            raise GoldenValidationError(f"{sample_id}: duplicate golden_id {golden_id}")
        seen.add(golden_id)
        if point.get("polarity") not in {"positive", "negative"}:
            raise GoldenValidationError(f"{golden_id}: invalid polarity")
        if not str(point.get("quote") or "").strip():
            raise GoldenValidationError(f"{golden_id}: empty quote")
        if not str(point.get("quote_sha256") or "").strip():
            raise GoldenValidationError(
                f"{golden_id}: quote_sha256 missing (unverified citation)"
            )
        if quote_sha256(point["quote"]) != point["quote_sha256"]:
            raise GoldenValidationError(
                f"{golden_id}: quote_sha256 does not match quote"
            )
        locator = point.get("locator")
        if not isinstance(locator, Mapping):
            raise GoldenValidationError(f"{golden_id}: missing locator")
        if "page_number" not in locator and "line_start" not in locator:
            raise GoldenValidationError(
                f"{golden_id}: locator has neither page nor line"
            )
        if unit == "pdf_page":
            page = int(locator.get("page_number", 0))
            if page < 1 or page not in pages:
                raise GoldenValidationError(f"{golden_id}: locator outside read_scope")
        else:
            start = int(locator.get("line_start", 0))
            end = int(locator.get("line_end", start))
            if start < 1 or end < start or not any(
                int(first) <= start <= end <= int(last) for first, last in ranges
            ):
                raise GoldenValidationError(f"{golden_id}: locator outside read_scope")


def evaluate(
    *,
    samples: Sequence[Mapping[str, Any]],
    golden: Mapping[str, Any],
    selections: Mapping[str, Mapping[str, Any]],
    locator_check: Callable[[Mapping[str, Any], Mapping[str, Any]], bool],
) -> dict[str, Any]:
    """Build one report from selected spans and golden annotation."""
    golden_samples = golden.get("samples")
    if not isinstance(golden_samples, Mapping):
        raise GoldenValidationError("golden.json has no samples mapping")
    rows: list[dict[str, Any]] = []
    totals = {
        "documents": 0,
        "golden_points": 0,
        "required_points": 0,
        "required_matched": 0,
        "optional_points": 0,
        "optional_matched": 0,
        "negative_points": 0,
        "negative_points_hit": 0,
        "selected_span_count": 0,
        "selected_in_scope": 0,
        "judged_in_scope": 0,
        "noise_spans": 0,
        "role_confusion": 0,
        "modality_confusion": 0,
        "duplicate_span_count": 0,
        "selected_utf8_bytes": 0,
        "locator_roundtrip_verified": 0,
        "locator_roundtrip_failed": 0,
    }
    for sample in samples:
        sample_id = sample["sample_id"]
        if sample_id not in golden_samples:
            raise GoldenValidationError(f"{sample_id}: no golden annotation")
        entry = golden_samples[sample_id]
        _validate_golden_sample(sample_id, entry)
        selection = selections.get(sample_id)
        if selection is None:
            raise GoldenValidationError(f"{sample_id}: no selection result supplied")
        if selection.get("source_sha256") != sample["sha256"]:
            raise GoldenValidationError(
                f"{sample_id}: selection sha {selection.get('source_sha256')} != sample sha {sample['sha256']}"
            )
        spans = selection.get("spans") or []
        scope = entry["read_scope"]
        in_scope = _span_in_scope(scope)
        scope_spans = [span for span in spans if in_scope(span)]

        golden_rows = []
        for point in entry["points"]:
            verified = locator_check(sample, point)
            golden_rows.append(_golden_row(point, spans, locator_verified=verified))

        required_rows = [
            row
            for row in golden_rows
            if row["polarity"] == "positive"
            and row["priority"] == "required"
            and row["verified"]
        ]
        optional_rows = [
            row
            for row in golden_rows
            if row["polarity"] == "positive"
            and row["priority"] == "optional"
            and row["verified"]
        ]
        negative_rows = [row for row in golden_rows if row["polarity"] == "negative"]
        required_matched = sum(row["result"] == "full" for row in required_rows)
        optional_matched = sum(row["result"] == "full" for row in optional_rows)
        negative_hit = sum(row["result"] == "noise" for row in negative_rows)

        positive_ids = {
            span_id
            for row in golden_rows
            if row["polarity"] == "positive"
            for span_id in row["matched_span_ids"]
        }
        noise_ids = {
            span_id
            for row in golden_rows
            if row["polarity"] == "negative"
            for span_id in row["matched_span_ids"]
        }
        judged_ids = positive_ids | noise_ids
        unverified_required = sum(
            row["polarity"] == "positive"
            and row["priority"] == "required"
            and not row["verified"]
            for row in golden_rows
        )
        duplicate_span_count, total_selected, duplicate_ratio = _duplicates(spans)
        utf8_bytes = sum(len((span.raw_text or "").encode("utf-8")) for span in spans)
        role_confusion_rows = [row for row in golden_rows if row["role_confusion"]]
        modality_confusion_rows = [
            row for row in golden_rows if row["modality_confusion"]
        ]

        row = {
            "sample_id": sample_id,
            "doc_type": sample["doc_type"],
            "language": sample["language"],
            "source_sha256": sample["sha256"],
            "source_byte_size": sample["byte_size"],
            "metadata_is_fixture": bool(sample.get("metadata_is_fixture")),
            "annotation_scope": dict(scope),
            "parse": dict(selection.get("parse") or {}),
            "selection": {
                key: selection.get(key)
                for key in (
                    "status",
                    "document_kind",
                    "selection_limit",
                    "candidate_count",
                    "source_units",
                    "omitted_candidate_count",
                    "dropped_financial_count",
                    "selected_span_count",
                    "locator_roundtrip_verified",
                    "locator_roundtrip_failed",
                    "coverage_complete",
                )
            },
            "parser_options": dict(sample.get("parser_options") or {}),
            "golden_results": golden_rows,
            "required_coverage": {
                "numerator": required_matched,
                "denominator": len(required_rows),
                "rate": _rate(required_matched, len(required_rows)),
                "unverified_required_excluded": unverified_required,
                "definition": "required positive golden points that are verified at their locator and fully contained in selected text on the cited page/lines",
            },
            "optional_coverage": {
                "numerator": optional_matched,
                "denominator": len(optional_rows),
                "rate": _rate(optional_matched, len(optional_rows)),
                "definition": "same rule as required_coverage for optional points",
            },
            "noise": {
                "negative_points": len(negative_rows),
                "negative_points_hit": negative_hit,
                "selected_span_count": len(spans),
                "selected_in_scope": len(scope_spans),
                "judged_in_scope": len(judged_ids),
                "unjudged_in_scope": max(0, len(scope_spans) - len(judged_ids)),
                "noise_spans": len(noise_ids),
                "selected_noise_rate": {
                    "numerator": len(noise_ids),
                    "denominator": len(judged_ids),
                    "rate": _rate(len(noise_ids), len(judged_ids)),
                    "definition": "selected spans inside the annotation scope that carry a negative golden quote, over all in-scope selected spans judged by any golden point",
                },
            },
            "duplicate": {
                "duplicate_span_count": duplicate_span_count,
                "total_selected": total_selected,
                "duplicate_ratio": duplicate_ratio,
                "definition": "1 - unique normalized selected texts / selected spans",
            },
            "role_confusion": {
                "count": len(role_confusion_rows),
                "golden_ids": [row["golden_id"] for row in role_confusion_rows],
            },
            "modality_confusion": {
                "count": len(modality_confusion_rows),
                "golden_ids": [row["golden_id"] for row in modality_confusion_rows],
            },
            "bytes": {
                "selected_utf8_bytes": utf8_bytes,
                "source_raw_bytes": int(sample["byte_size"]),
                "selected_to_source_ratio": round(
                    utf8_bytes / max(1, int(sample["byte_size"])), 6
                ),
                "selected_char_count": sum(len(span.raw_text or "") for span in spans),
            },
            "elapsed_seconds": selection.get("elapsed_seconds"),
        }
        rows.append(row)
        totals["documents"] += 1
        totals["golden_points"] += len(golden_rows)
        totals["required_points"] += len(required_rows)
        totals["required_matched"] += required_matched
        totals["optional_points"] += len(optional_rows)
        totals["optional_matched"] += optional_matched
        totals["negative_points"] += len(negative_rows)
        totals["negative_points_hit"] += negative_hit
        totals["selected_span_count"] += len(spans)
        totals["selected_in_scope"] += len(scope_spans)
        totals["judged_in_scope"] += len(judged_ids)
        totals["noise_spans"] += len(noise_ids)
        totals["role_confusion"] += len(role_confusion_rows)
        totals["modality_confusion"] += len(modality_confusion_rows)
        totals["duplicate_span_count"] += duplicate_span_count
        totals["selected_utf8_bytes"] += utf8_bytes
        totals["locator_roundtrip_verified"] += int(
            selection.get("locator_roundtrip_verified") or 0
        )
        totals["locator_roundtrip_failed"] += int(
            selection.get("locator_roundtrip_failed") or 0
        )

    totals["required_coverage_rate"] = _rate(
        totals["required_matched"], totals["required_points"]
    )
    totals["optional_coverage_rate"] = _rate(
        totals["optional_matched"], totals["optional_points"]
    )
    totals["selected_noise_rate"] = _rate(
        totals["noise_spans"], totals["judged_in_scope"]
    )
    totals["duplicate_ratio"] = _rate(
        totals["duplicate_span_count"], totals["selected_span_count"]
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "evaluator_version": EVALUATOR_VERSION,
        "totals": totals,
        "samples": rows,
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReportValidationError(message)


def validate_report(
    report: Mapping[str, Any],
    *,
    samples: Sequence[Mapping[str, Any]],
    golden: Mapping[str, Any],
    baseline: str,
    parser: Mapping[str, str],
    selector: Mapping[str, str],
) -> None:
    """Reject reports that disagree with their inputs or their own arithmetic."""
    _require(
        report.get("schema_version") == SCHEMA_VERSION,
        f"schema_version must be {SCHEMA_VERSION}",
    )
    _require(
        bool(re.fullmatch(r"[0-9a-f]{40}", str(report.get("baseline") or ""))),
        "baseline must be a 40-char commit sha",
    )
    _require(
        report.get("baseline") == baseline,
        f"baseline {report.get('baseline')} != pinned {baseline}",
    )
    _require(report.get("parser") == dict(parser), "parser name/version mismatch")
    _require(report.get("selector") == dict(selector), "selector name/version mismatch")
    scope = report.get("scope")
    _require(
        isinstance(scope, Mapping) and bool(scope.get("definition")),
        "scope.definition must state what the denominators cover",
    )
    _require(
        isinstance(scope, Mapping) and bool(scope.get("denominators")),
        "scope.denominators must be declared",
    )

    by_id = {sample["sample_id"]: sample for sample in samples}
    golden_samples = golden["samples"]
    rows = report.get("samples")
    _require(isinstance(rows, list), "samples must be a list")
    _require(
        [row.get("sample_id") for row in rows] == [s["sample_id"] for s in samples],
        "report sample order/ids must match samples.json",
    )

    for row in rows:
        sample = by_id[row["sample_id"]]
        _require(
            row.get("source_sha256") == sample["sha256"],
            f"{row['sample_id']}: report sha does not match samples.json",
        )
        _require(
            int(row.get("source_byte_size") or 0) == int(sample["byte_size"]),
            f"{row['sample_id']}: report byte_size does not match samples.json",
        )
        _require(
            bool(row.get("annotation_scope")),
            f"{row['sample_id']}: report is missing its annotation scope",
        )
        golden_rows = row.get("golden_results")
        _require(
            isinstance(golden_rows, list), f"{row['sample_id']}: golden_results missing"
        )
        known = {
            point["golden_id"] for point in golden_samples[row["sample_id"]]["points"]
        }
        reported = [item.get("golden_id") for item in golden_rows]
        _require(
            len(reported) == len(set(reported)),
            f"{row['sample_id']}: duplicated golden_id",
        )
        unknown = sorted(set(reported) - known)
        _require(
            not unknown, f"{row['sample_id']}: unknown golden references {unknown}"
        )
        _require(
            set(reported) == known,
            f"{row['sample_id']}: golden_results must cover every annotated point",
        )

        required = [
            item
            for item in golden_rows
            if item["polarity"] == "positive" and item["priority"] == "required"
        ]
        verified_required = [item for item in required if item["verified"]]
        coverage = row["required_coverage"]
        _require(
            coverage["denominator"] == len(verified_required),
            f"{row['sample_id']}: required denominator {coverage['denominator']} != "
            f"verified required points {len(verified_required)}",
        )
        _require(
            coverage["numerator"]
            == sum(item["result"] == "full" for item in verified_required),
            f"{row['sample_id']}: required numerator does not match golden_results",
        )
        _require(
            coverage["rate"]
            == (
                None
                if coverage["denominator"] == 0
                else round(coverage["numerator"] / coverage["denominator"], 4)
            ),
            f"{row['sample_id']}: required rate does not match numerator/denominator",
        )

        negative = [item for item in golden_rows if item["polarity"] == "negative"]
        noise = row["noise"]
        _require(
            noise["negative_points"] == len(negative),
            f"{row['sample_id']}: negative point count mismatch",
        )
        _require(
            noise["negative_points_hit"]
            == sum(item["result"] == "noise" for item in negative),
            f"{row['sample_id']}: negative hits do not match golden_results",
        )
        _require(
            noise["selected_noise_rate"]["denominator"] == noise["judged_in_scope"],
            f"{row['sample_id']}: noise denominator must equal judged_in_scope",
        )
        _require(
            noise["selected_noise_rate"]["numerator"] == noise["noise_spans"],
            f"{row['sample_id']}: noise numerator must equal noise_spans",
        )

        role_count = sum(bool(item["role_confusion"]) for item in golden_rows)
        _require(
            row["role_confusion"]["count"] == role_count,
            f"{row['sample_id']}: role confusion count mismatch",
        )
        modality_count = sum(bool(item["modality_confusion"]) for item in golden_rows)
        _require(
            row["modality_confusion"]["count"] == modality_count,
            f"{row['sample_id']}: modality confusion count mismatch",
        )

        duplicate = row["duplicate"]
        total = row["selection"]["selected_span_count"]
        _require(
            duplicate["total_selected"] == total,
            f"{row['sample_id']}: duplicate total must equal selected_span_count",
        )
        _require(
            duplicate["duplicate_ratio"]
            == (
                0.0
                if total == 0
                else round(duplicate["duplicate_span_count"] / total, 4)
            ),
            f"{row['sample_id']}: duplicate ratio does not match arithmetic",
        )

        byte_row = row["bytes"]
        _require(
            int(byte_row["source_raw_bytes"]) == int(sample["byte_size"]),
            f"{row['sample_id']}: source_raw_bytes mismatch",
        )
        _require(
            byte_row["selected_to_source_ratio"]
            == round(
                byte_row["selected_utf8_bytes"] / max(1, int(sample["byte_size"])), 6
            ),
            f"{row['sample_id']}: selected ratio does not match arithmetic",
        )

    totals = report.get("totals")
    _require(isinstance(totals, Mapping), "totals missing")
    for key in (
        "required_points",
        "required_matched",
        "negative_points",
        "negative_points_hit",
        "selected_span_count",
        "judged_in_scope",
        "noise_spans",
        "role_confusion",
        "modality_confusion",
    ):
        expected = sum(row_totals(key, row) for row in rows)
        _require(
            totals.get(key) == expected,
            f"totals.{key} {totals.get(key)} != sum of samples {expected}",
        )
    _require(
        totals.get("selected_noise_rate")
        == (
            None
            if totals["judged_in_scope"] == 0
            else round(totals["noise_spans"] / totals["judged_in_scope"], 4)
        ),
        "totals.selected_noise_rate does not match arithmetic",
    )
    _require(
        report.get("output_scope") == "source-only",
        "report must declare output_scope=source-only (no investment evaluation)",
    )


def row_totals(key: str, row: Mapping[str, Any]) -> Any:
    if key in {"required_points"}:
        return row["required_coverage"]["denominator"]
    if key in {"required_matched"}:
        return row["required_coverage"]["numerator"]
    if key in {"negative_points"}:
        return row["noise"]["negative_points"]
    if key in {"negative_points_hit"}:
        return row["noise"]["negative_points_hit"]
    if key in {"selected_span_count"}:
        return row["selection"]["selected_span_count"]
    if key in {"judged_in_scope"}:
        return row["noise"]["judged_in_scope"]
    if key in {"noise_spans"}:
        return row["noise"]["noise_spans"]
    if key in {"role_confusion"}:
        return row["role_confusion"]["count"]
    if key in {"modality_confusion"}:
        return row["modality_confusion"]["count"]
    raise KeyError(key)


def iter_golden_ids(golden: Mapping[str, Any]) -> Iterable[str]:
    for entry in golden["samples"].values():
        for point in entry["points"]:
            yield point["golden_id"]


__all__ = [
    "EVALUATOR_VERSION",
    "GoldenValidationError",
    "ReportValidationError",
    "SCHEMA_VERSION",
    "evaluate",
    "match_negative",
    "match_positive",
    "normalize_text",
    "quote_sha256",
    "role_class",
    "validate_report",
]
