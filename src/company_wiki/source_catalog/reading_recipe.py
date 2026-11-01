"""Source-reading algorithm recipe, independent of task/store implementation.

The source composition owner declares entry points and carrier boundaries.
Imports inside those algorithm boundaries form the dependency closure, so a
new helper cannot silently disappear from cache identity. The closure reads
only algorithm code and the grammar owner's packaged linguistic identity,
never document trees, tests or model-service configuration.
Catalog policy data remains source-scoped in narrative_decision_inventory.
"""
from __future__ import annotations

import ast
from collections.abc import Callable, Iterable
from functools import lru_cache
from hashlib import sha256
from importlib.util import resolve_name
from pathlib import Path
import sys


_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_READING_ENTRY_POINTS = (
    "company_wiki.source_catalog.narrative_reading",
    "company_wiki.document_understanding.pipeline",
    "company_wiki.document_understanding.summary_input",
)
_PDF_ENTRY_POINTS = (
    "company_wiki.source_catalog.narrative_pdf_layout",
    "company_wiki.source_catalog.narrative_pdf_intent",
    "company_wiki.source_catalog.narrative_evidence",
)
_PDF_ALGORITHMS = (
    "company_wiki.source_catalog.narrative_pdf",
    "company_wiki.source_catalog.narrative_native_ranges",
    "company_wiki.document_understanding.geometry_intent",
    "company_wiki.document_understanding.profiles.geometry_policy",
    "company_wiki.document_normalization.layout_snapshots",
    "company_wiki.document_normalization.pdf_table_observations",
)


def _module_path(name: str) -> Path | None:
    module = sys.modules.get(name)
    source = getattr(module, "__file__", None)
    if source is not None:
        return Path(source)
    if not name.startswith("company_wiki."):
        return None
    path = _PACKAGE_ROOT.joinpath(*name.split(".")[1:])
    candidate = path.with_suffix(".py")
    if candidate.is_file():
        return candidate
    candidate = path / "__init__.py"
    return candidate if candidate.is_file() else None


@lru_cache(maxsize=256)
def _imports(name: str, is_package: bool, source: bytes) -> tuple[str, ...]:
    # Cache parsing by the *actual bytes*, never mtime: rule-only changes and
    # same-size replacements must still invalidate the algorithm identity.
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
    locate: Callable[[str], Path | None] = _module_path,
    includes: Callable[[str], bool],
) -> dict[str, str]:
    """Hash each reachable owned algorithm once, following literal imports.

    Member imports are considered only when they name a real source module.
    No child modules are imported or executed to discover their dependencies.
    A missing declared entry is an error rather than a complete empty recipe.
    """
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
        contents = path.read_bytes().replace(b"\r\n", b"\n")
        hashes[name] = sha256(contents).hexdigest()
        pending.extend(_imports(name, path.name == "__init__.py", contents))
    return hashes


def business_algorithm_hashes(*, pdf_frontend: bool) -> dict[str, str]:
    """Describe the current shared reading algorithm, not historical parsers."""
    def includes(name: str) -> bool:
        if not pdf_frontend and name.startswith(_PDF_ALGORITHMS):
            return False
        if name.startswith(("company_wiki.document_understanding.decision_",
                            "company_wiki.source_catalog.narrative_decision_inventory")):
            return False
        return ((pdf_frontend and name.startswith(_PDF_ALGORITHMS))
                or name.startswith(("company_wiki.document_understanding.",
                                 "company_wiki.source_catalog.narrative_"))
                or name in {
                    "company_wiki.source_catalog.reading_recipe",
                    "company_wiki.source_catalog.n6_candidate_operating_facts",
                    "company_wiki.document_normalization.text_matching",
                    "company_wiki.document_normalization.form_fields",
                    "company_wiki.document_normalization.table_shapes",
                    "company_wiki.source_contract.selection_annotations",
                })

    frontends = _PDF_ENTRY_POINTS if pdf_frontend else ()
    hashes = algorithm_hashes((*_READING_ENTRY_POINTS, *frontends, __name__), includes=includes)
    from company_wiki.document_understanding.statement_grammar import resource_identity
    hashes["statement_grammar_resources"] = resource_identity()
    return hashes
