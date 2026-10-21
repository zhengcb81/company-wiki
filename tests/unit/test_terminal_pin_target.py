"""Terminal storage consumes a neutral pin instead of source-layer naming logic."""
from __future__ import annotations

import pytest

from company_wiki.automation.terminal_receipt_contracts import FinalArtifactPin
from company_wiki.narrative_subject import NarrativeSubject, publication_target
from company_wiki.source_contract import source_id_for_sha256


@pytest.mark.parametrize("projected", [False, True])
def test_final_pin_owns_exact_raw_or_projected_effect_target(projected):
    source = {
        "schema_version": "2.0", "document_id": "document", "source_id": source_id_for_sha256("a" * 64),
        "content_sha256": "a" * 64, "byte_size": 1, "mime_type": "application/json",
    }
    subject = NarrativeSubject.from_raw(source)
    generation = None
    if projected:
        subject = NarrativeSubject.from_dict({
            "kind": "official_json", "item_key": "urn:company-wiki:source-projection:sha256:" + "b" * 64,
            "subject_sha256": "b" * 64, "parent_source_refs": [source],
            "issuer": {}, "as_of_date": "2026-10-21", "adapter": {}, "coverage": {},
        })
        generation = "c" * 64
    pin = FinalArtifactPin(
        "effect", "artifact", "d" * 64, 1, source["document_id"], source["source_id"],
        source["content_sha256"], subject if projected else None, generation,
    )
    assert pin.effect_target == publication_target(subject, generation)
    assert "effect_target" not in pin.to_dict()
