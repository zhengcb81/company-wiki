"""The processed-document endpoint composes owners through public ports."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from company_wiki.source_contract import (
    SourceChunkSinkError,
    SourceProcessingDescriptor,
    SourceReadError,
    SourceRef,
    source_id_for_sha256,
)
from company_wiki.source_catalog.processed_document import read_processed_document
from company_wiki.source_catalog.processed_document_parser import _TempFileParseSession


ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DOCUMENT = ROOT / "src/company_wiki/source_catalog/processed_document.py"


def _function_tree(source: str, name: str) -> ast.FunctionDef:
    module = ast.parse(source)
    return next(
        node for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def test_processed_reader_uses_the_pathless_stream_and_processing_descriptor_ports():
    source = PROCESSED_DOCUMENT.read_text(encoding="utf-8")
    function = _function_tree(source, "read_processed_document")
    calls = {
        node.func.attr
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert "describe_processing_version" in calls
    assert "stream_version" in calls
    assert "open_described_version" not in calls


def test_processed_document_endpoint_does_not_reach_into_catalog_storage():
    source = PROCESSED_DOCUMENT.read_text(encoding="utf-8")
    module = ast.parse(source)
    storage_reaches = [
        node.lineno
        for node in ast.walk(module)
        if isinstance(node, ast.Attribute)
        and node.attr == "catalog"
        and isinstance(node.value, ast.Name)
        and node.value.id == "reader"
    ]
    internal_attributes = [
        node.attr
        for node in ast.walk(module)
        if isinstance(node, ast.Attribute)
        and node.attr in {"original_path", "manifest_json", "exact_source_locations"}
    ]
    source_manifest_names = [
        node.id
        for node in ast.walk(module)
        if isinstance(node, ast.Name) and node.id == "SourceManifest"
    ]

    assert storage_reaches == []
    assert internal_attributes == []
    assert source_manifest_names == []


def _descriptor() -> SourceProcessingDescriptor:
    digest = hashlib.sha256(b"x").hexdigest()
    ref = SourceRef(
        document_id="test-document",
        source_id=source_id_for_sha256(digest),
        content_sha256=digest,
        byte_size=1,
        mime_type="application/pdf",
    )
    return SourceProcessingDescriptor(
        source_ref=ref,
        format_hint="pdf",
        source_type="filing",
        entity_ids=("test-entity",),
        published_date=None,
        retrieved_at="2026-01-01T00:00:00Z",
        collector_name="test",
        collector_version="1.0.0",
        immutable_status="immutable",
    )


def test_temp_parse_session_attempts_directory_cleanup_after_discard_failure(monkeypatch):
    session = _TempFileParseSession(_descriptor())
    temporary_path = Path(session._temporary.name)
    cleanup_calls = []
    cleanup = session._temporary.cleanup

    def fail_discard():
        raise OSError("staged file could not be unlinked")

    def observe_cleanup():
        cleanup_calls.append(True)
        cleanup()

    monkeypatch.setattr(session, "discard_candidate", fail_discard)
    monkeypatch.setattr(session._temporary, "cleanup", observe_cleanup)

    with pytest.raises(SourceChunkSinkError, match="cleanup"):
        session.close()

    assert cleanup_calls == [True]
    assert not temporary_path.exists()


def test_source_failure_survives_parser_session_close_failure(caplog):
    descriptor = _descriptor()
    source_failure = SourceReadError("unavailable", "source_read_failed")

    class Reader:
        def describe_processing_version(self, _ref):
            return descriptor

        def describe_version(self, _ref):
            return {}

        def stream_version(self, *_args, **_kwargs):
            raise source_failure

    class Session:
        def close(self):
            raise OSError("temporary directory cleanup failed")

    class Parser:
        def requires_verified_content(self, _descriptor):
            return False

        def begin_stream(self, _descriptor):
            return Session()

    request = {
        "schema_version": "company-wiki-processed-document/1",
        "source_ref": descriptor.source_ref.to_dict(),
    }

    with pytest.raises(SourceReadError) as caught:
        read_processed_document(Reader(), request, parser=Parser())

    assert caught.value.reason == "source_read_failed"
    assert "Parser session cleanup also failed" in caplog.text
