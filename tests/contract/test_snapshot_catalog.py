"""WU-0.2: production catalog snapshot generator contract tests.

``scripts/snapshot_catalog.py --read-only --catalog <db> --max-samples N``
must export from the production catalog ONLY:

- anonymized schema (table names + columns, no data);
- root policy (root_id/kind/priority, paths replaced by root_id);
- candidate status distributions (document/location counts by status);
- at most N de-path'd sample rows (no absolute paths, no personal paths).

Hard requirements:

1. deterministic output — same snapshot twice hashes identical;
2. field anonymization — no absolute paths or user-visible directories
   in the exported JSON;
3. row cap — samples never exceed --max-samples;
4. read-only connection — catalog bytes unchanged, no WAL/SHM side files;
5. busy timeout — the connection must set a non-trivial busy_timeout so a
   locked production catalog fails with a timeout error instead of hanging;
6. replayable in CI without the three real root dirs.

RED phase: the script does not exist, so subprocess calls fail with
FileNotFoundError (recorded as ERROR).  Mutation: replacing mode=ro with
mode=rw, removing the busy_timeout, or emitting raw absolute paths must
each flip the corresponding test red.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
import unittest

WIKI_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = WIKI_ROOT / "scripts" / "snapshot_catalog.py"

# Paths that must never appear in exported content (anonymization check).
# NOTE: "company-wiki" intentionally excluded — it legitimately appears in
# document_id URN namespaces (urn:company-wiki:document:sha256:...) which are
# logical identifiers, not paths.
FORBIDDEN_SUBSTRINGS = [
    "Users",
    "Dropbox",
    "dayu-agent",
    ".source_catalog",
    "C:/",
    "C:\\",
]


def _make_catalog(root: Path) -> Path:
    db = root / "catalog.sqlite3"
    con = sqlite3.connect(db)
    con.execute("PRAGMA user_version = 7")
    con.executescript(
        """
        CREATE TABLE roots (
            root_id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL,
            priority INTEGER NOT NULL, last_scan_run TEXT, last_scanned_at TEXT
        );
        CREATE TABLE scan_runs (
            run_id TEXT PRIMARY KEY, started_at TEXT, completed_at TEXT,
            status TEXT NOT NULL, report_json TEXT
        );
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT,
            source_type TEXT, document_kind TEXT, published_date TEXT,
            source_status TEXT NOT NULL, metadata_priority INTEGER NOT NULL,
            metadata_json TEXT NOT NULL, text_fingerprint TEXT,
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
        );
        CREATE TABLE locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL,
            source_id TEXT, document_id TEXT, role TEXT NOT NULL,
            location_status TEXT NOT NULL, observed_size INTEGER,
            observed_mtime_ns INTEGER, last_seen_run TEXT NOT NULL,
            manifest_json TEXT, metadata_json TEXT NOT NULL, error TEXT
        );
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL UNIQUE,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL,
            first_seen_at TEXT NOT NULL
        );
        """
    )
    con.executemany(
        "INSERT INTO roots VALUES (?,?,?,?,NULL,NULL)",
        [
            ("company_raw", "C:/Users/jane/company-wiki/companies", "company_raw", 10),
            ("dayu_portfolio", "C:/Users/jane/dayu-agent/workspace/portfolio", "dayu_portfolio", 20),
            ("dropbox_stock", "C:/Users/jane/Dropbox/Stock", "directory", 30),
        ],
    )
    con.execute(
        "INSERT INTO scan_runs VALUES ('scan-x','2026-08-08T13:44:53Z','2026-08-08T13:47:06Z','completed_with_errors','{}')"
    )
    con.executemany(
        "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("d1", "s1", "annual 2025", "filing", "annual_report", "2025-04-30", "active", 1, "{}", None, "2025-05-01T00:00:00Z", "2026-08-08T13:44:53Z"),
            ("d2", "s2", "quarterly Q1", "filing", "quarterly_report", "2025-05-15", "retired", 1, "{}", None, "2025-05-16T00:00:00Z", "2026-08-08T13:44:53Z"),
            ("d3", "s3", "rejected filing", "filing", "regulatory_filing", "2025-06-01", "upstream_rejected", 1, "{}", None, "2025-06-02T00:00:00Z", "2026-08-08T13:44:53Z"),
        ],
    )
    con.executemany(
        "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("l1", "company_raw", "ACME/2025-04-30_annual.pdf", "C:/Users/jane/company-wiki/companies/ACME/2025-04-30_annual.pdf", "s1", "d1", "original_primary", "active", 1000, 1, "scan-x", None, "{}", None),
            ("l2", "dropbox_stock", "ACME/2025-04-30_annual.pdf", "C:/Users/jane/Dropbox/Stock/ACME/2025-04-30_annual.pdf", "s1", "d1", "original_primary", "active", 1000, 2, "scan-x", None, "{}", None),
            ("l3", "dayu_portfolio", "filings/.rejections/x.pdf", "C:/Users/jane/dayu-agent/workspace/portfolio/filings/.rejections/x.pdf", "s3", "d3", "original_primary", "active", 500, 3, "scan-x", None, "{}", None),
        ],
    )
    con.executemany(
        "INSERT INTO sources VALUES (?,?,?,?,?)",
        [
            ("s1", "a" * 64, 1000, "application/pdf", "2025-05-01T00:00:00Z"),
            ("s2", "b" * 64, 800, "application/pdf", "2025-05-16T00:00:00Z"),
            ("s3", "c" * 64, 500, "application/pdf", "2025-06-02T00:00:00Z"),
        ],
    )
    con.commit()
    con.close()
    return db


def _run(*args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


class SnapshotCatalogTests(unittest.TestCase):
    def test_requires_readonly_flag(self) -> None:
        proc = _run("--catalog", "x.sqlite3")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("read-only", (proc.stdout + proc.stderr).lower())

    def test_deterministic_output(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            catalog = _make_catalog(Path(td))
            p1 = _run("--read-only", "--catalog", str(catalog), "--max-samples", "10")
            p2 = _run("--read-only", "--catalog", str(catalog), "--max-samples", "10")
            self.assertEqual(p1.returncode, 0, p1.stderr)
            self.assertEqual(p1.stdout, p2.stdout, "snapshot output not deterministic")
            h1 = hashlib.sha256(p1.stdout.encode("utf-8")).hexdigest()
            h2 = hashlib.sha256(p2.stdout.encode("utf-8")).hexdigest()
            self.assertEqual(h1, h2, "snapshot hash not stable across runs")

    def test_schema_and_root_policy_anonymized(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            catalog = _make_catalog(Path(td))
            proc = _run("--read-only", "--catalog", str(catalog), "--max-samples", "10")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertIn("schema", data)
            self.assertIn("root_policy", data)
            self.assertIn("status_distributions", data)
            self.assertIn("samples", data)
            # root policy entries carry root_id/kind/priority but no raw path
            for entry in data["root_policy"]:
                self.assertIn("root_id", entry)
                self.assertNotIn("path", entry)
            blob = json.dumps(data, ensure_ascii=False)
            for forbidden in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(forbidden, blob, f"forbidden substring leaked: {forbidden}")

    def test_sample_row_cap_and_depath(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            catalog = _make_catalog(Path(td))
            proc = _run("--read-only", "--catalog", str(catalog), "--max-samples", "2")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertLessEqual(len(data["samples"]), 2, "sample cap violated")
            blob = json.dumps(data, ensure_ascii=False)
            for forbidden in FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(forbidden, blob, f"de-path failure: {forbidden}")

    def test_status_distributions_present(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            catalog = _make_catalog(Path(td))
            proc = _run("--read-only", "--catalog", str(catalog), "--max-samples", "10")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            dist = data["status_distributions"]
            self.assertIn("documents_by_status", dist)
            self.assertIn("locations_by_status", dist)
            self.assertEqual(dist["documents_by_status"].get("active"), 1)
            self.assertEqual(dist["documents_by_status"].get("retired"), 1)
            self.assertEqual(dist["documents_by_status"].get("upstream_rejected"), 1)
            self.assertEqual(dist["locations_by_status"].get("active"), 3)

    def test_catalog_readonly_and_no_side_files(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            catalog = _make_catalog(Path(td))
            before = catalog.read_bytes()
            proc = _run("--read-only", "--catalog", str(catalog), "--max-samples", "10")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(catalog.read_bytes(), before, "catalog modified")
            for side in (catalog.parent / f"{catalog.name}-wal", catalog.parent / f"{catalog.name}-shm"):
                self.assertFalse(side.exists(), f"side file created: {side}")

    def test_open_readonly_rejects_writes(self) -> None:
        """Unit-level: the read-only opener must reject writes even before any
        tool code decides to be careful — a mode=rw mutation must flip this
        test red."""
        import tempfile

        sys.path.insert(0, str(WIKI_ROOT / "scripts"))
        from snapshot_catalog import _open_readonly  # noqa: E402

        with tempfile.TemporaryDirectory() as td:
            catalog = _make_catalog(Path(td))
            con = _open_readonly(catalog)
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    con.execute("CREATE TABLE evil (x TEXT)")
            finally:
                con.close()

    def test_busy_timeout_set(self) -> None:
        """The connection must set a non-zero busy_timeout so a locked
        production catalog fails with a timeout instead of hanging forever."""
        script_text = SCRIPT.read_text(encoding="utf-8") if SCRIPT.is_file() else ""
        if not script_text:
            self.fail("snapshot_catalog.py missing (RED)")
        self.assertIn("busy_timeout", script_text, "busy_timeout not set")
        # busy_timeout must be applied BEFORE any query on the connection
        timeout_pos = script_text.find("busy_timeout")
        first_query_pos = script_text.find("SELECT")
        self.assertNotEqual(timeout_pos, -1)
        self.assertTrue(
            timeout_pos < first_query_pos,
            "busy_timeout must be set before the first query",
        )


if __name__ == "__main__":
    unittest.main()
