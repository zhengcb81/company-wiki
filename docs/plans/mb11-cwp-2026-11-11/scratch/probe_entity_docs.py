"""Scratch probe: how many documents match ENT_ACME in the restored fixture?"""
import sys

sys.path.insert(0, r"C:\Users\郑曾波\Projects\mb11-cwp\src")
sys.path.insert(0, r"C:\Users\郑曾波\Projects\mb11-cwp\tests")

import importlib.util

spec = importlib.util.spec_from_file_location(
    "tpcb",
    r"C:\Users\郑曾波\Projects\mb11-cwp\tests\contract\test_public_canonical_browser.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

import tempfile
from pathlib import Path

ENT = getattr(module, "ENT_ACME", None)
print("ENT_ACME =", ENT)

# The workspace fixture is a pytest fixture; rebuild it manually.
workspace = None
for name in ("workspace",):
    fn = getattr(module, name, None)
    print(name, "->", fn)

# Use pytest to instantiate the fixture directly.
import pytest


@pytest.fixture
def _ws(workspace):  # noqa: F811 - re-declare for clarity
    return workspace


class Plugin:
    def pytest_fixture_setup(self, fixturedef, request):
        return None


# Simpler: call the fixture function with a tmp_path via pytest's request.
from _pytest.fixtures import FixtureRequest  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="probe-ent-"))
# The workspace fixture likely takes tmp_path (and maybe monkeypatch).
import inspect

sig = inspect.signature(module.workspace)
print("workspace signature:", sig)

# Build minimal request objects for tmp_path/monkeypatch only.
class FakeRequest:
    def __init__(self, tmp_path):
        self._values = {"tmp_path": tmp_path}

    def getfixturevalue(self, name):
        if name in self._values:
            return self._values[name]
        raise KeyError(name)


gen = module.workspace.__wrapped__ if hasattr(module.workspace, "__wrapped__") else module.workspace
try:
    result = gen(FakeRequest(tmp))
except TypeError as exc:
    print("fixture call failed:", exc)
    sys.exit(1)
if hasattr(result, "__next__"):
    fixture_obj = next(result)
else:
    fixture_obj = result
print("fixture type:", type(fixture_obj))

# fixture_obj shape: (_, catalog, _) per the test
if isinstance(fixture_obj, tuple):
    catalog = fixture_obj[1]
else:
    catalog = fixture_obj

records = catalog.browse_entity_records(ENT)
doc_ids = sorted({r.document_id for r in records})
print("distinct documents via typed port:", len(doc_ids))
rows = catalog.reader.fetchall(
    "SELECT document_id FROM document_entities WHERE entity_id = ?", (ENT,)
)
print("document_entities rows:", len(rows), sorted(str(r[0]) for r in rows))
rows2 = catalog.reader.fetchall(
    "SELECT document_id, metadata_json FROM documents"
)
for row in rows2:
    meta = str(row["metadata_json"] or "")
    if "canonical_entity_id" in meta:
        print("json-match doc:", str(row["document_id"])[:50], meta[:120])
