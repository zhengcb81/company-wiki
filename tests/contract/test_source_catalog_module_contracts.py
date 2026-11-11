"""Module-level API contracts within the source catalog package.

The AST contract rejects known and statically resolvable private sibling paths;
it is a CI boundary check, not a Python runtime sandbox. A new dynamic form
needs a failing probe before it is accepted in this package.
"""

from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path


SOURCE_PACKAGE = "company_wiki.source_catalog"
SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
    return ".".join((SOURCE_PACKAGE, *parts))


MODULES = {_module_name(path): path for path in SOURCE_ROOT.rglob("*.py")}
PUBLIC_PORTS = {
    "canonical_writer.py": {"CanonicalSourceWriter"},
    "local_reconcile.py": {
        "prepare_local_source", "prepare_local_source_operation",
    },
    "narrative_business_meaning.py": {
        "BUSINESS_CLAUSE_BOUNDARY_PATTERN", "BUSINESS_OBJECT_PATTERN",
        "BUSINESS_STRUCTURE_PATTERN", "COMPANY_ANCHOR_PATTERN",
        "FINANCIAL_ONLY_PATTERN", "GENERIC_DEFINITION_PATTERN",
        "business_objects", "business_qualification", "classify_operating_fact",
        "concrete_operating_event", "describes_business", "describes_business_structure",
        "detect_business_fact", "detect_legacy_business_fact", "is_component_structure",
        "prepare_business_observation", "reject_finance_only_text",
        "reject_legacy_finance_only_text",
    },
    "narrative_pdf_groups.py": {
        "PdfContextGroup", "PdfGroupRules", "bounding_box",
        "build_pdf_context_groups", "has_visual_overlap",
    },
    "narrative_business_groups.py": {
        "BusinessEnrichmentResult", "BusinessGroupDiagnostic", "enrich_business_groups",
        "evaluate_operating_fact", "extract_commercialization_milestone",
    },
    "narrative_evidence.py": {
        "QA_ANSWER_PATTERN", "emit_pdf_page", "emit_pdf_text_units",
        "evidence_algorithm_sha256", "has_pdf_question", "pdf_text_blocks",
        "record_pdf_native_view",
    },
    "narrative_reading_admission.py": {
        "CONTEXT_ROLES", "is_admitted", "is_financial_only",
    },
    "official_source_flow.py": {
        "OfficialSourceError", "attach_capture_http_observation",
        "capture_official_source", "import_official_source", "journal_capture",
        "list_retained_official_captures", "persist_capture",
        "persist_completed_capture", "recover_official_source",
        "validate_capture_receipt",
    },
    "security_listing_evidence.py": {
        "IssuerListing", "IssuerListingEvidence", "LISTING_EVIDENCE_SCHEMA_VERSION",
        "ListingEvidenceError", "build_sec_20f_listing_evidence", "encode_evidence",
    },
    "narrative_replay.py": {
        "PdfReplayPlan", "plan_pdf_replay", "prepare_pdf_replay",
        "prepare_pdf_replay_bytes", "replay_algorithm_sha256", "span_roundtrip_key",
        "unit_roundtrip_key", "verify_replayed_pdf_spans",
    },
    "narrative_pdf_page_checkpoints.py": {
        "CHECKPOINT_PROTOCOL", "MAX_CPU_THREADS", "MAX_INPUT_BYTES",
        "MAX_MEMORY_BYTES", "MAX_OUTPUT_BYTES", "MAX_PAGES", "MAX_SECONDS",
        "CompletedPages", "decode_output", "decode_single_json",
        "implementation_sha256", "request_sha256",
    },
    "narrative_pdf_candidates.py": {
        "observe_pdf_candidate", "pdf_candidate_algorithm_sha256",
    },
    "narrative_pdf_intent.py": {
        "PDF_INTENT_EXECUTION_VERSION", "SourceGeometrySession",
        "pdf_intent_algorithm_sha256", "scan_planned_pages",
    },
}
PUBLIC_METHOD_PORTS = {
    "canonical_writer.py": {"CanonicalSourceWriter": {"discard_staged", "read_existing_original"}},
}


def _provider_module(node: ast.ImportFrom, current_module: str, path: Path) -> str:
    if node.level == 0:
        return node.module or ""
    package = current_module if path.name == "__init__.py" else current_module.rpartition(".")[0]
    return resolve_name("." * node.level + (node.module or ""), package)


def _call_name(
    node: ast.AST,
    modules: dict[str, str],
    callables: dict[str, str],
    shadowed_nodes: set[int] | None = None,
) -> str:
    if isinstance(node, ast.Name):
        if shadowed_nodes and id(node) in shadowed_nodes:
            return node.id
        return callables.get(node.id, {
            "__import__": "builtins.__import__",
            "getattr": "builtins.getattr",
            "setattr": "builtins.setattr",
            "delattr": "builtins.delattr",
            "vars": "builtins.vars",
        }.get(node.id, node.id))
    if isinstance(node, ast.Attribute):
        parent = _module_reference(node.value, modules, shadowed_nodes=shadowed_nodes)
        return f"{parent}.{node.attr}" if parent else f"{_call_name(node.value, modules, callables, shadowed_nodes)}.{node.attr}"
    return ""


def _is_module_registry(
    node: ast.AST | None,
    modules: dict[str, str],
    aliases: set[str],
    shadowed_nodes: set[int] | None = None,
) -> bool:
    if isinstance(node, ast.Name):
        if shadowed_nodes and id(node) in shadowed_nodes:
            return False
        return node.id in aliases
    if isinstance(node, ast.Attribute) and node.attr == "modules":
        return _module_reference(node.value, modules, shadowed_nodes=shadowed_nodes) == "sys"
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "copy":
            return _is_module_registry(node.func.value, modules, aliases, shadowed_nodes)
        if isinstance(node.func, ast.Name) and node.func.id == "dict" and node.args:
            return _is_module_registry(node.args[0], modules, aliases, shadowed_nodes)
    return False


def _module_reference(
    node: ast.AST,
    aliases: dict[str, str],
    *,
    callables: dict[str, str] | None = None,
    registry_aliases: set[str] | None = None,
    current_module: str = "",
    path: Path | None = None,
    shadowed_nodes: set[int] | None = None,
) -> str | None:
    callables = callables or {}
    registry_aliases = registry_aliases or set()
    if isinstance(node, ast.Name):
        if shadowed_nodes and id(node) in shadowed_nodes:
            return None
        return aliases.get(node.id)
    if isinstance(node, ast.Attribute):
        parent = _module_reference(node.value, aliases, callables=callables,
                                   registry_aliases=registry_aliases,
                                   current_module=current_module, path=path,
                                   shadowed_nodes=shadowed_nodes)
        if parent is not None:
            return f"{parent}.{node.attr}"
    if isinstance(node, ast.Subscript) and _is_module_registry(
        node.value, aliases, registry_aliases, shadowed_nodes
    ):
        key = node.slice
        return key.value if isinstance(key, ast.Constant) and isinstance(key.value, str) else None
    if isinstance(node, ast.Call):
        target = _call_name(node.func, aliases, callables, shadowed_nodes)
        if target in {"importlib.import_module", "builtins.__import__"} and node.args:
            name = node.args[0]
            if not isinstance(name, ast.Constant) or not isinstance(name.value, str):
                return None
            if name.value.startswith("."):
                package = None
                if target == "importlib.import_module" and len(node.args) > 1:
                    package_arg = node.args[1]
                    package = package_arg.value if isinstance(package_arg, ast.Constant) else None
                if package is None:
                    package = current_module if path and path.name == "__init__.py" else current_module.rpartition(".")[0]
                try:
                    return resolve_name(name.value, package)
                except (ImportError, TypeError, ValueError):
                    return None
            return name.value
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get" and _is_module_registry(
            node.func.value, aliases, registry_aliases, shadowed_nodes
        ) and node.args:
            key = node.args[0]
            return key.value if isinstance(key, ast.Constant) and isinstance(key.value, str) else None
    return None


def _private_module_accesses(path: Path, tree: ast.Module) -> list[str]:
    current = _module_name(path)
    module_aliases: dict[str, str] = {}
    callable_aliases: dict[str, str] = {}
    module_registry_aliases: set[str] = set()
    selector_aliases: dict[str, set[str] | None] = {}
    imported_classes: dict[str, str] = {}
    scoped_module_aliases: dict[int, dict[str, str]] = {}
    scoped_blocked_module_aliases: dict[int, set[str]] = {}
    violations: list[str] = []
    named_member_values: dict[str, set[str]] = {}
    shadowed_name_nodes: set[int] = set()

    def scope_arguments(scope: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> set[str]:
        args = scope.args
        names = {arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
        if args.vararg:
            names.add(args.vararg.arg)
        if args.kwarg:
            names.add(args.kwarg.arg)
        return names

    def scope_bindings(scope: ast.AST) -> tuple[set[str], set[str], set[str]]:
        names: set[str] = set()
        globals_: set[str] = set()
        module_imports: set[str] = set()
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            names.update(scope_arguments(scope))
        body = scope.body if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else [scope.body]

        def visit(node: ast.AST, *, root: bool = False) -> None:
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                if node.generators:
                    visit(node.generators[0].iter)
                return
            if not root and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.add(node.name)
                return
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                names.add(node.id)
            elif isinstance(node, ast.Import):
                for imported in node.names:
                    local = imported.asname or imported.name.split(".")[0]
                    names.add(local)
                    if imported.name == SOURCE_PACKAGE or imported.name.startswith(SOURCE_PACKAGE + "."):
                        module_imports.add(local)
            elif isinstance(node, ast.ImportFrom):
                provider = _provider_module(node, current, path)
                if node.module == "*":
                    return
                for imported in node.names:
                    local = imported.asname or imported.name
                    names.add(local)
                    child = f"{provider}.{imported.name}"
                    if is_source_package(provider) and (child in MODULES or is_private_module_name(child)):
                        module_imports.add(local)
            elif isinstance(node, ast.Global):
                globals_.update(node.names)
            elif isinstance(node, ast.Nonlocal):
                globals_.update(node.names)
            elif isinstance(node, ast.ExceptHandler) and node.name:
                names.add(node.name)
            for child in ast.iter_child_nodes(node):
                visit(child)

        for statement in body:
            visit(statement, root=True)
        return names - globals_, globals_, module_imports

    def mark_scope(scope: ast.AST, inherited: set[str]) -> None:
        bindings, _, module_imports = scope_bindings(scope)
        local_shadow = inherited | (bindings - module_imports)

        def visit(node: ast.AST, *, root: bool = False) -> None:
            if not root and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                if isinstance(scope, ast.ClassDef):
                    child_inherited = inherited
                else:
                    child_inherited = local_shadow
                mark_scope(node, child_inherited)
                return
            if isinstance(node, ast.Name) and node.id in local_shadow:
                shadowed_name_nodes.add(id(node))
            for child in ast.iter_child_nodes(node):
                visit(child)

        body = scope.body if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else [scope.body]
        for statement in body:
            visit(statement)

    def literal_names(node: ast.AST) -> set[str] | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            values = [literal_names(item) for item in node.elts]
            if all(value is not None and len(value) == 1 for value in values):
                return {next(iter(value)) for value in values if value is not None}
        if isinstance(node, ast.Name):
            return named_member_values.get(node.id)
        return None

    scope_types = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
    parent_nodes = {
        id(child): parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    def enclosing_scope(node: ast.AST) -> ast.AST:
        parent = parent_nodes.get(id(node))
        while parent is not None and parent is not tree and not isinstance(parent, scope_types):
            parent = parent_nodes.get(id(parent))
        return parent if parent is not None else tree

    def enclosing_scopes(node: ast.AST) -> list[ast.AST]:
        scopes: list[ast.AST] = []
        parent = parent_nodes.get(id(node))
        while parent is not None:
            if parent is tree or isinstance(parent, scope_types):
                scopes.append(parent)
            parent = parent_nodes.get(id(parent))
        if tree not in scopes:
            scopes.append(tree)
        return scopes

    def lexical_scopes(node: ast.AST) -> list[ast.AST]:
        scopes = enclosing_scopes(node)
        if any(isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) for scope in scopes):
            return [scope for scope in scopes if not isinstance(scope, ast.ClassDef)]
        return scopes

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.comprehension)):
            values = literal_names(node.iter)
            if values is not None and isinstance(node.target, ast.Name):
                named_member_values[node.target.id] = values
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            values = literal_names(value) if value is not None else None
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if values is not None:
                for target in targets:
                    if isinstance(target, ast.Name):
                        named_member_values[target.id] = values

    def module_reference(node: ast.AST | None) -> str | None:
        if isinstance(node, ast.Name):
            for scope in lexical_scopes(node):
                scoped = scoped_module_aliases.get(id(scope), {})
                if node.id in scoped:
                    return scoped[node.id]
                if node.id in scoped_blocked_module_aliases.get(id(scope), set()):
                    return None
                if shadowed_name_nodes and id(node) in shadowed_name_nodes:
                    return None
        return _module_reference(
            node,
            module_aliases,
            callables=callable_aliases,
            registry_aliases=module_registry_aliases,
            current_module=current,
            path=path,
            shadowed_nodes=shadowed_name_nodes,
        )

    def call_name(node: ast.AST) -> str:
        return _call_name(node, module_aliases, callable_aliases, shadowed_name_nodes)

    def is_source_package(name: str | None) -> bool:
        return name == SOURCE_PACKAGE or bool(name and name.startswith(SOURCE_PACKAGE + "."))

    def is_private_module_name(name: str | None) -> bool:
        if not is_source_package(name):
            return False
        suffix = (name or "")[len(SOURCE_PACKAGE):].strip(".")
        return any(part.startswith("_") and not part.startswith("__") for part in suffix.split("."))

    for scope in ast.walk(tree):
        if not isinstance(scope, scope_types):
            continue
        parent = parent_nodes.get(id(scope))
        while parent is not None and parent is not tree and not isinstance(parent, scope_types):
            parent = parent_nodes.get(id(parent))
        if parent is tree:
            mark_scope(scope, set())

    def approved_lazy_facade_import(node: ast.Call) -> bool:
        return (
            path.name == "__init__.py"
            and call_name(node.func) == "importlib.import_module"
            and len(node.args) == 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "module_name"
            and isinstance(node.args[1], ast.Name)
            and node.args[1].id == "__name__"
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            provider = _provider_module(node, current, path)
            if any(imported.name == "*" for imported in node.names) and (
                is_source_package(provider) or provider in {"sys", "importlib", "operator"}
            ):
                violations.append(
                    f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                    f"uses wildcard import from boundary-sensitive module {provider}"
                )
            if is_private_module_name(provider):
                violations.append(
                    f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                    f"imports private module {provider}"
                )
            if provider == "importlib":
                for imported in node.names:
                    if imported.name == "import_module":
                        callable_aliases[imported.asname or imported.name] = "importlib.import_module"
            elif provider == "builtins":
                for imported in node.names:
                    if imported.name in {"getattr", "setattr", "delattr", "vars", "__import__"}:
                        callable_aliases[imported.asname or imported.name] = f"builtins.{imported.name}"
            elif provider == "operator":
                for imported in node.names:
                    if imported.name in {"attrgetter", "methodcaller"}:
                        callable_aliases[imported.asname or imported.name] = f"operator.{imported.name}"
            elif provider == "sys":
                for imported in node.names:
                    if imported.name == "modules":
                        module_registry_aliases.add(imported.asname or imported.name)
                        violations.append(
                            f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                            "imports the process module registry"
                        )
            if not is_source_package(provider):
                continue
            provider_path = MODULES.get(provider)
            provider_tree = (
                ast.parse(provider_path.read_bytes(), filename=str(provider_path))
                if provider_path is not None else None
            )
            provider_classes = {
                item.name for item in provider_tree.body if isinstance(item, ast.ClassDef)
            } if provider_tree is not None else set()
            for imported in node.names:
                local = imported.asname or imported.name
                if imported.name.startswith("_") and not imported.name.startswith("__"):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        f"imports private {provider}.{imported.name}"
                    )
                child_module = f"{provider}.{imported.name}"
                if child_module in MODULES:
                    if enclosing_scope(node) is tree:
                        module_aliases[local] = child_module
                    else:
                        scoped_module_aliases.setdefault(id(enclosing_scope(node)), {})[local] = child_module
                elif imported.name in provider_classes:
                    imported_classes[local] = provider
        elif isinstance(node, ast.Import):
            for imported in node.names:
                local = imported.asname or imported.name.split(".")[0]
                alias_module = imported.name if imported.asname else imported.name.split(".")[0]
                if enclosing_scope(node) is tree:
                    module_aliases[local] = alias_module
                elif is_source_package(alias_module):
                    scoped_module_aliases.setdefault(id(enclosing_scope(node)), {})[local] = alias_module
                if is_private_module_name(imported.name):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        f"imports private module {imported.name}"
                    )
                if imported.name == SOURCE_PACKAGE or imported.name.startswith(SOURCE_PACKAGE + "."):
                    local = imported.asname or imported.name.split(".")[0]
                    if enclosing_scope(node) is tree:
                        module_aliases[local] = imported.name
                    else:
                        scoped_module_aliases.setdefault(id(enclosing_scope(node)), {})[local] = imported.name

    # Follow simple module/callable aliases and known dynamic imports. Unknown
    # computed imports are rejected below rather than treated as an escape hatch.
    for _ in range(max(1, len(tree.body) + 1)):
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if isinstance(value, ast.Name) and value.id in callable_aliases:
                for target in targets:
                    if isinstance(target, ast.Name) and target.id not in callable_aliases:
                        callable_aliases[target.id] = callable_aliases[value.id]
                        changed = True
            source_call = call_name(
                value.func if isinstance(value, ast.Call) else value,
            )
            result_callable = source_call
            if isinstance(value, ast.Call) and source_call == "builtins.getattr" and len(value.args) > 1:
                owner = module_reference(value.args[0])
                member_names = literal_names(value.args[1])
                result_callable = (
                    f"{owner}.{next(iter(member_names))}"
                    if owner and member_names and len(member_names) == 1
                    else ""
                )
            if result_callable in {"builtins.getattr", "builtins.setattr", "builtins.delattr", "builtins.vars", "builtins.__import__", "importlib.import_module", "operator.attrgetter", "operator.methodcaller"}:
                for target in targets:
                    if isinstance(target, ast.Name) and callable_aliases.get(target.id) != result_callable:
                        callable_aliases[target.id] = result_callable
                        changed = True
            if isinstance(value, ast.Call) and source_call in {"operator.attrgetter", "operator.methodcaller"}:
                selected = set()
                known = True
                for argument in value.args:
                    names = literal_names(argument)
                    if names is None:
                        known = False
                        break
                    selected.update(names)
                for target in targets:
                    if isinstance(target, ast.Name) and target.id not in selector_aliases:
                        selector_aliases[target.id] = selected if known else None
                        changed = True
            if isinstance(value, ast.Name) and value.id in selector_aliases:
                for target in targets:
                    if isinstance(target, ast.Name) and target.id not in selector_aliases:
                        selector_aliases[target.id] = selector_aliases[value.id]
                        changed = True
            if _is_module_registry(value, module_aliases, module_registry_aliases, shadowed_name_nodes):
                for target in targets:
                    if isinstance(target, ast.Name) and target.id not in module_registry_aliases:
                        module_registry_aliases.add(target.id)
                        changed = True
            source = module_reference(value)
            owner_scope = enclosing_scope(node)
            aliases = module_aliases if owner_scope is tree else scoped_module_aliases.setdefault(id(owner_scope), {})
            if source is not None:
                for target in targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if aliases.get(target.id) != source:
                        aliases[target.id] = source
                        changed = True
                    if owner_scope is not tree:
                        scoped_blocked_module_aliases.setdefault(id(owner_scope), set()).discard(target.id)
            else:
                for target in targets:
                    if isinstance(target, ast.Name):
                        if target.id in aliases:
                            aliases.pop(target.id)
                            changed = True
                        if owner_scope is not tree:
                            scoped_blocked_module_aliases.setdefault(id(owner_scope), set()).add(target.id)
        if not changed:
            break

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = call_name(node.func)
            if target in {"importlib.import_module", "builtins.__import__"}:
                imported = module_reference(node)
                if imported is None and not approved_lazy_facade_import(node):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        "uses an unresolved dynamic import"
                    )
                elif imported and is_private_module_name(imported):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        f"dynamically imports private {imported}"
                    )
            if target in {"builtins.getattr", "builtins.setattr", "builtins.delattr"} and node.args:
                provider = module_reference(node.args[0])
                member = node.args[1] if len(node.args) > 1 else None
                member_names = literal_names(member) if member is not None else None
                if provider == "sys":
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        "reflects over the process module registry owner"
                    )
                if provider in {"importlib", "builtins"} and target == "builtins.getattr" and (
                    member_names is None or len(member_names) != 1
                ):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        "uses an unresolved dynamic import-function lookup"
                    )
                if provider == "importlib" and target == "builtins.getattr" and member_names != {"import_module"}:
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        "reads importlib through an unapproved reflective member"
                    )
                if is_source_package(provider):
                    if (
                        target != "builtins.getattr"
                        or not isinstance(member, ast.Constant)
                        or not isinstance(member.value, str)
                        or member.value.startswith("_")
                    ):
                        violations.append(
                            f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                            f"uses reflective access/mutation on {provider}"
                        )
            if target == "builtins.vars" and node.args:
                provider = module_reference(node.args[0])
                if provider in {"sys", "importlib", "builtins"} or is_source_package(provider):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        f"reflects over module namespace {provider}"
                    )
            if target in {"object.__getattribute__", "object.__getattr__"} and node.args:
                provider = module_reference(node.args[0])
                member = node.args[1] if len(node.args) > 1 else None
                if provider in {"sys", "importlib", "builtins"} or (is_source_package(provider) and (
                    not isinstance(member, ast.Constant)
                    or not isinstance(member.value, str)
                    or member.value.startswith("_")
                )):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        f"uses low-level reflection on {provider}"
                    )
            selector_call = node.func if isinstance(node.func, ast.Call) else None
            if selector_call is not None and call_name(
                selector_call.func
            ) in {"operator.attrgetter", "operator.methodcaller"} and node.args:
                provider = module_reference(node.args[0])
                selected = set()
                known = True
                for argument in selector_call.args:
                    names = literal_names(argument)
                    if names is None:
                        known = False
                        break
                    selected.update(names)
                if is_source_package(provider) and (not known or any(name.startswith("_") for name in selected)):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        f"uses reflective selector on {provider}"
                    )
            if isinstance(node.func, ast.Name) and node.func.id in selector_aliases and node.args:
                provider = module_reference(node.args[0])
                selected = selector_aliases[node.func.id]
                if is_source_package(provider) and (
                    selected is None or any(name.startswith("_") for name in selected)
                ):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        f"uses reflective selector on {provider}"
                    )
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and _is_module_registry(node.func.value, module_aliases, module_registry_aliases, shadowed_name_nodes)
            ):
                key = node.args[0] if node.args else None
                if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: dynamic sys.modules lookup"
                    )
                elif is_private_module_name(module_reference(node)):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        f"loads private {module_reference(node)} from sys.modules"
                    )
        elif isinstance(node, ast.Subscript) and _is_module_registry(
            node.value, module_aliases, module_registry_aliases, shadowed_name_nodes
        ):
            key = node.slice
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                violations.append(
                    f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: dynamic sys.modules lookup"
                )
            elif is_private_module_name(module_reference(node)):
                violations.append(
                    f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                    f"loads private {module_reference(node)} from sys.modules"
                )
        elif isinstance(node, ast.Attribute):
            provider = module_reference(node.value)
            if (provider == "sys" and node.attr in {"modules", "__dict__"}) or (
                provider == "sys.modules"
            ) or (provider == "importlib" and node.attr == "__dict__"):
                violations.append(
                    f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                    "accesses the process module registry"
                )
            if is_source_package(provider) and node.attr.startswith("_"):
                violations.append(
                    f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                    f"accesses private {provider}.{node.attr}"
                )

    instance_classes: dict[str, str] = {}

    def class_provider(value: ast.AST | None) -> str | None:
        if isinstance(value, ast.Name):
            return instance_classes.get(value.id) or imported_classes.get(value.id)
        if isinstance(value, ast.Attribute):
            module = module_reference(value.value)
            module_path = MODULES.get(module or "")
            if module_path is None:
                return None
            provider_tree = ast.parse(module_path.read_bytes(), filename=str(module_path))
            if any(isinstance(item, ast.ClassDef) and item.name == value.attr
                   for item in provider_tree.body):
                return module
        if isinstance(value, ast.Call):
            return class_provider(value.func)
        return None

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        provider = class_provider(value)
        if provider is None and isinstance(node, ast.AnnAssign):
            provider = class_provider(node.annotation)
        if provider is None:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                instance_classes[target.id] = provider

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not node.attr.startswith("_"):
            continue
        provider = class_provider(node.value)
        if provider is not None and provider != current:
            violations.append(
                f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                f"accesses private {provider}.{node.attr}"
            )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        target = call_name(node.func)
        if target not in {"builtins.getattr", "builtins.setattr", "builtins.delattr", "builtins.vars"}:
            continue
        module_owner = module_reference(node.args[0])
        class_owner = class_provider(node.args[0]) if module_owner is None else None
        provider = module_owner or class_owner
        if provider is None or provider == current:
            continue
        member = node.args[1] if len(node.args) > 1 else None
        member_values = literal_names(member) if member is not None else None
        if module_owner is not None:
            forbidden = (
                target != "builtins.getattr"
                or member_values is None
                or any(value.startswith("_") for value in member_values)
            )
        else:
            # Public data objects may be read by a statically bounded field
            # loop; unknown or private names cannot be proven to be public.
            forbidden = (
                target == "builtins.vars"
                or member_values is None
                or any(value.startswith("_") for value in member_values)
            )
        if forbidden:
            violations.append(
                f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                f"uses reflective access/mutation on {provider}"
            )

    def parameter_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        args = function.args
        return [
            arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)
        ]

    def parameter_reads_private(function: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
        def inspect(candidate: ast.AST) -> bool:
            if isinstance(candidate, ast.Attribute) and candidate.attr.startswith("_"):
                if isinstance(candidate.value, ast.Name) and candidate.value.id == name:
                    return True
            if not isinstance(candidate, ast.Call):
                return False
            target = call_name(candidate.func)
            if target in {"builtins.getattr", "builtins.setattr", "builtins.delattr", "builtins.vars"}:
                if candidate.args and isinstance(candidate.args[0], ast.Name) and candidate.args[0].id == name:
                    member = candidate.args[1] if len(candidate.args) > 1 else None
                    values = literal_names(member) if member is not None else None
                    if target != "builtins.getattr" or values is None or any(value.startswith("_") for value in values):
                        return True
            if target in {"object.__getattribute__", "object.__getattr__"}:
                if candidate.args and isinstance(candidate.args[0], ast.Name) and candidate.args[0].id == name:
                    member = literal_names(candidate.args[1]) if len(candidate.args) > 1 else None
                    if member is None or any(value.startswith("_") for value in member):
                        return True
            selector = candidate.func if isinstance(candidate.func, ast.Call) else None
            if selector is not None and call_name(selector.func) in {
                "operator.attrgetter", "operator.methodcaller"
            }:
                selected: set[str] = set()
                known = True
                for argument in selector.args:
                    values = literal_names(argument)
                    if values is None:
                        known = False
                        break
                    selected.update(values)
                if candidate.args and isinstance(candidate.args[0], ast.Name) and candidate.args[0].id == name:
                    if not known or any(value.startswith("_") for value in selected):
                        return True
            return False

        def own_scope_nodes(statements: list[ast.stmt]) -> list[ast.AST]:
            nodes: list[ast.AST] = []
            pending = list(statements)
            while pending:
                candidate = pending.pop()
                nodes.append(candidate)
                if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    continue
                pending.extend(ast.iter_child_nodes(candidate))
            return nodes

        def is_comprehension_target(candidate: ast.AST) -> bool:
            parent = parent_nodes.get(id(candidate))
            while parent is not None and parent is not function:
                if isinstance(parent, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    return True
                parent = parent_nodes.get(id(parent))
            return False

        own_nodes = own_scope_nodes(function.body)
        rebind_lines = [
            candidate.lineno
            for candidate in own_nodes
            if isinstance(candidate, ast.Name)
            and isinstance(candidate.ctx, ast.Store)
            and candidate.id == name
            and not is_comprehension_target(candidate)
        ]
        if rebind_lines:
            first_rebind = min(rebind_lines)
            if any(
                inspect(candidate)
                and getattr(candidate, "lineno", first_rebind) < first_rebind
                for candidate in own_nodes
            ):
                return True
            for nested in own_nodes:
                if not isinstance(nested, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                bindings, _, _ = scope_bindings(nested)
                if name in bindings:
                    continue
                if isinstance(nested, ast.ClassDef):
                    class_nodes = own_scope_nodes(nested.body)
                    if nested.lineno < first_rebind and any(inspect(candidate) for candidate in class_nodes):
                        return True
                elif parameter_reads_private(nested, name):
                    called_before_rebind = any(
                        isinstance(candidate, ast.Call)
                        and isinstance(candidate.func, ast.Name)
                        and candidate.func.id == nested.name
                        and candidate.lineno < first_rebind
                        for candidate in own_nodes
                    )
                    if called_before_rebind:
                        return True
            return False

        def visit(candidate: ast.AST, *, root: bool = False) -> bool:
            if not root and isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                # Defaults and decorators execute in the enclosing scope. The body
                # is a closure only when the nested scope does not rebind this name.
                header_nodes: list[ast.AST] = []
                if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    header_nodes.extend(candidate.decorator_list)
                    header_nodes.extend(candidate.args.defaults)
                    header_nodes.extend(value for value in candidate.args.kw_defaults if value is not None)
                    if candidate.returns is not None:
                        header_nodes.append(candidate.returns)
                if any(visit(item) for item in header_nodes):
                    return True
                bindings, _, _ = scope_bindings(candidate)
                if name in bindings:
                    return False
            if inspect(candidate):
                return True
            return any(visit(child) for child in ast.iter_child_nodes(candidate))

        return any(visit(statement) for statement in function.body)

    functions_by_scope: dict[int, dict[str, ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    instance_classes_by_scope: dict[int, dict[str, str]] = {}
    class_defs_by_name: dict[str, list[ast.ClassDef]] = {}
    for definition in ast.walk(tree):
        owner_scope = enclosing_scope(definition)
        if isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions_by_scope.setdefault(id(owner_scope), {})[definition.name] = definition
            for argument in (*definition.args.posonlyargs, *definition.args.args, *definition.args.kwonlyargs):
                if isinstance(argument.annotation, ast.Name):
                    instance_classes_by_scope.setdefault(id(definition), {})[argument.arg] = argument.annotation.id
        elif isinstance(definition, ast.ClassDef):
            class_defs_by_name.setdefault(definition.name, []).append(definition)
    for assignment in ast.walk(tree):
        if isinstance(assignment, ast.AnnAssign) and isinstance(assignment.target, ast.Name):
            if isinstance(assignment.annotation, ast.Name):
                instance_classes_by_scope.setdefault(id(enclosing_scope(assignment)), {})[
                    assignment.target.id
                ] = assignment.annotation.id
        elif isinstance(assignment, ast.Assign) and isinstance(assignment.value, ast.Call):
            if isinstance(assignment.value.func, ast.Name):
                for target in assignment.targets:
                    if isinstance(target, ast.Name):
                        instance_classes_by_scope.setdefault(id(enclosing_scope(assignment)), {})[
                            target.id
                        ] = assignment.value.func.id

    def method_candidates(
        call: ast.Call, context: ast.AST | None = None
    ) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        if not isinstance(call.func, ast.Attribute):
            return []
        receiver = call.func.value
        class_name = None
        if isinstance(receiver, ast.Call) and isinstance(receiver.func, ast.Name):
            class_name = receiver.func.id
        elif isinstance(receiver, ast.Name) and receiver.id in {"self", "cls"}:
            for scope in enclosing_scopes(context or call):
                if isinstance(scope, ast.ClassDef):
                    class_name = scope.name
                    break
        elif isinstance(receiver, ast.Name):
            for scope in enclosing_scopes(context or call):
                class_name = instance_classes_by_scope.get(id(scope), {}).get(receiver.id)
                if class_name is not None:
                    break
        if class_name is None:
            return []
        return [
            member for class_def in class_defs_by_name.get(class_name, [])
            for member in class_def.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and member.name == call.func.attr
        ]

    function_aliases: dict[int, dict[str, tuple[ast.FunctionDef | ast.AsyncFunctionDef, bool]]] = {}

    def function_candidates(call: ast.Call) -> list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, bool]]:
        if isinstance(call.func, ast.Name):
            for scope in lexical_scopes(call):
                alias = function_aliases.get(id(scope), {}).get(call.func.id)
                if alias is not None:
                    return [alias]
                candidate = functions_by_scope.get(id(scope), {}).get(call.func.id)
                if candidate is not None:
                    return [(candidate, False)]
                if id(call.func) in shadowed_name_nodes:
                    return []
            return []
        return [(candidate, True) for candidate in method_candidates(call)]

    for _ in range(max(1, len(tree.body) + 1)):
        changed = False
        for assignment in ast.walk(tree):
            if not isinstance(assignment, (ast.Assign, ast.AnnAssign)) or assignment.value is None:
                continue
            owner_scope = enclosing_scope(assignment)
            source_alias: tuple[ast.FunctionDef | ast.AsyncFunctionDef, bool] | None = None
            if isinstance(assignment.value, ast.Name):
                for scope in lexical_scopes(assignment):
                    source_alias = function_aliases.get(id(scope), {}).get(assignment.value.id)
                    if source_alias is not None:
                        break
                    function = functions_by_scope.get(id(scope), {}).get(assignment.value.id)
                    if function is not None:
                        source_alias = (function, False)
                        break
                    if id(assignment.value) in shadowed_name_nodes:
                        break
            elif isinstance(assignment.value, ast.Attribute):
                fake_call = ast.Call(func=assignment.value, args=[], keywords=[])
                candidates = method_candidates(fake_call, assignment)
                if candidates:
                    source_alias = (candidates[0], True)
            targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                aliases = function_aliases.setdefault(id(owner_scope), {})
                if source_alias is not None:
                    if aliases.get(target.id) != source_alias:
                        aliases[target.id] = source_alias
                        changed = True
                elif target.id in aliases:
                    aliases.pop(target.id)
                    changed = True
        if not changed:
            break
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for function, is_bound_method in function_candidates(node):
            names = parameter_names(function)
            if (is_bound_method or isinstance(node.func, ast.Attribute)) and names and names[0] in {"self", "cls"}:
                names = names[1:]
            passed = list(zip(names, node.args))
            passed.extend((keyword.arg, keyword.value) for keyword in node.keywords if keyword.arg is not None)
            for parameter, argument in passed:
                if is_source_package(module_reference(argument)) and parameter_reads_private(function, parameter):
                    violations.append(
                        f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno}: "
                        f"passes a source module into {function.name} which reads private {parameter} members"
                    )
    return sorted(set(violations))


def test_source_catalog_modules_do_not_import_or_reach_into_private_siblings():
    violations: list[str] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        if path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_bytes(), filename=str(path))
        violations.extend(_private_module_accesses(path, tree))

    assert not violations, "source catalog private sibling dependencies remain:\n" + "\n".join(violations)


def test_shared_module_ports_are_declared_by_their_owners():
    missing: list[str] = []
    for filename, expected in PUBLIC_PORTS.items():
        provider = SOURCE_ROOT / filename
        tree = ast.parse(provider.read_bytes(), filename=str(provider))
        exports = next(
            (ast.literal_eval(node.value) for node in tree.body
             if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == "__all__"
                     for target in node.targets)),
            (),
        )
        if not isinstance(exports, (list, tuple, set)):
            missing.append(f"{filename}: __all__ must be a literal sequence")
            continue
        absent = expected - set(exports)
        missing.extend(f"{filename}: missing {name}" for name in sorted(absent))
    assert not missing, "owner module ports are not explicitly exported:\n" + "\n".join(missing)


def test_storage_owner_public_methods_are_available_without_path_lookups():
    missing: list[str] = []
    for filename, classes in PUBLIC_METHOD_PORTS.items():
        provider = SOURCE_ROOT / filename
        tree = ast.parse(provider.read_bytes(), filename=str(provider))
        for class_name, expected in classes.items():
            node = next(
                (item for item in tree.body
                 if isinstance(item, ast.ClassDef) and item.name == class_name),
                None,
            )
            if node is None:
                missing.append(f"{filename}: missing {class_name}")
                continue
            methods = {
                item.name for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            missing.extend(
                f"{filename}: {class_name}.{name} is not public"
                for name in sorted(expected - methods)
            )
    assert not missing, "storage owner lacks public operations:\n" + "\n".join(missing)


def test_module_boundary_scanner_catches_alias_and_reflection_bypasses():
    provider = f"{SOURCE_PACKAGE}.narrative_evidence"
    probe = SOURCE_ROOT / "_boundary_probe.py"
    cases = (
        "from .narrative_evidence import _private",
        "from ._paragraph_worker import public",
        "import company_wiki.source_catalog._paragraph_worker as hidden\nhidden.public()",
        "from . import narrative_evidence as api\napi._private()",
        "from . import narrative_evidence as api\nother = api\nother._private()",
        "from . import narrative_evidence as api\ngetattr(api, '_private')()",
        "from . import narrative_evidence as api\nname = '_private'\ngetattr(api, name)()",
        "from .canonical_writer import CanonicalSourceWriter\n"
        "writer = CanonicalSourceWriter(catalog)\nwriter._remove_staged(staged)",
        "from .canonical_writer import CanonicalSourceWriter\n"
        "writer = CanonicalSourceWriter(catalog)\ngetattr(writer, '_remove_staged')()",
        "import importlib as loader\n"
        "api = loader.import_module('company_wiki.source_catalog.narrative_evidence')\n"
        "api._private()",
        "from importlib import import_module as load\n"
        "api = load('company_wiki.source_catalog.narrative_evidence')\n"
        "api._private()",
        "import sys\n"
        "api = sys.modules['company_wiki.source_catalog.narrative_evidence']\n"
        "api._private()",
        "from sys import modules as registry\n"
        "api = registry['company_wiki.source_catalog.narrative_evidence']\n"
        "api._private()",
        "from builtins import getattr as reflect\n"
        "from . import narrative_evidence as api\nreflect(api, '_private')()",
        "from builtins import vars as namespace\n"
        "from . import narrative_evidence as api\nnamespace(api)['_private']()",
        "from builtins import setattr as assign\n"
        "from . import narrative_evidence as api\nassign(api, '_private', value)",
        "from . import narrative_evidence as api\nlookup = getattr\nlookup(api, '_private')()",
        "import importlib\n"
        "loader = getattr(importlib, 'import_module')\n"
        "api = loader('company_wiki.source_catalog._paragraph_worker')\napi.public()",
        "import importlib\noperation_name = choose_name()\n"
        "loader = getattr(importlib, operation_name)\n"
        "api = loader('company_wiki.source_catalog._paragraph_worker')\napi.public()",
        "import importlib\n"
        "loader = importlib.__dict__['import_module']\n"
        "api = loader('company_wiki.source_catalog._paragraph_worker')\napi.public()",
        "from . import narrative_evidence as api\n"
        "object.__getattribute__(api, '_private')()",
        "import operator as op\n"
        "from . import narrative_evidence as api\n"
        "read_private = op.attrgetter('_private')\nread_private(api)()",
        "from operator import methodcaller as invoke\n"
        "from . import narrative_evidence as api\n"
        "invoke('_private')(api)",
        "from importlib import import_module as load\n"
        "module_name = build_module_name()\napi = load(module_name)\napi._private()",
        "import sys\nmodule_name = build_module_name()\n"
        "api = sys.modules[module_name]\napi._private()",
        "import sys\nregistry = sys.modules\nmodule_name = build_module_name()\n"
        "api = registry.get(module_name)\napi._private()",
        "import sys\nregistry = sys.modules.copy()\n"
        "api = registry['company_wiki.source_catalog._paragraph_worker']\napi.public()",
        "import sys\nregistry = dict(sys.modules)\n"
        "api = registry['company_wiki.source_catalog._paragraph_worker']\napi.public()",
        "import sys\nregistry = dict(sys.modules.items())\n"
        "api = registry['company_wiki.source_catalog._paragraph_worker']\napi.public()",
        "import sys\nregistry = getattr(sys, 'modules')\n"
        "api = registry['company_wiki.source_catalog._paragraph_worker']\napi.public()",
        "import sys\nlookup = sys.modules.get\n"
        "api = lookup('company_wiki.source_catalog._paragraph_worker')\napi.public()",
        "api = __import__('company_wiki.source_catalog.narrative_evidence', fromlist=['x'])\n"
        "api._private()",
        "def load_private():\n"
        "    from . import narrative_evidence as local_api\n"
        "    return local_api._private()",
        "from . import narrative_evidence as api\n"
        "def helper(api):\n    return api._private()\nhelper(api)",
        "from . import narrative_evidence as api\n"
        "def helper(api):\n    return api._private()\nrun = helper\nrun(api)",
        "from . import narrative_evidence as api\n"
        "class Reader:\n    def helper(self, value):\n        return value._private()\n\n"
        "Reader().helper(api)",
        "from . import narrative_evidence as api\n"
        "class Reader:\n    def helper(self, value):\n        return value._private()\n\n"
        "def invoke(reader: Reader):\n    reader.helper(api)\n",
        "from . import narrative_evidence as api\n"
        "def outer():\n    def helper(value):\n        return value._private()\n    helper(api)\nouter()",
        "from . import narrative_evidence as api\n"
        "def outer():\n    from . import narrative_evidence as local_api\n"
        "    alias = local_api\n    return alias._private()\nouter()",
        "from . import narrative_evidence as api\n"
        "def helper():\n    alias = api\n    return alias._private()\nhelper()",
        "from . import narrative_evidence as api\n"
        "def outer():\n    from . import narrative_evidence as local_api\n"
        "    def inner():\n        return local_api._private()\n    inner()\nouter()",
        "from . import narrative_evidence as api\n"
        "def outer(value):\n    def inner():\n        return value._private()\n    inner()\nouter(api)",
        "from . import narrative_evidence as api\n"
        "def outer(value):\n    def inner():\n        return value._private()\n"
        "    inner()\n    value = local_object\nouter(api)",
        "from . import narrative_evidence as api\n"
        "def outer(api):\n    def inner():\n        nonlocal api\n        return api._private()\n"
        "    inner()\nouter(api)",
        "from . import narrative_evidence as api\n"
        "def outer(value):\n    class Nested:\n        item = value._private\n    return Nested\nouter(api)",
        "from . import narrative_evidence as api\n"
        "def reader(items):\n    [item for api in items]\n    return api._private()\nreader([])",
        "from . import narrative_evidence as api\n"
        "class Reader:\n    api = local_object\n"
        "    def read(self):\n        return api._private()\n",
        "from . import narrative_evidence as api\n"
        "def outer():\n    def helper(value):\n        return value._private()\n"
        "    run = helper\n    run(api)\nouter()",
        "from . import narrative_evidence as api\n"
        "class Reader:\n    def helper(self, value):\n        return value._private()\n"
        "def outer():\n    reader = Reader()\n    run = reader.helper\n    run(api)\nouter()",
        "from . import narrative_evidence as api\n"
        "def helper(value):\n    return object.__getattribute__(value, '_private')\nhelper(api)",
        "import operator\nfrom . import narrative_evidence as api\n"
        "def helper(value):\n    return operator.attrgetter('_private')(value)\nhelper(api)",
        "import operator\nfrom . import narrative_evidence as api\n"
        "def helper(value):\n    return operator.methodcaller('_private')(value)\nhelper(api)",
        "from . import narrative_evidence as api\n"
        "def helper(value):\n    return object.__getattribute__(value, '_private')\nhelper(api)",
        "from sys import *\n"
        "api = modules['company_wiki.source_catalog._paragraph_worker']\napi.public()",
        "from importlib import *\n"
        "api = import_module('company_wiki.source_catalog._paragraph_worker')\napi.public()",
        "from operator import *\n"
        "from . import narrative_evidence as api\nattrgetter('_private')(api)",
        "from .narrative_evidence import *\n",
        "api = __import__('company_wiki.source_catalog._private', fromlist=['x'])\napi.call()",
    )
    for source in cases:
        violations = _private_module_accesses(probe, ast.parse(source))
        assert violations, f"module boundary scanner missed private access in {provider}: {source}"


def test_module_boundary_scanner_allows_declared_public_member_access():
    probe = SOURCE_ROOT / "_boundary_probe.py"
    source = (
        "from . import narrative_evidence as narrative\nnarrative.emit_pdf_page()\n"
        "import operator\noperator.attrgetter('emit_pdf_page')(narrative)\n"
        "def shadowed(api):\n    return api._private\n"
        "def local_assignment():\n    api = local_object\n    return api._field\n"
        "def outer(api):\n"
        "    class Nested:\n        value = api._field\n"
        "    return Nested\n"
        "from . import narrative_evidence as narrative_alias\n"
        "narrative_alias = local_object\nnarrative_alias._field\n"
        "from . import narrative_evidence as api\n"
        "def rebound_import():\n    from . import narrative_evidence as api\n"
        "    api = local_object\n    return api._field\n"
        "rebound_import()\n"
        "def helper(value):\n    def nested(value):\n        return value._private()\n    return value.emit_pdf_page()\n"
        "helper(narrative)\n"
        "def helper_with_nested_parameter(value):\n"
        "    def nested(value):\n        return value._private()\n"
        "    return value.emit_pdf_page()\n"
        "helper_with_nested_parameter(narrative)\n"
        "def reassigned_closure(value):\n"
        "    def nested():\n        return value._private()\n"
        "    value = local_object\n    nested()\n"
        "reassigned_closure(narrative)\n"
        "def local_import():\n    from . import narrative_evidence as api\n    return api.emit_pdf_page()"
    )
    assert not _private_module_accesses(probe, ast.parse(source))


def test_lazy_package_facade_resolves_only_declared_public_exports():
    import company_wiki.source_catalog as package

    assert package.__all__
    assert all(not name.startswith("_") for name in package.__all__)
    assert set(package.__all__) <= set(dir(package))
