"""Small syntax-based dependency checks for source-system boundaries.

These checks inspect imports and executable root conditionals. They do not
certify generated content, source truth, or runtime dependency resolution;
those belong to behavior tests at their public ports.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator

_PROHIBITED_IMPORTS = frozenset(
    {
        "auto_synthesis",
        "batch_assessment",
        "contradiction_detector",
        "evolve_questions",
        "ingest_v2",
        "ingested_db",
        "writer_policy",
    }
)

def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _name(node.value) + "." + node.attr
    return ""


def import_names(tree: ast.AST) -> Iterator[tuple[str, int]]:
    """Actual imports, including aliases and constant dynamic imports.

    Strings/docstrings/comments are data. Non-constant plugin loading is not
    statically decidable and must be tested at its explicit runtime port.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = item.name
                yield item.name, node.lineno
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                name = "." * node.level + (node.module or "") + "." + item.name
                aliases[item.asname or item.name] = name.lstrip(".")
                yield name, node.lineno
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        target = _name(node.func)
        first, *rest = target.split(".")
        target = ".".join((aliases.get(first, first), *rest))
        if target in {"__import__", "importlib.import_module"}:
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                yield argument.value, node.lineno


def source_catalog_does_not_import_prohibited_modules(
    src_dir: Path | None = None,
) -> tuple[bool, list[str]]:
    """Check source boundaries from syntax, including package initializers."""
    src_dir = src_dir or Path(__file__).resolve().parent
    violations: list[str] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name.startswith("test_"):
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8-sig"))
        for name, line in import_names(tree):
            prohibited = set(name.strip(".").split(".")) & _PROHIBITED_IMPORTS
            violations.extend(f"{py_file.relative_to(src_dir)}:{line}:{module}" for module in sorted(prohibited))
    return not violations, violations


_FLAG_NAMES = (
    "v2_scan_shadow",
    "v2_persist_assertions",
    "v2_resolve_shadow",
    "v2_resolve_active",
    "v2_bundle_active",
    "legacy_bridge_enabled",
)

# Modules allowed to know the flag names / hold flag state: the frozen flag
# machine (flags.py), the persistent snapshot (runtime_policy.py), and the
# gate itself (which scans for the names). Any other production module
# hardcoding the six-flag dict is a second policy source and violates
# FC-201/FC-205.
_POLICY_OWNERS = frozenset({"flags.py", "runtime_policy.py", "architecture_gate.py"})

# Legacy metadata containers may only be read inside the resolver's gated
# bridge (_source_metadata).  Any other production read is a bypass of the
# snapshot's legacy_bridge_enabled decision.
_LEGACY_KEYS = ("acquisition", "dayu_meta")


# Historical root names must remain in layout/policy owners; ordinary text
# containing them is not an architectural violation.
_ROOT_HARDCODE_TOKENS = (
    "dropbox_stock",
    "company_raw",
    "dayu_portfolio",
    "Dropbox",
)
# Exact source-relative paths: only these owners interpret physical layouts
# or retain a documented historical import format. No basename-wide exemption.
_ROOT_HARDCODE_ALLOWED_FILES = frozenset({
    "adapters/registry.py", "policy_2x.py", "policy_3x.py", "config.py",
    "adapter_dispatch.py", "adapters/company_raw.py", "adapters/dayu.py",
    "adapters/sidecar.py", "scanner.py", "models.py", "canonical_writer.py",
    "portfolio_promoter.py", "admission.py", "focus_cleanup.py", "architecture_gate.py",
    "backfill_v2.py", "cli.py",
})


def no_root_specific_hardcode(src_dir: Path | None = None) -> tuple[bool, list[str]]:
    """Find old root tokens in executable string literals, never documentation.

    Exceptions are exact source-relative owner paths, not a basename wildcard
    that silently exempts a different package's config.py. Checking every
    executable literal catches assignments and dispatch tables as well as
    conditionals, so moving a root special case out of an ``if`` cannot bypass
    the architecture check.
    """
    src_dir = src_dir or Path(__file__).resolve().parent
    owner_paths = _ROOT_HARDCODE_ALLOWED_FILES
    violations: list[str] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name.startswith("test_") or py_file.relative_to(src_dir).as_posix() in owner_paths:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8-sig"))
        docstrings: set[ast.Constant] = set()
        for scope in ast.walk(tree):
            if not isinstance(
                scope, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ) or not scope.body:
                continue
            first = scope.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(first.value)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and node not in docstrings
                and node.value in _ROOT_HARDCODE_TOKENS
            ):
                violations.append(
                    f"{py_file.relative_to(src_dir)}:{node.lineno}: hardcodes {node.value!r}"
                )
    return not violations, violations


def no_hardcoded_flag_dicts(
    src_dir: Path | None = None,
) -> tuple[bool, list[str]]:
    """FC-205: no production module outside flags.py / runtime_policy.py may
    hardcode the six-flag dict (second policy source, FC-201 deletion
    deadline).  Occurrences inside the policy owners and test files are
    allowed."""
    if src_dir is None:
        src_dir = Path(__file__).resolve().parent
    violations: list[str] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name.startswith("test_") or py_file.name.startswith("__"):
            continue
        if py_file.name in _POLICY_OWNERS:
            continue
        text = py_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith('"v2_') or line.strip().startswith("'v2_"):
                neighbors = " ".join(lines[max(0, i - 1) : i + 2])
                hits = sum(1 for flag in _FLAG_NAMES if flag in neighbors)
                if hits >= 2:
                    violations.append(f"{py_file.name}:{i + 1}:hardcoded flag dict")
    return len(violations) == 0, violations


# The legacy-bridge read pattern is a loop over the two container keys and a
# .get(key) from a metadata dict.  Container WRITERS (acquisition_service
# builds the dict, scanner/normalizer store it) and constant definitions
# (visibility_bridge LEGACY_PROFILE_KEYS) are not bridge reads — only the
# loop-with-get pattern is the resolver-only seam.
#
# Built from parts so this module does not contain the literal pattern
# string: the leg04 freeze gate asserts the pattern exists in exactly ONE
# source file (resolver.py), and this gate module must not trip it.
_BRIDGE_LOOP_PATTERN = "for key in " + '("acquisition", "dayu_meta")'


def no_legacy_container_reads_outside_resolver(
    src_dir: Path | None = None,
) -> tuple[bool, list[str]]:
    """FC-205: the legacy-container bridge-read loop may only exist inside
    the resolver's gated _source_metadata.  Any other module with the same
    read pattern is a legacy-bridge bypass of the snapshot's
    legacy_bridge_enabled decision."""
    if src_dir is None:
        src_dir = Path(__file__).resolve().parent
    violations: list[str] = []
    resolver_path = src_dir / "resolver.py"
    resolver_text = resolver_path.read_text(encoding="utf-8")
    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name.startswith("test_") or py_file.name.startswith("__"):
            continue
        if py_file == resolver_path:
            continue
        if py_file == Path(__file__).resolve():
            continue  # the gate itself carries the pattern constant
        text = py_file.read_text(encoding="utf-8")
        if _BRIDGE_LOOP_PATTERN in text:
            violations.append(
                f"{py_file.name}: legacy bridge-read loop outside resolver"
            )
    if _BRIDGE_LOOP_PATTERN not in resolver_text:
        violations.append("resolver.py bridge loop missing (gate weakened)")
    return len(violations) == 0, violations


__all__ = [
    "no_hardcoded_flag_dicts",
    "no_legacy_container_reads_outside_resolver",
    "no_root_specific_hardcode",
    "source_catalog_does_not_import_prohibited_modules",
]
