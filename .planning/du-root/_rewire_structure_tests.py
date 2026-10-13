"""Rewire the DU-STRUCTURE tests onto a uniquely-named fixture module.

The lane imported its fixtures as a bare ``fixtures`` after prepending the fixture
directory to ``sys.path``. That only resolves when that directory is first; running the DU
unit suites together lets the repository's own ``tests/fixtures`` win, and collection fails
with ``cannot import name 'available_inputs' from 'fixtures'``.

``tests/`` is not a package, so a ``tests.fixtures....`` import is not available. The fix
follows the convention this repository already uses for shared test helpers (``support.*``,
``helpers.*``): give the module a unique name and import it by that name.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = ROOT / "tests" / "unit" / "document_understanding_structure"

OLD_BLOCK = (
    'FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" '
    '/ "document_understanding_structure"\n'
    "if str(FIXTURE_ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(FIXTURE_ROOT))\n"
)
NEW_BLOCK = (
    "FIXTURE_ROOT = Path(__file__).resolve().parents[2] / \"fixtures\" "
    "/ \"document_understanding_structure\"\n"
    "if str(FIXTURE_ROOT) not in sys.path:\n"
    "    sys.path.insert(0, str(FIXTURE_ROOT))\n"
)

REPLACEMENTS = {
    "test_structure_red.py": (
        "from fixtures import load_observation  # noqa: E402",
        "from du_structure_fixtures import load_observation  # noqa: E402",
    ),
    "test_structure_contracts.py": (
        "from fixtures import available_inputs, load_observation  # noqa: E402",
        "from du_structure_fixtures import available_inputs, load_observation  # noqa: E402",
    ),
}

for name, (old_import, new_import) in REPLACEMENTS.items():
    path = TARGET / name
    text = path.read_text(encoding="utf-8")
    updated = text.replace(OLD_BLOCK, NEW_BLOCK).replace(old_import, new_import)
    path.write_text(updated, encoding="utf-8")
    print(f"{name}: changed={updated != text}")
