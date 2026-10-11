"""Short integration for the W06 root-portability harness (phase B).

Every test talks to the REAL SourceCatalog / SourceVersionReader with a real
temporary catalog and real bytes — no mocked buffers.  The consumer spy runs
as a fresh subprocess and records direct file access.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.source_root_portability.fixture_builder import (  # noqa: E402
    build_fixture,
    nfc,
    sha256_bytes,
    write_config,
)
from tools.source_root_portability.report import assert_worktree_binding  # noqa: E402
from tools.source_root_portability.scenarios import (  # noqa: E402
    Harness,
    scenario_s1,
    scenario_s2,
    scenario_s5,
    scenario_s7,
)


@pytest.fixture
def workspace(tmp_path):
    owned = tmp_path / "owned"
    attempt = tmp_path / "attempt"
    attempt.mkdir(parents=True, exist_ok=True)
    lake = build_fixture(owned)
    harness = Harness(owned, attempt, lake)
    harness.open_catalog(lake.config_path)
    try:
        yield harness, lake
    finally:
        harness.close_catalog()


def _register_all(harness: Harness) -> None:
    for root_id in ("local_company", "external_dayu", "external_dropbox"):
        paths = {
            doc.relative_path for doc in harness.fixture.docs.values()
            if doc.root_id == root_id
        }
        harness.register(root_id, paths)


def test_bound_to_worktree_code():
    assert_worktree_binding(_ROOT)


def test_register_query_open_keeps_exact_bytes_and_facts(workspace):
    harness, lake = workspace
    _register_all(harness)
    for doc in lake.docs.values():
        ref = harness.ref_for(doc)
        read = harness.verified_read(ref, doc)
        assert read["read_sha256"] == doc.content_sha256
        assert read["verification"]["byte_hash_match"] is True
        assert read["byte_size"] == doc.byte_size
        facts = harness.facts(ref, doc)
        assert facts["document_kind"] == doc.document_kind
        assert facts["published_date"] == doc.published_date
        assert facts["fiscal_year"] == doc.fiscal_year
        assert facts["period_end"] == doc.period_end


def test_scenario_s1_export_bundle_is_pathless(workspace):
    harness, lake = workspace
    record = scenario_s1(harness)
    assert record["status"] == "PASS", record.get("failure")
    export = record["evidence"]["export"]
    assert export["exit_code"] == 0
    assert export["path_fields_present"] is False
    assert record["evidence"]["api_surface"]["open_verified_exists"] is False


def test_root_move_with_config_remap_keeps_old_refs(workspace, tmp_path):
    harness, lake = workspace
    _register_all(harness)
    doc = lake.docs["txt"]
    ref = harness.ref_for(doc)
    before_policy = harness.policy_observation([ref])
    lake_b = harness.owned_root / "lake_B"
    lake_b.mkdir(parents=True, exist_ok=True)
    moved = {}
    for root_id, root_dir in lake.root_dirs.items():
        target = lake_b / root_dir.name
        shutil.move(str(root_dir), str(target))
        moved[root_id] = target
    new_config = harness.owned_root / "cfg" / "config_lake_B.yaml"
    write_config(new_config, root_paths=moved, catalog_dir=lake.catalog_dir)
    lake.root_dirs = moved
    lake.lake_root = lake_b
    harness.open_catalog(new_config)
    after_policy = harness.policy_observation([ref])
    read = harness.verified_read(ref, doc)
    assert read["read_sha256"] == doc.content_sha256
    assert read["verification"]["byte_hash_match"] is True
    assert isinstance(before_policy, str) and isinstance(after_policy, str)


def test_scenario_s2_replays_root_move(workspace):
    harness, lake = workspace
    _register_all(harness)
    record = scenario_s2(harness)
    assert record["status"] == "PASS", record.get("failure")
    observation = record["evidence"]["policy_observation"]
    assert observation["change_observed"] == (
        observation["before_policy_sha256"] != observation["after_policy_sha256"]
    )
    for read in record["evidence"]["reads_after_move"]:
        assert read["verification"]["byte_hash_match"] is True
        assert read["resolution"] == "current_root"


def test_corruption_refusal_and_recovery(workspace):
    harness, lake = workspace
    _register_all(harness)
    record = scenario_s5(harness)
    evidence = record["evidence"]
    assert evidence["raw_unavailable"]["bytes_claimed_verified"] is False
    assert evidence["raw_unavailable"]["receipt_issued"] is False
    assert evidence["corruption"]["refused"] is True
    assert evidence["corruption"]["reason"] in {
        "content_sha256_mismatch", "byte_size_mismatch", "changed_during_read",
    }
    assert evidence["new_version"]["distinct"] is True
    assert evidence["new_version"]["old_ref_after_new_content"]["status"] != "ok"
    assert record["status"] == "PASS", record.get("failure")


def test_duplicate_copies_are_one_logical_source(workspace):
    harness, lake = workspace
    _register_all(harness)
    doc = lake.docs["txt"]
    ref = harness.ref_for(doc)
    summary = harness.duplicate_summary(ref)
    assert summary["logical_source_count"] == 1
    assert summary["physical_copy_count"] == 2
    assert {copy["root_id"] for copy in summary["copies"]} == {
        "external_dayu", "external_dropbox",
    }
    assert summary["copies"][0]["candidate_rank"] == 1
    victim = lake.root_dirs[summary["copies"][0]["root_id"]] / doc.relative_path
    backup = victim.read_bytes()
    victim.unlink()
    try:
        read = harness.verified_read(ref, doc)
        assert read["read_sha256"] == doc.content_sha256
    finally:
        victim.write_bytes(backup)


def test_consumer_spy_is_pathless_and_fresh_process(workspace):
    harness, lake = workspace
    _register_all(harness)
    doc = lake.docs["txt"]
    ref = harness.ref_for(doc)
    probe = harness.consumer_probe(ref, "probe_txt")
    assert probe["exit_code"] == 0
    assert probe["pid"] not in (None, __import__("os").getpid())
    result = probe["probe"]
    assert result["read_sha256"] == doc.content_sha256
    assert result["raw_non_reader_opens"] == 0
    assert result["bytes_origin"] == "fresh_read"
    raw_entries = [
        entry for entry in result["open_log"] if entry["path_class"] == "raw"
    ]
    assert raw_entries, "expected the official reader to touch the raw original"
    assert all(entry["attributed_to"] == "company_wiki" for entry in raw_entries)


def test_scenario_s7_fresh_process_replay(workspace):
    harness, lake = workspace
    _register_all(harness)
    record = scenario_s7(harness)
    assert record["status"] == "PASS", record.get("failure")
    consumer = record["evidence"]["consumer_process"]
    assert consumer["distinct_from_runner"] is True
    assert consumer["reopen"]["bytes_origin"] == "fresh_read"
    assert consumer["reopen"]["read_sha256"] == lake.docs["txt"].content_sha256


def test_fixture_builder_hash_contract():
    docs = build_fixture.__globals__["fixture_docs"]()
    for doc in docs.values():
        assert doc.content_sha256 == hashlib.sha256(doc.body).hexdigest()
        assert doc.byte_size == len(doc.body)
    assert docs["txt"].content_sha256 == docs["txt_copy"].content_sha256
    assert nfc("年报 文件") == "年报 文件"


def test_cleanup_keeps_sentinels_and_only_removes_generated_paths(tmp_path):
    from tools.source_root_portability import run as run_module

    owned = tmp_path / "owned"
    owned.mkdir()
    sentinel = owned / "keep me.txt"
    sentinel.write_text("sentinel-bytes", encoding="utf-8")
    baseline = run_module.snapshot_baseline(owned)
    assert baseline["exists"] is True
    assert baseline["sentinels"] == [
        {"path_ref": "keep me.txt",
         "sha256": __import__("hashlib").sha256(b"sentinel-bytes").hexdigest()},
    ]
    build_fixture(owned)
    restored, raw_unchanged = run_module.cleanup_owned_root(owned, baseline)
    assert restored is True
    assert raw_unchanged is True
    assert sentinel.is_file()
    assert sentinel.read_text(encoding="utf-8") == "sentinel-bytes"
    assert not (owned / "lake_A").exists()
    assert not (owned / "catalog").exists()
    assert [item.name for item in owned.iterdir()] == ["keep me.txt"]
