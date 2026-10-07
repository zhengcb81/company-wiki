"""Exact reads bind their source, never the directory of unrelated sources."""

from dataclasses import replace
import json
import sqlite3

import pytest

from company_wiki.source_catalog import RootSpec, SourceCatalog
from company_wiki.source_catalog.source_reader import SourceReadError, SourceVersionReader
from test_source_version_reader import BODY, _fixture


def _reader(tmp_path):
    catalog, paths, roots, ids = _fixture(tmp_path)
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(ids["document_id"], ids["source_id"], ids["content_sha256"])
    return catalog, reader, ref, paths[0], roots[0]


def test_exact_pin_ignores_unrelated_roots_and_root_order(tmp_path):
    catalog, reader, ref, _, root = _reader(tmp_path)
    try:
        pin = reader.read_policy_sha256(ref)
        query_pin = reader.read_policy_sha256()
        unrelated = RootSpec("unrelated", tmp_path / "other", "directory", priority=1)
        catalog.config = replace(catalog.config, roots=(unrelated, root))
        assert reader.read_policy_sha256() != query_pin  # selection still global
        assert reader.read_policy_sha256(ref) == pin
        assert reader.open_version(ref, expected_read_policy_sha256=pin).data == BODY
        catalog.config = replace(catalog.config, roots=(root, unrelated))
        assert reader.read_policy_sha256(ref) == pin
    finally:
        catalog.close()


def test_exact_pin_survives_catalog_and_registered_root_relocation(tmp_path):
    catalog, reader, ref, path, root = _reader(tmp_path)
    pin = reader.read_policy_sha256(ref)
    config = catalog.config
    catalog.close()
    moved_catalog = tmp_path / "moved-catalog"
    config.catalog_dir.rename(moved_catalog)
    moved_root = tmp_path / "moved-companies"
    root.path.rename(moved_root)
    config = replace(config, catalog_dir=moved_catalog,
                     roots=(replace(root, path=moved_root),))
    relocated = SourceCatalog(config)
    try:
        reader = SourceVersionReader(relocated)
        assert reader.read_policy_sha256(ref) == pin
        opened = reader.open_version(ref, expected_read_policy_sha256=pin)
        assert opened.data == BODY and opened.source_read_policy_sha256 == pin
        assert not path.exists()
    finally:
        relocated.close()


@pytest.mark.parametrize("change", [
    {"priority": 11}, {"max_file_size": 4096},
    {"allowed_statuses": ("active",)}, {"allowed_document_kinds": ("annual_report",)},
    {"reusable_for_filing": False},
])
def test_exact_pin_binds_relevant_read_rules(tmp_path, change):
    catalog, reader, ref, _, root = _reader(tmp_path)
    try:
        pin = reader.read_policy_sha256(ref)
        catalog.config = replace(catalog.config, roots=(replace(root, **change),))
        assert reader.read_policy_sha256(ref) != pin
        with pytest.raises(SourceReadError, match="read_policy_mismatch"):
            reader.open_version(ref, expected_read_policy_sha256=pin)
    finally:
        catalog.close()


def test_exact_pin_does_not_replace_real_bytes_or_current_admission(tmp_path):
    catalog, reader, ref, path, root = _reader(tmp_path)
    try:
        pin = reader.read_policy_sha256(ref)
        path.write_bytes(b"X" + BODY[1:])
        assert reader.read_policy_sha256(ref) == pin
        with pytest.raises(SourceReadError, match="no_verified_location"):
            reader.open_version(ref, expected_read_policy_sha256=pin)
        path.write_bytes(BODY)
        catalog.config = replace(catalog.config, roots=(replace(root, max_file_size=1),))
        new_pin = reader.read_policy_sha256(ref)
        with pytest.raises(SourceReadError, match="root_admission_denied"):
            reader.open_version(ref, expected_read_policy_sha256=new_pin)
    finally:
        catalog.close()


def test_global_pin_compatibility_is_explicit_and_never_accepts_arbitrary_pins(tmp_path):
    catalog, reader, ref, _, _ = _reader(tmp_path)
    try:
        global_pin, exact_pin = reader.read_policy_sha256(), reader.read_policy_sha256(ref)
        assert exact_pin != global_pin
        opened = reader.open_version(ref, expected_read_policy_sha256=global_pin)
        assert opened.source_read_policy_sha256 == global_pin
        verified = reader.verify_version(ref, expected_read_policy_sha256=exact_pin)
        assert verified.source_read_policy_sha256 == exact_pin
        with pytest.raises(SourceReadError, match="read_policy_mismatch"):
            reader.open_version(ref, expected_read_policy_sha256="a" * 64)
        with pytest.raises(SourceReadError, match="invalid_read_policy_pin"):
            reader.open_version(ref, expected_read_policy_sha256="invalid")
    finally:
        catalog.close()


@pytest.mark.parametrize("field,value", [
    ("security_id", "OTHER"), ("canonical_entity_id", "ent-other"),
    ("fiscal_year", 2024), ("period_end", "2024-12-31"),
])
def test_exact_pin_binds_visible_source_identity_and_period(tmp_path, field, value):
    catalog, reader, ref, _, _ = _reader(tmp_path)
    try:
        pin = reader.read_policy_sha256(ref)
        row = catalog.reader.exact_source_version(ref.document_id)
        metadata = json.loads(row["metadata_json"])
        metadata["acquisition"][field] = value
        with sqlite3.connect(catalog.config.database_path) as connection:
            connection.execute("UPDATE documents SET metadata_json=? WHERE document_id=?",
                               (json.dumps(metadata), ref.document_id))
        assert reader.describe_version(ref)[field] == value
        assert reader.read_policy_sha256(ref) != pin
        with pytest.raises(SourceReadError, match="read_policy_mismatch"):
            reader.open_version(ref, expected_read_policy_sha256=pin)
    finally:
        catalog.close()
