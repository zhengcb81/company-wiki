"""Contract tests for immutable original source documents."""

from pathlib import Path

import pytest

import common
from source_policy import (
    ContentPathKind,
    SourceMutationError,
    assert_content_writable,
    classify_content_path,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "relative",
    [
        "companies/示例公司/raw/news/item.md",
        "companies/示例公司/raw/report.pdf",
        "companies/示例公司/2025年年度报告.pdf",
        "sectors/半导体/raw/research.pdf",
        "themes/国产替代/raw/source.md",
    ],
)
def test_original_source_paths_are_immutable(tmp_path: Path, relative: str) -> None:
    path = tmp_path / Path(relative)
    assert classify_content_path(path, tmp_path) is ContentPathKind.ORIGINAL_SOURCE
    with pytest.raises(SourceMutationError, match="immutable original source"):
        assert_content_writable(path, tmp_path)


@pytest.mark.unit
@pytest.mark.parametrize(
    "relative",
    [
        "companies/示例公司/wiki/overview.md",
        "companies/示例公司/extracts/report.md",
        "companies/示例公司/segments/report.jsonl",
        "sectors/半导体/wiki/overview.md",
        "themes/国产替代/wiki/overview.md",
    ],
)
def test_derived_paths_are_mutable(tmp_path: Path, relative: str) -> None:
    path = tmp_path / Path(relative)
    assert classify_content_path(path, tmp_path) is ContentPathKind.DERIVED_ARTIFACT
    assert_content_writable(path, tmp_path)


@pytest.mark.unit
def test_ambiguous_entity_content_fails_closed(tmp_path: Path) -> None:
    ambiguous = tmp_path / "sectors" / "半导体" / "unclassified" / "document.md"
    assert classify_content_path(ambiguous, tmp_path) is ContentPathKind.ORIGINAL_SOURCE
    with pytest.raises(SourceMutationError):
        assert_content_writable(ambiguous, tmp_path)


@pytest.mark.unit
def test_traversal_from_derived_directory_into_raw_is_rejected(tmp_path: Path) -> None:
    disguised = (
        tmp_path
        / "companies"
        / "示例公司"
        / "wiki"
        / ".."
        / "raw"
        / "report.pdf"
    )

    assert classify_content_path(disguised, tmp_path) is ContentPathKind.ORIGINAL_SOURCE
    with pytest.raises(SourceMutationError):
        assert_content_writable(disguised, tmp_path)


@pytest.mark.unit
def test_common_writers_enforce_source_policy(tmp_path: Path, monkeypatch) -> None:
    raw_file = tmp_path / "companies" / "示例公司" / "raw" / "news.md"
    raw_file.parent.mkdir(parents=True)
    monkeypatch.setattr(common, "WIKI_ROOT", tmp_path)

    with pytest.raises(SourceMutationError):
        common.atomic_write(raw_file, "must not be written")
    assert not raw_file.exists()

    assert common.safe_write_file(raw_file, "must not be written") is False
    assert not raw_file.exists()
