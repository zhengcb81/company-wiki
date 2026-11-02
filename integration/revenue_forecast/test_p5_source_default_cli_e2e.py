"""P5-RF CLI E2E: the PUBLIC source_preparation entry drives SourceRef v2
with NO opt-in flag, against the three real repos' current committed code
(the proven recipe of tests/test_source_ref_v2_three_repo_e2e.py, driven
through the CLI instead of the Python API).

Acceptance proof for the default migration (plan card §6):
- the CLI carries the required --company-wiki-catalog-config;
- the record path is the verified raw open (never derived bodies);
- deleting ALL derived artifacts and the derived tree does not break a
  second journey (independent of old derived state);
- a corrupted raw refuses closed; restoring the original bytes heals into
  the same identity with zero downloads.

Uses sibling checkouts by default; explicit FF_V2_CODE_ROOT/CWP_V2_CODE_ROOT
may select integration trees. Missing dependencies fail visibly, never skip.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
ROOT = RF_CODE_ROOT
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

AS_OF = "2026-09-27"
REQUEST = {
    "schema_version": "1.1",
    "company_query": "Apple Inc.",
    "market": "US",
    "document_kind": "annual_report",
    "fiscal_year": 2025,
    "as_of_date": AS_OF,
}


def _env_roots() -> tuple[Path, Path]:
    ff_root = Path(os.environ.get("FF_V2_CODE_ROOT", ROOT.parent / "filing-fetch"))
    cwp_root = Path(os.environ.get("CWP_V2_CODE_ROOT", ROOT.parent / "company-wiki"))
    for root in (ff_root, cwp_root):
        if not root.is_dir():
            raise FileNotFoundError(f"Required offline source dependency missing: {root}")
    return ff_root, cwp_root


def _build_wiki(tmp: Path, ff_root: Path, cwp_root: Path, *, missing_title: bool = False):
    """Proven three-repo fixture recipe (see test_source_ref_v2_three_repo_e2e)."""
    from e2e_support import isolated_wiki

    isolated_wiki.PRODUCTION_WIKI = cwp_root
    cwp_src = str(cwp_root / "src")
    existing = os.environ.get("PYTHONPATH", "")
    if cwp_src not in existing.split(os.pathsep):
        os.environ["PYTHONPATH"] = (
            cwp_src + os.pathsep + existing if existing else cwp_src)
    wiki = isolated_wiki.IsolatedWiki(tmp / "wiki")
    catalog_text = wiki.config_path.read_text(encoding="utf-8")
    wiki.config_path.write_text(
        catalog_text.replace(
            "    priority: 10\n",
            "    priority: 10\n    reusable_for_filing: false\n",
        )
        + "reusable_root_kinds: [directory]\n",
        encoding="utf-8",
    )
    source = wiki.seed_market("US")
    sidecar_path = source.with_name(source.name + ".source.json")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar.update(
        {
            "retrieved_at": "2026-09-27T00:00:00Z",
            "adapter_name": "p5-cli-e2e",
            "adapter_version": "1.0.0",
        }
    )
    if missing_title:
        sidecar.pop("source_title", None)
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    wiki.scan()
    return wiki, source


def _run_cli(wiki, ff_root: Path, cwp_root: Path, request: dict):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(cwp_root / "src")
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "scripts" / "source_preparation.py"),
            "--company-wiki-config",
            str(wiki.root / "company_wiki.json"),
            "--filing-fetch-root",
            str(ff_root),
            "--company-wiki-catalog-config",
            str(wiki.config_path),
        ],
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=str(ROOT),
        env=env,
        timeout=300,
        check=False,
    )



def _seed_legacy_artifacts(wiki):
    """Put actual obsolete rows/files in the isolated catalog before deleting them."""
    derived = wiki.catalog_dir / "derived"
    derived.mkdir(exist_ok=True)
    con = sqlite3.connect(wiki.catalog_dir / "catalog.sqlite3")
    try:
        document_id, source_id = con.execute("SELECT document_id, primary_source_id FROM documents LIMIT 1").fetchone()
        for role in ("normalized", "sections", "summary"):
            path = derived / f"legacy-{role}.md"
            body = b"obsolete fixture body; default raw reader must ignore this"
            path.write_bytes(body)
            con.execute(
                "INSERT INTO artifacts (artifact_id, document_id, source_id, artifact_role, path, "
                "content_sha256, byte_size, mime_type, generator_name, generator_version, status, "
                "metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"p5-legacy-{role}", document_id, source_id, role, str(path),
                 hashlib.sha256(body).hexdigest(), len(body), "text/markdown", "legacy-fixture",
                 "0.0", "completed", "{}", "2026-09-27T00:00:00Z"),
            )
        con.commit()
        assert con.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 3
    finally:
        con.close()
    assert len(list(derived.iterdir())) == 3
    return derived


def test_cli_default_v2_journey_survives_derived_deletion(tmp_path):
    """Public CLI, NO --source-reader-v2 flag: full v2 journey, then delete
    every derived artifact and the derived tree — a second journey still
    succeeds with zero downloads (raw-only verification)."""
    ff_root, cwp_root = _env_roots()
    wiki, source = _build_wiki(tmp_path, ff_root, cwp_root)
    derived = _seed_legacy_artifacts(wiki)

    proc = _run_cli(wiki, ff_root, cwp_root, REQUEST)
    assert proc.returncode == 0, f"journey failed: {proc.stderr[-800:]}"
    record = json.loads(proc.stdout)
    rr = record["reuse_receipt"]
    assert rr["artifact_read"] == [], rr
    assert rr["download_calls"] == 0
    assert rr["parser_calls"] is None and rr["llm_calls"] is None
    assert "canonical_path" not in json.dumps(record["company_wiki_trace"])

    assert derived.is_dir()
    shutil.rmtree(derived)
    assert not derived.exists()
    sqlite = wiki.catalog_dir / "catalog.sqlite3"
    if sqlite.is_file():
        con = sqlite3.connect(sqlite)
        con.execute("DELETE FROM artifacts")
        con.commit()
        con.close()

    second = _run_cli(wiki, ff_root, cwp_root, REQUEST)
    assert second.returncode == 0, f"post-delete: {second.stderr[-800:]}"
    rr2 = json.loads(second.stdout)["reuse_receipt"]
    assert rr2["download_calls"] == 0
    assert rr2["artifact_read"] == []


def test_cli_corrupted_raw_refuses_then_heals(tmp_path):
    """Corrupting the stored raw body must refuse closed (never a bad read);
    restoring the original bytes heals into the same identity, zero downloads."""
    ff_root, cwp_root = _env_roots()
    wiki, source = _build_wiki(tmp_path, ff_root, cwp_root)

    proc = _run_cli(wiki, ff_root, cwp_root, REQUEST)
    assert proc.returncode == 0, proc.stderr[-800:]
    content_sha = json.loads(proc.stdout)["capture"]["snapshot_sha256"]
    original = source.read_bytes()
    assert hashlib.sha256(original).hexdigest() == content_sha

    source.write_bytes(original + b"XX")
    bad = _run_cli(wiki, ff_root, cwp_root, REQUEST)
    assert bad.returncode != 0, "corrupted raw must never be accepted"
    # the reader refuses closed; per-location hash failures aggregate into
    # no_verified_location (failures detail never leaks byte paths)
    assert "source reader refused" in bad.stderr, bad.stderr[-400:]
    failure = json.loads(bad.stderr)
    assert bad.returncode == 3 and not bad.stdout
    assert failure["error_code"] == "upstream" and failure["source_failure_reason"] == "no_verified_location"
    assert {key: failure[key] for key in ("stage", "calls", "downloads")} == {
        "stage": "source_reader", "calls": 2, "downloads": 0}
    assert str(source) not in bad.stderr

    source.write_bytes(original)
    healed = _run_cli(wiki, ff_root, cwp_root, REQUEST)
    assert healed.returncode == 0, healed.stderr[-800:]
    healed_record = json.loads(healed.stdout)
    assert healed_record["capture"]["snapshot_sha256"] == content_sha
    assert healed_record["reuse_receipt"]["download_calls"] == 0


def test_cli_verified_missing_title_is_display_only_metadata(tmp_path):
    """A legacy catalog may lack a title even when the raw is qualified."""
    ff_root, cwp_root = _env_roots()
    wiki, source = _build_wiki(tmp_path, ff_root, cwp_root, missing_title=True)
    original = source.read_bytes()
    before_sha = hashlib.sha256(original).hexdigest()
    # The sidecar lacks a declared source title, as in real older imports.
    proc = _run_cli(wiki, ff_root, cwp_root, REQUEST)
    assert proc.returncode == 0, proc.stderr[-1000:]
    result = json.loads(proc.stdout)
    manifest = result["company_wiki_trace"]["source_manifest"]
    assert manifest["title"] is None
    assert result["title"] == f"{manifest['document_kind']} [{result['source_id']}]"
    assert result["reuse_receipt"]["download_calls"] == 0
    assert result["capture"]["snapshot_sha256"] == before_sha
    assert source.read_bytes() == original
    assert "canonical_path" not in json.dumps(result)
