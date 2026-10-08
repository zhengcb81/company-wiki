"""Committed references use a content version, never a capture approval."""

import hashlib
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog.canonical_writer import CanonicalImportError, CanonicalSourceWriter
from company_wiki.source_catalog.source_reader import SourceReadError, SourceRef, SourceVersionReader

SHA = hashlib.sha256(b"original transcript bytes").hexdigest()
SOURCE = "urn:company-wiki:source:sha256:" + SHA
DOCUMENT = "urn:company-wiki:document:sha256:" + SHA


def test_reference_selects_exact_sha_once_without_metadata_search(monkeypatch):
    calls = []
    ref = SourceRef(DOCUMENT, SOURCE, SHA, 25, "text/plain")

    def query(document, source, sha):
        calls.append((document, source, sha))
        return ref

    monkeypatch.setattr(SourceVersionReader, "__init__", lambda self, catalog: None)
    monkeypatch.setattr(SourceVersionReader, "query_ref", lambda self, *args: query(*args))
    writer = CanonicalSourceWriter.__new__(CanonicalSourceWriter)
    writer.catalog = SimpleNamespace()
    assert writer.source_ref_for_import(None, None, SHA) == ref
    assert calls == [(DOCUMENT, SOURCE, SHA)]


@pytest.mark.parametrize("reason", ["document_not_indexed", "expected_version_mismatch", "source_not_active"])
def test_missing_wrong_or_inactive_committed_version_still_fails(monkeypatch, reason):
    monkeypatch.setattr(SourceVersionReader, "__init__", lambda self, catalog: None)

    def unavailable(*args):
        raise SourceReadError("unavailable", reason)

    monkeypatch.setattr(SourceVersionReader, "query_ref", unavailable)
    writer = CanonicalSourceWriter.__new__(CanonicalSourceWriter)
    writer.catalog = SimpleNamespace()
    with pytest.raises(CanonicalImportError, match="not indexed to its bytes"):
        writer.source_ref_for_import(None, None, SHA)
