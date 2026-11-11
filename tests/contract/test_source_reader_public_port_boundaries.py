"""The source reader and browse API must cross storage boundaries by ports."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki"


def _calls_on_dotted_owner(tree: ast.AST, owner: tuple[str, ...]) -> list[ast.Call]:
    def dotted(node: ast.AST) -> tuple[str, ...] | None:
        if isinstance(node, ast.Name):
            return (node.id,)
        if isinstance(node, ast.Attribute):
            parent = dotted(node.value)
            return (*parent, node.attr) if parent else None
        return None

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and dotted(node.func.value) == owner
    ]


def _read_tree(relative: str) -> ast.Module:
    path = SOURCE_ROOT / relative
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_source_reader_uses_only_public_catalog_methods():
    tree = _read_tree("source_catalog/source_reader.py")
    calls = _calls_on_dotted_owner(tree, ("self", "catalog"))

    assert not [
        f"line {call.lineno}: {ast.unparse(call.func)}"
        for call in calls
        if isinstance(call.func, ast.Attribute)
        and call.func.attr.startswith("_")
    ]


def test_source_reader_uses_only_public_resolver_and_policy_ports():
    tree = _read_tree("source_catalog/source_reader.py")
    private_imports = [
        f"line {node.lineno}: {node.module}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module in {"resolver", "policy"}
        for alias in node.names
        if alias.name.startswith("_")
    ]
    private_resolver_calls = [
        f"line {node.lineno}: {ast.unparse(node.func)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "resolver"
        and node.func.attr.startswith("_")
    ]

    violations = private_imports + private_resolver_calls
    assert not violations, "SourceVersionReader bypasses owner ports:\n" + "\n".join(violations)


def test_local_inventory_uses_only_public_source_location_and_resolver_ports():
    tree = _read_tree("source_catalog/local_inventory.py")
    private_imports = [
        f"line {node.lineno}: {node.module}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.endswith(("resolver", "source_location", "source_reader", "adapters.common"))
        for alias in node.names
        if alias.name.startswith("_")
    ]
    private_owner_calls = [
        f"line {node.lineno}: {ast.unparse(node.func)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "resolver"
        and node.func.attr.startswith("_")
    ]
    violations = private_imports + private_owner_calls
    assert not violations, (
        "Local inventory bypasses source-owner ports:\n"
        + "\n".join(violations)
    )
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module == "company_wiki.source_catalog.adapters.common"
        for node in ast.walk(tree)
    ), "Local inventory must not depend on a provider adapter helper module"


def test_local_original_does_not_export_physical_paths_to_reconcile():
    inventory = _read_tree("source_catalog/local_inventory.py")
    original = next(
        node for node in inventory.body
        if isinstance(node, ast.ClassDef) and node.name == "LocalOriginal"
    )
    locations = next(
        node for node in original.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "locations"
    )
    annotation = ast.unparse(locations.annotation)
    assert "RegisteredLocationBinding" in annotation
    assert "Path" not in annotation and "RootSpec" not in annotation

    reconcile = _read_tree("source_catalog/local_reconcile.py")
    sidecar_readers = {
        node.name: node
        for node in reconcile.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"_sec_cache", "_sec_sidecar"}
    }
    for method in sidecar_readers.values():
        assert not any(
            isinstance(node, ast.Name) and node.id == "path"
            for node in ast.walk(method)
        )
        assert any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "read_registered_sidecar"
            for node in ast.walk(method)
        )


def test_registered_sidecar_port_uses_location_binding_not_path():
    inventory = _read_tree("source_catalog/local_inventory.py")
    method = next(
        node for node in inventory.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "read_registered_sidecar"
    )
    parameters = [arg.arg for arg in method.args.args + method.args.kwonlyargs]
    assert {"catalog", "ref", "location", "kind", "budget"} <= set(parameters)
    assert not {"path", "absolute_path", "root"} & set(parameters)
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "budget"
        and node.func.attr == "read_metadata_observation"
        for node in ast.walk(method)
    )


def test_filesystem_discovery_policy_has_one_shared_owner():
    expected = "company_wiki.source_catalog.filesystem_discovery"
    for relative in ("source_catalog/local_inventory.py", "source_catalog/scanner.py"):
        tree = _read_tree(relative)
        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module is not None
            and (node.module == expected or node.module.endswith("filesystem_discovery"))
        ]
        assert imports, f"{relative} must depend on the discovery policy owner"
        assert any(
            alias.name == "SKIP_DIRS" and alias.asname is None
            for node in imports
            for alias in node.names
        ), f"{relative} must use the public discovery policy"

    for relative in (
        "source_catalog/scanner.py",
        "source_catalog/adapters/dayu.py",
        "source_catalog/source_group_scope.py",
    ):
        tree = _read_tree(relative)
        assert any(
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.endswith("filesystem_discovery")
            and any(alias.name == "walk_document_files" for alias in node.names)
            for node in ast.walk(tree)
        ), f"{relative} must use the shared document traversal port"

    discovery = _read_tree("source_catalog/filesystem_discovery.py")
    owner_names = {
        node.name for node in discovery.body if isinstance(node, ast.FunctionDef)
    }
    assert "walk_document_files" in owner_names


def test_read_budget_has_a_shared_contract_owner():
    budget_tree = _read_tree("source_catalog/read_budget.py")
    budget_classes = {
        node.name for node in budget_tree.body if isinstance(node, ast.ClassDef)
    }
    assert "ReadBudget" in budget_classes

    for relative in (
        "source_catalog/resolver.py",
        "source_catalog/source_reader.py",
        "source_catalog/local_inventory.py",
    ):
        tree = _read_tree(relative)
        assert any(
            isinstance(node, ast.ImportFrom)
            and (
                node.module == "company_wiki.source_catalog.read_budget"
                or (node.level == 1 and node.module == "read_budget")
            )
            and any(alias.name == "ReadBudget" for alias in node.names)
            for node in ast.walk(tree)
        ), f"{relative} must consume the shared ReadBudget contract"

    resolver = _read_tree("source_catalog/resolver.py")
    assert not any(
        isinstance(node, ast.ClassDef) and node.name == "ReadBudget"
        for node in resolver.body
    ), "Resolver must implement budget use, not own the shared budget contract"
    exports = next(
        ast.literal_eval(node.value)
        for node in resolver.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    )
    assert "ReadBudget" not in exports

    catalog_root = SOURCE_ROOT / "source_catalog"
    violations = []
    for path in catalog_root.rglob("*.py"):
        if path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            resolver_import = node.module == "resolver" and node.level == 1
            resolver_import = resolver_import or node.module == "company_wiki.source_catalog.resolver"
            if resolver_import:
                violations.extend(
                    f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: {alias.name}"
                    for alias in node.names
                    if alias.name == "ReadBudget"
                )
    assert not violations, "consumers must import the shared budget owner:\n" + "\n".join(violations)


def test_registered_location_results_have_a_shared_contract_owner():
    contract = _read_tree("source_catalog/location_read_contract.py")
    expected = {
        "RegisteredLocationBinding",
        "SourceLocationReadResult",
        "RegisteredLocationDescriptor",
    }
    assert expected <= {
        node.name for node in contract.body if isinstance(node, ast.ClassDef)
    }

    resolver = _read_tree("source_catalog/resolver.py")
    assert expected <= {
        alias.name
        for node in resolver.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "company_wiki.source_catalog.location_read_contract"
        for alias in node.names
    }
    assert not expected & {
        node.name for node in resolver.body if isinstance(node, ast.ClassDef)
    }, "Resolver must implement the ports, not own their shared DTOs"
    exports = next(
        ast.literal_eval(node.value)
        for node in resolver.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    )
    assert not expected & set(exports), "Resolver must not re-export the location contract"

    inventory = _read_tree("source_catalog/local_inventory.py")
    assert any(
        isinstance(node, ast.ImportFrom)
        and (
            node.module == "company_wiki.source_catalog.location_read_contract"
            or (node.level == 1 and node.module == "location_read_contract")
        )
        and any(alias.name == "RegisteredLocationBinding" for alias in node.names)
        for node in ast.walk(inventory)
    ), "local inventory consumes the pathless location contract directly"
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module in {"resolver", "company_wiki.source_catalog.resolver"}
        and any(alias.name == "RegisteredLocationBinding" for alias in node.names)
        for node in ast.walk(inventory)
    ), "local inventory must not import Resolver-owned implementation DTOs"


def test_consumers_keep_public_location_helper_names():
    reader = _read_tree("source_catalog/source_reader.py")
    imports = [
        alias
        for node in ast.walk(reader)
        if isinstance(node, ast.ImportFrom)
        and node.module in {"source_location", "company_wiki.source_catalog.source_location"}
        for alias in node.names
        if alias.name == "relative_segments"
    ]
    assert imports
    assert all(alias.asname is None for alias in imports), (
        "SourceVersionReader must not disguise a public source_location port as private"
    )

    company_index = _read_tree("source_catalog/company_source_index.py")
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module in {"source_location", "company_wiki.source_catalog.source_location"}
        for node in ast.walk(company_index)
    ), "CompanySourceIndex must leave physical location validation to Catalog"


def test_resolver_does_not_import_local_inventory_for_budget_type_checks():
    resolver = _read_tree("source_catalog/resolver.py")
    assert not any(
        isinstance(node, ast.ImportFrom)
        and (node.module or "").endswith("local_inventory")
        for node in ast.walk(resolver)
    ), "Resolver must depend on the shared budget contract, not LocalInventory"
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "import_module"
        and any(
            isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value.endswith("local_inventory")
            for argument in node.args
        )
        for node in ast.walk(resolver)
    )


def test_local_reconcile_uses_public_reader_verification_port():
    reconcile = _read_tree("source_catalog/local_reconcile.py")
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "reader"
        and node.func.attr.startswith("_")
        for node in ast.walk(reconcile)
    ), "local reconciliation must not call a private SourceVersionReader method"
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "reader"
        and node.func.attr == "verify_version_with_scope"
        and any(keyword.arg == "scope_qualification" for keyword in node.keywords)
        for node in ast.walk(reconcile)
    )


def test_company_index_and_duplicate_cleanup_use_owner_ports():
    company_index = _read_tree("source_catalog/company_source_index.py")
    assert any(
        isinstance(node, ast.Attribute) and node.attr == "source_copy_availability"
        for node in ast.walk(company_index)
    )
    assert any(
        isinstance(node, ast.Attribute) and node.attr == "document_candidates"
        for node in ast.walk(company_index)
    )
    assert not any(
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "self"
        and node.value.attr == "catalog"
        and node.attr in {"reader", "config"}
        for node in ast.walk(company_index)
    ), "CompanySourceIndex must use Catalog's typed ports"

    duplicate_cleanup = _read_tree("source_catalog/duplicate_cleanup.py")
    assert any(
        isinstance(node, ast.Attribute)
        and node.attr == "duplicate_cleanup_location_records"
        for node in ast.walk(duplicate_cleanup)
    )
    assert not any(
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "self"
        and node.value.attr == "catalog"
        and node.attr in {"reader", "config"}
        for node in ast.walk(duplicate_cleanup)
    ), "duplicate inventory must not query SQLite or inspect CatalogConfig"

    service = _read_tree("source_catalog/service.py")
    catalog = next(
        node for node in service.body
        if isinstance(node, ast.ClassDef) and node.name == "SourceCatalog"
    )
    public_methods = {
        node.name for node in catalog.body
        if isinstance(node, ast.FunctionDef)
    }
    assert {
        "annotate_locations",
        "source_copy_availability",
        "document_candidates",
        "duplicate_cleanup_location_records",
    } <= public_methods


def test_resolver_registered_original_port_accepts_identities_not_paths():
    tree = _read_tree("source_catalog/resolver.py")
    resolver = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SourceResolver"
    )
    method = next(
        node for node in resolver.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "read_registered_original"
    )
    parameters = [arg.arg for arg in method.args.args + method.args.kwonlyargs]

    assert {"ref", "location_id", "budget"} <= set(parameters)
    assert not {"path", "absolute_path", "expected_sha256"} & set(parameters)
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_current_source_location"
        for node in ast.walk(method)
    )


def test_resolver_uses_public_read_budget_and_source_location_owner():
    tree = _read_tree("source_catalog/resolver.py")
    private_runtime_names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        and node.name in {"_ReadBudget", "_needs_hydration"}
    }
    private_aliases = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
        and target.id in {"_ReadBudget", "_needs_hydration"}
    }
    assert not private_runtime_names | private_aliases
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "company_wiki.source_catalog.read_budget"
        and any(alias.name == "ReadBudget" for alias in node.names)
        for node in tree.body
    )
    assert any(
        isinstance(node, ast.Attribute)
        and node.attr == "is_hydration_required"
        and isinstance(node.value, ast.Name)
        and node.value.id == "source_location"
        for node in ast.walk(tree)
    )


def test_resolver_read_ports_share_one_current_catalog_identity_check():
    tree = _read_tree("source_catalog/resolver.py")
    resolver = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SourceResolver"
    )
    methods = {
        node.name: node
        for node in resolver.body
        if isinstance(node, ast.FunctionDef)
    }
    for name in ("read_verified_source_location", "read_registered_original"):
        assert any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_current_source_location"
            for node in ast.walk(methods[name])
        )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "source_location_candidates"
        for node in ast.walk(methods["_current_source_location"])
    )


def test_company_source_index_uses_public_resolver_ports():
    tree = _read_tree("source_catalog/company_source_index.py")
    private_imports = [
        f"line {node.lineno}: {node.module}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.endswith("resolver")
        for alias in node.names
        if alias.name.startswith("_")
    ]
    private_calls = [
        f"line {node.lineno}: {ast.unparse(node.func)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and ast.unparse(node.func.value) == "self._resolver"
        and node.func.attr.startswith("_")
    ]
    violations = private_imports + private_calls
    assert not violations, "CompanySourceIndex bypasses resolver ports:\n" + "\n".join(violations)
    public_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and ast.unparse(node.func.value) == "self._resolver"
    }
    assert {"entity_matches", "project_source_metadata"} <= public_calls


def test_assertion_service_uses_public_resolver_metadata_projection():
    tree = _read_tree("source_catalog/assertion_service.py")
    private_imports = [
        f"line {node.lineno}: {node.module}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.endswith("resolver")
        for alias in node.names
        if alias.name.startswith("_")
    ]
    misplaced_types = [
        f"line {node.lineno}: {node.module}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.endswith("source_reader")
        for alias in node.names
        if alias.name in {"SourceReadError", "SourceRef"}
    ]
    violations = private_imports + misplaced_types
    assert not violations, "Assertion service bypasses source ports:\n" + "\n".join(violations)
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "project_source_metadata"
        for node in ast.walk(tree)
    )


def test_resolver_verified_read_port_is_catalog_bound_and_pathless():
    tree = _read_tree("source_catalog/resolver.py")
    resolver = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SourceResolver"
    )
    method = next(
        node for node in resolver.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "read_verified_source_location"
    )
    parameters = [arg.arg for arg in method.args.args + method.args.kwonlyargs]

    assert "ref" in parameters
    assert "location_id" in parameters
    assert not {"path", "absolute_path", "expected_sha256"} & set(parameters)
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_current_source_location"
        for node in ast.walk(method)
    )
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "company_wiki.source_catalog.location_read_contract"
        and any(alias.name == "SourceLocationReadResult" for alias in node.names)
        for node in tree.body
    )


def test_document_browser_consumes_typed_catalog_queries_not_sql_storage():
    tree = _read_tree("source_catalog/public_document_browser.py")
    calls = _calls_on_dotted_owner(tree, ("self", "catalog", "reader"))

    assert not [
        f"line {call.lineno}: {ast.unparse(call.func)}"
        for call in calls
        if isinstance(call.func, ast.Attribute)
        and call.func.attr in {"fetchone", "fetchall"}
    ]


def test_source_catalog_publishes_owner_ports_for_reader_and_browser():
    service = _read_tree("source_catalog/service.py")
    public_methods = {
        node.name
        for node in service.body
        if isinstance(node, ast.ClassDef) and node.name == "SourceCatalog"
        for node in node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "source_location_candidates" in public_methods
    assert "browse_entity_records" in public_methods
    assert "browse_document_records" in public_methods
    assert "iter_original_version_identities" in public_methods


def test_source_read_policy_uses_the_public_policy_owner_port():
    tree = _read_tree("source_catalog/source_read_policy.py")
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "policy"
    ]

    assert any(
        alias.name == "root_is_reusable_for_filing"
        for node in imports
        for alias in node.names
    )
    assert not any(
        alias.name == "_effective_reusable"
        for node in imports
        for alias in node.names
    ), "read-policy fingerprint must not call a policy implementation helper"
