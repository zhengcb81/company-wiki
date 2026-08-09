"""WU-803 RED/audit tests: resolver→bundle 接合 — zero side effects +
snapshot consistency."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.artifact_dag import bundle_snapshot_match  # noqa: E402


def test_bundle_query_has_no_write_imports():
    """WU-803: bundle query must not trigger parser/LLM/writes."""
    import ast

    source = (Path(__file__).resolve().parents[2] / "src" /
              "company_wiki" / "source_catalog" /
              "source_bundle.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    forbidden = {"parser", "llm", "summarizer", "requests", "urllib"}
    assert not (imports & forbidden)


def test_snapshot_consistency_contract():
    """filing 与 artifact 必须同 snapshot；错配 → STALE_BUNDLE。"""
    assert bundle_snapshot_match(filing_snapshot="snap-1",
                                 artifact_snapshot="snap-1")
    assert not bundle_snapshot_match(filing_snapshot="snap-1",
                                     artifact_snapshot="snap-2")


def test_bundle_roles_deterministic_selection():
    from company_wiki.source_catalog.artifact_dag import select_artifacts

    artifacts = [
        {"role": "normalized", "status": "completed",
         "input_document_hash": "h", "schema_version": "2.0"},
        {"role": "summary", "status": "completed",
         "input_document_hash": "h", "schema_version": "2.0"},
    ]
    selected, rejected = select_artifacts(artifacts, document_hash="h")
    assert selected == ["normalized", "summary"]
    assert rejected == []
