"""Local codec behaviour is invariant under JSON formatting."""
from __future__ import annotations

import io
import json
from unittest.mock import patch

import pytest

from company_wiki.source_catalog import source_export_v2_cli, official_source_cli
from company_wiki.source_catalog.official_source_flow import _byte_cap


def test_export_request_formatting_has_no_secondary_size_permission():
    value = {"schema_version": "2.0", "source_refs": [], "evidence_spans": []}
    class Input:
        buffer = io.BytesIO(json.dumps(value).encode() + b" " * (17 * 1024 * 1024))
    with patch.object(source_export_v2_cli.sys, "stdin", Input()):
        assert source_export_v2_cli._read_request() == ((), ())


def test_official_request_whitespace_and_real_invalid_json(tmp_path):
    path = tmp_path / "request.json"
    path.write_bytes(b'{"schema_version":"example"}' + b" " * 70000)
    assert official_source_cli._read_json(path) == {"schema_version": "example"}
    path.write_bytes(b'{"schema_version":"one","schema_version":"two"}')
    with pytest.raises(ValueError, match="duplicate"):
        official_source_cli._read_json(path)


def test_explicit_official_source_budget_is_not_capped_again():
    assert _byte_cap(129 * 1024 * 1024) == 129 * 1024 * 1024
    for invalid in (0, -1, True, float("nan")):
        with pytest.raises(ValueError):
            _byte_cap(invalid)


@pytest.mark.parametrize(
    ("module_name", "padding", "stream", "reason", "payload"),
    [
        (
            "source_query_cli", 70_000, "out", "reader_unavailable",
            {"entity": "Example", "document_kind": "annual_report",
             "as_of_date": "2026-11-27"},
        ),
        (
            "company_source_index_cli", 1_050_000, "err", "catalog_unavailable",
            {"schema_version": "company-wiki-company-source-index-request/1",
             "company": {"entity": "Example", "market": None, "security_id": None},
             "as_of_date": "2026-11-27", "document_kinds": [],
             "page_size": 5, "cursor": None},
        ),
    ],
)
def test_query_request_whitespace_does_not_override_its_fields(
    capsys, monkeypatch, module_name, padding, stream, reason, payload,
):
    from importlib import import_module
    from types import SimpleNamespace

    cli = import_module(f"company_wiki.source_catalog.{module_name}")
    request = io.BytesIO(json.dumps(payload).encode("utf-8") + b" " * padding)
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(buffer=request))

    def unavailable(_path):
        # At this point the actual wire parser accepted the request.
        raise FileNotFoundError

    monkeypatch.setattr(cli, "load_catalog_config", unavailable)
    assert cli.main(["--config", "unused.yaml"]) == 2
    captured = capsys.readouterr()
    result = json.loads(getattr(captured, stream))
    assert result["status"] == "unavailable"
    assert result["reason"] == reason
