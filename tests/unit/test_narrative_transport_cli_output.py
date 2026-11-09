"""Vendor diagnostics cannot contaminate the binary CLI protocol."""

from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_transport_cli as cli


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
    config = object()
    artifacts = SimpleNamespace(close=lambda: closed.append("artifacts"))
    catalog = SimpleNamespace(open_narrative_artifact_reader=lambda: artifacts,
                              close=lambda: closed.append("catalog"))
    monkeypatch.setattr(cli, "load_catalog_config", lambda _: config)
    monkeypatch.setattr(cli, "SourceCatalog", lambda _: catalog)
    monkeypatch.setattr(cli, "SourceVersionReader", lambda _: object())

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


@pytest.mark.parametrize("failure", [False, True])
def test_native_descriptor_writes_do_not_contaminate_the_cli_wire(failure):
    root = Path(__file__).resolve().parents[2]
    probe = r"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, sys.argv[1])
from company_wiki.automation import narrative_transport_cli as cli
from company_wiki.automation.narrative_transport_contracts import NarrativeTransportError

cli.load_catalog_config = lambda path: None
cli.SourceVersionReader = lambda catalog: None
cli.SourceCatalog = lambda config: SimpleNamespace(
    open_narrative_artifact_reader=lambda: SimpleNamespace(close=lambda: None), close=lambda: None,
)

def dispatch(*args, **kwargs):
    os.write(1, b'native standard output\n')
    os.write(2, b'native standard error\n')
    if sys.argv[2] == 'fail':
        raise NarrativeTransportError('blocked', 'fixture_refusal')
    return b'{"bundle":"exact bytes"}', {"status": "ok"}

cli.dispatch_transport_request = dispatch
raise SystemExit(cli.main(['--config', 'unused.yaml']))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, str(root / "src"), "fail" if failure else "ok"],
        input=b"{}", capture_output=True, timeout=20, check=False,
    )
    assert result.returncode == (2 if failure else 0)
    assert result.stdout == (b"" if failure else b'{"bundle":"exact bytes"}')
    assert len(result.stderr.splitlines()) == 1
    receipt = json.loads(result.stderr)
    if failure:
        assert (receipt["status"], receipt["reason"]) == ("blocked", "fixture_refusal")
    else:
        assert receipt == {"status": "ok"}
