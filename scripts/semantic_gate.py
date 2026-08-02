#!/usr/bin/env python3
"""Compute gold-corpus integrity and semantic readiness from source data, never handwritten status."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def source_id_from_markdown(path: Path) -> str | None:
    content = path.read_text(encoding="utf-8", errors="replace")
    if not content.startswith("---"):
        return None
    match = re.search(r"(?m)^source_id:\s*([^\s]+)\s*$", content.split("---", 2)[1])
    return match.group(1) if match else None


def evaluate_gold_integrity(gold_root: Path, min_sources: int = 30) -> dict[str, Any]:
    gold_root = gold_root.resolve()
    violations: list[dict[str, Any]] = []
    source_files = sorted((gold_root / "sources").rglob("*.md"))
    sources: dict[str, Path] = {}
    for path in source_files:
        source_id = source_id_from_markdown(path)
        if not source_id:
            violations.append({"id": "source-id-missing", "path": str(path.relative_to(gold_root))})
        elif source_id in sources:
            violations.append({"id": "source-id-duplicate", "source_id": source_id})
        else:
            sources[source_id] = path
    if len(sources) < min_sources:
        violations.append(
            {"id": "gold-source-count", "actual": len(sources), "minimum": min_sources}
        )

    annotations = gold_root / "annotations"
    evidence_data = load_json(annotations / "evidence_spans.json")
    claims_data = load_json(annotations / "material_claims.json")
    routing_data = load_json(annotations / "routing_targets.json")
    contradiction_data = load_json(annotations / "contradictions.json")

    spans_by_id: dict[str, dict[str, Any]] = {}
    for source_id, spans in evidence_data.get("spans", {}).items():
        if source_id not in sources:
            violations.append({"id": "span-source-missing", "source_id": source_id})
            continue
        source_text = sources[source_id].read_text(encoding="utf-8", errors="replace")
        for span in spans:
            span_id = str(span.get("span_id", ""))
            if not span_id or span_id in spans_by_id:
                violations.append({"id": "span-id-invalid", "span_id": span_id})
                continue
            spans_by_id[span_id] = span
            text = str(span.get("text", ""))
            if not text or text not in source_text:
                violations.append({"id": "span-text-not-found", "span_id": span_id})
            start = span.get("start")
            end = span.get("end")
            if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(source_text)):
                violations.append({"id": "span-offset-invalid", "span_id": span_id})
            elif source_text[start:end].strip() != text.strip():
                violations.append({"id": "span-offset-mismatch", "span_id": span_id})

    claim_ids: set[str] = set()
    for claim in claims_data.get("claims", []):
        claim_id = str(claim.get("claim_id", ""))
        if not claim_id or claim_id in claim_ids:
            violations.append({"id": "claim-id-invalid", "claim_id": claim_id})
        claim_ids.add(claim_id)
        if claim.get("source_id") not in sources:
            violations.append(
                {"id": "claim-source-missing", "claim_id": claim_id, "source_id": claim.get("source_id")}
            )
        evidence = claim.get("evidence_spans")
        if not isinstance(evidence, list) or not evidence:
            violations.append({"id": "claim-evidence-missing", "claim_id": claim_id})
        else:
            for span_id in evidence:
                if span_id not in spans_by_id:
                    violations.append(
                        {"id": "claim-evidence-unresolved", "claim_id": claim_id, "span_id": span_id}
                    )

    routing_sources: set[str] = set()
    for case in routing_data.get("routing", []):
        source_id = str(case.get("source_id", ""))
        routing_sources.add(source_id)
        if source_id not in sources:
            violations.append({"id": "routing-source-missing", "source_id": source_id})
        targets = case.get("expected_targets")
        if not isinstance(targets, list) or not targets:
            violations.append({"id": "routing-targets-missing", "source_id": source_id})

    for contradiction in contradiction_data.get("contradictions", []):
        original = contradiction.get("original_claim", {})
        correcting = contradiction.get("correcting_claim", {})
        if original.get("source_id") not in sources:
            violations.append(
                {"id": "contradiction-original-source-missing", "source_id": original.get("source_id")}
            )
        if correcting.get("source_id") not in sources:
            violations.append(
                {"id": "contradiction-correcting-source-missing", "source_id": correcting.get("source_id")}
            )

    quality_path = gold_root / "expected" / "quality_metrics.json"
    if quality_path.is_file():
        quality = load_json(quality_path)
        for name, metric in quality.get("metrics", {}).items():
            actual = metric.get("actual")
            target = metric.get("target")
            status = str(metric.get("status", ""))
            if isinstance(actual, (int, float)) and isinstance(target, (int, float)):
                if actual < target and status.startswith("pass"):
                    violations.append(
                        {
                            "id": "handwritten-status-contradicts-threshold",
                            "metric": name,
                            "actual": actual,
                            "target": target,
                            "status": status,
                        }
                    )
        declared_sources = quality.get("metrics", {}).get("source_coverage", {}).get("total_sources")
        if isinstance(declared_sources, int) and declared_sources != len(sources):
            violations.append(
                {
                    "id": "declared-source-count-mismatch",
                    "declared": declared_sources,
                    "actual": len(sources),
                }
            )

    counts = {
        "source_files": len(source_files),
        "unique_sources": len(sources),
        "evidence_spans": len(spans_by_id),
        "material_claims": len(claim_ids),
        "routing_cases": len(routing_data.get("routing", [])),
        "contradictions": len(contradiction_data.get("contradictions", [])),
    }
    return {
        "schema_version": 1,
        "result": "pass" if not violations else "fail",
        "counts": counts,
        "violations": violations,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--min-sources", type=int, default=30)
    parser.add_argument("--receipt", type=Path)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    result = evaluate_gold_integrity(args.gold_root, min_sources=args.min_sources)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
