"""Conservative, cache-free unit selection for the complete Git push range.

Static imports are an optimization, not a replacement for CI's full unit suite.
Uncertain ranges, configuration, test entrypoints and dynamic execution use it all.
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


def _imports(tree: ast.AST, module: str, package: bool) -> set[str]:
    names = set()
    for node in ast.walk(tree):
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
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update({alias.asname or alias.name: alias.name for alias in node.names})
        elif isinstance(node, ast.ImportFrom) and node.module:
            aliases.update({alias.asname or alias.name: f"{node.module}.{alias.name}" for alias in node.names})
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
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


def select_unit_tests(root: Path, changes: set[str] | None) -> tuple[list[str], str]:
    """Select whole test files, never individual asserts, and explain fallbacks."""
    full = ["tests/unit"]
    if changes is None:
        return full, "unknown push range"
    global_names = {"pyproject.toml", "pytest.ini", "conftest.py", "tests/conftest.py"}
    global_prefixes = ("config/", ".github/", ".githooks/", "tools/", "tests/fixtures/")
    if any(name in global_names or name.startswith((*global_prefixes, "requirements"))
           or name.endswith("/conftest.py") for name in changes):
        return full, "configuration or test entrypoint changed"
    relevant = {name for name in changes if name.endswith(".py") or name.startswith(("src/", "scripts/", "tests/"))}
    if not relevant:
        return [], "no behavior changes"
    paths = {p.relative_to(root).as_posix(): p for directory in ("src", "scripts", "tools", "tests")
             for p in (root / directory).rglob("*.py")}
    if not relevant <= paths.keys():
        return full, "deleted or unknown dependency"
    modules = {alias: name for name in paths for alias in _aliases(name)}
    reverse: dict[str, set[str]] = {}
    uncertain = set()
    try:
        for name, path in paths.items():
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            if _dynamic_execution(tree):
                if name in relevant:
                    return full, "dynamic execution changed"
                uncertain.add(name)
            imports = _imports(tree, _aliases(name)[0], path.name == "__init__.py")
            for target in imports:
                while target:
                    if target in modules:
                        reverse.setdefault(modules[target], set()).add(name)
                        break
                    target = target.rpartition(".")[0]
    except (OSError, SyntaxError, UnicodeError):
        return full, "dependency graph unavailable"
    # Existing computed imports/CLI consumers cannot safely be ruled out by a
    # static graph. Keep their unit callers, even alongside known consumers.
    affected = relevant | uncertain
    pending = list(affected)
    while pending:
        for caller in reverse.get(pending.pop(), ()):
            if caller not in affected:
                affected.add(caller)
                pending.append(caller)
    # Check for a known consumer of the actual change separately: uncertainty
    # seeds must never make a brand-new untested source silently appear covered.
    known, pending = set(relevant), list(relevant)
    while pending:
        for caller in reverse.get(pending.pop(), ()):
            if caller not in known:
                known.add(caller)
                pending.append(caller)
    if not any(name.startswith("tests/unit/test_") for name in known):
        return full, "no known unit consumer"
    tests = sorted(name for name in affected if name.startswith("tests/unit/test_"))
    return tests, "affected unit tests"
