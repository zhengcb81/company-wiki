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


class _ScopeVisitor(ast.NodeVisitor):
    """Maps every call node to its QUALIFIED scope: `Class.method`, not just the class.

    The first version mapped a call to its OUTERMOST container, so every method of
    `SourceCatalog` collapsed into the one key `service.py::SourceCatalog` - which the
    review exploited: adding a NEW method that reads the column still resolved to the
    baselined class key and passed (B-VR-B10-03).  Qualified keys give every method its own
    identity, so a new method is a new key and the ratchet sees it.
    """

    def __init__(self) -> None:
        self._stack: list[str] = []
        self.scopes: dict[int, str] = {}

    def _enter(self, node: ast.AST) -> None:
        self._stack.append(getattr(node, "name", "?"))
        self.generic_visit(node)
        self._stack.pop()

    visit_FunctionDef = _enter
    visit_AsyncFunctionDef = _enter
    visit_ClassDef = _enter

    def visit_Call(self, node: ast.Call) -> None:
        if self._stack:
            self.scopes[id(node)] = ".".join(self._stack)
        self.generic_visit(node)


def _names_exact_column(node: ast.AST) -> bool:
    """True only when the expression references the column EXACTLY.

    A substring match made the gate red for OTHER tables' columns: the review built
    `json.loads(row["acquisition_metadata_json"])` and the gate demanded convergence onto the
    documents column (B-VR-B10-05).  Only an exact `metadata_json` constant counts.
    """
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and sub.value == COLUMN:
            return True
    return False


def _scan_confirmed_direct_readers() -> set[str]:
    """`relative/path.py::Class.method` for every `json.loads(...)` that names the column.

    RECURSIVE on purpose (`source_catalog/adapters/` holds 8 modules of its own), and the
    scope is the qualified `Class.method` so a new method cannot hide behind its class.
    """
    found: set[str] = set()
    for path in sorted(SOURCE.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        visitor = _ScopeVisitor()
        visitor.visit(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name != "loads":
                continue
            if not any(_names_exact_column(argument) for argument in node.args):
                continue
            relative = path.relative_to(SOURCE).as_posix()
            found.add(f"{relative}::{visitor.scopes.get(id(node), '<module>')}")
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


def _reads_column_as_value(node: ast.AST) -> bool:
    """True when the expression reads the column as a VALUE (not a SQL string literal)."""
    for sub in ast.walk(node):
        if (isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.Constant)
                and sub.slice.value == COLUMN):
            return True
        if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "get" and sub.args
                and isinstance(sub.args[0], ast.Constant) and sub.args[0].value == COLUMN):
            return True
    return False


def _scan_column_value_handoffs() -> set[str]:
    """`relative/path.py::Class.method` for every call that RECEIVES the column's value.

    The `json.loads` scan can be walked around: a generic helper called as
    `_parse(row["metadata_json"])` names the column at the call site (whose callee is not
    `loads`) and passes a parameter (which is not the column) to `json.loads`.  I measured
    that in a temp copy - the whole gate passed - and then found the same shape in three
    production sites, so the first ratchet is a ratchet over the COMMON shape, not a
    completeness proof.  This scan closes the indirection and keeps the SQL text that merely
    mentions the column name out of the count.
    """
    found: set[str] = set()
    for path in sorted(SOURCE.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        visitor = _ScopeVisitor()
        visitor.visit(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not any(_reads_column_as_value(argument) for argument in node.args):
                continue
            relative = path.relative_to(SOURCE).as_posix()
            found.add(f"{relative}::{visitor.scopes.get(id(node), '<module>')}")
    return found


def test_b10_handoff_scan_is_not_vacuous() -> None:
    handoffs = _scan_column_value_handoffs()
    assert handoffs, "the handoff scan found nothing - it would prove nothing"
    assert handoffs & set(read_chain.COLUMN_VALUE_HANDOFFS), (
        "no scanned handoff matches the baseline: this ratchet is not measuring anything"
    )


def test_b10_no_new_column_value_handoff() -> None:
    handoffs = _scan_column_value_handoffs()
    baseline = set(read_chain.COLUMN_VALUE_HANDOFFS)
    new = sorted(handoffs - baseline)
    assert not new, (
        "new places hand the shared column's value into a call: " + ", ".join(new) +
        " - if that call parses the column, converge it onto store.metadata_object; if it "
        "does not, register it in read_chain.COLUMN_VALUE_HANDOFFS with the reason "
        "(the ratchet may only shrink)"
    )


def test_b10_handoff_baseline_has_no_stale_entry() -> None:
    handoffs = _scan_column_value_handoffs()
    stale = sorted(set(read_chain.COLUMN_VALUE_HANDOFFS) - handoffs)
    assert not stale, (
        "the handoff baseline still lists sites that no longer pass the column: " +
        ", ".join(stale) + " - remove them so the ratchet keeps meaning something"
    )


def test_b10_gate_boundaries_stay_documented() -> None:
    """The gate's measured limits must stay written down next to the gate.

    A gate whose reach is not documented gets trusted beyond it.  Each of these shapes was
    PROBED against the gate; deleting one from the record would silently turn a known limit
    into an assumed guarantee, so the ids are pinned.
    """
    assert read_chain.GATE_BOUNDARIES, "the measured gate boundaries were removed"
    assert set(read_chain.GATE_BOUNDARIES) == {
        "intermediate_variable",
        "subscript_inside_the_callee",
        "third_party_or_alternative_parser",
        "closed_helper_at_call_site",
    }, "the documented boundary set changed without updating this test"
    assert "PROBED" in read_chain.GATE_BOUNDARIES["intermediate_variable"], (
        "each boundary must say whether it was actually probed"
    )


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
    baseline = read_chain.CONFIRMED_DIRECT_READERS
    stale = sorted(
        key for key, annotation in baseline.items()
        if annotation.get("visible_to_scan") != "False" and key not in confirmed
    )
    assert not stale, (
        "the baseline still lists sites that no longer parse the column: " + ", ".join(stale) +
        " - remove them so the ratchet keeps meaning something"
    )
    # Blind spots are invisible to the scan BY CONSTRUCTION (renamed parameter), so they are
    # exempt from the staleness check - but their code must still exist, or the entry lies.
    for key, annotation in baseline.items():
        if annotation.get("visible_to_scan") != "False":
            continue
        module_file = SOURCE / key.split("::")[0]
        symbol = key.split("::")[1].rsplit(".", 1)[-1]
        assert f"def {symbol}" in module_file.read_text(encoding="utf-8"), (
            f"the blind spot {key} no longer exists - remove it from the baseline"
        )


def test_b10_baseline_declares_which_table_each_reader_reads() -> None:
    """B-VR-B10-02: the flat list mixed the documents column with the artifacts column.

    Both tables have a column named `metadata_json`, so every confirmed reader must say
    WHICH table it reads - otherwise the B10-3 convergence list is scoped to the wrong
    rows.
    """
    allowed = {"documents", "artifacts", "documents+artifacts"}
    assert read_chain.CONFIRMED_DIRECT_READERS, "the baseline is empty"
    for key, annotation in read_chain.CONFIRMED_DIRECT_READERS.items():
        assert annotation.get("table") in allowed, (
            f"{key} does not declare which table its column belongs to"
        )
        assert annotation.get("note"), f"{key} has no note explaining the classification"
        assert annotation.get("visible_to_scan") in (None, "True", "False"), (
            f"{key}.visible_to_scan must be 'True' or 'False' (as a string, like the rest "
            "of the registry)"
        )


def test_b10_explicit_non_chain_readers_are_declared_and_real() -> None:
    """A reader that deliberately RAISES on malformed content must stay declared.

    section_query's contract is a named error, not a silent {} - so it is NOT converged,
    and that decision is registered (the B10 rule: no permanent silent double-run).  The
    declaration must point at code that exists, and the site must still be a direct reader
    (otherwise the declaration describes something that is gone).
    """
    assert read_chain.EXPLICIT_NON_CHAIN_READERS, "nothing is declared as non-chain"
    for key, reason in read_chain.EXPLICIT_NON_CHAIN_READERS.items():
        assert reason.strip(), f"{key} has an empty reason"
        module_rel, _, symbol = key.split("::")[0], "::", key.split("::")[1]
        module_file = SOURCE / module_rel
        assert module_file.is_file(), f"{key}: {module_rel} does not exist"
        source = module_file.read_text(encoding="utf-8")
        short = symbol.rsplit(".", 1)[-1]
        assert short in source, f"{key}: symbol {short} not found in {module_rel}"
        assert key in read_chain.CONFIRMED_DIRECT_READERS, (
            f"{key} is declared non-chain but no longer appears among the direct readers"
        )
    assert "section_query.py::SectionQueryService.list_sections" in (
        read_chain.EXPLICIT_NON_CHAIN_READERS
    ), "the known deliberate-raise reader must stay declared"


def test_b10_registered_adapters_are_complete_and_importable() -> None:
    required = {"version", "semantics", "byte_level", "reads_files", "removal_condition"}
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
    """The function BODY must not open files.  Transitive access is NOT covered here.

    B-VR-B10-01 (P1) is exactly that gap: `reader.bundle`'s body only calls
    build_source_bundle, yet the bundle path hashes artifact files through
    artifact_handle.validate_artifact.  So this test is a SYNTACTIC check on the body, and
    the registry must carry the transitive truth separately - which the next test pins.
    """
    forbidden = {"open", "read_bytes", "read_text", "read_verified_bytes", "_read_verified_bytes"}
    nodes = _function_nodes(SOURCE / "reader.py", symbol)
    for node in nodes:
        used = {
            (child.func.attr if isinstance(child.func, ast.Attribute)
             else getattr(child.func, "id", ""))
            for child in ast.walk(node) if isinstance(child, ast.Call)
        }
        assert not (used & forbidden), (
            f"reader.{symbol} is registered as CLAIM-level but its body now uses "
            f"{sorted(used & forbidden)}: re-pointing it at the byte chain changes its failure "
            "semantics, which B10 explicitly refuses to do silently"
        )


def test_b10_registry_states_transitive_file_access_truthfully() -> None:
    """`bundle` reads artifact files through the bundle path - the registry must say so.

    The reviewer refuted the earlier 'never opens a file' claim by corrupting an artifact and
    watching the verdict flip.  Pinning `reads_files` means the corrected fact cannot quietly
    revert, and the two entries that really are file-free stay pinned as such.
    """
    adapters = read_chain.LEGACY_READ_ADAPTERS
    bundle = adapters["company_wiki.source_catalog.reader.ReadOnlyCatalogReader.bundle"]
    assert bundle["reads_files"] is True, (
        "bundle reaches artifact_handle.validate_artifact, which hashes artifact files: "
        "reads_files must stay True (B-VR-B10-01)"
    )
    for dotted in ("company_wiki.source_catalog.reader.ReadOnlyCatalogReader.resolve_handle",
                   "company_wiki.source_catalog.service._read_shared_metadata"):
        assert adapters[dotted]["reads_files"] is False, f"{dotted} is file-free"
        assert adapters[dotted]["byte_level"] is False, f"{dotted} is not the byte chain"
