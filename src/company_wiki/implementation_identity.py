"""Hash the installed implementation declared by an algorithm's owner."""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterable
from functools import lru_cache
from hashlib import sha256
from importlib.util import resolve_name
from pathlib import Path
import sys


def _code_bytes(path: str | Path, *, universal_newlines: bool = False) -> bytes:
    contents = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return contents.replace(b"\r", b"\n") if universal_newlines else contents


def code_sha256(path: str | Path | None, *, universal_newlines: bool = False) -> str:
    if path is None:
        raise ValueError("algorithm has no installed source file")
    return sha256(_code_bytes(path, universal_newlines=universal_newlines)).hexdigest()


@lru_cache(maxsize=256)
def _imports(name: str, is_package: bool, source: bytes) -> tuple[str, ...]:
    # Cache only the parse, keyed by bytes. A same-size rules change still
    # invalidates the fingerprint, even with an unchanged mtime.
    package = name if is_package else name.rpartition(".")[0]
    imports: list[str] = []
    for node in ast.walk(ast.parse(source, filename=name)):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = (resolve_name("." * node.level + (node.module or ""), package)
                    if node.level else node.module or "")
            if base:
                imports.append(base)
                imports.extend(base + "." + alias.name for alias in node.names
                               if alias.name != "*")
        elif (isinstance(node, ast.Call) and node.args
              and isinstance(node.args[0], ast.Constant)
              and isinstance(node.args[0].value, str)
              and ((isinstance(node.func, ast.Name)
                    and node.func.id in {"import_module", "__import__"})
                   or (isinstance(node.func, ast.Attribute)
                       and node.func.attr == "import_module"))):
            imports.append(node.args[0].value)
    return tuple(imports)


def algorithm_hashes(
    entry_points: Iterable[str], *,
    locate: Callable[[str], Path | None],
    includes: Callable[[str], bool],
) -> dict[str, str]:
    """Hash reachable algorithm files without importing discovered modules."""
    roots = set(entry_points)
    pending = list(roots)
    seen: set[str] = set()
    hashes: dict[str, str] = {}
    while pending:
        name = pending.pop()
        if name in seen or not includes(name):
            continue
        seen.add(name)
        path = locate(name)
        if path is None or not path.is_file():
            if name in roots:
                raise RuntimeError(f"reading algorithm {name} has no source file")
            continue
        contents = _code_bytes(path)
        hashes[name] = sha256(contents).hexdigest()
        pending.extend(_imports(name, path.name == "__init__.py", contents))
    return hashes


def _loaded_source_path(name: str) -> Path | None:
    filename = getattr(sys.modules.get(name), "__file__", None)
    return Path(filename) if isinstance(filename, str) and filename else None


def owned_algorithm_hashes(
    package: str, root: Path, entry_points: Iterable[str], *,
    includes: Callable[[str], bool],
) -> dict[str, str]:
    """Resolve imports within one owner's namespace, honoring loaded code."""
    def locate(name: str) -> Path | None:
        loaded = _loaded_source_path(name)
        if loaded is not None:
            return loaded
        if name == package:
            return root / "__init__.py"
        path = root.joinpath(*name[len(package) + 1:].split("."))
        source = path.with_suffix(".py")
        return source if source.is_file() else path / "__init__.py"

    return algorithm_hashes(
        entry_points,
        locate=locate,
        includes=lambda name: (name == package or name.startswith(package + ".")) and includes(name),
    )


def owned_tree_hashes(package: str, roots: Iterable[Path]) -> dict[str, str]:
    """Describe a package tree without loading its unimported modules."""
    hashes: dict[str, str] = {}
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            parts = path.relative_to(root).with_suffix("").parts
            if parts[-1] == "__init__":
                parts = parts[:-1]
            name = ".".join((package, *parts))
            if name not in hashes:
                hashes[name] = code_sha256(_loaded_source_path(name) or path)
    return hashes


__all__ = ["algorithm_hashes", "code_sha256", "owned_algorithm_hashes", "owned_tree_hashes"]
