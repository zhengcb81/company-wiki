"""Changed executable tests are consumers themselves, not unknown runtime."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.changed_unit_tests import select_unit_tests  # noqa: E402


def write(root: Path, relative: str, source: str = "def test_case():\n    assert True\n"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize("suite", ["contract", "integration", "e2e"])
def test_changed_test_module_runs_directly_without_full_units(tmp_path, suite):
    relative = f"tests/{suite}/test_changed.py"
    write(tmp_path, relative)
    write(tmp_path, "tests/unit/test_unrelated.py")
    selected, _ = select_unit_tests(tmp_path, {relative, "docs/plans/current/progress.md"})
    assert selected == [relative]


def test_known_unit_consumer_of_changed_contract_is_kept(tmp_path):
    relative = "tests/contract/test_shared.py"
    write(tmp_path, relative, "VALUE = 3\n")
    write(tmp_path, "tests/unit/test_consumer.py", "from tests.contract.test_shared import VALUE\n")
    selected, _ = select_unit_tests(tmp_path, {relative})
    assert selected == [relative, "tests/unit/test_consumer.py"]


def test_unknown_runtime_is_not_hidden_by_changed_contract(tmp_path):
    relative = "tests/contract/test_contract.py"
    write(tmp_path, relative)
    write(tmp_path, "src/new_runtime.py", "VALUE = 2\n")
    assert select_unit_tests(tmp_path, {relative, "src/new_runtime.py"})[0] == ["tests/unit"]


def test_shared_test_configuration_keeps_full_fallback(tmp_path):
    relative = "tests/contract/test_contract.py"
    write(tmp_path, relative)
    write(tmp_path, "tests/contract/conftest.py", "VALUE = 2\n")
    assert select_unit_tests(tmp_path, {relative, "tests/contract/conftest.py"})[0] == ["tests/unit"]


def test_deleted_test_module_keeps_unknown_dependency_fallback(tmp_path):
    assert select_unit_tests(tmp_path, {"tests/contract/test_deleted.py"})[0] == ["tests/unit"]


def test_runtime_change_still_selects_its_unit_consumers(tmp_path):
    write(tmp_path, "src/calculation.py", "VALUE = 1\n")
    write(tmp_path, "tests/unit/test_calculation.py", "from calculation import VALUE\n")
    assert select_unit_tests(tmp_path, {"src/calculation.py"})[0] == ["tests/unit/test_calculation.py"]
