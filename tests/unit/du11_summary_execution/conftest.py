from __future__ import annotations
import pytest
from company_wiki.automation.models import canonical_json_hash
from company_wiki.automation.narrative_contracts import (
    NarrativeSelectResult,
    NarrativeSummaryResult,
)
from company_wiki.document_understanding.summary_tasks import build_summary_task_plan
from company_wiki.source_contract import (
    EvidenceSpan,
    EvidenceCoordinates,
    ParseStatus,
    source_id_for_sha256,
)


@pytest.fixture
def materials():
    sha = "a" * 64
    source = source_id_for_sha256(sha)
    spans = [
        EvidenceSpan.create(
            source_id=source,
            coordinates=EvidenceCoordinates(page_number=1, paragraph_index=i),
            raw_text=text,
            structured_value={"language": "en", "source_role": "company_filing"},
            parser_name="fixture",
            parser_version="1.0.0",
            parse_status=ParseStatus.PARSED,
            quality_flags=(),
        ).to_dict()
        for i, text in enumerate(
            [
                "Product Alpha entered client validation.",
                "Product Beta will ship next year.",
            ]
        )
    ]
    selected = NarrativeSelectResult.from_dict(
        {
            "schema_version": "narrative-select-result/2.0",
            "source_ref": {
                "schema_version": "2.0",
                "document_id": "doc-execution",
                "source_id": source,
                "content_sha256": sha,
                "byte_size": 100,
                "mime_type": "application/pdf",
            },
            "expected_read_policy_sha256": "b" * 64,
            "source_metadata": {
                "source_class": "filing",
                "title": "Fixture annual report",
                "document_kind": "annual_report",
                "language": "en",
            },
            "parser": {"name": "fixture", "version": "1.0.0"},
            "selector": {"name": "fixture", "version": "1.0.0"},
            "selection": {
                "status": "selected",
                "coverage_complete": True,
                "source_units": 2,
                "candidate_count": 2,
                "selected_count": 2,
                "omitted_candidate_count": 0,
                "dropped_financial_count": 0,
                "pages_total": 1,
                "pages_read": 1,
                "lines_total": 0,
                "tables_total": 0,
                "tables_scanned": 0,
            },
            "evidence_spans": spans,
            "prompt_review": {
                "status": "not_reviewed",
                "source_sha256": None,
                "evidence_sha256": None,
                "policy_hash": None,
                "reviewed_at": None,
            },
            "transcript_lineage": None,
            "transcript_byte_bindings": [],
            "summary_scope": "selected_evidence_only",
        }
    )
    summary = NarrativeSummaryResult.from_dict(
        {
            "schema_version": "narrative-summary-result/2.0",
            "source_ref": selected.source_ref.to_dict(),
            "language": "en",
            "translate": False,
            "status": "completed",
            "draft": {
                "source_id": source,
                "source_sha256": sha,
                "language": "en",
                "status": "draft",
                "claims": [
                    {
                        "claim_id": "t1-source",
                        "text": spans[0]["raw_text"],
                        "evidence_ids": [spans[0]["span_id"]],
                        "claim_type": "company_statement",
                        "modality": "uncertain",
                        "needs_review": False,
                    }
                ],
            },
            "model": {
                "adapter_id": "fixture",
                "model_id": "fixture",
                "prompt_version": "fixture-v5",
                "response_sha256": "c" * 64,
            },
            "prompt_review": selected.prompt_review.to_dict(),
        }
    )
    plan = build_summary_task_plan(
        selected.evidence_spans, reading_context=selected.reading_context, max_claims=4
    )
    report = {
        "schema_version": "source-extractive-execution/1",
        "plan_sha256": plan.binding_sha256,
        "tasks": [
            {
                "task": t.key,
                "task_binding_sha256": canonical_json_hash(t.to_binding()),
                "source_disposition": "admitted" if i == 0 else "deferred",
                "reason": "source_card" if i == 0 else "draft_byte_budget",
                "claim_id": "t1-source" if i == 0 else None,
                "model_disposition": "consider" if i == 0 else "unprocessed",
                "priority": "high" if i == 0 else None,
            }
            for i, t in enumerate(plan.tasks)
        ],
        "source_coverage_complete": False,
        "model_coverage_complete": False,
        "model_diagnostic": "RANK_INCOMPLETE",
    }
    return selected, summary, report
