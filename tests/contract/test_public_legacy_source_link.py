"""Actual isolated catalog tests; no production data and no synthetic PASS claim."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.public_legacy_source_link import (
    LegacyLinkError,
    REQUEST_SCHEMA,
    legacy_source_key,
    resolve_legacy_source,
)


def build(tmp_path):
    files = tmp_path / "originals"
    files.mkdir()
    path = files / "article.txt"
    path.write_text("A registered original has immutable bytes.\n", encoding="utf-8")
    (files / "article.txt.source.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "canonical_entity_id": "company-name:Controlled",
                "display_name": "Controlled",
                "market": "CN",
                "security_id": "688012",
                "document_kind": "news",
                "filing_date": "2026-01-01",
                "provider": "controlled",
                "provider_document_id": "controlled-1",
                "language": "en",
            }
        ),
        encoding="utf-8",
    )
    config = CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / "catalog",
        roots=(
            RootSpec(
                "originals",
                files,
                "directory",
                read_only=True,
                reusable_for_filing=True,
            ),
        ),
        reusable_root_kinds=("directory",),
    )
    catalog = SourceCatalog(config)
    catalog.scan()
    return catalog, path


def request(path, **extra):
    return {
        "schema_version": REQUEST_SCHEMA,
        "legacy_source_id": legacy_source_key(str(path.resolve())),
        **extra,
    }


def tree_digest(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_actual_current_bytes_and_zero_business_writes(tmp_path):
    catalog, path = build(tmp_path)
    catalog.close()
    catalog = SourceCatalog(catalog.config)
    before = tree_digest(tmp_path)
    value = resolve_legacy_source(
        catalog, request(path, expected_byte_size=path.stat().st_size)
    )
    assert value["state"] == "available", value
    assert (
        value["source_ref"]["content_sha256"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert value["historical_version_status"] == "legacy_source_version_unpinned"
    assert value["document_version_id"].startswith("cwpdv1-")
    assert value["current_byte_verification"]["byte_size"] == path.stat().st_size
    assert str(tmp_path) not in json.dumps(value)
    receipt = value.pop("receipt_sha256")
    assert (
        receipt
        == hashlib.sha256(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode()
        ).hexdigest()
    )
    catalog.close()
    after = tree_digest(tmp_path)
    # SQLite may create empty WAL/shared-memory coordination files when an
    # otherwise read-only connection opens a WAL-mode database. They contain
    # no committed business frames; the catalog and every original are exact.
    for name in set(after) - set(before):
        assert name in {"catalog\\catalog.sqlite3-wal", "catalog\\catalog.sqlite3-shm"}
        if name.endswith("-wal"):
            assert (tmp_path / name).stat().st_size == 0
    assert {name: digest for name, digest in after.items() if name in before} == before


def test_unknown_key_and_size_mismatch_do_not_choose_by_title(tmp_path):
    catalog, path = build(tmp_path)
    assert (
        resolve_legacy_source(
            catalog,
            {"schema_version": REQUEST_SCHEMA, "legacy_source_id": "src_" + "0" * 16},
        )["state"]
        == "not_found"
    )
    assert resolve_legacy_source(catalog, request(path, expected_byte_size=1))[
        "reason_codes"
    ] == ["legacy_source_size_changed"]
    catalog.close()


def test_changed_and_missing_bytes_refuse(tmp_path):
    catalog, path = build(tmp_path)
    frozen_request = request(path)
    path.write_text("different bytes", encoding="utf-8")
    assert resolve_legacy_source(catalog, frozen_request)["state"] == "unavailable"
    path.unlink()
    assert resolve_legacy_source(catalog, frozen_request)["state"] == "unavailable"
    catalog.close()


def test_truncated_legacy_key_collision_is_ambiguous(tmp_path):
    from unittest.mock import patch

    catalog, path = build(tmp_path)
    frozen_request = request(path)
    (path.parent / "other.txt").write_text(
        "different registered byte version", encoding="utf-8"
    )
    catalog.scan()
    # Force only a digest collision; both sources are actual scanned engine
    # records. A path key cannot select one of two distinct byte versions.
    with patch(
        "company_wiki.source_catalog.public_legacy_source_link.legacy_source_key",
        return_value=frozen_request["legacy_source_id"],
    ):
        assert resolve_legacy_source(catalog, frozen_request)["state"] == "ambiguous"
    catalog.close()


def test_old_absolute_key_is_only_lookup_after_migration(tmp_path):
    catalog, path = build(tmp_path)
    frozen_request = request(path)
    moved = tmp_path / "migrated"
    path.parent.rename(moved)
    config = replace(
        catalog.config, roots=(replace(catalog.config.roots[0], path=moved),)
    )
    catalog.close()
    catalog = SourceCatalog(config)
    value = resolve_legacy_source(catalog, frozen_request)
    assert value["state"] == "available", value
    assert not path.exists()
    catalog.close()


@pytest.mark.parametrize(
    "extra",
    [
        {"legacy_source_id": "../private/a.pdf"},
        {"legacy_source_id": "src_" + "a" * 16 + "\n"},
        {"expected_byte_size": True},
        {"expected_byte_size": -1},
        {"unknown": 1},
        {"evidence": {"quote": "short"}},
        {"evidence": {"quote": "a" * 20, "legacy_page_kind": "guessed"}},
        {"evidence": {"quote": "a" * 20, "physical_path": "private"}},
    ],
)
def test_malformed_input_refuses(tmp_path, extra):
    catalog, path = build(tmp_path)
    with pytest.raises(LegacyLinkError):
        resolve_legacy_source(catalog, request(path, **extra))
    catalog.close()


def test_unsupported_evidence_does_not_claim_page_replay(tmp_path):
    catalog, path = build(tmp_path)
    value = resolve_legacy_source(
        catalog,
        request(path, evidence={"quote": "A registered original has immutable bytes."}),
    )
    assert value["state"] == "available"
    assert value["evidence_validation"] == {
        "state": "unavailable",
        "reason": "native_pdf_required",
    }
    catalog.close()


def test_cli_invalid_json_and_missing_catalog_are_named(tmp_path):
    cli = [
        sys.executable,
        "-B",
        "-m",
        "company_wiki.source_catalog.public_legacy_source_link_cli",
        "--config",
        str(tmp_path / "missing.yaml"),
    ]
    # Self-contained like the sibling readiness/recovery CLI tests: the
    # subprocess resolves the package from the checkout without ambient env.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHON_DOTENV_DISABLED"] = "1"
    result = subprocess.run(
        cli,
        input=b'{"schema_version":1,"schema_version":2}',
        capture_output=True,
        timeout=10,
        env=env,
    )
    assert result.returncode == 2
    assert json.loads(result.stderr)["reason"] == "invalid_request"
    assert str(tmp_path).encode() not in result.stderr
