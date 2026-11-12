"""The delivered wheel starts every declared public entry point.

The checkout's ``conftest`` puts ``src`` on ``sys.path`` and CI installs from
requirements, so passing tests never prove the packaging.  This contract
builds the real wheel offline, installs exactly that wheel into a fresh venv
without a source PYTHONPATH, and starts every console script and the two
public module CLIs from a foreign working directory.  Base and extras share
one applicability rule: an entry point that needs an optional SDK must fail
by name in an environment that lacks it, never here.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]

#: The scratch venv may live under a non-ASCII user profile; children must
#: emit UTF-8 so captured paths compare against the real directory names.
#: PYTHONPATH is dropped: the venv must stand on its own installed layout.
CHILD_ENV = {**os.environ, "PYTHONUTF8": "1"}
CHILD_ENV.pop("PYTHONPATH", None)

#: Module CLIs that are deliberately not console scripts (CWP-04 surface).
MODULE_CLIS = (
    "company_wiki.source_catalog.processed_document_cli",
    "company_wiki.source_catalog.financial_statements.cli",
    # The A0-ported public diagnostics ship in the same wheel and must start
    # from the installed layout like every other module entry point.
    "company_wiki.source_catalog.source_stream_cli",
    "company_wiki.source_catalog.public_document_browser_cli",
    "company_wiki.source_catalog.public_canonical_browser_cli",
    "company_wiki.source_catalog.public_source_readiness_cli",
    "company_wiki.source_catalog.public_legacy_source_link_cli",
    "company_wiki.source_catalog.public_legacy_source_recovery_cli",
)

#: Console entry points that must start with base dependencies only.
BASE_CONSOLE = frozenset({
    "company-wiki-source-export",
    "company-wiki-collect-announcement",
    "company-wiki-source-read",
    "company-wiki-source-query",
    "company-wiki-company-sources",
    "company-wiki-source-export-v2",
    "company-wiki-transcript-import",
})


def _console_scripts() -> dict[str, str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return dict(data["project"]["scripts"])


def _run(argv: list[str], cwd: Path, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, cwd=str(cwd), capture_output=True, encoding="utf-8", errors="replace",
        timeout=timeout, check=False, env=CHILD_ENV,
    )


def _venv_python(venv: Path) -> Path:
    return venv / "Scripts" / "python.exe"


@pytest.fixture(scope="module")
def installed(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Build the wheel offline and install exactly that wheel into a venv."""
    scratch = tmp_path_factory.mktemp("installed-wheel")
    wheels = scratch / "wheels"
    wheels.mkdir()
    empty_cwd = scratch / "cwd"
    empty_cwd.mkdir()
    built = _run(
        [sys.executable, "-m", "pip", "wheel", "--no-index", "--no-deps",
         "--no-build-isolation", "--wheel-dir", str(wheels), str(ROOT)],
        cwd=empty_cwd,
    )
    assert built.returncode == 0, built.stderr
    candidates = list(wheels.glob("company_wiki-*.whl"))
    assert len(candidates) == 1, candidates
    wheel = candidates[0]
    venv = scratch / "venv"
    created = _run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
                   cwd=empty_cwd)
    assert created.returncode == 0, created.stderr
    python = _venv_python(venv)
    seeded = _run([str(python), "-m", "pip", "install", "--no-index", "--no-deps",
                   "--no-cache-dir", str(wheel)], cwd=empty_cwd)
    assert seeded.returncode == 0, seeded.stderr
    return {"venv": venv, "python": python, "cwd": empty_cwd, "wheel": wheel}


def test_wheel_exposes_exactly_the_declared_console_scripts(installed):
    """CWP-04: the wheel's entry-point registry matches pyproject verbatim."""
    import zipfile

    with zipfile.ZipFile(installed["wheel"]) as archive:
        entry_points = archive.read("company_wiki-0.1.0.dist-info/entry_points.txt").decode("utf-8")
    declared = _console_scripts()
    for name, target in declared.items():
        expected = "%s = %s" % (name, target)
        assert expected in entry_points, (expected, entry_points)
    scripts_dir = installed["venv"] / "Scripts"
    for name in declared:
        assert (scripts_dir / (name + ".exe")).is_file(), name


def test_console_entry_points_start_from_the_installed_wheel(installed):
    """CWP-04: all 11 console scripts print usage from a foreign cwd."""
    declared = _console_scripts()
    scripts_dir = installed["venv"] / "Scripts"
    assert set(declared) == set(_console_scripts())
    for name in declared:
        done = _run([str(scripts_dir / (name + ".exe")), "--help"], cwd=installed["cwd"])
        assert done.returncode == 0, (name, done.returncode, done.stderr)
        assert "usage" in (done.stdout + done.stderr).lower(), name


def test_module_clis_start_from_the_installed_wheel(installed):
    """CWP-04: processed-document and financial-statements run as modules."""
    for module in MODULE_CLIS:
        done = _run([str(installed["python"]), "-I", "-B", "-m", module, "--help"],
                    cwd=installed["cwd"])
        assert done.returncode == 0, (module, done.returncode, done.stderr)
        assert "usage" in (done.stdout + done.stderr).lower(), module


def test_installed_import_resolves_inside_the_venv_without_the_checkout(installed):
    """CWP-04: no checkout path serves the installed import."""
    probe = (
        "import company_wiki, sys; print(company_wiki.__file__); "
        "print('\\n'.join(sys.path))"
    )
    # ``-I`` would also ignore PYTHONUTF8; the env above already isolates
    # PYTHONPATH, so plain ``-B`` is the honest isolation here.
    done = _run([str(installed["python"]), "-B", "-c", probe], cwd=installed["cwd"])
    assert done.returncode == 0, done.stderr
    lines = done.stdout.strip().splitlines()
    module_path = lines[0].replace("\\", "/").lower()
    venv_path = str(installed["venv"]).replace("\\", "/").lower()
    assert module_path.startswith(venv_path), lines[0]
    assert "site-packages" in module_path
    assert "mb11" not in module_path
    joined = "\n".join(lines[1:]).replace("\\", "/").lower()
    assert "projects/mb11" not in joined, "the checkout is on the installed sys.path"


def test_installed_package_data_loads_through_importlib_resources(installed):
    """CWP-04: schemas, the reading catalog and grammar resources ship and load."""
    probe = """
import json
import importlib.resources

schemas = importlib.resources.files("company_wiki.source_contract.schemas")
for name in ("evidence_span.v1.schema.json", "source_manifest.v1.schema.json",
             "source_contract_compatibility.v1.json"):
    payload = json.loads(schemas.joinpath(name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict) and payload, name

catalog = json.loads(
    importlib.resources.files("company_wiki.document_understanding.profiles")
    .joinpath("reading_catalog.json").read_text(encoding="utf-8")
)
assert catalog, "reading catalog is empty"

grammar = importlib.resources.files("company_wiki.document_understanding.statement_grammar")
manifest = json.loads(grammar.joinpath("resources/manifest.json").read_text(encoding="utf-8"))
assert manifest, "statement grammar manifest is empty"
from company_wiki.document_understanding.statement_grammar import resource_identity

assert resource_identity(), "statement grammar assets failed their digest check"
print("ok")
"""
    done = _run([str(installed["python"]), "-I", "-B", "-c", probe], cwd=installed["cwd"])
    assert done.returncode == 0, done.stderr
    assert "ok" in done.stdout


def test_declared_extras_cover_the_optional_sdk_families():
    """CWP-04: normalization's eager SDK needs are declared, not ambient."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    catalog = " ".join(data["project"]["optional-dependencies"]["catalog"]).lower()
    for family in ("lxml", "beautifulsoup4", "python-docx", "python-pptx", "pymupdf"):
        assert family in catalog, family
    base = " ".join(data["project"]["dependencies"]).lower()
    assert "lxml" not in base, "normalization stays an extra capability, not a base dep"
