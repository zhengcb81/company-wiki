"""Packaging contract: a clean install must expose the canonical src package."""

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_setuptools_backend_is_importable_standard_backend():
    data = load_pyproject()
    assert data["build-system"]["build-backend"] in {
        "setuptools.build_meta",
        "setuptools.build_meta:__legacy__",
    }


def test_package_discovery_uses_src_layout_and_includes_company_wiki():
    data = load_pyproject()
    setuptools = data["tool"]["setuptools"]
    assert setuptools["package-dir"] == {"": "src"}
    find = setuptools["packages"]["find"]
    assert find["where"] == ["src"]
    assert "company_wiki*" in find["include"]


def test_canonical_package_has_init_file():
    assert (ROOT / "src" / "company_wiki" / "__init__.py").is_file()


def test_pytest_has_one_configuration_source():
    data = load_pyproject()
    assert (ROOT / "pytest.ini").is_file()
    assert "pytest" not in data.get("tool", {})
