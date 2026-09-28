"""Phase D: transcript/provider layers stay small and one directional."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "company_wiki" / "source_catalog"

EXPECTED_MODULES = {
    "transcript_use_policy.py",
    "transcript_fetch_admission.py",
    "transcript_fetch_validation.py",
    "transcript_tool_contract.py",
    "transcript_admission_service.py",
    "transcript_text_extract.py",
    "transcript_lineage.py",
    "transcript_preflight_service.py",
}

FORBIDDEN_IMPORTS = {
    "provider_use_policy.py": {
        "acquisition",
        "authorization",
        "canonical_writer",
        "resolver",
        "sqlite3",
        "stat",
        "subprocess",
        "tempfile",
    },
    "transcript_use_policy.py": {
        "canonical_writer",
        "config",
        "sqlite3",
        "subprocess",
        "tempfile",
    },
    "transcript_fetch_admission.py": {
        "canonical_writer",
        "config",
        "sqlite3",
        "subprocess",
        "tempfile",
    },
    "transcript_fetch_validation.py": {
        "canonical_writer",
        "config",
        "sqlite3",
        "subprocess",
        "tempfile",
    },
    "transcript_tool_contract.py": {
        "canonical_writer",
        "config",
        "pathlib",
        "sqlite3",
        "subprocess",
        "tempfile",
    },
    "transcript_text_extract.py": {
        "canonical_writer",
        "config",
        "sqlite3",
        "subprocess",
        "tempfile",
    },
    "transcript_lineage.py": {
        "canonical_writer",
        "config",
        "sqlite3",
        "subprocess",
        "tempfile",
    },
}

LEGACY_COMPLEXITY_FREEZES = {
    "provider_use_policy.py",
    "transcript_import.py",
    "transcript_import_cli.py",
    "transcript_material.py",
}


def _local_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.rsplit(".", maxsplit=1)[-1])
        elif isinstance(node, ast.Import):
            imports.update(alias.name.rsplit(".", maxsplit=1)[-1] for alias in node.names)
    return imports


def test_phase_d_modules_exist() -> None:
    missing = sorted(name for name in EXPECTED_MODULES if not (SOURCE / name).is_file())
    assert not missing, f"missing Phase D layers: {missing}"


def test_transcript_layers_do_not_import_forbidden_dependencies() -> None:
    failures: list[str] = []
    for name, forbidden in FORBIDDEN_IMPORTS.items():
        path = SOURCE / name
        if not path.is_file():
            failures.append(f"{name}: missing")
            continue
        found = sorted(_local_imports(path) & forbidden)
        if found:
            failures.append(f"{name}: {found}")
    assert not failures, "forbidden transcript dependencies: " + "; ".join(failures)


def test_phase_d_legacy_complexity_freezes_are_removed() -> None:
    ratchet = (ROOT / "tests" / "contract" / "test_fc1204_complexity_ratchet.py")
    tree = ast.parse(ratchet.read_text(encoding="utf-8"))
    frozen: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            frozen.update(
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            )
    assert not (LEGACY_COMPLEXITY_FREEZES & frozen)
