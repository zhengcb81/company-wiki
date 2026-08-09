"""WU-1001 RED/audit tests: atomic SourceBundle CLI."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "resolve_bundle.py"


def _catalog(tmp_path: Path) -> Path:
    """A minimal read-only catalog with one document + one artifact."""
    import sqlite3

    path = tmp_path / "catalog.sqlite3"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE documents (document_id TEXT PRIMARY KEY, "
                "primary_source_id TEXT, published_date TEXT)")
    con.execute("CREATE TABLE sources (source_id TEXT PRIMARY KEY, "
                "content_sha256 TEXT)")
    con.execute("CREATE TABLE artifacts (artifact_id TEXT, document_id TEXT, "
                "artifact_role TEXT, source_id TEXT, path TEXT, content_sha256 "
                "TEXT, byte_size INTEGER, mime_type TEXT, generator_name TEXT, "
                "generator_version TEXT, status TEXT, error TEXT, "
                "schema_version TEXT, source_sha256 TEXT, created_at TEXT)")
    con.execute("INSERT INTO documents VALUES ('d1', 's1', '2026-04-15')")
    con.execute("INSERT INTO sources VALUES ('s1', 'c' * 64)")
    con.execute("INSERT INTO artifacts VALUES "
                "('a1','d1','normalized','s1','/tmp/n.md','n' * 64,10,'text/markdown',"
                "'producer','1.0','completed',NULL,'2.0','c' * 64,'2026-01-01')")
    con.commit()
    con.close()
    return path


def test_cli_outputs_bundle_json(tmp_path):
    catalog = _catalog(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(CLI), "--document-id", "d1",
         "--catalog", str(catalog)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["source"]["document_id"] == "d1"
    assert "catalog_snapshot" in payload
    assert proc.stderr == ""  # diagnostics never pollute stdout


def test_cli_not_found_exit_1(tmp_path):
    catalog = _catalog(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(CLI), "--document-id", "nope",
         "--catalog", str(catalog)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert proc.returncode == 1
    error = json.loads(proc.stderr)
    assert error["error_code"] == 1


def test_cli_missing_catalog_exit_5(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(CLI), "--document-id", "d1",
         "--catalog", str(tmp_path / "none.sqlite3")],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert proc.returncode == 5


def test_cli_readonly_no_writes(tmp_path):
    catalog = _catalog(tmp_path)
    before = catalog.stat().st_mtime_ns
    subprocess.run(
        [sys.executable, str(CLI), "--document-id", "d1",
         "--catalog", str(catalog)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert catalog.stat().st_mtime_ns == before  # read-only guarantee
