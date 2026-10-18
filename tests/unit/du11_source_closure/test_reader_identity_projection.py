"""The verified-reader receipt owns representation without rewriting facts."""
import json

import pytest

from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_catalog.source_reader_cli import main
from unit.du11_identity_projection.test_identity_projection import indexed  # noqa: F401


@pytest.mark.parametrize("indexed", ["9896", "09896"], indirect=True)
@pytest.mark.parametrize("purpose", ["preview", "filing_reuse"])
def test_reader_exposes_same_observation_canonical_identity(indexed, purpose, capfdbinary, monkeypatch):  # noqa: F811
    catalog, _, ref, raw, facts = indexed
    root = catalog.config.project_root
    config = root / "config" / "source_catalog.yaml"
    config.parent.mkdir()
    config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog",
        "reusable_root_kinds": ["directory"], "roots": [{"root_id": "raw", "path": "lake",
            "kind": "directory", "adapter_id": "sidecar_filing_v1", "reusable_for_filing": True}]}), encoding="utf-8")
    before = raw.read_bytes(), raw.with_name(raw.name + ".source.json").read_bytes()
    observations = []
    describe = SourceVersionReader._describe_version

    def observe(self, *args, **kwargs):
        observations.append(1)
        return describe(self, *args, **kwargs)

    monkeypatch.setattr(SourceVersionReader, "_describe_version", observe)
    code = main(["--config", str(config), "--document-id", ref.document_id,
        "--source-id", ref.source_id, "--content-sha256", ref.content_sha256,
        "--purpose", purpose, "--include-canonical-identity"])
    out = capfdbinary.readouterr()
    assert code == 0, out.err
    receipt = json.loads(out.err)
    assert receipt["canonical_identity"] == {"schema_version": "source-canonical-identity/1",
        "market": "HK", "security_id": "09896"}
    assert receipt["manifest"]["security_id"] == facts["security_id"]
    assert out.out == before[0]
    assert len(observations) == 1
    assert (raw.read_bytes(), raw.with_name(raw.name + ".source.json").read_bytes()) == before


def test_single_observation_reader_keeps_read_policy_pin_validation(indexed):  # noqa: F811
    _, reader, ref, _, _ = indexed
    from company_wiki.source_catalog.source_reader import SourceReadError

    with pytest.raises(SourceReadError, match="invalid_read_policy_pin"):
        reader.open_described_version(ref, expected_read_policy_sha256="malformed")
