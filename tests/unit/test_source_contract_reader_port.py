"""Source contracts accept a narrow backend, without importing a catalog."""
import subprocess
import sys
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_contract import SourceExportBundleV2, SourceExportError
from contract.test_source_export_v2 import _fixture


def test_export_accepts_delegating_read_backend_without_concrete_inheritance(tmp_path):
    catalog, _, _, ref, span = _fixture(tmp_path, text_mode=True)
    reader = SourceVersionReader(catalog)

    class Backend:
        open_version = reader.open_version
        verify_version = reader.verify_version
        describe_version = reader.describe_version

    try:
        assert SourceExportBundleV2.build(source_reader=Backend(), refs=(ref,),
                                         evidence_spans=(span,)).bundle_sha256
    finally:
        catalog.close()


def _pure_identity_contract_probe(*, additional_import=""):
    source_root = Path(__file__).resolve().parents[2] / "src"
    code = '''
import importlib.abc
from pathlib import Path
import sys

class NoCatalogRuntime(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'company_wiki.source_catalog' or fullname.startswith('company_wiki.source_catalog.'):
            raise AssertionError('pure source contract imported catalog runtime: ' + fullname)

source_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(source_root))
sys.meta_path.insert(0, NoCatalogRuntime())
from company_wiki.source_contract import source_version
from company_wiki.source_contract.source_version import SourceRef, VerifiedContent
assert Path(source_version.__file__).resolve() == source_root / 'company_wiki/source_contract/source_version.py'
assert not any(m.startswith('company_wiki.source_catalog') for m in sys.modules)
assert SourceRef and VerifiedContent
'''
    # pytest's conftest changes only this process's sys.path. The fresh probe
    # must bind the candidate tree rather than rely on PYTHONPATH or an older
    # editable install; -S also prevents unrelated site startup dependencies.
    return subprocess.run(
        [sys.executable, '-I', '-S', '-B', '-c', code + additional_import, str(source_root)],
        capture_output=True, text=True, timeout=10,
    )


@pytest.mark.parametrize("inherited_pythonpath", ["absent", "unrelated-tree"])
def test_pure_source_identity_contract_import_has_no_catalog_runtime(
    tmp_path, monkeypatch, inherited_pythonpath,
):
    if inherited_pythonpath == "absent":
        monkeypatch.delenv("PYTHONPATH", raising=False)
    else:
        shadow = tmp_path / "company_wiki"
        shadow.mkdir()
        (shadow / "__init__.py").write_text("raise AssertionError('wrong source tree')\n")
        monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    result = _pure_identity_contract_probe()
    assert result.returncode == 0, result.stderr


def test_pure_source_identity_import_probe_rejects_catalog_dependency():
    result = _pure_identity_contract_probe(additional_import="\nimport company_wiki.source_catalog\n")
    assert result.returncode != 0
    assert "pure source contract imported catalog runtime: company_wiki.source_catalog" in result.stderr


def test_public_backend_cannot_attest_forged_bytes_using_correct_identity_fields(tmp_path):
    catalog, _, _, ref, span = _fixture(tmp_path, text_mode=True)
    reader = SourceVersionReader(catalog)

    class Backend:
        verify_version = reader.verify_version
        describe_version = reader.describe_version

        def open_version(self, ref, *, purpose):
            original = reader.open_version(ref, purpose=purpose)
            # The actual selected quote stays untouched. The altered prefix
            # must still invalidate the whole original.
            assert span.coordinates.char_start > 0 and original.data[0] != 0
            return replace(original, data=b"\x00" + original.data[1:])

    try:
        with pytest.raises(SourceExportError, match='source bytes do not match'):
            SourceExportBundleV2.build(source_reader=Backend(), refs=(ref,), evidence_spans=(span,))
    finally:
        catalog.close()


def test_stream_observation_uses_its_digest_even_if_a_subclass_overrides_reporting():
    from company_wiki.source_contract.source_version import (
        SourceByteVerifier, SourceRef, SourceRefMismatchError, VerifiedContent,
    )

    original = b"real source"
    digest = sha256(original).hexdigest()
    ref = SourceRef("fixture-document", "urn:company-wiki:source:sha256:" + digest,
                    digest, len(original), "text/plain")

    class ReportingOverride(SourceByteVerifier):
        def hexdigest(self):
            return digest

    verifier = ReportingOverride(retain_bytes=True)
    verifier.update(b"fake source")
    with pytest.raises(SourceRefMismatchError, match="source bytes do not match"):
        VerifiedContent.from_observation(
            ref, verifier.observe(), read_at="2026-11-09T00:00:00Z",
            policy_sha256="a" * 64, source_read_policy_sha256="b" * 64,
        )
