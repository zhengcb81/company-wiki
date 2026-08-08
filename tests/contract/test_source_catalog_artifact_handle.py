"""WU-5.1: ArtifactHandle validator (fail-closed, RED first).

An artifact (normalized/summary/sections) is consumable ONLY when ALL of:
- status == completed (pending/failed/stale rejected);
- source_id == the document's primary source (wrong binding rejected);
- the artifact file exists and its hash matches content_sha256;
- generator_name/version are registered in the compatibility registry;
- created_at and the document's as_of are sane (future rejected);
- the artifact path lives inside an allowed root.

RED phase: the module does not exist (ImportError).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


WIKI_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WIKI_ROOT / "src"))

from company_wiki.source_catalog.artifact_handle import (  # noqa: E402
    ArtifactHandle,
    validate_artifact,
)

_BODY = b"# normalized"


def _artifact(tmp_path: Path, **overrides):
    path = tmp_path / "normalized.md"
    path.write_bytes(_BODY)
    base = dict(
        artifact_id="art-1",
        document_id="doc-1",
        source_id="src-1",
        artifact_role="normalized",
        path=str(path),
        content_sha256=hashlib.sha256(_BODY).hexdigest(),
        byte_size=len(_BODY),
        mime_type="text/markdown",
        generator_name="normalizer",
        generator_version="1.0.0",
        status="completed",
        created_at="2026-08-08T10:00:00Z",
        error=None,
    )
    base.update(overrides)
    return base


def _source_document(**overrides):
    base = dict(
        document_id="doc-1",
        primary_source_id="src-1",
        source_sha256="b" * 64,
        as_of_date="2026-08-08",
    )
    base.update(overrides)
    return base


def _registry():
    return {"normalizer": {"1.0.0"}, "summarizer": {"2.0.0"}, "section_extractor": {"3.0.0"}}


def test_valid_artifact_passes(tmp_path):
    handle = validate_artifact(
        _artifact(tmp_path),
        source=_source_document(),
        registry=_registry(),
        allowed_roots=(tmp_path,),
        now="2026-08-08T12:00:00Z",
    )
    assert isinstance(handle, ArtifactHandle)
    assert handle.reusable is True


def test_rejects_pending_status(tmp_path):
    handle = validate_artifact(
        _artifact(tmp_path, status="pending"),
        source=_source_document(), registry=_registry(),
        allowed_roots=(tmp_path,), now="2026-08-08T12:00:00Z",
    )
    assert handle.reusable is False
    assert "status" in handle.reason


def test_rejects_wrong_source_binding(tmp_path):
    handle = validate_artifact(
        _artifact(tmp_path, source_id="src-other"),
        source=_source_document(), registry=_registry(),
        allowed_roots=(tmp_path,), now="2026-08-08T12:00:00Z",
    )
    assert handle.reusable is False
    assert "source" in handle.reason


def test_rejects_missing_file(tmp_path):
    handle = validate_artifact(
        _artifact(tmp_path, path=str(tmp_path / "nope.md")),
        source=_source_document(), registry=_registry(),
        allowed_roots=(tmp_path,), now="2026-08-08T12:00:00Z",
    )
    assert handle.reusable is False
    assert "file" in handle.reason


def test_rejects_hash_mismatch(tmp_path):
    path = tmp_path / "normalized.md"
    path.write_bytes(b"different bytes")
    handle = validate_artifact(
        _artifact(tmp_path, path=str(path), content_sha256="a" * 64),
        source=_source_document(), registry=_registry(),
        allowed_roots=(tmp_path,), now="2026-08-08T12:00:00Z",
    )
    assert handle.reusable is False
    assert "hash" in handle.reason


def test_rejects_unknown_generator(tmp_path):
    handle = validate_artifact(
        _artifact(tmp_path, generator_name="rogue", generator_version="9.9.9"),
        source=_source_document(), registry=_registry(),
        allowed_roots=(tmp_path,), now="2026-08-08T12:00:00Z",
    )
    assert handle.reusable is False
    assert "generator" in handle.reason


def test_rejects_future_created_at(tmp_path):
    handle = validate_artifact(
        _artifact(tmp_path, created_at="2099-01-01T00:00:00Z"),
        source=_source_document(), registry=_registry(),
        allowed_roots=(tmp_path,), now="2026-08-08T12:00:00Z",
    )
    assert handle.reusable is False
    assert "created_at" in handle.reason


def test_rejects_outside_allowed_root(tmp_path, tmp_path_factory):
    other = tmp_path_factory.mktemp("other")
    (other / "x.md").write_bytes(_BODY)
    handle = validate_artifact(
        _artifact(tmp_path, path=str(other / "x.md")),
        source=_source_document(), registry=_registry(),
        allowed_roots=(tmp_path,), now="2026-08-08T12:00:00Z",
    )
    assert handle.reusable is False
    assert "root" in handle.reason
