"""Actual scope proof controls relevance before ancillary date/cache failures."""
import pytest

from helpers.source_fact_fixture import lake, html, imported, close
from contract.test_local_request_relevance import request
from company_wiki.source_catalog import local_reconcile
from company_wiki.source_catalog.local_reconcile import prepare_local_source


@pytest.mark.parametrize("options", [
    {"year": 2022}, {"period": "Q1", "form": "10-Q"},
])
def test_discovered_unrelated_original_ignores_its_unusable_date(tmp_path, options):
    cat = lake(tmp_path)
    try:
        base = cat.config.roots[0].path / "Acme"
        base.mkdir()
        data = html(**options, end="June 30, 2022", transform="unknown:date-format")
        path = base / "2026-annual.htm"  # A misleading name is only a hint.
        path.write_bytes(data)
        result = prepare_local_source(cat, request())
        assert result["status"] == "not_found" and not result["blocks_download"], result
        assert result["source_ref"] is None and result["download_events"] == 0
        assert path.read_bytes() == data
    finally:
        close(cat)


@pytest.mark.parametrize("body", [
    html(end="June 30, 2026", transform="unknown:date-format"),
    b"<html><body>Unknown filing period and identity.</body></html>",
])
def test_discovered_target_or_unknown_never_becomes_absence(tmp_path, body):
    cat = lake(tmp_path)
    try:
        base = cat.config.roots[0].path / "Acme"
        base.mkdir()
        path = base / "2022-old.htm"  # Wrong label must not exclude actual2026.
        path.write_bytes(body)
        for _retry in range(2):
            result = prepare_local_source(cat, request())
            assert result["status"] in {"blocked", "unavailable"}, result
            assert result["blocks_download"] and result["source_ref"] is None
            assert result["download_events"] == 0
        assert path.read_bytes() == body
    finally:
        close(cat)


@pytest.mark.parametrize("bad_sidecar", [False, True])
def test_actual_nonrelevance_is_not_reproved_in_same_call(tmp_path, monkeypatch, bad_sidecar):
    cat = lake(tmp_path)
    try:
        options = {} if bad_sidecar else {"end": "June 30, 2022", "transform": "unknown:date-format"}
        ref, path = imported(cat, html(year=2022, **options))
        if bad_sidecar:
            path.with_name("meta.json").write_text("{broken", encoding="utf-8")
        calls = []
        original = local_reconcile._proven_facts
        def observe(catalog, checked, *args, **kwargs):
            if checked.ref.document_id == ref.document_id:
                calls.append(checked.ref.content_sha256)
            return original(catalog, checked, *args, **kwargs)
        monkeypatch.setattr(local_reconcile, "_proven_facts", observe)
        result = prepare_local_source(cat, request())
        assert result["status"] == "not_found" and not result["blocks_download"], result
        assert calls == [ref.content_sha256]
    finally:
        close(cat)


def test_wrong_declared_old_year_does_not_exclude_actual_requested_original(tmp_path):
    cat = lake(tmp_path)
    try:
        ref, path = imported(cat, html(), published="2026-07-30", declared_year=2022)
        result = prepare_local_source(cat, request())
        assert result["status"] == "ready", result
        assert result["source_ref"]["content_sha256"] == ref.content_sha256
        assert result["download_events"] == 0 and path.read_bytes() == html()
    finally:
        close(cat)
