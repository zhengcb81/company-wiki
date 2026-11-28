"""An opt-in owner's raw roots are never touched by pytest discovery."""

import runpy
import sqlite3
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("recipe", [
    "test_lt_uj_real_e2e.py",
    "test_zr409_fourth_root_real_journeys.py",
])
def test_collecting_a_real_data_recipe_never_opens_owner_state(tmp_path, monkeypatch, recipe):
    monkeypatch.setenv("COMPANY_WIKI_REAL_WIKI_ROOT", str(tmp_path))
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = tuple(sys.path)

    def refused(*_args, **_kwargs):
        pytest.fail("discovery attempted to read the raw owner database")

    ordinary_is_file = Path.is_file

    def is_file(path):
        if path.name == "catalog.sqlite3":
            pytest.fail("discovery attempted to probe the raw owner database")
        return ordinary_is_file(path)

    monkeypatch.setattr(Path, "is_file", is_file)
    monkeypatch.setattr(sqlite3, "connect", refused)
    runpy.run_path(str(ROOT / "contract" / recipe))
    assert tuple(sys.path) == before
