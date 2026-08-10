"""FC-504 RED/acceptance tests: Dropbox-only canary sample registry.

A canary sample descriptor carries NO absolute paths — only root_id +
relative_path; sample_id is the sha256 of ``root_id|relative_path``;
content_sha256 pins the bytes; expected identity/period/provider record
the intended filing.  Registration validates the descriptor, proves the
bytes are exclusive of other roots (read-only catalog check), and — when
the real root has fewer than 2 eligible filings (as FC-503's replay
proved: eligible=0) — returns ``needs_user_samples`` instead of
fabricating a sample.
"""
import hashlib
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.canary_registry import (  # noqa: E402
    canary_decision,
    exclusive_of_other_roots,
    register_canary,
    sample_id_for,
    validate_sample_descriptor,
)


def _descriptor(**overrides) -> dict:
    desc = {
        "root_id": "dropbox_stock",
        "relative_path": "金融/保险/中国平安/601318-2024年报.pdf",
        "content_sha256": "a" * 64,
        "expected_identity": "601318",
        "expected_period_end": "2024-12-31",
        "expected_provider": "cninfo",
    }
    desc.update(overrides)
    if "sample_id" not in overrides:
        desc["sample_id"] = sample_id_for(desc["root_id"], desc["relative_path"])
    return desc


def _mini_catalog(tmp_path: Path, sha: str, root_id: str = "company_raw") -> Path:
    db = tmp_path / "catalog.sqlite3"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE documents (
          document_id TEXT PRIMARY KEY, primary_source_id TEXT,
          title TEXT, source_status TEXT);
        CREATE TABLE sources (
          source_id TEXT PRIMARY KEY, content_sha256 TEXT,
          byte_size INTEGER, mime_type TEXT);
        CREATE TABLE locations (
          location_id TEXT PRIMARY KEY, root_id TEXT, relative_path TEXT,
          absolute_path TEXT, source_id TEXT, document_id TEXT,
          role TEXT, location_status TEXT);
        """
    )
    con.execute("INSERT INTO sources VALUES ('s1',?,3,'application/pdf')", (sha,))
    con.execute("INSERT INTO documents VALUES ('d1','s1','t','active')")
    con.execute(
        "INSERT INTO locations VALUES ('l1',?,'x','x','s1','d1',"
        "'original_primary','active')", (root_id,))
    con.commit()
    con.close()
    return db


# --- path safety: no absolute paths anywhere --------------------------------


def test_fc504_absolute_path_rejected():
    """A descriptor must not leak absolute paths (drive, root, or ..)."""
    for bad in (
        _descriptor(relative_path="C:/Users/x/Dropbox/Stock/a.pdf"),
        _descriptor(relative_path="/abs/Dropbox/Stock/a.pdf"),
        _descriptor(relative_path=r"..\..\outside.pdf"),
    ):
        with pytest.raises(ValueError):
            validate_sample_descriptor(bad)


def test_fc504_valid_descriptor_accepted():
    """A relative-path descriptor with a matching hashed sample_id is
    accepted, and the output carries no absolute path."""
    sample = validate_sample_descriptor(_descriptor())
    assert sample.sample_id == sample_id_for(
        sample.root_id, sample.relative_path
    )
    assert ":" not in sample.relative_path.split("/")[0]
    assert ".." not in sample.relative_path.split("/")


def test_fc504_sample_id_must_match_hash():
    """The sample_id is the sha256 of root_id|relative_path — a forged id
    is rejected."""
    desc = _descriptor(sample_id="b" * 64)
    with pytest.raises(ValueError):
        validate_sample_descriptor(desc)


def test_fc504_sample_id_formula_is_root_and_path():
    """The sample_id is exactly sha256(root_id|relative_path) — weakening
    the formula (e.g. path-only) must break the pin."""
    assert sample_id_for("dropbox_stock", "a/b.pdf") == hashlib.sha256(
        "dropbox_stock|a/b.pdf".encode("utf-8")
    ).hexdigest()
    assert sample_id_for("dropbox_stock", "a/b.pdf") != sample_id_for(
        "company_raw", "a/b.pdf"
    )


# --- exclusivity: no same content hash in other roots -----------------------


def test_fc504_exclusive_when_hash_absent_elsewhere(tmp_path):
    """A sample whose content hash has no active location in another root
    is exclusive."""
    sha = "a" * 64
    catalog = _mini_catalog(tmp_path, "b" * 64)  # other root has different hash
    assert exclusive_of_other_roots(catalog, sha, ("company_raw",))


def test_fc504_not_exclusive_when_hash_present_elsewhere(tmp_path):
    """A sample whose content hash already lives in company_raw is NOT
    exclusive — registering it would fabricate Dropbox-only proof."""
    sha = "a" * 64
    catalog = _mini_catalog(tmp_path, sha)
    assert not exclusive_of_other_roots(catalog, sha, ("company_raw",))
    with pytest.raises(ValueError):
        register_canary(_descriptor(content_sha256=sha), catalog=catalog,
                        other_root_ids=("company_raw",))


# --- decision: no existing eligible filings -> needs user samples -----------


def test_fc504_decision_needs_user_samples_when_no_eligible():
    """The real-root inventory (FC-503) reports eligible=0 — the registry
    must return needs_user_samples, never fabricate a canary."""
    report = {
        "buckets": {"eligible": 0, "needs_review": 0,
                    "unprovable": 7167, "retired_or_conflict": 0},
    }
    decision = canary_decision(report)
    assert decision == "needs_user_samples"
    # registration alone must not select anything — the decision gates it
    assert register_canary(_descriptor(), catalog=None) is not None


def test_fc504_decision_uses_eligible_candidates():
    """With >= 2 eligible candidates the registry may select them."""
    report = {
        "buckets": {"eligible": 2, "needs_review": 0,
                    "unprovable": 100, "retired_or_conflict": 0},
    }
    assert canary_decision(report) == "selectable"
