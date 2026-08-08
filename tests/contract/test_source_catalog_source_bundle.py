"""WU-5.2: SourceBundle query — one call returns source + verified artifacts.

``build_source_bundle`` takes the resolved source document, its artifacts
(all roles), the generator registry and allowed roots, and returns:

- ``source`` (the original handle — the lineage anchor);
- per-role ArtifactHandle for each artifact that PASSES the WU-5.1
  validator (normalized / summary / sections);
- ``invalid`` entries with reason codes for artifacts that fail;
- a deterministic bundle hash binding source + all valid handles.

An invalid artifact never contaminates a still-valid original (the source
handle remains reusable; only the failed role is unusable).

RED phase: the module does not exist (ImportError).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


WIKI_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WIKI_ROOT / "src"))

from company_wiki.source_catalog.source_bundle import (  # noqa: E402
    SourceBundle,
    build_source_bundle,
)

_BODY = b"# normalized"


def _artifact(tmp_path: Path, role: str = "normalized", **overrides):
    path = tmp_path / f"{role}.md"
    path.write_bytes(_BODY)
    base = dict(
        schema_version="1.0",
        artifact_id=f"art-{role}",
        document_id="doc-1",
        source_id="src-1",
        source_sha256="b" * 64,
        artifact_role=role,
        path=str(path),
        content_sha256=hashlib.sha256(_BODY).hexdigest(),
        byte_size=len(_BODY),
        mime_type="text/markdown",
        generator_name={
            "normalized": "normalizer",
            "summary": "summarizer",
            "sections": "section_extractor",
        }[role],
        generator_version="1.0.0",
        status="completed",
        created_at="2026-08-08T10:00:00Z",
        error=None,
    )
    base.update(overrides)
    return base


def _source():
    return dict(
        document_id="doc-1",
        primary_source_id="src-1",
        source_sha256="b" * 64,
        as_of_date="2026-08-08",
    )


def _registry():
    return {
        "normalizer": {"1.0.0"},
        "summarizer": {"1.0.0"},
        "section_extractor": {"1.0.0"},
    }


def test_bundle_with_all_roles_valid(tmp_path):
    bundle = build_source_bundle(
        source=_source(),
        artifacts=[
            _artifact(tmp_path, "normalized"),
            _artifact(tmp_path, "summary"),
            _artifact(tmp_path, "sections"),
        ],
        registry=_registry(),
        allowed_roots=(tmp_path,),
        now="2026-08-08T12:00:00Z",
    )
    assert isinstance(bundle, SourceBundle)
    assert bundle.source["document_id"] == "doc-1"
    assert set(bundle.valid_handles.keys()) == {"normalized", "summary", "sections"}
    assert bundle.invalid == {}
    assert len(bundle.bundle_hash) == 64


def test_bundle_hash_deterministic(tmp_path):
    args = dict(
        source=_source(),
        artifacts=[
            _artifact(tmp_path, "normalized"),
            _artifact(tmp_path, "summary"),
        ],
        registry=_registry(),
        allowed_roots=(tmp_path,),
        now="2026-08-08T12:00:00Z",
    )
    b1 = build_source_bundle(**args)
    b2 = build_source_bundle(**args)
    assert b1.bundle_hash == b2.bundle_hash


def test_invalid_artifact_isolated_others_remain_valid(tmp_path):
    """A stale summary must not poison the valid normalized artifact or the
    source itself."""
    bundle = build_source_bundle(
        source=_source(),
        artifacts=[
            _artifact(tmp_path, "normalized"),
            _artifact(tmp_path, "summary", status="pending"),
        ],
        registry=_registry(),
        allowed_roots=(tmp_path,),
        now="2026-08-08T12:00:00Z",
    )
    assert "normalized" in bundle.valid_handles
    assert "summary" not in bundle.valid_handles
    assert "summary" in bundle.invalid
    assert "status" in bundle.invalid["summary"].reason


def test_invalid_binding_does_not_contaminate(tmp_path):
    bundle = build_source_bundle(
        source=_source(),
        artifacts=[
            _artifact(tmp_path, "normalized", source_id="src-other"),
            _artifact(tmp_path, "sections"),
        ],
        registry=_registry(),
        allowed_roots=(tmp_path,),
        now="2026-08-08T12:00:00Z",
    )
    assert "normalized" not in bundle.valid_handles
    assert "sections" in bundle.valid_handles
    assert "source" in bundle.invalid["normalized"].reason


def test_bundle_hash_changes_when_artifact_invalidates(tmp_path):
    """Removing a valid artifact (making it invalid) must change the hash —
    consumers cannot miss a role silently changing."""
    valid = build_source_bundle(
        source=_source(),
        artifacts=[_artifact(tmp_path, "normalized")],
        registry=_registry(),
        allowed_roots=(tmp_path,),
        now="2026-08-08T12:00:00Z",
    )
    stale = build_source_bundle(
        source=_source(),
        artifacts=[_artifact(tmp_path, "normalized", status="failed")],
        registry=_registry(),
        allowed_roots=(tmp_path,),
        now="2026-08-08T12:00:00Z",
    )
    assert valid.bundle_hash != stale.bundle_hash
    assert "normalized" not in stale.valid_handles
