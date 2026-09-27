"""Validate human-authored G1 summary drafts against the isolated pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAN_ROOT = PROJECT_ROOT / "docs" / "plans" / "narrative-evidence-pilot-2026-09-26"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from company_wiki.source_catalog.narrative_evidence import (  # noqa: E402
    SourceSummaryDraft,
    SummaryClaim,
    validate_summary_draft,
)
from company_wiki.source_contract import source_id_for_sha256  # noqa: E402


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(
    metrics: dict,
    claim_spec: dict,
    manifest: dict,
    *,
    source_metrics: str = "g1_pilot_metrics_v6.json",
    source_claim_spec: str = "g1_summary_claims.json",
) -> dict:
    samples = {sample["id"]: sample for sample in manifest["samples"]}
    metrics_by_id = {row["sample_id"]: row for row in metrics["samples"]}
    claims_by_sample: dict[str, list[dict]] = {}
    for claim in claim_spec["claims"]:
        claims_by_sample.setdefault(claim["sample_id"], []).append(claim)

    draft_reports = []
    for sample_id, claims in claims_by_sample.items():
        sample = samples[sample_id]
        measured = metrics_by_id[sample_id]
        claims_by_id = {claim["id"]: claim for claim in claims}
        if not measured["source_sha256"].startswith(sample["sha256_prefix"]):
            raise ValueError(f"pilot source hash no longer matches manifest: {sample_id}")
        preview_by_id = {
            item["span_id"]: item for item in measured["selected_evidence_preview"]
        }
        anchor_by_id = {
            check["check_id"]: check for check in measured["anchor_checks"]
        }

        source_ids: list[str] = []
        claim_rows = []
        summary_claims = []
        for claim in claims:
            response_to = claim.get("response_to_claim_id")
            if response_to is not None:
                linked_question = claims_by_id.get(response_to)
                if not linked_question or linked_question["claim_type"] != "analyst_question":
                    raise ValueError(f"response link must target an analyst question: {claim['id']}")
            evidence_ids: list[str] = []
            for check_id in claim["anchor_check_ids"]:
                check = anchor_by_id[check_id]
                if not check["passed"] or check["match_scope"] != "selected_span_window":
                    raise ValueError(f"anchor lacks a precise selected span: {sample_id}/{check_id}")
                evidence_ids.extend(check["matched_evidence_ids"])
            evidence_ids = list(dict.fromkeys(evidence_ids))
            if not evidence_ids or any(evidence_id not in preview_by_id for evidence_id in evidence_ids):
                raise ValueError(f"summary references missing selected evidence: {claim['id']}")
            has_cjk = re.search(r"[\u3400-\u9fff]", claim["text"]) is not None
            if (sample["language"] == "en" and has_cjk) or (
                sample["language"] == "zh" and not has_cjk
            ):
                raise ValueError(f"summary claim language does not match source: {claim['id']}")
            if response_to is not None:
                question_ids: list[str] = []
                for check_id in linked_question["anchor_check_ids"]:
                    check = anchor_by_id[check_id]
                    if not check["passed"] or check["match_scope"] != "selected_span_window":
                        raise ValueError(f"linked question lacks a precise span: {response_to}")
                    question_ids.extend(check["matched_evidence_ids"])
                if not question_ids or any(evidence_id not in preview_by_id for evidence_id in question_ids):
                    raise ValueError(f"linked question references missing evidence: {response_to}")
                question_groups = {
                    preview_by_id[evidence_id].get("qa_group_id")
                    for evidence_id in question_ids
                }
                answer_groups = {
                    preview_by_id[evidence_id].get("qa_group_id")
                    for evidence_id in evidence_ids
                }
                if not ((question_groups & answer_groups) - {None}):
                    raise ValueError(f"question and response do not share a qa_group_id: {claim['id']}")

            summary_claims.append(
                SummaryClaim(
                    claim_id=claim["id"],
                    text=claim["text"],
                    evidence_ids=tuple(evidence_ids),
                    claim_type=claim["claim_type"],
                    modality=claim["modality"],
                    needs_review=True,
                )
            )
            for evidence_id in evidence_ids:
                source_ids.append(evidence_id)
            claim_rows.append(
                {
                    "claim_id": claim["id"],
                    "response_to_claim_id": response_to,
                    "qa_group_link_verified": response_to is not None,
                    "text": claim["text"],
                    "claim_type": claim["claim_type"],
                    "modality": claim["modality"],
                    "needs_review": True,
                    "evidence": [
                        {
                            "evidence_id": evidence_id,
                            "locator_v1": preview_by_id[evidence_id]["locator_v1"],
                            "source_role": preview_by_id[evidence_id]["source_role"],
                            "qa_group_id": preview_by_id[evidence_id].get("qa_group_id"),
                            "selection_group_id": preview_by_id[evidence_id].get("selection_group_id"),
                            "quality_flags": preview_by_id[evidence_id]["quality_flags"],
                            "excerpt": preview_by_id[evidence_id]["excerpt"],
                        }
                        for evidence_id in evidence_ids
                    ],
                }
            )

        source_sha = measured["source_sha256"]
        source_id = source_id_for_sha256(source_sha)
        evidence_objects = [
            SimpleNamespace(
                span_id=evidence_id,
                structured_value={"source_role": preview_by_id[evidence_id]["source_role"]},
                quality_flags=tuple(preview_by_id[evidence_id]["quality_flags"]),
            )
            for evidence_id in sorted(set(source_ids))
        ]
        draft = SourceSummaryDraft(
            source_id=source_id,
            source_sha256=source_sha,
            language=sample["language"],
            claims=tuple(summary_claims),
            status="needs_review",
        )
        validate_summary_draft(
            draft,
            source_id=source_id,
            source_sha256=source_sha,
            language=sample["language"],
            evidence_spans=evidence_objects,
        )
        draft_reports.append(
            {
                "sample_id": sample_id,
                "source_id": source_id,
                "source_sha256": source_sha,
                "document_kind": measured["document_kind"],
                "draft_status": draft.status,
                "automated_citation_role_validation": "passed",
                "semantic_review": "not_performed",
                "claims": claim_rows,
            }
        )

    return {
        "schema_version": "narrative-g1-summary-validation/0.1.0",
        "source_metrics": source_metrics,
        "claim_spec": source_claim_spec,
        "authorship": claim_spec["authorship"],
        "execution_scope": "offline validation only; no LLM/API, catalog writer, or worker",
        "semantic_review": "not_performed; all drafts remain needs_review",
        "sample_count": len(draft_reports),
        "claim_count": sum(len(item["claims"]) for item in draft_reports),
        "status": "citation_and_role_checks_passed",
        "drafts": draft_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--claims", type=Path, default=None)
    parser.add_argument(
        "--run-root",
        type=Path,
        help="Isolated test root; inputs, output, and temporary artifacts must stay beneath it.",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    run_root = None
    if args.run_root is not None:
        if not args.run_root.is_dir():
            raise ValueError("run root must be an existing isolated directory")
        run_root = args.run_root.resolve(strict=True)
        if any(value is None for value in (args.metrics, args.manifest, args.claims)):
            raise ValueError("--metrics, --manifest, and --claims are required with --run-root")
        input_paths = {
            "metrics": args.metrics.resolve(strict=True),
            "manifest": args.manifest.resolve(strict=True),
            "claims": args.claims.resolve(strict=True),
        }
        for label, path in input_paths.items():
            if not path.is_relative_to(run_root):
                raise ValueError(f"isolated {label} input must remain inside --run-root")
        output = (args.output or run_root / "outputs" / "g1_summary_validation.json").resolve()
        if not output.is_relative_to(run_root):
            raise ValueError("isolated summary output must remain inside --run-root")
    else:
        plan_root = PLAN_ROOT.resolve(strict=True)
        input_paths = {
            "metrics": (args.metrics or PLAN_ROOT / "g1_pilot_metrics_v6.json").resolve(strict=True),
            "manifest": (args.manifest or PLAN_ROOT / "g1_sample_manifest.json").resolve(strict=True),
            "claims": (args.claims or PLAN_ROOT / "g1_summary_claims.json").resolve(strict=True),
        }
        output = (args.output or PLAN_ROOT / "g1_summary_validation_v1.json").resolve()
        if not output.is_relative_to(plan_root):
            raise ValueError("summary pilot output must remain inside the planning directory")
    if output.exists():
        raise FileExistsError("summary pilot output exists; remove it only after reviewing it")

    report = build_report(
        _load(input_paths["metrics"]),
        _load(input_paths["claims"]),
        _load(input_paths["manifest"]),
        source_metrics=input_paths["metrics"].name,
        source_claim_spec=input_paths["claims"].name,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: report[key] for key in ("status", "sample_count", "claim_count", "semantic_review")},
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
