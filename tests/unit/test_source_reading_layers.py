"""Small regression checks for the financial-data and PDF reading boundaries.

This examines named production seams only, never historical scripts/worktrees.
Behavioral tests separately exercise interchangeable ports and exact sources.
"""
import ast
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "src/company_wiki"
PDF_CONSUMERS = (
    "narrative_select", "narrative_verify", "narrative_runtime",
    "narrative_batch", "narrative_generation", "narrative_replay",
)


def _imports(tree):
    """Include aliases, relative imports and constant dynamic imports."""
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = item.name
                yield item.name
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                name = "." * node.level + (node.module or "") + "." + item.name
                aliases[item.asname or item.name] = name.lstrip(".")
                yield name
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        target = _name(node.func)
        first, *rest = target.split(".")
        target = ".".join((aliases.get(first, first), *rest))
        if target in {"__import__", "importlib.import_module"}:
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                yield argument.value


def _name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _name(node.value) + "." + node.attr
    return ""


def violations(source, layer):
    tree = ast.parse(source)
    forbidden = {
        "pdf_consumer": {"docling", "pymupdf", "fitz", "torch", "transformers",
                         "narrative_pdf_enhancement", "_paragraph_worker", "financial_statements"},
        "pdf_implementation": {"financial_statements", "httpx", "requests", "sqlite3", "canonical_writer"},
        "statements_service": {"httpx", "requests", "urllib", "sqlite3", "sina_provider",
                               "source_location", "security_master"},
        "statements_storage": {"httpx", "requests", "urllib", "sina_provider"},
        "statements_provider": {"repository", "store", "canonical_writer", "sqlite3"},
    }[layer]
    if layer.startswith("statements_"):
        forbidden = forbidden | {"docling", "pymupdf", "fitz", "narrative_pdf_reading"}
    errors = [f"import:{name}" for name in _imports(tree)
              if set(name.strip(".").split(".")) & forbidden]
    if layer == "statements_service":
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {
                "staging_root", "fetchone", "fetchall", "execute", "executemany",
                "read_bytes", "write_bytes", "read_text", "write_text", "catalog_dir",
            }:
                errors.append(f"storage detail:{node.attr}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and ".source.json" in node.value:
                errors.append("sidecar path")
    if layer == "pdf_consumer":
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and (
                "COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG" in node.value
                or "_paragraph_worker" in node.value
            ):
                errors.append("private PDF deployment")
    return errors


@pytest.mark.parametrize("name", PDF_CONSUMERS)
def test_pdf_consumers_use_reading_port_only(name):
    assert not violations((SOURCE / f"automation/{name}.py").read_text(encoding="utf-8"), "pdf_consumer")


@pytest.mark.parametrize("name", ["narrative_pdf_reading", "narrative_pdf_enhancement",
                                  "narrative_pdf_paragraphs", "_paragraph_worker"])
def test_pdf_owner_never_fetches_financial_data_or_commits_originals(name):
    assert not violations((SOURCE / f"source_catalog/{name}.py").read_text(encoding="utf-8"), "pdf_implementation")


@pytest.mark.parametrize("name,layer", [
    ("service", "statements_service"), ("repository", "statements_storage"),
    ("contracts", "statements_storage"), ("normalize", "statements_storage"),
    ("provider_contracts", "statements_storage"), ("sina_provider", "statements_provider"),
])
def test_statements_layers_do_not_bypass_their_ports(name, layer):
    path = SOURCE / f"source_catalog/financial_statements/{name}.py"
    assert not violations(path.read_text(encoding="utf-8"), layer)


@pytest.mark.parametrize("source,layer", [
    ("import docling.document_converter as hidden", "pdf_consumer"),
    ("from ..source_catalog import _paragraph_worker as hidden", "pdf_consumer"),
    ("import importlib as i; i.import_module('docling.document_converter')", "pdf_consumer"),
    ("from importlib import import_module as load; load('pymupdf')", "pdf_consumer"),
    ("__import__('httpx')", "statements_service"),
    ("from ..source_location import resolve_path", "statements_service"),
    ("writer.staging_root / 'page.json'", "statements_service"),
    ("catalog.store.fetchone('select 1')", "statements_service"),
    ("from .sina_provider import SINA_PROVIDER_ID", "statements_storage"),
    ("from ..canonical_writer import CanonicalSourceWriter", "statements_provider"),
    ("from ..narrative_pdf_reading import PdfReading", "statements_service"),
    ("from .financial_statements import sina_provider", "pdf_implementation"),
])
def test_regression_check_detects_actual_bypasses(source, layer):
    assert violations(source, layer)


@pytest.mark.parametrize("source,layer", [
    ("from ..source_catalog.narrative_pdf_reading import PdfReading", "pdf_consumer"),
    ("from .provider_contracts import StatementsProvider", "statements_service"),
    ("writer.import_third_party_dataset_bytes(data=data)", "statements_service"),
    ("from .contracts import SINA_PROVIDER_ID", "statements_storage"),
])
def test_regression_check_allows_public_ports(source, layer):
    assert not violations(source, layer)
