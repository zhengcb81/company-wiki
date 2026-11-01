"""Committed references use a content version, never a capture approval."""

import hashlib
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog.canonical_writer import CanonicalImportError, CanonicalSourceWriter
from company_wiki.source_catalog.source_reader import SourceReadError, SourceRef

SHA = hashlib.sha256(b"original transcript bytes").hexdigest()
SOURCE = "urn:company-wiki:source:sha256:" + SHA
DOCUMENT = "urn:company-wiki:document:sha256:" + SHA


def test_reference_selects_exact_sha_once_without_metadata_search():
    calls = []
    ref = SourceRef(DOCUMENT, SOURCE, SHA, 25, "text/plain")

    def query(document):
        calls.append(document)
        return {"source_id": SOURCE, "content_sha256": SHA, "source_status": "active",
                "byte_size": 25, "mime_type": "text/plain"}

    writer = CanonicalSourceWriter.__new__(CanonicalSourceWriter)
    writer.catalog = SimpleNamespace(reader=SimpleNamespace(exact_source_version=query))
    assert writer.source_ref_for_import(None, None, SHA) == ref
    assert calls == [DOCUMENT]


@pytest.mark.parametrize("reason", ["document_not_indexed", "expected_version_mismatch", "source_not_active"])
def test_missing_wrong_or_inactive_committed_version_still_fails(reason):
    calls = []

    def query(document):
        calls.append(document)
        if reason == "document_not_indexed":
            return None
        return {"source_id": SOURCE, "content_sha256": "b" * 64 if reason == "expected_version_mismatch" else SHA,
                "source_status": "inactive" if reason == "source_not_active" else "active",
                "byte_size": 25, "mime_type": "text/plain"}

    writer = CanonicalSourceWriter.__new__(CanonicalSourceWriter)
    writer.catalog = SimpleNamespace(reader=SimpleNamespace(exact_source_version=query))
    with pytest.raises(CanonicalImportError, match="not indexed to its bytes") as rejected:
        writer.source_ref_for_import(None, None, SHA)
    assert calls == [DOCUMENT]
    assert isinstance(rejected.value.__cause__, SourceReadError)
    assert rejected.value.__cause__.reason == reason
