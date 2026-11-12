"""Module owner isolation: neutral ports must not reach a concrete runtime.

Each test in this file proves one boundary by refusing the concrete runtime
in a fresh process and then using the neutral port.  A refusal that comes from
a missing third-party dependency, a sandbox permission, or a fixture mistake
is an environment failure, not a product result; the probes therefore block
only modules this repository owns.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"


def run_probe(probe: str, *args: str, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, str(SOURCE_ROOT), *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


_REFUSING_IMPORTER = '''
import sys


class RefuseRuntime:
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == prefix or fullname.startswith(prefix + ".")
               for prefix in sys.argv[2:]):
            raise AssertionError("concrete runtime reached: " + fullname)
        return None


sys.meta_path.insert(0, RefuseRuntime())
sys.path.insert(0, sys.argv[1])
'''


# --------------------------------------------------------------------------
# CWP-03: the neutral verified-source guard must not import catalog runtime
# --------------------------------------------------------------------------

GUARD_PROBE = _REFUSING_IMPORTER + '''
from company_wiki.automation import narrative_source_guard
from company_wiki.source_contract import SourceRef, VerifiedContent

assert narrative_source_guard.SourceRef is SourceRef
assert narrative_source_guard.VerifiedContent is VerifiedContent
assert not any(
    name == "company_wiki.source_catalog.resolver"
    or name == "company_wiki.source_catalog.service"
    or name == "company_wiki.source_catalog.store"
    or name == "company_wiki.source_catalog.source_reader"
    for name in sys.modules
), sorted(name for name in sys.modules if name.startswith("company_wiki.source_catalog"))

ref = SourceRef(
    document_id="ENT_00000000-0000-4000-8000-000000000001",
    source_id="urn:company-wiki:source:sha256:" + "a" * 64,
    content_sha256="a" * 64,
    byte_size=4,
    mime_type="text/plain",
)
opened = VerifiedContent(
    document_id=ref.document_id,
    source_id=ref.source_id,
    content_sha256=ref.content_sha256,
    data=b"body",
    byte_size=ref.byte_size,
    read_at="2026-11-12T00:00:00Z",
    policy_sha256="p" * 64,
    source_read_policy_sha256="q" * 64,
)


class ProtocolReader:
    """A reader with only the two protocol members the guard may use."""

    def open_version(self, requested, *, purpose,
                     expected_read_policy_sha256=None):
        assert requested == ref
        assert purpose == "narrative_derivation"
        return opened

    def describe_version(self, requested):
        assert requested == ref
        return {
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "content_sha256": ref.content_sha256,
            "byte_size": ref.byte_size,
            "mime_type": ref.mime_type,
        }


class Event:
    source_ref = ref
    expected_read_policy_sha256 = None


payload = Event()
guard = narrative_source_guard
assert guard.validate_opened_source(ref, opened, expected_read_policy_sha256=None) is None
assert guard.open_verified_source(ProtocolReader(), payload) is opened
assert guard.source_ref(payload) == ref
print("ok")
'''


def test_source_guard_imports_without_catalog_runtime():
    """CWP-03: the neutral guard loads with no catalog runtime present."""
    completed = run_probe(
        GUARD_PROBE,
        "company_wiki.source_catalog.resolver",
        "company_wiki.source_catalog.service",
        "company_wiki.source_catalog.store",
        "company_wiki.source_catalog.source_reader",
    )
    assert completed.returncode == 0, completed.stderr
    assert "ok" in completed.stdout


def test_narrative_transport_imports_without_catalog_runtime():
    """CWP-03: the transport's neutral types come from the contract owner."""
    completed = run_probe(
        _REFUSING_IMPORTER + '''
from company_wiki.automation import narrative_transport
from company_wiki.source_contract import SourceRef, VerifiedContent

assert narrative_transport.SourceRef is SourceRef
assert narrative_transport.VerifiedContent is VerifiedContent
print("ok")
''',
        "company_wiki.source_catalog.resolver",
        "company_wiki.source_catalog.source_reader",
    )
    assert completed.returncode == 0, completed.stderr
    assert "ok" in completed.stdout


def test_source_contract_owns_the_neutral_source_types():
    """CWP-03: the contract owner is the single definition site."""
    from company_wiki import source_contract
    from company_wiki.source_contract import SourceRef, VerifiedContent

    assert source_contract.SourceRef is SourceRef
    assert source_contract.VerifiedContent is VerifiedContent
    assert SourceRef.__module__ == "company_wiki.source_contract.source_version"
    assert VerifiedContent.__module__ == "company_wiki.source_contract.source_version"


# --------------------------------------------------------------------------
# CWP-01: the transport must not read OCR configuration out of its reader
# --------------------------------------------------------------------------

TRANSPORT_OCR_PROBE = _REFUSING_IMPORTER + '''
from company_wiki.automation import narrative_transport
from company_wiki.source_catalog import narrative_normalization

assert not hasattr(narrative_normalization.NarrativeNormalization, "from_reader"), (
    "no reader-shaped configuration back channel may survive"
)
assert hasattr(narrative_normalization.NarrativeNormalization, "from_project")
assert hasattr(narrative_normalization.NarrativeNormalization, "from_snapshot")
assert hasattr(narrative_normalization.NarrativeNormalization, "deferred_from_project")
print("ok")
'''


def test_transport_has_no_reader_back_channel_for_configuration():
    """CWP-01: no reader-shaped configuration back channel survives."""
    completed = run_probe(
        TRANSPORT_OCR_PROBE,
        "company_wiki.source_catalog.resolver",
        "company_wiki.source_catalog.source_reader",
    )
    assert completed.returncode == 0, completed.stderr
    assert "ok" in completed.stdout


# --------------------------------------------------------------------------
# CWP-02: PDF selection must take its work budget from an injected port
# --------------------------------------------------------------------------

BUDGET_PROBE = _REFUSING_IMPORTER + '''
import company_wiki.source_catalog.narrative_selection as selection

assert not hasattr(selection, "new_document_work_budget"), (
    "the selection module must not own a global budget factory"
)
import inspect

signature = inspect.signature(selection.RawNarrativeSelector.__init__)
assert "work_budget_factory" in signature.parameters, signature
print("ok")
'''


def test_raw_selector_does_not_own_a_global_budget_factory():
    """CWP-02: the selector takes a budget port instead of reading config."""
    completed = run_probe(BUDGET_PROBE)
    assert completed.returncode == 0, completed.stderr
    assert "ok" in completed.stdout


@pytest.mark.parametrize(
    "module",
    [
        "company_wiki.source_catalog.narrative_selection",
        "company_wiki.source_catalog.narrative_evidence",
        "company_wiki.source_catalog.narrative_reading",
    ],
)
def test_document_reading_modules_import_without_a_budget_policy_file(module):
    """CWP-02: importing a reading module never needs a budget policy file.

    An installed wheel ships no repository ``config/`` directory, so a module
    that resolved its ceiling at import time could not start there.
    """
    completed = run_probe(
        _REFUSING_IMPORTER
        + f'''
import importlib
import os

os.environ.pop("COMPANY_WIKI_BUDGET_CONFIG", None)
importlib.import_module({module!r})
print("ok")
'''
    )
    assert completed.returncode == 0, completed.stderr
    assert "ok" in completed.stdout


def test_budget_policy_file_is_not_inside_the_installed_package():
    """CWP-02: the ceiling is deployment configuration, not package data."""
    from company_wiki import resource_budget

    package_root = Path(resource_budget.__file__).resolve().parents[1]
    assert not (package_root / "config" / "resource_budget.yaml").is_file()
    assert resource_budget.budget_policy_path().parent.name == "config"


# --------------------------------------------------------------------------
# CWP-04: base entry points must start without any optional SDK
# --------------------------------------------------------------------------

_BASE_CONSOLE_MODULES = (
    "company_wiki.source_contract.cli",
    "company_wiki.source_catalog.announcement_cli",
    "company_wiki.source_catalog.source_reader_cli",
    "company_wiki.source_catalog.source_query_cli",
    "company_wiki.source_catalog.company_source_index_cli",
    "company_wiki.source_catalog.source_export_v2_cli",
    "company_wiki.source_catalog.transcript_import_cli",
)


@pytest.mark.parametrize("module", _BASE_CONSOLE_MODULES)
def test_base_console_modules_import_without_optional_sdks(module):
    """CWP-04: the seven base entry points never load an optional SDK."""
    completed = run_probe(
        _REFUSING_IMPORTER
        + f'''
import importlib

importlib.import_module({module!r})
print("ok")
''',
        "pymupdf",
        "fitz",
        "docx",
        "pptx",
        "openpyxl",
        "xlrd",
        "opencc",
        "bs4",
        "markdownify",
        "langid",
        "docling",
        "cryptography",
        "playwright",
    )
    assert completed.returncode == 0, completed.stderr
    assert "ok" in completed.stdout
