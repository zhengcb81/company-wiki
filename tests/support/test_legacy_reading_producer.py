"""Historical component provenance is independent of Git availability in CI."""
import gzip
from hashlib import sha256
import json
import subprocess

import pytest

from support import legacy_reading_producer as historical


def test_exact_historical_component_is_physically_deployed_without_running_git(tmp_path, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("normal fixture deployment must not invoke Git")
    monkeypatch.setattr(subprocess, "check_output", forbidden)
    bootstrap, observations, producer = historical.deploy_historical_reading_producer(tmp_path)
    manifest = json.loads((historical.FIXTURE/"manifest.json").read_text(encoding="utf-8"))
    assert sha256(producer.read_bytes()).hexdigest() == manifest["source_sha256"]
    assert producer.read_bytes() == gzip.decompress((historical.FIXTURE/manifest["artifact"]).read_bytes())
    assert (bootstrap/"sitecustomize.py").is_file() and not observations.exists()
    assert list(producer.parent.iterdir()) == [producer]


def test_resigning_an_edited_code_fixture_cannot_claim_the_original_git_blob(tmp_path, monkeypatch):
    directory = tmp_path/"tampered"
    directory.mkdir()
    manifest = json.loads((historical.FIXTURE/"manifest.json").read_text(encoding="utf-8"))
    data = gzip.decompress((historical.FIXTURE/manifest["artifact"]).read_bytes()) + b"\n# changed\n"
    compressed = gzip.compress(data, mtime=0)
    (directory/manifest["artifact"]).write_bytes(compressed)
    manifest.update(source_sha256=sha256(data).hexdigest(), source_bytes=len(data),
                    gzip_sha256=sha256(compressed).hexdigest())
    (directory/"manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(historical, "FIXTURE", directory)
    with pytest.raises(ValueError, match="actual Git blob"):
        historical.deploy_historical_reading_producer(tmp_path/"deployment")
    assert not (tmp_path/"deployment").exists()
