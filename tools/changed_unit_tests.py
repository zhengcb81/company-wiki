"""Conservative, cache-free unit selection for the complete Git push range.

Static imports are an optimization, not a replacement for CI's full unit suite.
Uncertain ranges, configuration, shared test entrypoints and dynamic runtime
execution use it all. Test-only changes retain their known helper consumers.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess


def changed_paths(root: Path, push_input: str) -> set[str] | None:
    """None means no trustworthy comparison; include both ends of renames."""
    changes: set[str] = set()
    if not push_input.strip():
        return None
    for line in push_input.splitlines():
        parts = line.split()
        if len(parts) != 4:
            return None
        _, new, _, old = parts
        if not all(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha) for sha in (old, new)):
            return None
        if set(new) == {"0"}:
            continue  # deleting a ref introduces no new code
        if set(old) == {"0"}:
            return None
        try:
            result = subprocess.run(
                ["git", "diff", "--no-renames", "--name-only", old, new, "--"],
                cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=15, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode:
            return None
        changes.update(result.stdout.splitlines())
    return changes


def _aliases(name: str) -> tuple[str, ...]:
    module = name.removesuffix(".py").replace("/", ".")
    module = module.removesuffix(".__init__")
    if module.startswith("src."):
        return (module[4:],)
    if module.startswith(("scripts.", "tests.")):
        return (module, module.split(".", 1)[1])
    return (module,)


def _nodes(tree):
    return tree if isinstance(tree, list) else ast.walk(tree)


def _dotted_name(node: ast.AST) -> str | None:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    return ".".join([node.id, *reversed(parts)]) if isinstance(node, ast.Name) else None


def _imports(tree: ast.AST, module: str, package: bool) -> set[str]:
    names = set()
    for node in _nodes(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module or ""
            if node.level:
                parent = module.split(".") if package else module.split(".")[:-1]
                parent = parent[:len(parent) - node.level + 1]
                prefix = ".".join([*parent, *([prefix] if prefix else [])])
            names.add(prefix)
            names.update(f"{prefix}.{alias.name}" for alias in node.names if alias.name != "*")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Literal import_module, mock.patch and module.function targets.
            if re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", node.value):
                names.add(node.value)
    return names


def _dynamic_execution(tree: ast.AST) -> bool:
    aliases = {}
    for node in _nodes(tree):
        if isinstance(node, ast.Import):
            aliases.update({alias.asname or alias.name: alias.name for alias in node.names})
        elif isinstance(node, ast.ImportFrom) and node.module:
            aliases.update({alias.asname or alias.name: f"{node.module}.{alias.name}" for alias in node.names})
    for node in _nodes(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted_name(node.func) or ast.unparse(node.func)
        head, _, tail = name.partition(".")
        name = aliases.get(head, head) + ("." + tail if tail else "")
        if name in {"exec", "eval", "builtins.exec", "builtins.eval", "os.system"} or name.startswith("subprocess."):
            return True
        if name.endswith("run_path"):
            return True  # A filesystem path cannot be resolved as a Python import.
        if name.endswith(("import_module", "__import__", "run_module", "run_path")):
            if (not node.args or not isinstance(node.args[0], ast.Constant)
                    or not isinstance(node.args[0].value, str)
                    or not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", node.args[0].value)):
                return True
    return False


def _is_unit_test_path(name: str) -> bool:
    """Recognise a test file at any depth, not a directory named test_*.

    Paths come from Git's repository-relative POSIX names on either host OS.
    """
    filename = name.rsplit("/", 1)[-1]
    return name.startswith("tests/unit/") and filename.startswith("test_") and filename.endswith(".py")


def _is_test_module_path(name: str) -> bool:
    filename = name.rsplit("/", 1)[-1]
    return (name.startswith("tests/")
            and filename.startswith("test_") and filename.endswith(".py"))


def _benchmark(name: str) -> bool:
    """This namespace contains isolated benchmark/test orchestration only."""
    return name.startswith("tools/document_understanding_benchmark/")


def _closure(seeds: set[str], reverse: dict[str, set[str]]) -> set[str]:
    affected, pending = set(seeds), list(seeds)
    while pending:
        for caller in reverse.get(pending.pop(), ()):
            if caller not in affected:
                affected.add(caller)
                pending.append(caller)
    return affected


def _module_owners(names: set[str], modules: dict[str, str]) -> set[str]:
    result = set()
    for target in names:
        while target:
            if target in modules:
                result.add(modules[target])
                break
            target = target.rpartition(".")[0]
    return result


def _test_calls(nodes: list[ast.AST]) -> list[ast.Call]:
    """Test bodies and reachable local helpers, excluding dormant definitions."""
    definitions: dict[str, list[ast.AST]] = {}
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.setdefault(node.name, []).append(node)
    pending = [node for name, functions in definitions.items() if name.startswith("test_") for node in functions]
    pending.extend(node for node in nodes[0].body if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    seen, calls = set(), []
    while pending:
        root = pending.pop()
        if id(root) in seen:
            continue
        seen.add(id(root))
        body = list(ast.iter_child_nodes(root)) if isinstance(root, (ast.FunctionDef, ast.AsyncFunctionDef)) else [root]
        while body:
            node = body.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(node, ast.Call):
                calls.append(node)
                name = _dotted_name(node.func) or ""
                if "." not in name or name.startswith(("self.", "cls.")):
                    pending.extend(definitions.get(name.rsplit(".", 1)[-1], ()))
            body.extend(ast.iter_child_nodes(node))
    return calls


def _called_imports(tree: ast.AST, module: str, package: bool, calls=None) -> set[str]:
    """Known imported call targets; a mere import cannot prove tool execution."""
    bindings = {}
    for node in _nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bindings[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module or ""
            if node.level:
                parent = module.split(".") if package else module.split(".")[:-1]
                prefix = ".".join([*parent[:len(parent) - node.level + 1], *([prefix] if prefix else [])])
            for alias in node.names:
                bindings[alias.asname or alias.name] = f"{prefix}.{alias.name}"
    names = set()
    for node in calls if calls is not None else _nodes(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
            name = _dotted_name(node.func) or ""
            head, _, tail = name.partition(".")
            if head in bindings:
                names.add(bindings[head] + ("." + tail if tail else ""))
    return names


def _literal_basenames(nodes: list[ast.AST]) -> set[str]:
    """Cheap benchmark-file prefilter; text alone never establishes ownership."""
    return {node.value.replace("\\", "/").rsplit("/", 1)[-1] for node in nodes
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and "\n" not in node.value and "\r" not in node.value}


def _file_path_names(nodes: list[ast.AST]) -> set[str]:
    """File access/declarations, not filename comparisons in unrelated policy."""
    parents = {child: node for node in nodes for child in ast.iter_child_nodes(node)}
    result = set()
    for node in nodes:
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if "\n" in node.value or "\r" in node.value:
            continue
        parent = parents.get(node)
        while parent is not None:
            if isinstance(parent, (ast.Compare, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                break
            if (isinstance(parent, (ast.Assign, ast.AnnAssign, ast.Call))
                    or isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div)):
                result.add(node.value.replace("\\", "/").rsplit("/", 1)[-1])
                break
            parent = parents.get(parent)
    return result


def select_unit_tests(root: Path, changes: set[str] | None) -> tuple[list[str], str]:
    """Select whole test files, never individual asserts, and explain fallbacks."""
    full = ["tests/unit"]
    if changes is None:
        return full, "unknown push range"
    # Plans retain diagnostic scripts and fixtures as evidence, not live code.
    # Filter by that directory responsibility before entrypoint/dependency rules.
    changes = {name for name in changes if not name.startswith(("docs/plans/", ".planning/"))}
    global_names = {
        "pyproject.toml", "pytest.ini", "conftest.py", "tests/conftest.py",
        "setup.cfg", "setup.py", "tox.ini", "uv.lock", "poetry.lock",
        "Pipfile", "Pipfile.lock", ".python-version", ".pre-commit-config.yaml",
    }
    global_prefixes = ("config/", ".github/", ".githooks/")
    if any(name in global_names or name.startswith((*global_prefixes, "requirements"))
           or name.endswith("/conftest.py") for name in changes):
        return full, "configuration or test entrypoint changed"
    if any(name.startswith("tools/") and not _benchmark(name) for name in changes):
        return full, "shared or unknown tooling changed"
    relevant = {name for name in changes if name.endswith(".py") or name.startswith(("src/", "scripts/", "tools/", "tests/"))}
    if not relevant:
        return [], "no behavior changes"
    resources = {name for name in relevant if not name.endswith(".py")}
    if resources:
        # A known literal reader cannot rule out a second dynamic-filename reader.
        # Do not claim a closed resource scope from textual names or comparisons.
        return full, "resource dependency scope unknown"
    python_changes = relevant - resources
    # An already-global production change needs no whole-repository graph.
    # This is the same dynamic rule below, evaluated before expensive discovery.
    preparsed = {}
    try:
        for name in python_changes:
            if name.startswith(("src/", "scripts/")) and (root / name).is_file():
                tree = ast.parse((root / name).read_text(encoding="utf-8-sig"))
                if _dynamic_execution(tree):
                    return full, "dynamic execution changed"
                preparsed[name] = tree
    except (OSError, SyntaxError, UnicodeError):
        return full, "dependency graph unavailable"
    paths = {p.relative_to(root).as_posix(): p for directory in ("src", "scripts", "tools", "tests")
             for p in (root / directory).rglob("*.py")}
    if not python_changes <= paths.keys() or any(not (root / name).is_file() for name in resources):
        return full, "deleted or unknown dependency"
    # An executable contract/integration/E2E module is itself a test consumer.
    # Test-only edits do not change runtime used by unrelated computed imports;
    # known helper consumers must still follow the same reverse import graph.
    test_modules_only = all(_is_test_module_path(name) for name in relevant)
    modules = {alias: name for name in paths for alias in _aliases(name)}
    benchmark_files: dict[str, set[str]] = {}
    for name in paths:
        if _benchmark(name):
            benchmark_files.setdefault(name.rsplit("/", 1)[-1], set()).add(name)
    reverse: dict[str, set[str]] = {}
    executions: dict[str, set[str]] = {}
    dynamic, executable_tests = set(), set()
    try:
        for name, path in paths.items():
            tree = preparsed.get(name)
            if tree is None:
                tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            nodes = list(ast.walk(tree))
            if _dynamic_execution(nodes):
                dynamic.add(name)
            if _is_test_module_path(name) and any(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
                for node in nodes
            ):
                executable_tests.add(name)
            imports = _imports(nodes, _aliases(name)[0], path.name == "__init__.py")
            for owner in _module_owners(imports, modules):
                reverse.setdefault(owner, set()).add(name)
            executing_calls = _test_calls(nodes) if _is_test_module_path(name) else None
            calls = _called_imports(nodes, _aliases(name)[0], path.name == "__init__.py", executing_calls)
            for owner in _module_owners(calls, modules):
                executions.setdefault(owner, set()).add(name)
            literal_basenames = _literal_basenames(nodes)
            # Isolated benchmark subprocesses also execute owned .py files by
            # path (launcher/sitecustomize), not Python import. These are possible
            # reverse dependencies only: filename text is never execution proof.
            file_names = _file_path_names(nodes) if literal_basenames & benchmark_files.keys() else set()
            for basename in file_names & benchmark_files.keys():
                for owner in benchmark_files[basename]:
                    reverse.setdefault(owner, set()).add(name)
    except (OSError, SyntaxError, UnicodeError):
        return full, "dependency graph unavailable"
    # Dynamic execution is exempt only for proven test-side benchmark tools.
    # A runtime caller, shared test entrypoint or import-only test cannot justify it.
    isolated_benchmarks = set()
    for name in paths:
        if not _benchmark(name):
            continue
        known = _closure({name}, reverse)
        if (all((_benchmark(item) or item.startswith("tests/"))
                and not item.endswith("/conftest.py") for item in known)
                and _closure({name}, executions) & executable_tests):
            isolated_benchmarks.add(name)
    if any(_benchmark(name) and name not in isolated_benchmarks for name in python_changes):
        return full, "benchmark execution or isolation unproven"
    if not test_modules_only and (dynamic & python_changes) - isolated_benchmarks:
        return full, "dynamic execution changed"
    known = _closure(relevant, reverse)
    # Each change needs its own consumer: another changed test cannot mask an
    # untested runtime or resource in a mixed push range.
    for name in relevant:
        consumers = _closure({name}, reverse)
        valid = _is_test_module_path if _benchmark(name) else _is_unit_test_path
        if _is_test_module_path(name):
            continue
        if not any(valid(item) for item in consumers):
            return full, "no known unit consumer"
    # Existing computed imports/CLI consumers cannot safely be ruled out by a
    # static graph. Keep their unit callers, even alongside known consumers.
    test_side_only = (
        all(_is_test_module_path(name) or _benchmark(name) for name in relevant)
        and all(name.startswith("tests/") or _benchmark(name) for name in known)
    )
    uncertain = set() if test_modules_only or test_side_only else dynamic - isolated_benchmarks
    affected = _closure(relevant | uncertain, reverse)
    expanded_seeds = {name for name in relevant if _benchmark(name) or _is_test_module_path(name)}
    expanded = _closure(expanded_seeds, reverse)
    tests = sorted(name for name in affected if _is_unit_test_path(name)
                   or (name in expanded and _is_test_module_path(name)))
    includes_nonunit_change = any(not _is_unit_test_path(name) for name in relevant)
    return tests, "affected test modules" if test_modules_only and includes_nonunit_change else "affected unit tests"
