"""Canonical narrative selection fixture; no real source/config/network."""

import hashlib

from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan, source_id_for_sha256


def response_draft(data):
    """Fake provider output, built independently of any prompt example."""
    row = data["evidence"][0]
    role = row[2] if len(row) > 2 else data["default_source_role"]
    flags = row[3] if len(row) > 3 else data["default_quality_flags"]
    claim_type = ("company_statement" if role in {"company_filing", "management"}
                  else "analyst_question" if role in {"analyst", "investor_question"}
                  else "uncertain")
    review = claim_type == "uncertain" or "locator_unstable" in flags
    return {"draft": {
        "source_id": data["source"]["source_id"],
        "source_sha256": data["source"]["source_sha256"],
        "language": data["source"]["language"],
        "claims": [{"claim_id": "claim-001", "text": row[1][:200], "evidence_ids": [row[0]],
                    "claim_type": claim_type, "modality": "question" if claim_type == "analyst_question" else "uncertain",
                    "needs_review": review}],
        "status": "needs_review" if review else "draft",
    }}


def selection(count=1, *, role="company_filing", flags=(), text_suffix=""):
    digest = hashlib.sha256(b"synthetic immutable original").hexdigest()
    source_id = source_id_for_sha256(digest)
    spans = [EvidenceSpan.create(
        source_id=source_id,
        coordinates=EvidenceCoordinates(page_number=index + 1, paragraph_index=0),
        raw_text=f"公司新产品已完成海外客户认证，正在推进新业务项目。{index}{text_suffix}",
        structured_value={
            "source_role": role,
            "language": "zh",
            "topics": ["overseas", "business_progress"],
            "selection_reasons": ["diagnostic_rule_" + str(n) for n in range(20)],
            "bbox": [72.123456, 180.654321, 500.123456, 600.654321],
            "block_sha256": digest,
            "text_sha256": digest,
            # Each page has an independent complete sentence. Group closure
            # tests use explicit multi-span fixtures; these are singleton groups.
            "selection_group_id": "urn:company-wiki:group:sha256:" + digest + f":singleton:{index}",
        },
        parser_name="synthetic-parser", parser_version="1.0.0",
        parse_status="parsed", quality_flags=flags,
    ).to_dict() for index in range(count)]
    return NarrativeSelectResult.from_dict({
        "schema_version": "narrative-select-result/2.0",
        "source_ref": {"schema_version": "2.0", "document_id": "doc-prompt-test",
                       "source_id": source_id, "content_sha256": digest,
                       "byte_size": 28, "mime_type": "application/pdf"},
        "expected_read_policy_sha256": digest,
        "source_metadata": {"source_class": "filing", "title": "合成招股说明书",
                            "document_kind": "prospectus", "language": "zh"},
        "parser": {"name": "synthetic-parser", "version": "1.0.0"},
        "selector": {"name": "synthetic-selector", "version": "1.0.0"},
        "selection": {"status": "partial", "coverage_complete": True,
                      "source_units": count + 20, "candidate_count": count + 20,
                      "selected_count": count, "omitted_candidate_count": 20,
                      "dropped_financial_count": 10, "pages_total": count,
                      "pages_read": count, "lines_total": 0,
                      "tables_total": 0, "tables_scanned": 0},
        "evidence_spans": spans,
        "prompt_review": {"status": "not_reviewed", "source_sha256": None,
                          "evidence_sha256": None, "policy_hash": None, "reviewed_at": None},
        "transcript_lineage": None, "transcript_byte_bindings": [],
        "summary_scope": "selected_evidence_only",
    })


