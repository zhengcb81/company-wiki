"""Static contracts for cross-package source boundaries.

Cross-package communication is allowed through declared source contracts and
public value types. Importing a private implementation name or making a lower
layer depend on a higher implementation package is not a supported boundary.
"""

from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path

import pytest

from support.layer_boundary_scan import LayerBoundaries, literal_exports as _literal_exports


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki"
_BOUNDARIES = LayerBoundaries(SOURCE_ROOT)


@lru_cache(maxsize=None)
def _scan(path: Path, tree: ast.AST):
    return _BOUNDARIES.scan(path, tree)


def _imports(path: Path, tree: ast.AST):
    return _scan(path, tree).imports


@lru_cache(maxsize=1)
def _parsed_production_python_files() -> tuple[tuple[Path, ast.AST], ...]:
    return tuple(
        (path, ast.parse(path.read_bytes(), filename=str(path)))
        for path in _BOUNDARIES.modules.values()
        if not path.name.startswith("test_")
    )


def test_boundary_scanner_catches_private_access_patterns():
    source_path = SOURCE_ROOT / "automation" / "_boundary_probe.py"
    cases = (
        "from company_wiki.source_catalog._impl import read_source",
        "from company_wiki.source_catalog.api import _read_source",
        "from company_wiki.source_catalog import api\napi._read_source()",
        "from company_wiki.source_catalog import api\ngetattr(api, '_read_source')()",
        "import company_wiki.source_catalog.api as source_api\nsource_api._read_source()",
        "from company_wiki.source_catalog import api\nname = '_read_source'\ngetattr(api, name)()",
        "from importlib import import_module\nMODULE = 'company_wiki.source_catalog._impl'\nimport_module(MODULE)",
    )

    for source in cases:
        violations = _scan(source_path, ast.parse(source)).violations
        assert violations, f"boundary scanner missed private access in: {source}"


def test_boundary_scanner_rejects_undeclared_module_attributes():
    source_path = SOURCE_ROOT / "automation" / "_boundary_probe.py"
    cases = (
        "import company_wiki.source_catalog.narrative_evidence as source_api\nsource_api.not_exported()",
        "from company_wiki.source_catalog import narrative_evidence as source_api\nsource_api.not_exported()",
        "import company_wiki.source_catalog.narrative_evidence as source_api\ngetattr(source_api, 'not_exported')()",
        "import company_wiki.document_understanding.operating_states.patterns as du_patterns\ndu_patterns.COURTESY.search('text')",
        "from importlib import import_module\nsource_api = import_module('company_wiki.source_catalog.narrative_evidence')\nsource_api.not_exported()",
        "import importlib as loader\nMODULE = 'company_wiki.source_catalog.narrative_evidence'\nsource_api = loader.import_module(MODULE)\ngetattr(source_api, 'not_exported')()",
    )
    for source in cases:
        violations = _scan(source_path, ast.parse(source)).violations
        assert violations, f"boundary scanner missed undeclared module API use in: {source}"

    import_metadata = (
        "import company_wiki.source_catalog.narrative_evidence as source_api\n"
        "getattr(source_api, '__name__')"
    )
    assert not _scan(source_path, ast.parse(import_metadata)).violations
    private_import = (
        "from company_wiki.document_understanding.operating_states.patterns "
        "import COURTESY"
    )
    assert _scan(source_path, ast.parse(private_import)).violations


@pytest.mark.parametrize(
    "source, expected",
    [
        ("from company_wiki import document_understanding as du\n"
         "du._implementation()", "_implementation"),
        ("from .. import document_understanding as du\n"
         "du._implementation()", "_implementation"),
        ("from .. import document_understanding as du\n"
         "alias = du\nalias._implementation()", "_implementation"),
        ("from importlib import import_module as load\n"
         "load('..document_understanding', __package__)._implementation()", "_implementation"),
        ("from importlib import import_module\nloader = import_module\n"
         "du = loader(name='company_wiki.document_understanding')\n"
         "from builtins import getattr as attr\nattr(du, '_implementation')", "_implementation"),
        ("__import__('company_wiki', fromlist=['document_understanding'])"
         ".document_understanding._implementation()", "_implementation"),
        ("import sys\nsys.modules['company_wiki.document_understanding']._implementation()",
         "_implementation"),
        ("from company_wiki import document_understanding as du\ndu.__path__", "__path__"),
        ("from company_wiki import document_understanding as du\n"
         "getattr(du, '__file__', None)", "__file__"),
        ("from company_wiki import document_understanding as du\n"
         "du.__dict__['_implementation']", "__dict__"),
        ("from company_wiki import document_understanding as du\n"
         "vars(du)['_implementation']", "vars"),
        ("from company_wiki import document_understanding as du\n"
         "modules = {'engine': du}\nfor module in modules.values():\n    module.__file__",
         "module object"),
        ("from company_wiki import document_understanding as du\n"
         "fingerprint(du)", "module object"),
        ("import company_wiki as root\nroot.__dict__['document_understanding']",
         "__dict__"),
        ("from company_wiki import __dict__ as registry\nregistry['document_understanding']",
         "__dict__"),
        ("import company_wiki as root\nvars(root)['document_understanding']", "vars"),
        ("from company_wiki import document_understanding as du\n"
         "def engine():\n    return du", "module object"),
        ("from company_wiki import document_understanding as du\n"
         "owner._engine = du", "module object"),
        ("from company_wiki import document_understanding as du\n"
         "def caller(engine=du):\n    return engine._implementation()", "module object"),
        ("from importlib import import_module as load\n"
         "root = 'company_wiki'\nload(f'{root}.document_understanding')._implementation()",
         "_implementation"),
        ("import inspect as introspection\nfrom company_wiki import document_understanding as du\n"
         "introspection.getsourcefile(du)", "inspect.getsourcefile"),
    ],
)
def test_boundary_scanner_resolves_indirect_cross_layer_access(source, expected):
    path = SOURCE_ROOT / "automation" / "_boundary_probe.py"
    violations = _scan(path, ast.parse(source)).violations
    assert any(expected in item for item in violations), violations


def test_boundary_scanner_does_not_mix_local_aliases_across_functions():
    path = SOURCE_ROOT / "automation" / "_boundary_probe.py"
    source = """
from company_wiki import document_understanding as engine

def first(engine):
    return engine._internal()

def second():
    from company_wiki.automation import models as engine
    return engine._internal()

def third():
    return engine._internal()
"""
    assert _scan(path, ast.parse(source)).violations == (
        "automation/_boundary_probe.py:12: private attribute company_wiki.document_understanding._internal",
    )


def test_boundary_scanner_allows_passing_a_published_callable_as_a_port():
    path = SOURCE_ROOT / "automation" / "_boundary_probe.py"
    source = """
from company_wiki import document_understanding as du
configure(understand=du.understand_units)
"""
    assert not _scan(path, ast.parse(source)).violations


@pytest.mark.parametrize(
    "source,private_name",
    [
        ("catalog = SourceCatalog(config)\nalias = catalog\nalias._store", "_store"),
        ("def run(catalog: 'SourceCatalog'):\n    return getattr(catalog, '_store')", "_store"),
        ("catalog: SourceCatalog | None = catalog_factory()\ncatalog._store", "_store"),
        ("class Runner:\n"
         "    def run(self):\n        return self.catalog._store\n"
         "    def __init__(self, catalog: SourceCatalog):\n        self.catalog = catalog", "_store"),
        ("class Runner:\n    catalog: SourceCatalog\n"
         "    def run(self):\n        return self.catalog._store", "_store"),
        ("import sys\nregistry = sys.modules\n"
         "registry[SourceCatalog.__module__]._implementation()", "_implementation"),
        ("from importlib import import_module\n"
         "import_module(SourceCatalog.__module__)._implementation()", "_implementation"),
        ("reader = SourceCatalog(config).open_narrative_artifact_reader()\nreader._reader", "_reader"),
        ("SourceCatalog(config).open_narrative_artifact_store()._catalog", "_catalog"),
        ("catalog = SourceCatalog(config)\nports = [catalog]\nports[0]._store", "_store"),
        ("(catalog,) = (SourceCatalog(config),)\ncatalog._store", "_store"),
    ],
)
def test_boundary_scanner_rejects_foreign_instance_and_definition_bypasses(source, private_name):
    path = SOURCE_ROOT / "automation" / "_boundary_probe.py"
    source = "from company_wiki.source_catalog import SourceCatalog\n" + source
    violations = _scan(path, ast.parse(source)).violations
    assert any(private_name in item for item in violations), violations


def test_boundary_scanner_allows_opaque_ports_and_local_fields():
    path = SOURCE_ROOT / "automation" / "_boundary_probe.py"
    source = """
from company_wiki.source_catalog import SourceCatalog

class Runner:
    def __init__(self, catalog: SourceCatalog):
        self._catalog = catalog
        self._local_state = []

    def run(self):
        return self._catalog.open_source_reader(), self._local_state

def unrelated(catalog):
    return catalog._local_cache
"""
    assert not _scan(path, ast.parse(source)).violations


@pytest.mark.parametrize(
    "source",
    [
        "from .. import document_understanding as du",
        "import importlib as loader\nloader.import_module('company_wiki.document_understanding')",
        "from importlib import import_module as load\nload('..document_understanding', __package__)",
        "__import__('company_wiki', fromlist=['document_understanding'])",
        "import sys\nsys.modules.get('company_wiki.document_understanding')",
    ],
)
def test_direction_checks_see_imports_through_namespace_and_loaders(source):
    path = SOURCE_ROOT / "document_normalization" / "_boundary_probe.py"
    assert any(
        module == "company_wiki.document_understanding"
        for _, module, _, _ in _imports(path, ast.parse(source))
    )


def test_cross_package_names_are_declared_by_the_provider_public_api():
    violations = []
    for path, tree in _parsed_production_python_files():
        violations.extend(_scan(path, tree).violations)

    assert not violations, "cross-package imports bypass the provider's public API:\n" + "\n".join(violations[:120])


# Frozen legacy import surfaces. Match the exact target and names rather than
# ignoring all dependencies of a compatibility file.
_LEGACY_EDGES = {
    ("source_catalog/narrative_transport_cli.py", "company_wiki.automation.narrative_transport_cli",
     ("main",)),
    ("source_contract/announcement_cli.py", "company_wiki.source_catalog.announcement_cli",
     ("main",)),
    ("source_contract/announcement_cli.py", "company_wiki.source_catalog.announcement_cli",
     ("build_parser",)),
    ("source_contract/announcement_collector.py", "company_wiki.source_catalog.announcement_collector",
     ("collect_announcement", "download_announcement")),
    ("document_normalization/pdf_table_observations/adapter.py",
     "company_wiki.document_understanding.pdf_table_observations",
     ("SCHEMA_OUT", "build_pdf_table_observations")),
    ("document_understanding/decision_inventory.py",
     "company_wiki.source_catalog.narrative_decision_inventory",
     ("build_decision_trace", "current_decision_trace", "decision_versions")),
}


@pytest.mark.parametrize(
    "layer,forbidden",
    [
        ("source_contract", {"document_model", "document_normalization", "document_understanding",
                             "parser_adapters", "source_catalog", "automation"}),
        ("document_model", {"document_normalization", "document_understanding", "parser_adapters",
                            "source_catalog", "automation"}),
        ("document_normalization", {"document_understanding", "source_catalog", "automation"}),
        ("document_understanding", {"document_normalization", "parser_adapters", "source_catalog", "automation"}),
        ("parser_adapters", {"document_understanding", "source_catalog", "automation"}),
        ("source_catalog", {"automation"}),
    ],
)
def test_dependencies_follow_layer_ownership(layer, forbidden):
    violations = [
        f"{relative}:{line}: {module} {names}"
        for path, tree in _parsed_production_python_files()
        if path.relative_to(SOURCE_ROOT).parts[0] == layer
        for relative in [path.relative_to(SOURCE_ROOT).as_posix()]
        for _, module, names, line in _imports(path, tree)
        if module.split(".")[1] in forbidden and (relative, module, names) not in _LEGACY_EDGES
    ]
    assert not violations, "\n".join(violations)


def test_production_uses_canonical_owners_instead_of_upward_compatibility_shims():
    shims = {
        "company_wiki.source_catalog.narrative_transport_cli": set(),
        "company_wiki.source_contract.announcement_cli": set(),
        "company_wiki.source_contract.announcement_collector": {"source_contract/__init__.py"},
        "company_wiki.document_understanding.decision_inventory": set(),
        "company_wiki.document_normalization.pdf_table_observations": set(),
        "company_wiki.document_normalization.pdf_table_observations.adapter": {
            "document_normalization/pdf_table_observations/__init__.py",
        },
    }
    violations = []
    for path, tree in _parsed_production_python_files():
        relative = path.relative_to(SOURCE_ROOT).as_posix()
        for _, module, _, line in _imports(path, tree):
            if module in shims and relative not in shims[module]:
                violations.append(f"{relative}:{line}: {module}")
    assert not violations, "\n".join(violations)


def test_source_qa_scope_uses_the_operating_state_public_qualifier_contract():
    path = SOURCE_ROOT / "source_catalog" / "narrative_qa_scopes.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    imports = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "company_wiki.document_understanding.operating_states"
    ]
    imported_names = {alias.name for node in imports for alias in node.names}
    assert "classify_qualifiers" in imported_names
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module == "company_wiki.document_understanding.operating_states.patterns"
        for node in ast.walk(tree)
    ), "source QA scope may use DU decisions, not DU regex tables"


def test_source_catalog_uses_discourse_observation_protocol_not_du_regex_objects():
    path = SOURCE_ROOT / "source_catalog" / "narrative_source_context.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "company_wiki.document_understanding"
        for alias in node.names
    }
    assert "observe_source_discourse" in imported
    assert not any(
        isinstance(node, ast.ImportFrom)
        and (node.module or "").startswith(
            "company_wiki.document_understanding.operating_states.patterns"
        )
        for node in ast.walk(tree)
    ), "source catalog consumes a DU observation, not its regex implementation"

    assert _literal_exports(
        SOURCE_ROOT / "document_understanding" / "operating_states" / "patterns.py"
    ) == set(), "operating-state regex tables are not a cross-layer API"


def test_source_acquisition_flow_does_not_construct_automation_requests():
    path = SOURCE_ROOT / "source_catalog" / "official_source_flow.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    violations = []
    for caller, module_name, _, line in _imports(path, tree):
        if module_name.startswith("company_wiki.automation"):
            violations.append(f"{line}:{module_name}")

    assert not violations, "source acquisition must emit source values, not own AUTO request DTOs:\n" + "\n".join(violations)


def test_source_parser_routing_is_owned_by_source_catalog():
    path = SOURCE_ROOT / "source_catalog" / "narrative_formats.py"
    assert path.is_file(), "source parser identity belongs to source_catalog"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    violations = [
        f"{node.lineno}:{node.module}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and (node.module or "").startswith("company_wiki.automation")
    ]
    exports = _literal_exports(path)

    assert not violations, "source parser routing cannot depend on AUTO:\n" + "\n".join(violations)
    assert exports is not None and {"NORMALIZED_MIME_TYPES", "parser_component", "source_class_for"} <= exports


def test_automation_parser_route_is_only_a_compatibility_reexport():
    from company_wiki.automation import narrative_formats as compatibility
    from company_wiki.source_catalog import narrative_formats as owner

    for name in owner.__all__:
        assert getattr(compatibility, name) is getattr(owner, name)


def test_selection_algorithm_identity_is_owned_by_its_public_api():
    from hashlib import sha256

    from company_wiki.source_catalog.narrative_selection import selection_algorithm_sha256

    owner_path = SOURCE_ROOT / "source_catalog" / "narrative_selection.py"
    inventory_path = SOURCE_ROOT / "source_catalog" / "narrative_decision_inventory.py"
    owner_exports = _literal_exports(owner_path)
    assert owner_exports is not None
    assert "selection_algorithm_sha256" in owner_exports
    expected = sha256(owner_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert selection_algorithm_sha256() == expected

    tree = ast.parse(inventory_path.read_text(encoding="utf-8-sig"))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_source_usability_version"
    )
    owner_imports = [
        node for node in ast.walk(function)
        if isinstance(node, ast.ImportFrom)
        and node.level == 1 and node.module == "narrative_selection"
    ]
    assert any(
        alias.name == "selection_algorithm_sha256"
        for node in owner_imports for alias in node.names
    ), "cache identity must ask its algorithm owner for the public fingerprint"
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "import_module"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "company_wiki.source_catalog.narrative_selection"
        for node in ast.walk(function)
    ), "consumers must not load the selector module to inspect its implementation"


def test_narrative_read_cli_is_owned_by_application_layer():
    cli_path = SOURCE_ROOT / "automation" / "narrative_transport_cli.py"
    source_path = SOURCE_ROOT / "source_catalog" / "narrative_transport_cli.py"
    assert cli_path.is_file(), "cross-package narrative transport belongs at the application edge"
    exports = _literal_exports(cli_path)
    assert exports is not None and {"main", "dispatch_transport_request"} <= exports

    # Deployed RF versions invoke the old executable module. The historical
    # path can forward only on execution. Importing it must load no runtime.
    tree = ast.parse(source_path.read_bytes())
    if ast.get_docstring(tree):
        del tree.body[0]
    forwarding = ast.parse("""
if __name__ == "__main__":
    from company_wiki.automation.narrative_transport_cli import main
    raise SystemExit(main())
""")
    assert ast.dump(tree) == ast.dump(forwarding)

    project = SOURCE_ROOT.parents[1] / "pyproject.toml"
    assert 'company-wiki-narrative-read = "company_wiki.automation.narrative_transport_cli:main"' in project.read_text(encoding="utf-8")


def test_historical_inventory_path_is_only_a_public_reexport():
    path = SOURCE_ROOT / "document_understanding" / "decision_inventory.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    definitions = [
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    imports = [
        node.module for node in tree.body
        if isinstance(node, ast.ImportFrom)
    ]

    assert definitions == []
    assert imports == ["company_wiki.source_catalog.narrative_decision_inventory"]


def test_processed_document_uses_source_contract_not_automation_dto():
    path = SOURCE_ROOT / "source_catalog" / "processed_document.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    imports = [
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    ]

    assert "company_wiki.automation.narrative_contracts" not in imports
    assert "company_wiki.source_contract" in imports


def test_source_ref_wire_contract_round_trips_and_checks_content_identity():
    import pytest

    from company_wiki.source_contract.source_manifest import source_id_for_sha256
    from company_wiki.source_contract import SourceRef, SourceRefError

    digest = "a" * 64
    value = {
        "schema_version": "2.0",
        "document_id": "doc-example",
        "source_id": source_id_for_sha256(digest),
        "content_sha256": digest,
        "byte_size": 17,
        "mime_type": "text/plain",
    }

    assert SourceRef.from_dict(value).to_dict() == value
    with pytest.raises(SourceRefError, match="identity"):
        SourceRef.from_dict({**value, "source_id": "source:wrong"})
    with pytest.raises(SourceRefError, match="field set"):
        SourceRef.from_dict({**value, "physical_path": "C:/private/file.txt"})


def test_cross_layer_symbols_are_listed_in_their_owner_public_exports():
    expected_exports = {
        "source_contract/__init__.py": {
            "SourceReadError", "SourceRef", "SourceRefError", "SourceVersionPort",
            "plain_json_value",
        },
        "resource_budget.py": {
            "BudgetPolicy", "WorkBudget", "WorkBudgetExceeded", "load_budget_policy",
        },
        "document_normalization/pdf_table_observations/__init__.py": {
            "build_pdf_table_observations",
        },
        "document_understanding/observation_adapter.py": {"wire_kind"},
        "document_understanding/summary_input.py": {
            "sent_policies", "unread_units", "SHARED_CONSTRAINTS",
        },
        "document_understanding/operating_states/assertion_roles.py": {
            "STATE_HEAD_PATTERN",
        },
        "source_catalog/narrative_decision_inventory.py": {"decision_versions"},
        "file_mutex.py": {
            "FileMutexLockedError", "os_file_mutex", "win32_filesystem_path",
        },
        "id_scope.py": {"normalize_id_scope"},
        "atomic_file.py": {"atomic_output"},
        "bounded_process.py": {"run_bounded", "run_json_process", "WINDOWS_WAIT_BOOTSTRAP"},
        "process_tree.py": {"WindowsJob", "assign_windows_job", "kill_owned_group"},
    }
    missing = []
    for relative, required in expected_exports.items():
        tree = ast.parse((SOURCE_ROOT / relative).read_text(encoding="utf-8-sig"))
        declared = set()
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "__all__"
                       for target in node.targets):
                continue
            if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                declared = {
                    item.value for item in node.value.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                }
        absent = required - declared
        if absent:
            missing.append(f"{relative}: {sorted(absent)}")

    assert not missing, "cross-layer public exports are not declared:\n" + "\n".join(missing)


def test_package_public_exports_are_importable_attributes():
    import importlib

    package_names = (
        "source_catalog",
        "document_understanding",
        "document_normalization",
        "source_contract",
        "automation",
        "document_model",
        "narrative_subject",
        "parser_adapters",
    )
    missing = []
    for name in package_names:
        package = importlib.import_module(f"company_wiki.{name}")
        for export in getattr(package, "__all__", ()):
            if not hasattr(package, export):
                missing.append(f"{name}.{export}")

    assert not missing, "declared package exports are not available:\n" + "\n".join(missing)


def test_profile_registry_exposes_isolated_public_catalog_views():
    from company_wiki.document_understanding.profiles import registry

    first = registry.decision_inventory_inputs()
    original_id = first["families"][0]["id"]
    first["families"][0]["id"] = "caller-mutation"
    assert registry.decision_inventory_inputs()["families"][0]["id"] == original_id

    context = registry.context_policy_config()
    context["generic_navigation_titles"] = ["caller-mutation"]
    assert "caller-mutation" not in registry.context_policy_config().get(
        "generic_navigation_titles", ()
    )
    assert registry.normalize_form_type("20-F/A") == "20-f"
