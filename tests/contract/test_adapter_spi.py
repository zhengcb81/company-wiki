"""WU-501 RED/audit tests: adapter SPI gates (SPI-01..04)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.adapters.interface import (  # noqa: E402
    NormalizedCandidate,
    check_candidate_determinism,
    check_no_duplicate_candidates,
)


def _candidate(path: str, group: str = "g1", sha: str = "h") -> NormalizedCandidate:
    return NormalizedCandidate(
        relative_path=path, content_sha256=sha, group_key=group, role="primary",
    )


def test_spi03_determinism_same_input_passes():
    first = [_candidate("a.pdf"), _candidate("b.pdf")]
    second = [_candidate("a.pdf"), _candidate("b.pdf")]
    assert check_candidate_determinism(first, second) == []


def test_spi03_reordered_output_fails():
    first = [_candidate("a.pdf"), _candidate("b.pdf")]
    second = [_candidate("b.pdf"), _candidate("a.pdf")]
    problems = check_candidate_determinism(first, second)
    assert problems


def test_spi03_hash_change_fails():
    first = [_candidate("a.pdf", sha="h1")]
    second = [_candidate("a.pdf", sha="h2")]
    assert check_candidate_determinism(first, second)


def test_spi03b_duplicate_candidates_rejected():
    candidates = [_candidate("a.pdf"), _candidate("a.pdf")]
    assert check_no_duplicate_candidates(candidates)


def test_spi04_unknown_root_no_fallback():
    """SPI-04: an unknown root must fail closed — it may never fall into a
    last-resort adapter.  The facade (WU-500) enforces this for v2; the v1
    path must also reject unknown kinds."""
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.models import ROOT_KINDS

    assert "unknown_kind" not in ROOT_KINDS
    import yaml

    payload = {
        "schema_version": "1.0",
        "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
        "roots": [
            {"root_id": "weird", "path": "${PROJECT_ROOT}/w",
             "kind": "unknown_kind", "adapter_id": "sidecar_filing_v1"},
        ],
    }
    cfg = Path("tests/fixtures") / "tmp_spi4.yaml"
    cfg.write_text(yaml.safe_dump(payload), encoding="utf-8")
    try:
        with pytest.raises(Exception):  # unsupported kind must fail closed
            load_catalog_config(cfg, project_root=Path("tests/fixtures"))
    finally:
        cfg.unlink(missing_ok=True)


def test_spi01_adapter_imports_are_pure():
    """SPI-01/ARC-FIT-02: adapter modules must not import store/resolver/
    download/parser/LLM."""
    import ast

    source = (Path(__file__).resolve().parents[2] / "src" /
              "company_wiki" / "source_catalog" / "adapters" /
              "interface.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    forbidden = {"store", "resolver", "download", "parser", "llm"}
    assert not (imports & forbidden)


# SPI-02 (reviewer F2): the scanner must never GAIN root-specific literal
# branches.  Existing dayu branches (3) are frozen legacy — Phase 15 removes
# them; any increase fails the gate.
_FROZEN_SCANNER_ROOT_BRANCHES = 7


def test_spi02_scanner_root_branch_freeze():
    import re

    source = (Path(__file__).resolve().parents[2] / "src" /
              "company_wiki" / "source_catalog" / "scanner.py").read_text(encoding="utf-8")
    patterns = (
        r'kind\s*==\s*"dayu_portfolio"',
        r'root_id\s*==\s*"dropbox_stock"',
        r'kind\s*==\s*"directory"',
        r'root\.kind\s*==\s*"company_raw"',
    )
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, source))
    assert total <= _FROZEN_SCANNER_ROOT_BRANCHES, (
        f"scanner gained root-specific branches: {total} > {_FROZEN_SCANNER_ROOT_BRANCHES}"
    )
