"""Offline fixture: the investigation config must scope RAW-DUP to company_raw.

Proves, without touching the live catalog, that a config listing only
``company_raw`` (a) never registers an outside root in the scan scope and
(b) never hashes a file under an unconfigured root, and that this lane's
``internal_groups`` filter drops mixed/outside groups instead of counting them
as internal savings.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
import sys


from g3_source_facts.raw_space import internal_groups

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from raw_duplicate_audit.assessment import run_assessment  # noqa: E402

CONTENT = b"G3-RAW-DUP-FIXTURE-CONTENT-" + b"x" * 2000
SHA = hashlib.sha256(CONTENT).hexdigest()


def _make_catalog(catalog_dir: Path, rows: list[dict]) -> Path:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    db = catalog_dir / "catalog.sqlite3"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL,
            first_seen_at TEXT NOT NULL);
        CREATE TABLE locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL,
            source_id TEXT, document_id TEXT, role TEXT,
            location_status TEXT NOT NULL, observed_size INTEGER,
            observed_mtime_ns INTEGER, last_seen_run TEXT,
            manifest_json TEXT, metadata_json TEXT, error TEXT);
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT,
            title TEXT, source_type TEXT, document_kind TEXT,
            published_date TEXT, source_status TEXT, metadata_priority INTEGER,
            metadata_json TEXT, first_seen_at TEXT, last_seen_at TEXT);
        INSERT INTO catalog_meta VALUES ('schema_version', '1.2.0');
        """
    )
    con.execute(
        "INSERT INTO sources VALUES (?, ?, ?, ?, ?)",
        (
            "urn:company-wiki:source:sha256:" + SHA,
            SHA,
            len(CONTENT),
            "application/pdf",
            "2026-01-01T00:00:00Z",
        ),
    )
    for row in rows:
        con.execute(
            "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row["location_id"],
                row["root_id"],
                row["relative_path"],
                row["absolute_path"],
                "urn:company-wiki:source:sha256:" + SHA,
                None,
                "original_primary",
                "active",
                len(CONTENT),
                1_700_000_000_000_000_000,
                None,
                None,
                None,
                None,
            ),
        )
    con.commit()
    con.close()
    return db


def _write(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(CONTENT)
    return path


def test_config_scopes_the_scan_to_company_raw_and_never_hashes_an_outside_root(
    tmp_path: Path,
):
    live = tmp_path / "live"
    internal_a = _write(live / "companies" / "acme" / "raw" / "a.pdf")
    internal_b = _write(live / "companies" / "acme" / "raw" / "b.pdf")
    outside = _write(tmp_path / "outside" / "portfolio" / "c.pdf")

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    catalog_dir = tmp_path / "catalog"
    config_path = config_dir / "source_catalog.yaml"
    config_path.write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                f'catalog_dir: "{catalog_dir.as_posix()}"',
                "reusable_root_kinds: [company_raw]",
                "roots:",
                "  - root_id: company_raw",
                "    kind: company_raw",
                f'    path: "{(live / "companies").as_posix()}"',
                "    priority: 10",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _make_catalog(
        catalog_dir,
        [
            {
                "location_id": "urn:company-wiki:location:sha256:" + "a" * 64,
                "root_id": "company_raw",
                "relative_path": "acme/raw/a.pdf",
                "absolute_path": internal_a.as_posix(),
            },
            {
                "location_id": "urn:company-wiki:location:sha256:" + "b" * 64,
                "root_id": "company_raw",
                "relative_path": "acme/raw/b.pdf",
                "absolute_path": internal_b.as_posix(),
            },
            {
                "location_id": "urn:company-wiki:location:sha256:" + "c" * 64,
                "root_id": "dayu_portfolio",
                "relative_path": "portfolio/c.pdf",
                "absolute_path": outside.as_posix(),
            },
        ],
    )

    output = tmp_path / "out" / "report.json"
    report = run_assessment(
        config_path=config_path,
        output_path=output,
        mode="verify",
        project_root=live,
        max_groups=20,
        max_read_bytes=268435456,
        deadline_seconds=60.0,
        max_detail_rows=100,
        overwrite=True,
    )

    assert report["status"] in {"succeeded", "partial"}, report.get("error_code")
    assert [root["root_id"] for root in report["scan_scope"]["roots"]] == [
        "company_raw"
    ]
    assert report["scan_scope"]["filesystem_sweep"] is False
    # exactly the two configured files were hashed; the outside root never was
    assert report["read_bytes"] == 2 * len(CONTENT), report["read_bytes"]

    groups = report["duplicate_groups"]
    assert groups, "the identical internal pair must form a candidate group"
    mixed = [
        group
        for group in groups
        if any(locator["root_id"] != "company_raw" for locator in group["locators"])
    ]
    assert mixed, "expected the mixed group to carry the outside reference"

    # this lane's filter never turns that mixed group into an internal saving
    assert internal_groups(report) == []
    assert outside.exists() and outside.read_bytes() == CONTENT
