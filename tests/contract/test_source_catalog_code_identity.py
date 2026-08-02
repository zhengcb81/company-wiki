"""Contracts for honest worker loaded/current source fingerprints."""

from __future__ import annotations


def test_source_bundle_fingerprint_changes_and_fails_closed(tmp_path):
    from company_wiki.source_catalog.code_identity import (
        CORE_SOURCE_PATHS,
        source_bundle_fingerprint,
    )

    for index, relative_path in enumerate(CORE_SOURCE_PATHS):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture-{index}\n", encoding="utf-8")

    first = source_bundle_fingerprint(tmp_path)
    assert isinstance(first["fingerprint"], str)
    assert len(first["fingerprint"]) == 64
    assert first["error"] is None
    assert [item["path"] for item in first["files"]] == list(CORE_SOURCE_PATHS)

    changed_path = tmp_path / CORE_SOURCE_PATHS[-1]
    changed_path.write_text("changed\n", encoding="utf-8")
    second = source_bundle_fingerprint(tmp_path)
    assert second["fingerprint"] != first["fingerprint"]

    changed_path.unlink()
    missing = source_bundle_fingerprint(tmp_path)
    assert missing["fingerprint"] is None
    assert missing["files"] == []
    assert CORE_SOURCE_PATHS[-1] in missing["error"]
