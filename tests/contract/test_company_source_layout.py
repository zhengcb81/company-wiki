"""Target company direct originals and legacy raw are one storage responsibility."""

import hashlib
import json
import pytest
from helpers.source_fact_fixture import lake, html, close
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_catalog.adapters.company_raw import CompanyRawAdapter


def original(cat, relative, *, data=None):
    data = data or html()
    path = cat.config.roots[0].path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    metadata = {
        "source_title": "10-K",
        "entity": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "annual_report",
        "provider": "sec",
        "form_type": "10-K",
        "fiscal_year": 2026,
        "fiscal_period": "FY",
        "filing_date": "2026-07-30",
        "published_date": "2026-07-30",
        "source_url": "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/original.htm",
        "content_sha256": hashlib.sha256(data).hexdigest(),
    }
    path.with_name(path.name + ".source.json").write_text(json.dumps(metadata))
    return path, data


def request():
    return SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        fiscal_year=2026,
        form_type="10-K",
        as_of_date="2026-10-08",
        mode="exact",
    )


@pytest.mark.parametrize("adapter", [None, "company_raw_v1"])
@pytest.mark.parametrize("layout", ["direct", "raw", "both"])
def test_company_direct_and_raw_discover_once_without_other_company(
    tmp_path, adapter, layout
):
    cat = lake(tmp_path)
    try:
        if adapter:
            from dataclasses import replace

            cat.config = replace(
                cat.config, roots=(replace(cat.config.roots[0], adapter_id=adapter),)
            )
        paths = []
        for relative in {
            "direct": ["Acme/annual.htm"],
            "raw": ["Acme/raw/annual.htm"],
            "both": ["Acme/annual.htm", "Acme/raw/annual.htm"],
        }[layout]:
            paths.append(original(cat, relative))
        original(cat, "Other/annual.htm", data=html(cik="777"))
        original(cat, "Acme/wiki/annual.htm", data=html(cik="888"))
        result = prepare_local_source(cat, request())
        assert result["status"] == "ready" and result["download_events"] == 0, result
        assert cat.reader.fetchone("SELECT COUNT(*) FROM documents")[0] == 1
        assert (
            cat.reader.fetchone(
                "SELECT COUNT(*) FROM locations WHERE relative_path LIKE 'Other/%' OR relative_path LIKE 'Acme/wiki/%'"
            )[0]
            == 0
        )
        from company_wiki.source_catalog.source_reader import SourceRef

        ref = SourceRef(**result["source_ref"])
        assert (
            SourceVersionReader(cat).open_version(ref, purpose="source_export").data
            == paths[0][1]
        )
        assert all(path.read_bytes() == data for path, data in paths)
    finally:
        close(cat)


def test_scoped_adapter_and_registration_scope_reject_escape_and_projection(tmp_path):
    cat = lake(tmp_path)
    try:
        path, data = original(cat, "Acme/annual.htm")
        other, _ = original(cat, "Other/annual.htm")
        original(cat, "Acme/wiki/annual.htm")
        scoped = CompanyRawAdapter().enumerate(
            cat.config.roots[0].path,
            relative_paths={"Acme/annual.htm"},
            compute_hash=False,
        )
        assert {item.relative_path for item in scoped} == {
            "Acme/annual.htm",
            "Acme/annual.htm.source.json",
        }
        from company_wiki.source_catalog.source_group_scope import (
            SourceRegistrationScope,
        )

        assert not SourceRegistrationScope(
            "x", frozenset({"Other/annual.htm"})
        ).company_paths(cat.config.roots[0].path, "Acme", ".source.json")
        assert not SourceRegistrationScope(
            "x", frozenset({"Acme/wiki/annual.htm"})
        ).company_paths(cat.config.roots[0].path, "Acme", ".source.json")
        link = path.parent / "escape.htm"
        try:
            link.symlink_to(other)
        except OSError:
            pytest.skip("OS does not grant symlink creation")
        assert not SourceRegistrationScope(
            "x", frozenset({"Acme/escape.htm"})
        ).company_paths(cat.config.roots[0].path, "Acme", ".source.json")
        assert path.read_bytes() == data
    finally:
        close(cat)


def test_same_root_link_cannot_import_another_company(tmp_path, monkeypatch):
    cat = lake(tmp_path)
    try:
        path, data = original(cat, "Acme/annual.htm")
        real = type(path).is_symlink
        monkeypatch.setattr(
            type(path), "is_symlink", lambda self: self == path or real(self)
        )
        result = prepare_local_source(cat, request())
        assert result["status"] == "not_found" and result["download_events"] == 0
        assert cat.reader.fetchone("SELECT COUNT(*) FROM documents")[0] == 0
    finally:
        close(cat)


def test_failed_registered_primary_is_named_gap_not_absence_or_crash(tmp_path):
    cat = lake(tmp_path)
    try:
        path, data = original(cat, "Acme/annual.htm")
        sidecar = path.with_name(path.name + ".source.json")
        metadata = json.loads(sidecar.read_text())
        metadata["content_sha256"] = "0" * 64
        sidecar.write_text(json.dumps(metadata))
        result = prepare_local_source(cat, request())
        assert result["status"] in {"blocked", "unavailable"} and result["blocks_download"]
        assert result["download_events"] == 0 and result["reason"] != "no_matching_local_period"
        assert path.read_bytes() == data
    finally:
        close(cat)
