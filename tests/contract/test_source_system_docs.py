"""CW-1 contract: entry documents must describe the upstream source-system boundary."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
ENTRY_DOCS = (
    "AGENTS.md",
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/OPERATIONS.md",
    "docs/adr/README.md",
)


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


@pytest.mark.parametrize("relative_path", ENTRY_DOCS)
def test_entry_docs_declare_upstream_boundary(relative_path: str):
    text = _read(relative_path)
    assert "StockWiki" in text
    assert "上游" in text
    assert "投资结论" in text


def test_architecture_declares_source_contract_pipeline():
    text = _read("docs/ARCHITECTURE.md")
    for term in (
        "source manifest",
        "EvidenceSpan",
        "immutable raw",
        "只读 export",
    ):
        assert term in text


def test_operations_disables_research_writers_and_scheduler_steps():
    text = _read("docs/OPERATIONS.md")
    for term in (
        "writer freeze",
        "assess",
        "judgment",
        "禁止运行",
    ):
        assert term in text


def test_adr_scope_note_covers_existing_decisions():
    text = _read("docs/adr/README.md")
    for number in range(1, 7):
        assert f"ADR-{number:03d}" in text
    assert "source/extraction quality" in text
    assert "accepted investment" in text
