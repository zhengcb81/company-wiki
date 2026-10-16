"""Retained byte evidence survives Git filters on Windows and Linux."""
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("autocrlf", ["true", "input", "false"])
@pytest.mark.parametrize("preserve_fixture_rule", [True, False], ids=["retained-bytes", "filter-control"])
@pytest.mark.parametrize("attribute_eol", ["lf", "crlf"])
def test_retained_plan_fixture_roundtrip_preserves_original_bytes(tmp_path, autocrlf, preserve_fixture_rule, attribute_eol):
    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), "-c", f"core.autocrlf={autocrlf}",
            *args], capture_output=True, check=True).stdout

    git("init", "--quiet")
    attributes = (ROOT / ".gitattributes").read_bytes().replace(b"\r\n", b"\n")
    if attribute_eol == "crlf":
        attributes = attributes.replace(b"\n", b"\r\n")
    if not preserve_fixture_rule:
        attributes = b"".join(line for line in attributes.splitlines(keepends=True)
                              if not line.startswith(b"/docs/plans/**/fixtures/** "))
    (tmp_path / ".gitattributes").write_bytes(attributes)
    relative = "docs/plans/example-independent-lane/fixtures/native-observation.json"
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    original = '{\r\n  "source_text": "原文",\r\n  "stage": "not_yet"\r\n}\r\n'.encode("utf-8")
    source.write_bytes(original)
    git("add", "--", ".gitattributes", relative)
    indexed = git("show", ":" + relative)
    expected = (original if preserve_fixture_rule or autocrlf == "false"
                else original.replace(b"\r\n", b"\n"))
    assert indexed == expected
    if preserve_fixture_rule:
        # Retained raw bytes are evidence, not source-code whitespace. Source
        # and test diffs still use the repository's normal whitespace checks.
        git("diff", "--cached", "--check")
    checkout = tmp_path / "roundtrip"
    checkout.mkdir()
    # A Linux-style checkout must keep original evidence bytes even if it was
    # staged by a Windows autocrlf=true client.
    subprocess.run(["git", "-C", str(tmp_path), "-c", "core.autocrlf=false",
        "checkout-index", "--force", "--prefix=" + checkout.as_posix() + "/", "--", relative],
        capture_output=True, check=True)
    assert (checkout / relative).read_bytes() == expected
