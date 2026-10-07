"""Report writers: JSON only, no apply surface, no machine-absolute paths, recoverable."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from g3_source_facts import cli
from g3_source_facts.report import ReportWriteError, write_json_report

_WINDOWS_ABSOLUTE = re.compile(r"[A-Za-z]:[\\/]")
_POSIX_ABSOLUTE = re.compile(
    r"(^|[\s\"'(\[])/(?:home|Users|var|tmp|workspace|mnt|root|api|data)(?:/|\b)"
)
_FORBIDDEN_KEYS = {
    "authorization",
    "authorisation",
    "token",
    "expiry",
    "expires_at",
    "receipt",
    "approval",
    "approved",
    "grant",
    "permission",
    "apply",
}


def _payload(schema: str) -> dict:
    return {"schema_version": schema, "items": [], "unknowns": ["x"], "conflicts": []}


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def test_write_replaces_its_own_previous_report_but_never_an_unknown_file(
    tmp_path: Path,
):
    target = tmp_path / "metadata_proposals.json"

    write_json_report(target, _payload("g3-metadata-proposals/1"))
    write_json_report(target, _payload("g3-metadata-proposals/1"))
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == (
        "g3-metadata-proposals/1"
    )

    unknown = tmp_path / "someone_else.json"
    unknown.write_text("{}", encoding="utf-8")
    with pytest.raises(ReportWriteError):
        write_json_report(unknown, _payload("g3-metadata-proposals/1"))
    assert unknown.read_text(encoding="utf-8") == "{}"


def test_report_recovery_keeps_previous_bytes_when_the_new_payload_is_invalid(
    tmp_path: Path,
):
    target = tmp_path / "raw_space_decision.json"
    write_json_report(target, _payload("g3-raw-space-decision/1"))
    before = target.read_bytes()

    with pytest.raises(ReportWriteError):
        write_json_report(target, {"schema_version": "other/9"})
    assert target.read_bytes() == before


def test_report_carries_no_machine_absolute_paths(tmp_path: Path):
    target = tmp_path / "metadata_proposals.json"
    payload = _payload("g3-metadata-proposals/1")
    payload["items"] = [{"locator": "C:/fake-machine-root/companies/x.pdf"}]
    with pytest.raises(ReportWriteError):
        write_json_report(target, payload)
    assert not target.exists()


def test_posix_style_machine_absolute_paths_are_refused_too(tmp_path: Path):
    target = tmp_path / "metadata_proposals.json"
    payload = _payload("g3-metadata-proposals/1")
    payload["items"] = [{"locator": "/home/fake-user/companies/x.pdf"}]
    with pytest.raises(ReportWriteError):
        write_json_report(target, payload)


def test_report_contains_no_authorization_token_expiry_or_receipt_surface(
    tmp_path: Path,
):
    target = tmp_path / "metadata_proposals.json"
    payload = _payload("g3-metadata-proposals/1")
    payload["authorization"] = "granted"
    with pytest.raises(ReportWriteError):
        write_json_report(target, payload)

    clean = _payload("g3-metadata-proposals/1")
    write_json_report(target, clean)
    stored = json.loads(target.read_text(encoding="utf-8"))
    keys = {key for key, _ in _walk(stored)}
    assert not (keys & _FORBIDDEN_KEYS)


def test_cli_exposes_no_apply_delete_or_update_switch():
    parser = cli.build_parser()
    options = set()
    for action in parser._actions:
        options.update(action.option_strings)
    for forbidden in (
        "--apply",
        "--delete",
        "--remove",
        "--update",
        "--write-db",
        "--hash-catalog",
        "--overwrite",
    ):
        assert forbidden not in options
    assert parser.prog == "g3_source_facts"
