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
