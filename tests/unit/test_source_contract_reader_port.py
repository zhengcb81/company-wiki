"""Source contracts accept a narrow backend, without importing a catalog."""
import os
import subprocess
import sys
from dataclasses import replace

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


def test_pure_source_identity_contract_import_has_no_catalog_runtime():
    code = '''
import sys
from company_wiki.source_contract.source_version import SourceRef, VerifiedContent
assert not any(m.startswith('company_wiki.source_catalog') for m in sys.modules)
assert SourceRef and VerifiedContent
'''
    result = subprocess.run([sys.executable, '-B', '-c', code], env=os.environ.copy(),
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_public_backend_cannot_attest_forged_bytes_using_correct_identity_fields(tmp_path):
    catalog, _, _, ref, span = _fixture(tmp_path, text_mode=True)
    reader = SourceVersionReader(catalog)

    class Backend:
        verify_version = reader.verify_version
        describe_version = reader.describe_version

        def open_version(self, ref, *, purpose):
            original = reader.open_version(ref, purpose=purpose)
            return replace(original, data=b'x' * len(original.data))

    try:
        with pytest.raises(SourceExportError, match='source bytes do not match'):
            SourceExportBundleV2.build(source_reader=Backend(), refs=(ref,), evidence_spans=(span,))
    finally:
        catalog.close()
