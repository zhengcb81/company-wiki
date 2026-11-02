"""Real FF -> CWP -> RF reuse against a temporary catalog and verified PDF.

Set FF_V2_CODE_ROOT and CWP_V2_CODE_ROOT to the isolated checkouts. The test
never authorizes a download or writes into either source repository.
"""

from __future__ import annotations

from datetime import date
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest


from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
RF_ROOT = RF_CODE_ROOT
sys.path.insert(0, str(RF_ROOT / "scripts"))

import source_preparation as preparation  # noqa: E402
from revenue_core import validate_sources  # noqa: E402


def test_verified_source_reuses_without_review_through_all_three_repositories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    ff_root_text = os.environ.get("FF_V2_CODE_ROOT")
    cwp_root_text = os.environ.get("CWP_V2_CODE_ROOT")
    if not ff_root_text or not cwp_root_text:
        pytest.skip("set FF_V2_CODE_ROOT and CWP_V2_CODE_ROOT")
    ff_root = Path(ff_root_text).resolve(strict=True)
    cwp_root = Path(cwp_root_text).resolve(strict=True)
    cwp_src = cwp_root / "src"
    assert (ff_root / "scripts" / "fetch_filing.py").is_file()
    assert (cwp_src / "company_wiki" / "source_catalog" / "source_reader_cli.py").is_file()
    monkeypatch.syspath_prepend(str(ff_root / "tests"))
    monkeypatch.syspath_prepend(str(cwp_src))
    monkeypatch.setenv(
        "PYTHONPATH", str(cwp_src) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    )
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    from e2e_support import isolated_wiki  # noqa: E402
    from company_wiki.source_catalog import SourceCatalog  # noqa: E402
    from company_wiki.source_catalog.config import load_catalog_config  # noqa: E402

    # The shared FF fixture copies a worker config, so point that read-only
    # dependency at the isolated CWP checkout rather than the production wiki.
    monkeypatch.setattr(isolated_wiki, "PRODUCTION_WIKI", cwp_root)
    wiki = isolated_wiki.IsolatedWiki(tmp_path / "wiki")
    # These legacy root reuse labels are storage hints, not a veto on an
    # already configured source whose business capture passes the v2 gates.
    catalog_text = wiki.config_path.read_text(encoding="utf-8")
    assert "    priority: 10\n" in catalog_text
    wiki.config_path.write_text(
        catalog_text.replace(
            "    priority: 10\n",
            "    priority: 10\n    reusable_for_filing: false\n",
        ) + "reusable_root_kinds: [directory]\n",
        encoding="utf-8",
    )
    source = wiki.seed_market("US")
    # Freeze the catalog observation on the same test timeline as the request;
    # otherwise a real scanner timestamp makes this fixture expire over time.
    sidecar_path = source.with_name(source.name + ".source.json")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar.update({
        "retrieved_at": "2026-09-27T00:00:00Z",
        "adapter_name": "three-repo-e2e",
        "adapter_version": "1.0.0",
    })
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    source_bytes = source.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    wiki.scan()

    catalog = SourceCatalog(load_catalog_config(wiki.config_path))
    try:
        row = catalog.store.fetchone(
            "SELECT d.document_id FROM documents d JOIN sources s "
            "ON s.source_id=d.primary_source_id WHERE s.content_sha256=?",
            (source_sha,),
        )
        assert row is not None
    finally:
        catalog.close()

    request = {
        "schema_version": "1.1", "company_query": "Apple Inc.",
        "market": "US", "document_kind": "annual_report",
        "fiscal_year": 2025, "as_of_date": "2026-09-27",
    }
    record = preparation.prepare_source(
        request, source_reader_v2=True, allow_download=False,
        company_wiki_catalog_config=wiki.config_path,
        company_wiki_config=wiki.root / "company_wiki.json",
        filing_fetch_root=ff_root, timeout_seconds=60.0,
    )
    assert record["capture"]["snapshot_sha256"] == source_sha
    assert record["capture"]["prompt_injection_status"] == "not_reviewed"
    assert record["reuse_receipt"]["download_calls"] == 0
    assert record["reuse_receipt"]["prompt_injection_status"] == "not_reviewed"
    assert "canonical_path" not in str(record)
    assert str(wiki.root) not in str(record)
    assert source.read_bytes() == source_bytes
    assert wiki.journal_outcomes() == []

    validate_sources(
        {"sources": [record]}, date.fromisoformat("2026-09-27"),
        require_capture=True,
    )

    # A same-size source corruption cannot be noticed by the DB-only FF
    # query, and must be refused by the one final verified CWP open. Restore
    # the fixture bytes before the test exits.
    source.write_bytes(source_bytes[:-1] + b"X")
    try:
        rc, out, err = wiki.run_fetch(request, extra_args=["--source-ref-v2"])
        assert rc == 0, err + out
        assert json.loads(out)["handle"]["source_ref"]["content_sha256"] == source_sha
        with pytest.raises(RuntimeError, match="source reader refused"):
            preparation.prepare_source(
                request, source_reader_v2=True, allow_download=False,
                company_wiki_catalog_config=wiki.config_path,
                company_wiki_config=wiki.root / "company_wiki.json",
                filing_fetch_root=ff_root, timeout_seconds=60.0,
            )
    finally:
        source.write_bytes(source_bytes)
    assert source.read_bytes() == source_bytes
    assert wiki.journal_outcomes() == []

    # The read receipt may carry an empty not_reviewed diagnostic object;
    # it is not a review prerequisite for exact bytes and matching metadata.
    review = record["company_wiki_trace"]["read_receipt"]["review"]
    assert review["status"] == "not_reviewed"
    assert review["reviewed_at"] is None
