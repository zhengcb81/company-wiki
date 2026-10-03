"""Vendor diagnostics cannot contaminate the binary CLI protocol."""

from __future__ import annotations

import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog import narrative_transport_cli as cli


def test_parser_console_output_does_not_corrupt_bundle_or_json_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_path = Path(__file__).parents[1] / "fixtures/narrative_transport_v1/read_request.json"
    request = request_path.read_bytes()
    input_stream = io.TextIOWrapper(io.BytesIO(request), encoding="utf-8")
    output_bytes, receipt_bytes = io.BytesIO(), io.BytesIO()
    output_stream = io.TextIOWrapper(output_bytes, encoding="utf-8")
    receipt_stream = io.TextIOWrapper(receipt_bytes, encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", input_stream)
    monkeypatch.setattr(sys, "stdout", output_stream)
    monkeypatch.setattr(sys, "stderr", receipt_stream)
    closed: list[str] = []
    config = SimpleNamespace(database_path=Path("unused.sqlite3"), catalog_dir=Path("unused"))
    catalog = SimpleNamespace(config=config, close=lambda: closed.append("catalog"))
    artifacts = SimpleNamespace(close=lambda: closed.append("artifacts"))
    monkeypatch.setattr(cli, "load_catalog_config", lambda _: config)
    monkeypatch.setattr(cli, "SourceCatalog", lambda _: catalog)
    monkeypatch.setattr(cli, "SourceVersionReader", lambda _: object())
    monkeypatch.setattr(cli.NarrativeArtifactStore, "for_reading", lambda *_: artifacts)

    class NoisyReader:
        def __init__(self, *_):
            pass

        def read(self, _):
            print("PDF parser suggests an optional layout package")
            print("PDF parser diagnostic", file=sys.stderr)
            return SimpleNamespace(data=b'{"bundle":"exact bytes"}', receipt={"status": "ok"})

    monkeypatch.setattr(cli, "NarrativeTransportReader", NoisyReader)
    assert cli.main(["--config", "unused.yaml"]) == 0
    output_stream.flush()
    receipt_stream.flush()
    assert output_bytes.getvalue() == b'{"bundle":"exact bytes"}'
    assert receipt_bytes.getvalue().count(b"\n") == 1
    assert json.loads(receipt_bytes.getvalue()) == {"status": "ok"}
    assert closed == ["artifacts", "catalog"]
