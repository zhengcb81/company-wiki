"""F-B10R2-MISSINGFILE (normalize side): one bad row must not abort the whole run.

Behaviour-level evidence for the same fix lives in
`assurance/runs/2026-09-11_r4-phase-b/evidence/barfix_normalize_probe.py`: it seeds a bad row
(its bytes replaced after the scan) plus a HEALTHY row behind it, and shows pre-fix (a temp
copy with the handler guard reverted) `escaped=true` at `normalizer.py:1859` with the healthy
row starved, post-fix `escaped=false` with the healthy row normalized.  These tests are the
pytest-level regressions for three of the four guards:

* the per-document read of the document's locations,
* the derived-artifact write,
* the handler's empty-parse ingest (`_ingest_without_raising` never raises).

The fourth guard (the record transaction) is covered by the same shape and by the probe; it is
not fault-injected here because `store.transaction` is also used by the harness itself, so a
targeted injection would be ambiguous about WHICH call it broke.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


from company_wiki.source_catalog import normalizer as normalizer_module
from company_wiki.source_catalog.config import CatalogConfig
from company_wiki.source_catalog.models import RootSpec
from company_wiki.source_catalog.normalizer import _ingest_without_raising, normalize_catalog
from company_wiki.source_catalog.store import CatalogStore
from company_wiki.source_contract.source_manifest import source_id_for_sha256

ROOT = "urn:company-wiki:root:sha256:" + "r" * 64
BAD_BODY = b"# Bad\n\nreplaced after the scan\n"
BAD_REPLACEMENT = b"# Bad\n\nREPLACED BYTES\n"
GOOD_BODY = b"# Good\n\nGood body text\n"
THIRD_BODY = b"# Third\n\nThird body text\n"
DOC_A = "urn:company-wiki:document:sha256:" + "a" * 64
DOC_B = "urn:company-wiki:document:sha256:" + "b" * 64
DOC_C = "urn:company-wiki:document:sha256:" + "c" * 64


def _insert(connection, table: str, values: dict) -> None:
    have = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    use = {key: value for key, value in values.items() if key in have}
    connection.execute(
        f"INSERT INTO {table} ({','.join(use)}) VALUES ({','.join('?' * len(use))})",
        tuple(use.values()),
    )


def _seed(tmp: Path) -> tuple[CatalogConfig, CatalogStore, Path]:
    """Three documents, in queue order: `aaa` (bad), `bbb` (healthy), `ccc` (healthy).

    The THIRD row exists so a guard can be fault-injected in the MIDDLE row: a test that
    injects into the first row cannot reach the write path at all (that row fails earlier),
    which is exactly how the first version of these tests managed to prove nothing.
    """
    raw = tmp / "raw" / "reports"
    raw.mkdir(parents=True, exist_ok=True)
    bad_path = raw / "a_bad.md"
    good_path = raw / "b_good.md"
    third_path = raw / "c_third.md"
    bad_path.write_bytes(BAD_BODY)
    good_path.write_bytes(GOOD_BODY)
    third_path.write_bytes(THIRD_BODY)
    config = CatalogConfig(
        project_root=tmp, catalog_dir=tmp / "catalog",
        roots=(RootSpec(root_id=ROOT, path=tmp / "raw", kind="company_raw", priority=1),),
    )
    store = CatalogStore(tmp / "catalog.sqlite3")
    now = "2026-01-01T00:00:00Z"
    with store.transaction() as connection:
        _insert(connection, "roots", {"root_id": ROOT, "path": str(tmp / "raw"),
                                      "kind": "company_raw", "priority": 1})
        for letter, body, path, relative in (
            ("a", BAD_BODY, bad_path, "reports/a_bad.md"),
            ("b", GOOD_BODY, good_path, "reports/b_good.md"),
            ("c", THIRD_BODY, third_path, "reports/c_third.md"),
        ):
            sha = hashlib.sha256(body).hexdigest()
            source_id = source_id_for_sha256(sha)
            document_id = "urn:company-wiki:document:sha256:" + letter * 64
            _insert(connection, "sources", {
                "source_id": source_id, "content_sha256": sha, "byte_size": len(body),
                "mime_type": "text/markdown", "relative_path": relative, "root_id": ROOT,
                "source_type": "regulatory_filing", "source_status": "active",
                "first_seen_at": now, "last_seen_at": now})
            _insert(connection, "documents", {
                "document_id": document_id, "primary_source_id": source_id,
                "title": Path(relative).stem, "source_type": "regulatory_filing",
                "document_kind": "annual_report", "published_date": "2026-06-18",
                "source_status": "active", "metadata_priority": 1, "metadata_json": "{}",
                "first_seen_at": now, "last_seen_at": now})
            _insert(connection, "locations", {
                "location_id": f"loc-{letter}", "root_id": ROOT, "relative_path": relative,
                "absolute_path": str(path), "source_id": source_id,
                "document_id": document_id, "role": "original_primary",
                "location_status": "active", "last_seen_run": "run-1",
                "manifest_json": json.dumps({
                    "schema_version": "1.0.0", "source_id": source_id,
                    "entity_ids": ["probe-issuer"], "original_path": relative,
                    "content_sha256": sha, "source_type": "regulatory_filing",
                    "published_date": "2026-06-18", "retrieved_at": "2026-06-18T00:00:00Z",
                    "collector_name": "probe", "collector_version": "1.0.0",
                    "mime_type": "text/markdown", "byte_size": len(body),
                    "immutable_status": "verified"}),
                "metadata_json": "{}"})
    # the bad row's bytes change AFTER the scan: it still exists, so the R1 guard passes
    bad_path.write_bytes(BAD_REPLACEMENT)
    return config, store, good_path


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _good_sha() -> str:
    return _sha(GOOD_BODY)


def _third_sha() -> str:
    return _sha(THIRD_BODY)


def test_the_handler_ingest_helper_never_raises(tmp_path: Path) -> None:
    """A manifest that no longer matches the bytes returns a NAMED problem, not an exception."""
    config, store, _ = _seed(tmp_path)
    locations = store.fetchall(
        "SELECT l.*,r.path AS root_path FROM locations l JOIN roots r ON r.root_id=l.root_id "
        "WHERE l.relative_path LIKE '%a_bad%'")
    manifest_payload = json.loads(locations[0]["manifest_json"])
    from company_wiki.source_contract.source_manifest import SourceManifest

    bundle, problem = _ingest_without_raising(
        locations[0]["root_path"], SourceManifest.from_dict(manifest_payload))
    assert bundle is None
    assert problem == "ingest_failed:SourceManifestMismatchError", problem


def test_a_bad_row_does_not_starve_the_healthy_row_behind_it(tmp_path: Path) -> None:
    config, store, _ = _seed(tmp_path)
    report = normalize_catalog(config, store, force=True, retry_limit=3)
    # the bad row is a per-document failure with BOTH reasons visible
    reasons = dict(report.terminal_reasons or {})
    assert reasons.get("SourceManifestMismatchError") == 1, reasons
    assert reasons.get("ingest_failed:SourceManifestMismatchError") == 1, reasons
    # and BOTH healthy rows behind it were normalized
    produced = sorted(path.parent.name for path in config.catalog_dir.rglob("normalized.md"))
    assert produced == sorted([_good_sha(), _third_sha()]), produced


def test_a_failing_locations_read_is_a_per_document_failure(tmp_path: Path, monkeypatch) -> None:
    """Fault injection: the per-document read raises for the BAD document only."""
    config, store, _ = _seed(tmp_path)
    real_fetchall = store.fetchall
    bad_document = "urn:company-wiki:document:sha256:" + "a" * 64

    def flaky(sql, params=()):
        if params and params[0] == bad_document:
            raise sqlite3.OperationalError("database is locked (injected)")
        return real_fetchall(sql, params)

    monkeypatch.setattr(store, "fetchall", flaky)
    report = normalize_catalog(config, store, force=True, retry_limit=3)
    reasons = dict(report.terminal_reasons or {})
    assert reasons.get("locations_read_failed:OperationalError") == 1, reasons
    produced = sorted(path.parent.name for path in config.catalog_dir.rglob("normalized.md"))
    assert produced == sorted([_good_sha(), _third_sha()]), produced


def test_an_unwritable_artifact_is_a_per_document_failure(tmp_path: Path, monkeypatch) -> None:
    """Fault injection in the MIDDLE row: the write fails, the loop continues.

    Injected on document `bbb` (not `aaa`), because the bad first row never reaches the write
    path at all - injecting there would assert nothing.
    """
    config, store, _ = _seed(tmp_path)
    real_atomic_write = normalizer_module._atomic_write
    seen: list[str] = []

    def flaky_atomic_write(path: Path, content: str) -> None:
        seen.append(str(path))
        if _good_sha() in str(path):
            raise OSError("no space left on device (injected)")
        real_atomic_write(path, content)

    monkeypatch.setattr(normalizer_module, "_atomic_write", flaky_atomic_write)
    report = normalize_catalog(config, store, force=True, retry_limit=3)
    assert seen, "the write was never attempted"
    reasons = dict(report.terminal_reasons or {})
    assert reasons.get("artifact_write_failed:OSError") == 1, reasons
    # the row AFTER the unwritable one still made it through
    produced = sorted(path.parent.name for path in config.catalog_dir.rglob("normalized.md"))
    assert produced == [_third_sha()], produced
    assert report.completed == 1, report.to_dict()
