"""Resolve static package references for the architecture contracts.

This follows imports, simple aliases and literal reflective lookups within a
scope. It never imports the code being inspected or executes a computed name.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from importlib.util import resolve_name
from pathlib import Path


_ROOT = "company_wiki"
_FEEDBACK_PACKAGE = "tools.feedback_loop"
_SHARED_OWNER = "<shared>"
_SHARED_CONTRACTS = {"document_model", "resource_budget", "source_contract"}
# This executable composes the catalogue and automation owners. Other root
# helpers depend on value contracts without reaching their runtime owners.
_ASSEMBLY_OWNERS = {"scheduled_reading": "automation"}
_LAYERS = {
    "automation", "document_model", "document_normalization", "document_understanding",
    "narrative_subject", "parser_adapters", "resource_budget", "source_catalog", "source_contract",
}
_RUNTIME_OWNERS = (_LAYERS - _SHARED_CONTRACTS) | {"feedback_loop"}
_BUILTINS = {
    "__import__", "getattr", "setattr", "delattr", "vars", "globals", "locals",
    "eval", "exec", "compile",
}
_DYNAMIC_CODE_EXECUTION = {"builtins.eval", "builtins.exec", "builtins.compile"}
_DYNAMIC_CODE_NAMES = {"eval", "exec", "compile"}
_BUILTIN_NAMESPACE_NAMES = {"builtins", "builtins.__dict__"}
_MODULE_GLOBALS = "builtins.current_namespace"
_ATTRIBUTE_LOOKUPS = {"builtins.getattr", "builtins.setattr", "builtins.delattr"}
_PUBLIC_METADATA = {"__all__", "__name__", "__qualname__", "__doc__", "__module__", "__version__"}
_SOURCE_INSPECTION = {
    "inspect.getfile", "inspect.getsourcefile", "inspect.getsource", "inspect.getsourcelines",
}
_REFLECTION_CALLS = _ATTRIBUTE_LOOKUPS | _SOURCE_INSPECTION | {"builtins.vars"}
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _canonical_name(name: str) -> str:
    if name == "src.company_wiki" or name.startswith("src.company_wiki."):
        return name.removeprefix("src.")
    return name


def owner(name: str) -> str | None:
    name = _canonical_name(name)
    if name == _FEEDBACK_PACKAGE or name.startswith(_FEEDBACK_PACKAGE + "."):
        return "feedback_loop"
    root, _, rest = name.partition(".")
    if root != _ROOT or not rest:
        return None
    layer = rest.split(".", 1)[0]
    return layer if layer in _LAYERS else _ASSEMBLY_OWNERS.get(layer, _SHARED_OWNER)


def _module_name(root: Path, path: Path, namespace: str) -> str:
    parts = path.relative_to(root).with_suffix("").parts
    return ".".join((namespace, *(parts[:-1] if parts[-1] == "__init__" else parts)))


def _cyclic_components(graph: dict[str, tuple[str, ...]]) -> tuple[tuple[str, ...], ...]:
    """Tarjan components with stable membership and output order."""
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    pending: list[str] = []
    active: set[str] = set()
    cycles: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        indices[node] = low[node] = len(indices)
        pending.append(node)
        active.add(node)
        for neighbor in graph[node]:
            if neighbor not in indices:
                visit(neighbor)
                low[node] = min(low[node], low[neighbor])
            elif neighbor in active:
                low[node] = min(low[node], indices[neighbor])
        if low[node] != indices[node]:
            return
        members = []
        while pending:
            member = pending.pop()
            active.remove(member)
            members.append(member)
            if member == node:
                break
        if len(members) > 1 or node in graph[node]:
            cycles.append(tuple(sorted(members)))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return tuple(sorted(cycles))


@cache
def _module_body(path: Path) -> list[ast.stmt]:
    return ast.parse(path.read_bytes(), filename=str(path)).body


@cache
def literal_exports(path: Path) -> frozenset[str] | None:
    for statement in _module_body(path):
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
        else:
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
            continue
        value = statement.value
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)) and all(
            isinstance(item, ast.Constant) and isinstance(item.value, str) for item in value.elts
        ):
            return frozenset(item.value for item in value.elts)
        break
    return None


@cache
def _top_level_symbols(path: Path) -> dict[str, ast.stmt]:
    symbols: dict[str, ast.stmt] = {}
    statements = list(_module_body(path))
    for node in statements:
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            # A lazy package facade declares the same public types for tooling.
            statements.extend(node.body)
        if isinstance(node, (*_FUNCTIONS, ast.ClassDef)):
            symbols[node.name] = node
        elif isinstance(node, ast.ImportFrom):
            symbols.update((alias.asname or alias.name, node) for alias in node.names)
    return symbols


@dataclass(frozen=True)
class _Reference:
    name: str
    module: bool = False
    provider_value: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _canonical_name(self.name))


@dataclass(frozen=True)
class BoundaryScan:
    imports: tuple[tuple[str, str, tuple[str, ...], int], ...]
    violations: tuple[str, ...]
    runtime_imports: tuple[str, ...]


class LayerBoundaries:
    def __init__(self, root: Path, *, feedback_root: Path | None = None):
        self.root = root
        self.feedback_root = feedback_root
        self.modules = {
            self.module_name(path): path
            for source in (root, feedback_root)
            if source is not None
            for path in sorted(source.rglob("*.py"))
        }
        self._owned_subpackages = {
            name for name, path in self.modules.items()
            if name.startswith(_ROOT + ".") and name.count(".") >= 2
            and path.name == "__init__.py" and literal_exports(path) is not None
        }

    def module_name(self, path: Path) -> str:
        if self.feedback_root is not None and path.is_relative_to(self.feedback_root):
            return _module_name(self.feedback_root, path, _FEEDBACK_PACKAGE)
        return _module_name(self.root, path, _ROOT)

    def relative_path(self, path: Path) -> str:
        if self.feedback_root is not None and path.is_relative_to(self.feedback_root):
            return "tools/feedback_loop/" + path.relative_to(self.feedback_root).as_posix()
        return path.relative_to(self.root).as_posix()

    @cache
    def private_owner(self, name: str) -> str | None:
        coarse = owner(name)
        while name:
            if name in self._owned_subpackages:
                return name
            name, _, _ = name.rpartition(".")
        return coarse

    def scan(self, path: Path, tree: ast.AST) -> BoundaryScan:
        scanner = _Scanner(self, path)
        scanner.visit(tree)
        return BoundaryScan(
            tuple(sorted(scanner.edges)), tuple(dict.fromkeys(scanner.violations)),
            tuple(sorted(scanner.runtime_imports)),
        )

    def runtime_import_cycles(self) -> tuple[tuple[str, ...], ...]:
        """Report potential runtime import components for diagnostics."""
        graph = {}
        for module, path in self.modules.items():
            tree = ast.parse(path.read_bytes(), filename=str(path))
            graph[module] = tuple(
                dependency for dependency in self.scan(path, tree).runtime_imports
                if dependency in self.modules
            )
        return _cyclic_components(graph)

    @cache
    def definition(self, name: str) -> tuple[str, bool] | None:
        """Find a callable's defining module and whether it is a class, through re-exports."""
        seen: set[str] = set()
        while name not in seen:
            seen.add(name)
            module, _, symbol = name.rpartition(".")
            path = self.modules.get(module)
            if path is None:
                break
            node = _top_level_symbols(path).get(symbol)
            if isinstance(node, (*_FUNCTIONS, ast.ClassDef)):
                return module, isinstance(node, ast.ClassDef)
            if not isinstance(node, ast.ImportFrom):
                break
            member = next(alias.name for alias in node.names if (alias.asname or alias.name) == symbol)
            provider = node.module or ""
            if node.level:
                package = module if path.name == "__init__.py" else module.rpartition(".")[0]
                provider = resolve_name("." * node.level + provider, package)
            name = f"{_canonical_name(provider)}.{member}"
        return None


class _Scanner(ast.NodeVisitor):
    def __init__(self, rules: LayerBoundaries, path: Path):
        self.rules = rules
        self.modules = rules.modules
        name = rules.module_name(path)
        self.caller = owner(name) or _SHARED_OWNER
        self.private_owner = rules.private_owner(name)
        self.package = name if path.name == "__init__.py" else name.rpartition(".")[0]
        self.path = rules.relative_path(path)
        self.edges: set[tuple[str, str, tuple[str, ...], int]] = set()
        self.runtime_imports: set[str] = set()
        self._runtime_branch = True
        self.violations: list[str] = []
        self.bindings: dict[str, object] = {name: _Reference(f"builtins.{name}") for name in _BUILTINS}
        self.bindings.update(
            __builtins__=_Reference("builtins", True),
            __package__=self.package,
            __name__=name,
        )
        self.imported_modules: set[str] = set()
        self.class_fields: dict[str, _Reference] | None = None
        self.receiver: tuple[str, dict[str, _Reference]] | None = None

    def _foreign(self, name: str) -> bool:
        provider = owner(name)
        return provider is not None and provider != self.caller

    def _private_foreign(self, name: str) -> bool:
        provider = self.rules.private_owner(name)
        return name == _ROOT or (provider is not None and provider != self.private_owner)

    def _external_namespace(self, name: str) -> bool:
        return name == _ROOT or self._foreign(name)

    def _report(self, node: ast.AST, detail: str) -> None:
        self.violations.append(f"{self.path}:{node.lineno}: {detail}")

    def _check_module_objects(self, node: ast.AST, values: Iterable[ast.AST | None]) -> None:
        for value in values:
            ref = self._reference(value)
            if ref is not None and ref.module and self._private_foreign(ref.name):
                self._report(node, f"module object {ref.name} must be used through its public members")

    def _child(self, base: _Reference, name: str) -> _Reference:
        qualified = _canonical_name(f"{base.name}.{name}")
        return _Reference(
            qualified, base.module and (qualified == _ROOT or qualified in self.modules),
            base.provider_value or self._is_foreign_class(base),
        )

    def _record_import(self, node: ast.AST, module: str, names: tuple[str, ...] = ()) -> None:
        module = _canonical_name(module)
        provider_owner = owner(module)
        if module != _ROOT and provider_owner is None:
            return
        parts = module.split(".")
        self.imported_modules.update(".".join(parts[:i]) for i in range(1, len(parts) + 1))
        if module != _ROOT:
            self.edges.add((self.caller, module, names, node.lineno))
            if self._runtime_branch:
                self.runtime_imports.add(module)
        if self.caller == _SHARED_OWNER and provider_owner in _RUNTIME_OWNERS:
            self._report(node, f"shared helper depends on runtime owner {module}")
        if self._private_foreign(module) and any(part.startswith("_") for part in parts[1:]):
            self._report(node, f"private module {module}")
        if self._foreign(module):
            provider = self.modules.get(module)
            exports = literal_exports(provider) if provider is not None else None
            if exports is None:
                self._report(node, f"{module} has no declared public API")
        for name in names:
            parent = _Reference(module, True)
            self._check_member(node, parent, name)
            child = self._child(parent, name)
            if child.module and child.name not in self.imported_modules:
                self._record_import(node, child.name)
            elif child.module and self._runtime_branch:
                self.runtime_imports.add(child.name)

    def _check_member(self, node: ast.AST, base: _Reference, name: str | None) -> None:
        child = self._child(base, name) if name is not None else None
        if base.name == _ROOT and child is not None and child.module:
            if child.name not in self.imported_modules:
                self._record_import(node, child.name)
            return
        if name is None:
            if self._private_foreign(base.name):
                self._report(node, f"dynamic attribute on {base.name} cannot be checked against its public API")
            return
        if name.startswith("_") and name not in _PUBLIC_METADATA:
            if self._private_foreign(base.name):
                self._report(node, f"private attribute {child.name}")
            return
        if not self._external_namespace(base.name):
            return
        if base.module and name not in _PUBLIC_METADATA:
            provider = self.modules.get(base.name)
            exports = literal_exports(provider) if provider is not None else None
            # An explicit dotted module import binds the intermediate namespaces.
            if child.module and child.name in self.imported_modules and isinstance(node, ast.Attribute):
                return
            if exports is None or name not in exports:
                self._report(node, f"{child.name} is not declared public")

    def _argument(self, call: ast.Call, index: int, name: str) -> ast.AST | None:
        return call.args[index] if index < len(call.args) else next(
            (kw.value for kw in call.keywords if kw.arg == name), None
        )

    def _literal(self, node: ast.AST | None):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.bindings.get(node.id)
        if isinstance(node, ast.Attribute) and node.attr == "__module__":
            ref = self._reference(node.value)
            if ref is not None and (definition := self.rules.definition(ref.name)) is not None:
                return definition[0]
        if isinstance(node, (ast.Tuple, ast.List)):
            return tuple(self._reference(item) or self._literal(item) for item in node.elts)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = self._literal(node.left), self._literal(node.right)
            if isinstance(left, str) and isinstance(right, str):
                return left + right
        if isinstance(node, ast.FormattedValue) and node.conversion == -1 and node.format_spec is None:
            return self._literal(node.value)
        if isinstance(node, ast.JoinedStr):
            parts = [self._literal(part) for part in node.values]
            if all(isinstance(part, str) for part in parts):
                return "".join(parts)
        return None

    def _module_lookup(self, node: ast.Call):
        callee = self._reference(node.func)
        if callee is None:
            return None
        if callee.name == "sys.modules.get":
            name = self._literal(self._argument(node, 0, "key"))
            return (name, (), name) if isinstance(name, str) else None
        if callee.name not in {"importlib.import_module", "builtins.__import__"}:
            return None
        name = self._literal(self._argument(node, 0, "name"))
        if not isinstance(name, str):
            return None
        if callee.name == "importlib.import_module":
            if name.startswith("."):
                package = self._literal(self._argument(node, 1, "package"))
                if not isinstance(package, str):
                    return None
                try:
                    name = resolve_name(name, package)
                except ImportError:
                    return None
            return name, (), name
        level = self._literal(self._argument(node, 4, "level"))
        fromlist = self._literal(self._argument(node, 3, "fromlist"))
        names = tuple(item for item in fromlist if isinstance(item, str)) if isinstance(fromlist, tuple) else ()
        if type(level) is int and level > 0:
            try:
                qualified = resolve_name("." * level + name, self.package)
            except ImportError:
                return None
            bound = qualified.rsplit(".", name.count("."))[0] if name else qualified
        else:
            qualified, bound = name, name.split(".", 1)[0]
        return qualified, names, qualified if names else bound

    def _loaded_module(self, node: ast.Subscript) -> str | None:
        base = self._reference(node.value)
        key = self._literal(node.slice)
        return key if base is not None and base.name == "sys.modules" and isinstance(key, str) else None

    def _reference(self, node: ast.AST | None) -> _Reference | None:
        if isinstance(node, ast.Name):
            value = self.bindings.get(node.id)
            return value if isinstance(value, _Reference) else None
        if isinstance(node, ast.IfExp):
            for branch in (node.body, node.orelse):
                ref = self._reference(branch)
                if ref is not None and (ref.module or self._is_foreign_class(ref)):
                    return ref
        if isinstance(node, ast.BoolOp):
            # `and` returns its final operand when all earlier operands are true;
            # `or` may return any operand that is the first truthy value.
            if isinstance(node.op, ast.And):
                if any(
                    isinstance(value, ast.Constant) and not bool(value.value)
                    for value in node.values[:-1]
                ):
                    return None
                values = node.values[-1:]
            else:
                values = node.values
            for value in values:
                if isinstance(node.op, ast.Or) and isinstance(value, ast.Constant):
                    if bool(value.value):
                        break
                    continue
                ref = self._reference(value)
                if ref is not None and (ref.module or self._is_foreign_class(ref)):
                    return ref
        if isinstance(node, ast.NamedExpr):
            return self._reference(node.value)
        if isinstance(node, ast.Attribute):
            if (self.receiver is not None and isinstance(node.value, ast.Name)
                    and node.value.id == self.receiver[0]):
                return self.receiver[1].get(node.attr)
            base = self._reference(node.value)
            return self._child(base, node.attr) if base is not None else None
        if isinstance(node, ast.Subscript):
            if (name := self._loaded_module(node)) is not None:
                return _Reference(name, True)
            base = self._reference(node.value)
            key = self._literal(node.slice)
            if base is not None and isinstance(key, str):
                if base.name in _BUILTIN_NAMESPACE_NAMES and key in _DYNAMIC_CODE_NAMES:
                    return _Reference(f"builtins.{key}")
                if base.name == _MODULE_GLOBALS and key == "__builtins__":
                    return _Reference("builtins", True)
            sequence, index = self._literal(node.value), self._literal(node.slice)
            if isinstance(sequence, tuple) and type(index) is int and -len(sequence) <= index < len(sequence):
                member = sequence[index]
                return member if isinstance(member, _Reference) else None
        if isinstance(node, ast.Call):
            if imported := self._module_lookup(node):
                return _Reference(imported[2], True)
            callee = self._reference(node.func)
            if callee is not None and (callee.provider_value or self._is_foreign_class(callee)):
                return _Reference(callee.name, provider_value=True)
            if callee is not None and callee.name == "builtins.vars":
                target = self._reference(self._argument(node, 0, "object"))
                if target is None:
                    return _Reference(_MODULE_GLOBALS)
                if target is not None and target.name == "builtins":
                    return _Reference("builtins.__dict__")
            if callee is not None and callee.name in {"builtins.globals", "builtins.locals"}:
                return _Reference(_MODULE_GLOBALS)
            if callee is not None and callee.name.endswith(".get"):
                namespace = callee.name.removesuffix(".get")
                key = self._literal(self._argument(node, 0, "key"))
                if namespace in {*_BUILTIN_NAMESPACE_NAMES, _MODULE_GLOBALS}:
                    if namespace == _MODULE_GLOBALS and key == "__builtins__":
                        return _Reference("builtins", True)
                    if key in _DYNAMIC_CODE_NAMES:
                        return _Reference(f"builtins.{key}")
            if callee is not None and callee.name == "builtins.getattr":
                base = self._reference(self._argument(node, 0, "object"))
                name = self._literal(self._argument(node, 1, "name"))
                if base is not None and isinstance(name, str):
                    return self._child(base, name)
        return None

    def _is_foreign_class(self, ref: _Reference) -> bool:
        if ref.module or not self._private_foreign(ref.name):
            return False
        definition = self.rules.definition(ref.name)
        return definition is not None and definition[1]

    def _annotated_reference(self, node: ast.AST | None) -> _Reference | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                node = ast.parse(node.value, mode="eval").body
            except SyntaxError:
                return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = self._annotated_reference(node.left)
            right = self._annotated_reference(node.right)
            return (left or right) if left is None or right is None or left == right else None
        if isinstance(node, ast.Subscript):
            container = self._reference(node.value)
            if container is not None and container.name == "typing.Optional":
                return self._annotated_reference(node.slice)
        ref = self._reference(node)
        return ref if ref is not None and self._is_foreign_class(ref) else None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._record_import(node, alias.name)
            bound = alias.name if alias.asname else alias.name.split(".", 1)[0]
            self.bindings[alias.asname or bound] = _Reference(bound, True)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if node.level:
            module = resolve_name("." * node.level + module, self.package)
        self._record_import(node, module, tuple(alias.name for alias in node.names))
        for alias in node.names:
            self.bindings[alias.asname or alias.name] = self._child(_Reference(module, True), alias.name)

    def _import_condition(self, test: ast.expr) -> bool | None:
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            inner = self._import_condition(test.operand)
            return None if inner is None else not inner
        guard = self._reference(test)
        if guard is not None and guard.name == "typing.TYPE_CHECKING":
            return False
        if (isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name) and test.left.id == "__name__"
                and len(test.ops) == 1 and isinstance(test.ops[0], (ast.Eq, ast.NotEq))
                and self._literal(test.comparators[0]) == "__main__"):
            return isinstance(test.ops[0], ast.NotEq)
        return None

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        condition = self._import_condition(node.test)
        outer = self._runtime_branch
        try:
            self._runtime_branch = outer and condition is not False
            for item in node.body:
                self.visit(item)
            self._runtime_branch = outer and condition is not True
            for item in node.orelse:
                self.visit(item)
        finally:
            self._runtime_branch = outer

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.visit(node.value)
        base = self._reference(node.value)
        if base is not None:
            self._check_member(node, base, node.attr)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        self.generic_visit(node)
        if (module := self._loaded_module(node)) is not None:
            self._record_import(node, module)

    def visit_Dict(self, node: ast.Dict) -> None:
        self.generic_visit(node)
        self._check_module_objects(node, (*node.keys, *node.values))

    def _visit_comprehension(self, generators: list[ast.comprehension],
                             values: Iterable[ast.AST]) -> None:
        if not generators:
            return
        # Python evaluates the first iterable outside the implicit comprehension
        # scope; targets and all remaining expressions live in the local scope.
        self.visit(generators[0].iter)
        enclosing_bindings, enclosing_imports = self.bindings, self.imported_modules
        self.bindings = enclosing_bindings.copy()
        self.imported_modules = enclosing_imports.copy()
        target_names = {
            target.id
            for generator in generators
            for target in ast.walk(generator.target)
            if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store)
        }
        try:
            for index, generator in enumerate(generators):
                if index:
                    self.visit(generator.iter)
                self.visit(generator.target)
                for condition in generator.ifs:
                    self.visit(condition)
            for value in values:
                self.visit(value)
                self._check_module_objects(value, (value,))
            for name, value in self.bindings.items():
                if name in target_names or value == enclosing_bindings.get(name):
                    continue
                previous = enclosing_bindings.get(name)
                value_is_boundary = isinstance(value, _Reference) and (
                    value.module or self._is_foreign_class(value)
                )
                previous_is_boundary = isinstance(previous, _Reference) and (
                    previous.module or self._is_foreign_class(previous)
                )
                if value_is_boundary or previous_is_boundary:
                    # Assignment expressions in comprehensions bind outside the
                    # implicit scope; retain either possible boundary value when
                    # the comprehension may execute zero or multiple times.
                    enclosing_bindings[name] = previous if previous_is_boundary else value
                else:
                    enclosing_bindings[name] = value
        finally:
            self.bindings, self.imported_modules = enclosing_bindings, enclosing_imports

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node.generators, (node.key, node.value))

    def visit_List(self, node: ast.List | ast.Tuple | ast.Set) -> None:
        self.generic_visit(node)
        self._check_module_objects(node, node.elts)

    visit_Tuple = visit_List
    visit_Set = visit_List

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node.generators, (node.elt,))

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node.generators, (node.elt,))

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node.generators, (node.elt,))

    def visit_Return(self, node: ast.Return) -> None:
        self.generic_visit(node)
        self._check_module_objects(node, (node.value,))

    def visit_Yield(self, node: ast.Yield) -> None:
        self.generic_visit(node)
        self._check_module_objects(node, (node.value,))

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        self.generic_visit(node)
        self._check_module_objects(node, (node.value,))

    def visit_Call(self, node: ast.Call) -> None:
        self.generic_visit(node)
        if imported := self._module_lookup(node):
            self._record_import(node, imported[0], imported[1])
        callee = self._reference(node.func)
        if callee is None or callee.name not in _REFLECTION_CALLS:
            self._check_module_objects(node, (*node.args, *(kw.value for kw in node.keywords)))
        if callee is None:
            return
        if callee.name in _DYNAMIC_CODE_EXECUTION:
            self._report(node, f"dynamic code execution via {callee.name} is forbidden by module boundary contracts")
        target = self._reference(self._argument(node, 0, "object"))
        if target is None:
            return
        if callee.name in _ATTRIBUTE_LOOKUPS:
            name = self._literal(self._argument(node, 1, "name"))
            self._check_member(node, target, name if isinstance(name, str) else None)
        elif self._private_foreign(target.name) and (
            callee.name == "builtins.vars" or callee.name in _SOURCE_INSPECTION
        ):
            self._report(node, f"{callee.name} reads implementation of {target.name}")

    def _assign(self, targets: list[ast.expr], value: ast.expr | None,
                annotation: ast.expr | None = None) -> None:
        if value is not None:
            self.visit(value)
        binding = self._annotated_reference(annotation) or self._reference(value) or self._literal(value)
        for target in targets:
            self.visit(target)
            if isinstance(target, ast.Name):
                self.bindings[target.id] = binding
                if self.class_fields is not None and isinstance(binding, _Reference):
                    self.class_fields[target.id] = binding
            elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(binding, tuple):
                if len(target.elts) == len(binding):
                    for item, member in zip(target.elts, binding):
                        if isinstance(item, ast.Name):
                            self.bindings[item.id] = member
            elif isinstance(target, (ast.Attribute, ast.Subscript)):
                self._check_module_objects(target, (value,))
                if (isinstance(target, ast.Attribute) and self.receiver is not None
                        and isinstance(target.value, ast.Name) and target.value.id == self.receiver[0]
                        and isinstance(binding, _Reference)):
                    self.receiver[1][target.attr] = binding

    def visit_Assign(self, node: ast.Assign) -> None:
        self._assign(node.targets, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.visit(node.annotation)
        self._assign([node.target], node.value, node.annotation)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._assign([node.target], node.value)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.bindings[node.id] = None

    def _local_body(self, body: Iterable[ast.AST], arguments: ast.arguments | None = None, *,
                    class_fields: dict[str, _Reference] | None = None,
                    receiver: tuple[str, dict[str, _Reference]] | None = None,
                    module_escape: ast.AST | None = None) -> None:
        enclosing = self.bindings
        enclosing_imports = self.imported_modules
        enclosing_fields, enclosing_receiver = self.class_fields, self.receiver
        self.bindings = enclosing.copy()
        self.imported_modules = enclosing_imports.copy()
        self.class_fields, self.receiver = class_fields, receiver
        try:
            if arguments is not None:
                positional = (*arguments.posonlyargs, *arguments.args)
                defaults = dict(zip(positional[len(positional) - len(arguments.defaults):], arguments.defaults))
                defaults.update(zip(arguments.kwonlyargs, arguments.kw_defaults))
                self.bindings.update(
                    {
                        arg.arg: self._annotated_reference(arg.annotation) or self._reference(defaults.get(arg))
                        for arg in (*positional, *arguments.kwonlyargs)
                    }
                )
                for variadic in (arguments.vararg, arguments.kwarg):
                    if variadic is not None:
                        self.bindings[variadic.arg] = None
            for item in body:
                self.visit(item)
            if module_escape is not None:
                self._check_module_objects(module_escape, (module_escape,))
        finally:
            self.bindings = enclosing
            self.imported_modules = enclosing_imports
            self.class_fields, self.receiver = enclosing_fields, enclosing_receiver

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.visit(node.args)
        self._check_module_objects(node, (*node.args.defaults, *node.args.kw_defaults))
        if node.returns is not None:
            self.visit(node.returns)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.bindings[node.name] = None
        parameters = (*node.args.posonlyargs, *node.args.args)
        receiver = self.receiver
        if self.class_fields is not None and parameters and not any(
            isinstance(decorator, ast.Name) and decorator.id in {"staticmethod", "classmethod"}
            for decorator in node.decorator_list
        ):
            receiver = (parameters[0].arg, self.class_fields)
        elif receiver is not None and any(arg.arg == receiver[0] for arg in (*parameters, *node.args.kwonlyargs)):
            receiver = None
        self._local_body(node.body, node.args, receiver=receiver)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.visit(node.args)
        self._check_module_objects(node, (*node.args.defaults, *node.args.kw_defaults))
        self._local_body([node.body], node.args, module_escape=node.body)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for item in (*node.bases, *node.keywords, *node.decorator_list):
            self.visit(item)
        self.bindings[node.name] = None
        fields = [item for item in node.body if not isinstance(item, _FUNCTIONS)]
        methods = [item for item in node.body if isinstance(item, _FUNCTIONS)]
        # Method use of a constructor-injected port is independent of source order.
        methods.sort(key=lambda method: method.name != "__init__")
        self._local_body((*fields, *methods), class_fields={})
