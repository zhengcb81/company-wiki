"""Exercise the CI scratch lifecycle with a real pytest child."""

from pathlib import Path
import shutil
import sys

import pytest

from tools.run_ci_evidence import execute_tests


@pytest.mark.parametrize("expected_exit", [0, 1])
def test_ci_reclaims_scratch_after_pytest_releases_open_sqlite(
    expected_exit, tmp_path, tmp_path_factory, monkeypatch,
):
    repository = Path(__file__).resolve().parents[2]
    project = tmp_path / "project"
    project.mkdir()
    shutil.copyfile(repository / "conftest.py", project / "conftest.py")
    (project / "pytest.ini").touch()
    witness = tmp_path / "scratch.txt"
    long_temp = tmp_path / ("pytest-temp-" + "a" * 54)
    long_temp.mkdir()
    for name in ("TMP", "TEMP", "TMPDIR"):
        monkeypatch.setenv(name, str(long_temp))
    monkeypatch.setenv("CW_BASETEMP_FALLBACK_ROOT", str(tmp_path_factory.getbasetemp()))
    monkeypatch.delenv("CW_SHORT_BASETEMP_DISABLE", raising=False)
    monkeypatch.delenv("CW_BASETEMP_DECISION_FILE", raising=False)
    monkeypatch.setenv("PYTHONPATH", str(repository))
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.setenv("S6_TEST_SCRATCH_WITNESS", str(witness))
    monkeypatch.chdir(project)
    (project / "test_child.py").write_text(
        "import os, sqlite3\n"
        "from pathlib import Path\n"
        "\n"
        "def test_real_sqlite_handle(tmp_path_factory):\n"
        "    global connection\n"
        "    scratch = tmp_path_factory.getbasetemp()\n"
        "    database = scratch / 'held.sqlite3'\n"
        "    connection = sqlite3.connect(database)\n"
        "    connection.execute('CREATE TABLE held (id INTEGER)')\n"
        "    Path(os.environ['S6_TEST_SCRATCH_WITNESS']).write_text("
        "str(scratch), encoding='utf-8')\n"
        f"    assert {expected_exit} == 0\n",
        encoding="utf-8",
    )
    base = [
        sys.executable, "-B", "-m", "pytest", "-q", "-p", "pytest_timeout",
        "-p", "tools.anti_trick_gate_spec.pytest_probe", "--s6-revision", "scratch-fixture",
    ]

    assert execute_tests(base, ["test_child.py"], tmp_path) == expected_exit
    scratch = Path(witness.read_text(encoding="utf-8"))
    assert (tmp_path / "tests.xml").is_file()
    assert (tmp_path / "executed.json").is_file()
    assert not scratch.exists()
    assert not any(tmp_path_factory.getbasetemp().glob(".cwci-*"))
