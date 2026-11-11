"""Unrelated obsolete source gaps cannot veto a genuinely absent requested period."""

import pytest
from helpers.source_fact_fixture import lake, html, imported, close
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.source_reader import SourceVersionReader


def request(**kwargs):
    return SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        fiscal_year=2026,
        form_type="10-K",
        as_of_date="2026-10-08",
        mode="exact",
        **kwargs,
    )


@pytest.mark.parametrize(
    "year,period,form,kind,reason", [
        (2022, "FY", "10-K", "annual_report", "no_matching_local_period"),
        (2026, "Q1", "10-Q", "regulatory_filing", "no_registered_local_source"),
    ],
)
def test_actual_wrong_scope_is_excluded_before_irrelevant_date_error(
    tmp_path, year, period, form, kind, reason,
):
    cat = lake(tmp_path)
    try:
        original = html(
            year=year, period=period, form=form, end="June 30, 2022",
            transform="unknown:date-format",
        )
        ref, path = imported(cat, original)
        result = prepare_local_source(cat, request())
        assert result["status"] == "not_found" and not result["blocks_download"]
        assert result["reason"] == reason
        assert result["download_events"] == 0 and path.read_bytes() == original
        actual = SourceVersionReader(cat).describe_version(ref)
        assert (actual["document_kind"], actual["fiscal_year"], actual["fiscal_period"], actual["form_type"]) == (
            kind, year, period, form,
        )
        before = cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0]
        retry = prepare_local_source(cat, request())
        assert retry["status"] == "not_found" and not retry["blocks_download"]
        assert cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0] == before
    finally:
        close(cat)


@pytest.mark.parametrize(
    "mutation", ["bad_date", "unknown_publication", "wrong_cik", "bad_sha"]
)
def test_genuine_target_gap_never_becomes_byte_absence(tmp_path, mutation):
    cat = lake(tmp_path)
    try:
        data = (
            html(end="June 30, 2026", transform="unknown:date-format")
            if mutation == "bad_date"
            else html(cik="99999" if mutation == "wrong_cik" else "12345")
        )
        ref, path = imported(cat, data)
        if mutation == "bad_sha":
            path.write_bytes(data + b"changed")
        result = prepare_local_source(cat, request())
        assert result["blocks_download"] and result["status"] in {
            "blocked",
            "unavailable",
        }
        assert result["download_events"] == 0
        assert result["reason"] != "no_matching_local_period"
    finally:
        close(cat)


def test_known_wrong_cache_year_is_not_an_exclusion_proof(tmp_path):
    cat = lake(tmp_path)
    try:
        ref, path = imported(cat, html())
        import json

        meta = {
            "company_id": "12345",
            "accession_number": "0000012345-26-000007",
            "primary_document": path.name,
            "form_type": "10-K",
            "report_date": "2026-06-30",
            "filing_date": "2026-07-30",
            "fiscal_year": 2025,
            "ingest_complete": True,
            "is_deleted": False,
            "files": [
                {
                    "name": path.name,
                    "sha256": ref.content_sha256,
                    "size": ref.byte_size,
                    "source_url": "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/"
                    + path.name,
                }
            ],
        }
        path.with_name("meta.json").write_text(json.dumps(meta))
        result = prepare_local_source(cat, request())
        assert (
            result["status"] == "ready"
            and result["source_ref"]["content_sha256"] == ref.content_sha256
        )
        from company_wiki.source_catalog.source_reader import SourceVersionReader

        manifest = SourceVersionReader(cat).describe_version(ref)
        assert (manifest["fiscal_year"], manifest["form_type"], manifest["title"]) == (
            2026,
            "10-K",
            "10-K",
        )
        assert result["download_events"] == 0
    finally:
        close(cat)


def test_unknown_title_is_description_not_eligibility(tmp_path):
    cat = lake(tmp_path)
    try:
        ref, path = imported(cat, html(title=""))
        import json

        meta = {
            "company_id": "12345",
            "accession_number": "0000012345-26-000007",
            "primary_document": path.name,
            "form_type": "10-K",
            "report_date": "2026-06-30",
            "filing_date": "2026-07-30",
            "ingest_complete": True,
            "is_deleted": False,
            "files": [
                {
                    "name": path.name,
                    "sha256": ref.content_sha256,
                    "size": ref.byte_size,
                    "source_url": "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/"
                    + path.name,
                }
            ],
        }
        path.with_name("meta.json").write_text(json.dumps(meta))
        result = prepare_local_source(cat, request())
        assert result["status"] == "ready" and result["download_events"] == 0
        from company_wiki.source_catalog.source_reader import SourceVersionReader

        assert SourceVersionReader(cat).describe_version(ref)["title"] is None
        assert (
            SourceVersionReader(cat).open_version(ref, purpose="source_export").data
            == path.read_bytes()
        )
    finally:
        close(cat)


@pytest.mark.parametrize("actual", ["wrong_cik", "wrong_year"])
def test_cached_request_hit_requires_actual_original_scope(tmp_path, actual):
    from helpers.source_fact_fixture import evidence
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    cat = lake(tmp_path)
    try:
        data = html(cik="99999") if actual == "wrong_cik" else html(year=2022, end="2022-06-30")
        ref, path = imported(cat, data, published="2026-07-30", declared_year=2026)
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        assert SourceVersionReader(cat).query_local(request()).status == "found"
        result = prepare_local_source(cat, request())
        if actual == "wrong_cik":
            assert result["status"] == "blocked" and result["blocks_download"]
            assert "primary_issuer_conflict" in str(result)
        else:
            assert result["status"] == "not_found" and not result["blocks_download"]
            assert result["reason"] == "no_matching_local_period"
            assert SourceVersionReader(cat).describe_version(ref)["fiscal_year"] == 2022
        assert result["download_events"] == 0 and path.read_bytes() == data
    finally:
        close(cat)


def test_correct_cache_is_qualified_once_with_existing_budget_and_reuses_proof(tmp_path, monkeypatch):
    from helpers.source_fact_fixture import evidence
    from company_wiki.source_catalog import local_reconcile
    from company_wiki.source_catalog.local_inventory import LocalPrepareLimits
    from company_wiki.source_catalog.source_reader import SourceVersionReader
    from pathlib import Path

    cat = lake(tmp_path)
    try:
        ref, path = imported(cat, html(), published="2026-07-30", declared_year=2026)
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        raw_open = Path.open
        opens = []
        def observe(self, *args, **kwargs):
            if self == path and args and args[0] == "rb":
                opens.append(self)
            return raw_open(self, *args, **kwargs)
        monkeypatch.setattr(Path, "open", observe)
        limits = LocalPrepareLimits(max_bytes=ref.byte_size)
        first = prepare_local_source(cat, request(), limits=limits)
        assert first["status"] == "ready" and len(opens) == 1
        assert SourceVersionReader(cat).describe_version(ref)["title"] == "10-K"
        before = cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0]
        def no_repeat_parse(_data):
            raise AssertionError("genuine original scope proof must be reused")
        monkeypatch.setattr(local_reconcile, "extract_sec_scope", no_repeat_parse)
        second = prepare_local_source(cat, request(), limits=limits)
        assert second["status"] == "ready" and len(opens) == 2
        assert cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0] == before
        assert second["download_events"] == 0
    finally:
        close(cat)


def test_annual_kind_cannot_be_qualified_by_actual_quarter_form(tmp_path):
    from dataclasses import replace
    from helpers.source_fact_fixture import evidence
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    cat = lake(tmp_path)
    try:
        ref, path = imported(cat, html(period="Q1", form="10-Q"), published="2026-07-30", declared_year=2026)
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        annual = replace(request(), form_type=None)
        assert SourceVersionReader(cat).query_local(annual).status == "found"
        result = prepare_local_source(cat, annual)
        assert result["status"] == "not_found" and not result["blocks_download"]
        assert result["source_ref"] is None and result["download_events"] == 0
        actual = SourceVersionReader(cat).describe_version(ref)
        assert (actual["document_kind"], actual["form_type"], actual["fiscal_period"]) == (
            "regulatory_filing", "10-Q", "Q1",
        )
    finally:
        close(cat)


@pytest.mark.parametrize("mode", ["exact", "latest_as_of"])
def test_registered_archive_reconciles_actual_scope_even_when_layout_discovery_finds_nothing(tmp_path, mode):
    from dataclasses import replace
    from helpers.source_fact_fixture import evidence

    cat = lake(tmp_path)
    try:
        original = html(year=2022, end="2022-06-30")
        ref, path = imported(cat, original, published="2026-07-30", declared_year=2026)
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        root = cat.config.roots[0].path
        archive = root / "Off-layout archive"
        archive.mkdir()
        moved = path.rename(archive / path.name)
        with cat.store.transaction() as connection:
            connection.execute(
                "UPDATE locations SET absolute_path=?, relative_path=? "
                "WHERE document_id=? AND role='original_primary'",
                (str(moved), moved.relative_to(root).as_posix(), ref.document_id),
            )

        requested = replace(request(), mode=mode)
        assert SourceVersionReader(cat).query_local(requested).status == "found"
        result = prepare_local_source(cat, requested)
        assert result["status"] == "not_found" and not result["blocks_download"], result
        assert result["reason"] == "no_matching_local_period"
        assert result["source_ref"] is None and result["download_events"] == 0
        assert SourceVersionReader(cat).describe_version(ref)["fiscal_year"] == 2022
        assert moved.read_bytes() == original
    finally:
        close(cat)


@pytest.mark.parametrize("mode", ["exact", "latest_as_of"])
def test_nonperiodic_sec_form_does_not_require_periodic_scope_proof(tmp_path, mode):
    from dataclasses import replace
    from helpers.source_fact_fixture import evidence

    cat = lake(tmp_path)
    try:
        original = b'<html><body><ix:nonNumeric name="dei:DocumentType">8-K</ix:nonNumeric><p>Company update</p></body></html>'
        ref, path = imported(cat, original, published="2026-07-30", document_kind="regulatory_filing")
        facts = {"form_type": "8-K"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        requested = replace(request(), document_kind="regulatory_filing", form_type="8-K", fiscal_year=None, mode=mode)
        assert SourceVersionReader(cat).query_local(requested).status == "found"

        result = prepare_local_source(cat, requested)
        assert result["status"] == "ready" and result["download_events"] == 0
        assert result["source_ref"]["content_sha256"] == ref.content_sha256
        assert path.read_bytes() == original
    finally:
        close(cat)


@pytest.mark.parametrize("broken", ["primary_cik", "hash", "locator", "method"])
def test_partial_or_unbound_scope_proof_is_checked_from_original(tmp_path, monkeypatch, broken):
    from helpers.source_fact_fixture import evidence
    from company_wiki.source_catalog import local_reconcile
    from company_wiki.source_catalog.assertion_service import get_verified_assertion, evidence_payload

    cat = lake(tmp_path)
    try:
        ref, path = imported(cat, html(), published="2026-07-30", declared_year=2026)
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        assert prepare_local_source(cat, request())["status"] == "ready"
        row = get_verified_assertion(cat.reader, ref.source_id, ref.content_sha256, reader="steady")
        payload = evidence_payload(row["evidence_json"], row["assertion_id"])
        field = "entity" if broken == "primary_cik" else "fiscal_year"
        proof = dict(payload["source_fact_evidence"][field])
        if broken == "primary_cik":
            proof.pop("primary_cik")
        elif broken == "hash":
            proof["content_sha256"] = "f" * 64
        elif broken == "locator":
            proof["locator"] = "official-import-declaration:/fiscal_year"
        else:
            proof.pop("extraction_method")
        cat.record_source_facts(ref=ref, facts={field: payload["source_fact_patch"][field]}, evidence={field: proof})
        original_parse = local_reconcile.extract_sec_scope
        parsed = []
        def observe(data):
            parsed.append(len(data))
            return original_parse(data)
        monkeypatch.setattr(local_reconcile, "extract_sec_scope", observe)
        assert prepare_local_source(cat, request())["status"] == "ready"
        assert parsed == [ref.byte_size]
    finally:
        close(cat)


@pytest.mark.parametrize("target", [True, False])
def test_bad_metadata_remains_gap_only_for_proven_requested_scope(tmp_path, target):
    cat = lake(tmp_path)
    try:
        data = html() if target else html(year=2022, end="2022-06-30")
        ref, path = imported(cat, data)
        path.with_name("meta.json").write_text("{broken", encoding="utf-8")
        result = prepare_local_source(cat, request())
        if target:
            assert result["status"] == "blocked" and result["blocks_download"]
            assert "local_metadata_unreadable" in str(result)
        else:
            assert result["status"] == "not_found" and not result["blocks_download"]
        assert path.read_bytes() == data and result["download_events"] == 0
    finally:
        close(cat)


def test_genuine_scope_cache_does_not_reverify_unrelated_annuals(tmp_path, monkeypatch):
    from helpers.source_fact_fixture import evidence
    from company_wiki.source_catalog import local_reconcile
    from company_wiki.source_catalog.local_inventory import LocalPrepareLimits
    from pathlib import Path

    cat = lake(tmp_path)
    try:
        old, old_path = imported(cat, html(year=2022, end="2022-06-30"), published="2022-07-30", declared_year=2022)
        ref, path = imported(cat, html(), published="2026-07-30", declared_year=2026)
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        assert prepare_local_source(cat, request())["status"] == "ready"
        raw_open = Path.open
        def reject_unrelated(self, *args, **kwargs):
            assert self != old_path or not args or args[0] != "rb", "qualified cached match must not re-read old originals"
            return raw_open(self, *args, **kwargs)
        monkeypatch.setattr(Path, "open", reject_unrelated)
        def no_repeat_parse(_data):
            raise AssertionError("scope proof must be reused")
        monkeypatch.setattr(local_reconcile, "extract_sec_scope", no_repeat_parse)
        result = prepare_local_source(cat, request(), limits=LocalPrepareLimits(max_bytes=ref.byte_size))
        assert result["status"] == "ready" and result["download_events"] == 0
    finally:
        close(cat)


def test_healthy_dayu_primary_is_usable_despite_unreadable_attachment(tmp_path, monkeypatch):
    import hashlib
    import json
    from pathlib import Path
    from company_wiki.source_catalog.source_group_scope import SourceRegistrationScope

    cat = lake(tmp_path, portfolio=True)
    try:
        group = cat.config.roots[1].path / "ACME/filings/fil_0000012345-26-000007"
        group.mkdir(parents=True)
        path = group / "original.htm"
        data = html()
        path.write_bytes(data)
        attachment = group / "unreadable.txt"
        attachment.write_bytes(b"unreadable attachment")
        (group / "meta.json").write_text(json.dumps({
            "company_id": "12345", "ticker": "ACME",
            "accession_number": "0000012345-26-000007", "primary_document": path.name,
            "form_type": "10-K", "report_date": "2026-06-30", "fiscal_year": 2026,
            "filing_date": "2026-07-30", "ingest_complete": True, "is_deleted": False,
            "files": [{"name": path.name, "sha256": hashlib.sha256(data).hexdigest(),
                       "size": len(data),
                       "source_url": "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/original.htm"}]
        }), encoding="utf-8")
        raw_open = Path.open
        failures = []
        def observed(self, *args, **kwargs):
            if self == attachment and args and args[0] == "rb":
                failures.append(self)
                raise PermissionError("unreadable attachment fixture")
            return raw_open(self, *args, **kwargs)
        monkeypatch.setattr(Path, "open", observed)
        result = prepare_local_source(cat, request(), registrations=(SourceRegistrationScope(
            "provider", frozenset({path.relative_to(cat.config.roots[1].path).as_posix()})),))
        assert result["status"] == "ready" and not result["blocks_download"], result
        assert failures and result["download_events"] == 0
        assert path.read_bytes() == data
    finally:
        close(cat)
