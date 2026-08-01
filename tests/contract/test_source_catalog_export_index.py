"""Contracts for the human-readable source-catalog index.md duplicate surfacing."""

from __future__ import annotations

from pathlib import Path


def _catalog_module():
    import company_wiki.source_catalog as module

    return module


def _build_catalog(tmp_path: Path, files: list[tuple[str, bytes]]):
    """Create a catalog with the given (root_name, content) files and scan it."""
    module = _catalog_module()
    project = tmp_path / "project"
    roots = sorted({name for name, _ in files})
    root_paths = {name: tmp_path / name for name in roots}
    for name in roots:
        root_paths[name].mkdir(parents=True, exist_ok=True)
    for index, (root_name, content) in enumerate(files):
        (root_paths[root_name] / f"doc-{index}.pdf").write_bytes(content)
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=tuple(
                module.RootSpec(f"root_{name}", root_paths[name], "directory", priority=10 + index * 10)
                for index, name in enumerate(roots)
            ),
        )
    )
    catalog.scan()
    return module, catalog


def test_index_md_lists_exact_duplicate_groups(tmp_path):
    content = b"ACME FY2025 audited annual report body."
    module, catalog = _build_catalog(
        tmp_path,
        [
            ("primary", content),
            ("secondary", content),  # same bytes, different filename/root
            ("tertiary", content),
        ],
    )

    exported = catalog.export_indexes()
    index_md = Path(exported["index_md"]).read_text(encoding="utf-8")

    assert "## Duplicate groups" in index_md
    # Three identical copies -> one group, copy_count == 3, 2 reclaimable copies.
    assert "| 3 |" in index_md


def test_index_md_handles_no_duplicate_groups(tmp_path):
    module, catalog = _build_catalog(
        tmp_path,
        [
            ("primary", b"unique document one content"),
            ("primary", b"unique document two content"),
        ],
    )

    exported = catalog.export_indexes()
    index_md = Path(exported["index_md"]).read_text(encoding="utf-8")

    assert "## Duplicate groups" in index_md
    assert "_No exact-copy duplicate groups._" in index_md
