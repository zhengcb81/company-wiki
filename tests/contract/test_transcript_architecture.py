"""Keep the transcript import path small and free of retired approval layers."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "company_wiki" / "source_catalog"

ACTIVE_MODULES = {
    "transcript_tool_contract.py",
    "transcript_import.py",
    "transcript_import_cli.py",
    "transcript_material.py",
    "transcript_lineage.py",
    "transcript_text_extract.py",
}
RETIRED_POLICY_MODULES = {
    "provider_use_policy.py",
    "transcript_use_policy.py",
    "transcript_fetch_admission.py",
    "transcript_fetch_validation.py",
    "transcript_preflight_service.py",
    "transcript_admission_service.py",
}
LEGACY_COMPLEXITY_FREEZES = {
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


def test_transcript_import_path_uses_the_small_active_module_set() -> None:
    missing = sorted(name for name in ACTIVE_MODULES if not (SOURCE / name).is_file())
    retired = sorted(name for name in RETIRED_POLICY_MODULES if (SOURCE / name).exists())
    assert not missing, f"missing active transcript modules: {missing}"
    assert not retired, f"retired transcript policy layers remain: {retired}"


def test_active_transcript_importer_does_not_import_retired_policy_layers() -> None:
    retired_names = {Path(name).stem for name in RETIRED_POLICY_MODULES}
    failures: list[str] = []
    for name in ("transcript_tool_contract.py", "transcript_import.py", "transcript_import_cli.py"):
        found = sorted(_local_imports(SOURCE / name) & retired_names)
        if found:
            failures.append(f"{name}: {found}")
    assert not failures, "retired transcript policy imports: " + "; ".join(failures)


def test_transcript_pipeline_is_not_kept_in_a_complexity_freeze() -> None:
    ratchet = ROOT / "tests" / "contract" / "test_fc1204_complexity_ratchet.py"
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
