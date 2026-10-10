"""Deterministic model fixtures for narrative handler integration tests."""

from __future__ import annotations

import json
from typing import Callable

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_model import (
    NARRATIVE_PROMPT_VERSION,
    NarrativeModelRequest,
    NarrativeModelResponse,
)


class ReplayNarrativeModel:
    def __init__(self, *, after_generate: Callable[[], None] | None = None) -> None:
        self.calls: list[NarrativeModelRequest] = []
        self._after_generate = after_generate

    def generate(self, request: NarrativeModelRequest) -> NarrativeModelResponse:
        self.calls.append(request)
        envelope = json.loads(request.data_json)
        evidence = envelope["evidence"]
        if not evidence:
            raise AssertionError("replay model must not be called for an empty selection")
        first = evidence[0]
        role = first[2] if len(first) > 2 else envelope["default_source_role"]
        if role in {"analyst", "investor_question"}:
            claim_type = "analyst_question"
            modality = "question"
            needs_review = False
            draft_status = "draft"
        elif role in {"company_filing", "management"}:
            claim_type = "company_statement"
            modality = "actual"
            needs_review = False
            draft_status = "draft"
        else:
            # Real PDFs can contain evidence without a trustworthy speaker
            # role. Keep the replay output conservative and contract-valid.
            claim_type = "uncertain"
            modality = "uncertain"
            needs_review = True
            draft_status = "needs_review"
        if "locator_unstable" in (first[3] if len(first) > 3 else envelope["default_quality_flags"]):
            needs_review = True
            draft_status = "needs_review"
        draft = {
            "source_id": envelope["source"]["source_id"],
            "source_sha256": envelope["source"]["source_sha256"],
            "language": envelope["source"]["language"],
            "claims": [
                {
                    "claim_id": "claim-replay-001",
                    # This fixture bootstraps production-current generation. Long
                    # historical drafts are constructed explicitly by read tests.
                    "text": first[1][:200],
                    "evidence_ids": [first[0]],
                    "claim_type": claim_type,
                    "modality": modality,
                    "needs_review": needs_review,
                }
            ],
            "status": draft_status,
        }
        response = NarrativeModelResponse(
            adapter_id="replay",
            model_id="fixture-v1",
            prompt_version=NARRATIVE_PROMPT_VERSION,
            response_bytes=canonical_json({"draft": draft}).encode("utf-8"),
        )
        if self._after_generate is not None:
            self._after_generate()
        return response


__all__ = ["ReplayNarrativeModel"]
