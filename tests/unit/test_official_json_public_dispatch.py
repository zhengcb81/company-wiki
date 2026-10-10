"""Public composition delegates official source operations without re-encoding."""
import sys

import pytest

from company_wiki.source_catalog import cli, official_source_cli


@pytest.mark.parametrize("implicit", [False, True])
@pytest.mark.parametrize("operation", ["read", "project", "export", "replay"])
def test_official_dispatch_before_outer_parser_stream_or_catalog(monkeypatch, implicit, operation):
    arguments = ["official", "--operation", operation, "--request", "请求.json"]
    calls = []

    def forbidden(*args, **kwargs):
        raise AssertionError("outer parser/config/catalog must not own official operations")

    def delegated(argv):
        calls.append(list(argv))
        return 17

    monkeypatch.setattr(cli, "_parser", forbidden)
    monkeypatch.setattr(cli, "load_catalog_config", forbidden)
    monkeypatch.setattr(official_source_cli, "main", delegated)
    if implicit:
        monkeypatch.setattr(sys, "argv", ["company-wiki-source-catalog", *arguments])
    assert cli.main(None if implicit else arguments) == 17
    assert calls == [arguments[1:]]


def test_official_dispatch_does_not_reconfigure_streams(monkeypatch):
    class Guard:
        def reconfigure(self, **kwargs):
            raise AssertionError("outer stream mutation before binary original read")

    monkeypatch.setattr(cli.sys, "stdout", Guard())
    monkeypatch.setattr(cli.sys, "stderr", Guard())
    monkeypatch.setattr(official_source_cli, "main", lambda argv: 0)
    assert cli.main(["official", "--operation", "read"]) == 0


def test_root_help_exposes_official_entry(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "official" in capsys.readouterr().out
