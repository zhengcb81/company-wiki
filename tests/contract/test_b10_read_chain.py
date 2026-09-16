"""B10 contract: the read chain stays single, and the old entry points stay EXPLICIT.

Requirement (R4 execution plan section B, B10): converge to a single read chain in a small
scope, old entry points only as explicit version adapters, and "no permanent silent
double-run".  Acceptance: switch only after an independent review, and if the two cannot be
made compatible the switch STOPS.

These tests enforce the parts that are machine-checkable:

* the single chain is what the registered v1 adapter actually calls (no second parse);
* no NEW place parses the shared column directly (ratchet, may only shrink);
* the baseline holds no stale entry (a site that disappeared must be removed, so the
  ratchet cannot rot into a rubber stamp);
* every registered adapter declares its version, its semantics, whether it is byte-level,
  and the condition under which it may be removed, and the symbol really exists;
* the claim-level adapters still do NOT read bytes - they must not be quietly re-pointed at
  the byte-level chain, because that would change their failure semantics.

The AST scan is repeated here on purpose: a contract test may not depend on the evidence
tooling under assurance/, which is not part of the product.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from company_wiki.source_catalog import read_chain

SOURCE = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"
COLUMN = "metadata_json"


def _enclosing_symbols(tree: ast.AST) -> dict[int, ast.AST]:
    owner: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for child in ast.walk(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                owner.setdefault(id(child), node)
    return owner


def _scan_confirmed_direct_readers() -> set[str]:
    """`relative/path.py::symbol` for every `json.loads(...)` whose ARGUMENT names the column.

    RECURSIVE on purpose: `source_catalog/adapters/` holds 8 modules of its own, and the
    first version of this scan used ``glob("*.py")``, so a direct reader added there would
    have passed the gate unnoticed.  The key keeps the relative path so two files with the
    same basename cannot collide.
    """
    found: set[str] = set()
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        owner = _enclosing_symbols(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name != "loads":
                continue
            argument = " ".join(ast.unparse(item) for item in node.args)
            if COLUMN not in argument:
                continue
            symbol = owner.get(id(node))
            relative = path.relative_to(SOURCE).as_posix()
            found.add(f"{relative}::{getattr(symbol, 'name', '<module>')}")
    return found


def _function_nodes(path: Path, symbol: str) -> list[ast.AST]:
    """EVERY definition of `symbol`, not the first one.

    Measured by the mutation harness: `reader.py` defines `resolve_handle` twice - a
    Protocol stub near the top and the real implementation further down - so a
    first-definition-wins lookup inspected the stub, and the mutant that made the REAL
    implementation read bytes survived.  That is the same class of defect the FC-1301
    review found in the reason-taxonomy gate, so all definitions are considered and an
    empty result is itself a failure.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [node for node in ast.walk(tree)
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol]
    assert nodes, f"{path.name} has no function {symbol}"
    return nodes


def test_b10_scan_is_not_vacuous() -> None:
    confirmed = _scan_confirmed_direct_readers()
    assert confirmed, "the AST scan found nothing - the test would prove nothing"
    assert "store.py::metadata_object" not in confirmed, (
        "the single chain parses the column through a helper, not a literal json.loads "
        "argument - if this fires, the scan and the chain have both changed"
    )
    assert confirmed & set(read_chain.CONFIRMED_DIRECT_READERS), (
        "no scanned site matches the baseline: the ratchet is no longer measuring anything"
    )


def test_b10_v1_adapter_delegates_to_the_single_chain() -> None:
    nodes = _function_nodes(SOURCE / "service.py", "_read_shared_metadata")
    for node in nodes:
        calls = [
            (child.func.attr if isinstance(child.func, ast.Attribute)
             else getattr(child.func, "id", ""))
            for child in ast.walk(node) if isinstance(child, ast.Call)
        ]
        assert "metadata_object" in calls, (
            "service._read_shared_metadata must delegate to store.metadata_object (the single "
            f"chain); it calls {calls}"
        )
        assert "loads" not in calls, (
            "a second parse came back into the v1 adapter - that is exactly the double "
            "implementation B10 converged away"
        )
    assert "company_wiki.source_catalog.service._read_shared_metadata" in (
        read_chain.LEGACY_READ_ADAPTERS
    ), "the adapter name must stay registered while callers still use it"


def test_b10_no_new_confirmed_direct_reader() -> None:
    confirmed = _scan_confirmed_direct_readers()
    baseline = set(read_chain.CONFIRMED_DIRECT_READERS)
    new = sorted(confirmed - baseline)
    assert not new, (
        "new direct readers of the shared column: " + ", ".join(new) +
        " - converge them onto store.metadata_object, or register and justify them in "
        "read_chain.CONFIRMED_DIRECT_READERS (the ratchet may only shrink)"
    )


def test_b10_baseline_has_no_stale_entry() -> None:
    confirmed = _scan_confirmed_direct_readers()
    stale = sorted(set(read_chain.CONFIRMED_DIRECT_READERS) - confirmed)
    assert not stale, (
        "the baseline still lists sites that no longer parse the column: " + ", ".join(stale) +
        " - remove them so the ratchet keeps meaning something"
    )


def test_b10_registered_adapters_are_complete_and_importable() -> None:
    required = {"version", "semantics", "byte_level", "removal_condition"}
    assert read_chain.LEGACY_READ_ADAPTERS, "the registry is empty - nothing is declared"
    for dotted, entry in read_chain.LEGACY_READ_ADAPTERS.items():
        missing = required - set(entry)
        assert not missing, f"{dotted} is missing {sorted(missing)}"
        assert isinstance(entry["byte_level"], bool), f"{dotted}.byte_level must be a bool"
        # The key names module + optional class + symbol, so resolve the LONGEST importable
        # prefix instead of splitting at the last dot: `...reader.ReadOnlyCatalogReader.
        # resolve_handle` is not a module path (measured - the first version of this test
        # tried exactly that and failed with ModuleNotFoundError).
        parts = dotted.split(".")
        module = None
        remainder: list[str] = []
        for split in range(len(parts), 0, -1):
            try:
                module = importlib.import_module(".".join(parts[:split]))
            except ModuleNotFoundError:
                continue
            remainder = parts[split:]
            break
        assert module is not None, f"{dotted} does not resolve to an importable module"
        target: object = module
        for part in remainder:
            target = getattr(target, part)
        assert target is not None, f"{dotted} does not resolve"
    assert read_chain.SINGLE_READ_CHAIN.rpartition(".")[2] in dir(
        importlib.import_module("company_wiki.source_catalog.store")
    ), "SINGLE_READ_CHAIN does not name a real function"


@pytest.mark.parametrize("symbol", ["resolve_handle", "bundle"])
def test_b10_claim_level_adapters_never_read_bytes(symbol: str) -> None:
    forbidden = {"open", "read_bytes", "read_text", "read_verified_bytes", "_read_verified_bytes"}
    nodes = _function_nodes(SOURCE / "reader.py", symbol)
    for node in nodes:
        used = {
            (child.func.attr if isinstance(child.func, ast.Attribute)
             else getattr(child.func, "id", ""))
            for child in ast.walk(node) if isinstance(child, ast.Call)
        }
        assert not (used & forbidden), (
            f"reader.{symbol} is registered as CLAIM-level but now uses "
            f"{sorted(used & forbidden)}: re-pointing it at the byte chain changes its failure "
            "semantics, which B10 explicitly refuses to do silently"
        )
