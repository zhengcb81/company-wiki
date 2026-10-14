"""B-node: engineering invariants for the decision-dependency component.

These are not a second copy of the mutation matrix. They attack the properties that make
the component trustworthy as *infrastructure*: a stable identity that survives a process
boundary, a manifest that cannot leak runtime or secret fields, budgets that actually
stop the work, inputs that are never mutated, and a module that cannot quietly start
calling the selector, the registry or the Store.

Every check is stated so that a permissive implementation cannot pass it by accident --
for example by hashing whatever it was handed, or by truncating a payload until it fits.
"""

from __future__ import annotations

import ast
import copy
import json
import math
import os
import pathlib
import subprocess
import sys
import types

import pytest
from fixtures.document_understanding_decision_dependencies import builders as b

from .wire_contract import (
    DEFAULT_LIMITS,
    FORBIDDEN_FIELD_NAMES,
    assert_comparison_shape,
    assert_frozen_shape,
    import_decision_module,
    keys_of,
)

PACKAGE_DIR = pathlib.Path(import_decision_module().__file__).resolve().parent
SRC_ROOT = PACKAGE_DIR.parents[2]

# --- helpers --------------------------------------------------------------------------


def _freeze(trace_value, **limits):
    frozen = import_decision_module().freeze_decision_dependencies(
        trace_value, limits=limits or None
    )
    assert_frozen_shape(frozen)
    return frozen


def _compare(frozen, current, **limits):
    result = import_decision_module().compare_decision_dependencies(
        frozen, current, limits=limits or None
    )
    assert_comparison_shape(result)
    return result


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


# --- 1. determinism, purity, finite JSON ----------------------------------------------


def test_freeze_is_deterministic_across_calls():
    first = _freeze(b.base_trace())
    second = _freeze(b.base_trace())
    assert _canonical(first) == _canonical(second)


def test_compare_is_deterministic_across_calls():
    frozen = _freeze(b.base_trace())
    mutated = b.bump_loser_priority(b.base_trace())
    assert _canonical(_compare(frozen, mutated)) == _canonical(_compare(frozen, mutated))


def test_output_is_finite_json_and_round_trips():
    """No NaN/Infinity may sneak in through a version field or a diagnostic."""
    frozen = _freeze(b.base_trace())
    comparison = _compare(frozen, b.base_trace())
    for payload in (frozen, comparison):
        encoded = _canonical(payload)
        assert "NaN" not in encoded
        assert "Infinity" not in encoded
        assert json.loads(encoded) == json.loads(json.dumps(payload, allow_nan=False))


def test_a_non_finite_algorithm_version_is_rejected():
    trace_value = b.base_trace()
    trace_value["versions"] = {"router": math.nan}
    with pytest.raises((ValueError, TypeError)):
        import_decision_module().freeze_decision_dependencies(trace_value)


def test_inputs_are_never_mutated():
    for name in ("base", "mutated"):
        source = b.base_trace() if name == "base" else b.bump_loser_priority(b.base_trace())
        before = copy.deepcopy(source)
        frozen = _freeze(source)
        assert source == before, f"freeze mutated its {name} trace"
        other = b.base_trace()
        other_before = copy.deepcopy(other)
        _compare(frozen, other)
        assert other == other_before, "compare mutated the current trace"
        frozen_before = copy.deepcopy(frozen)
        _compare(frozen, other)
        assert frozen == frozen_before, "compare mutated the frozen manifest"


# --- 2. cross-process identity ---------------------------------------------------------


def test_decision_digest_is_stable_across_processes():
    """The digest is a content identity, so it must not depend on this interpreter.

    A hash that drifted with PYTHONHASHSEED, dict ordering or a clock would make every
    generation look novel and every cache look stale.
    """
    trace_value = b.base_trace()
    payload = _canonical(trace_value)
    script = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(SRC_ROOT)!r})\n"
        "from company_wiki.document_understanding.decision_dependencies import "
        "freeze_decision_dependencies\n"
        "trace = json.load(sys.stdin)\n"
        "print(json.dumps(freeze_decision_dependencies(trace), sort_keys=True, "
        "separators=(',', ':'), ensure_ascii=False))\n"
    )
    outputs = []
    for _ in range(2):
        run = subprocess.run(
            [sys.executable, "-c", script],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
        )
        assert run.returncode == 0, run.stderr
        child = json.loads(run.stdout)
        outputs.append(child)
    local = _freeze(trace_value)
    assert outputs[0]["decision_digest"] == outputs[1]["decision_digest"] == local["decision_digest"]
    assert _canonical(outputs[0]) == _canonical(local)


def test_array_ordering_does_not_move_the_digest():
    shuffled = copy.deepcopy(b.base_trace())
    shuffled["components"] = list(reversed(shuffled["components"]))
    shuffled["candidates"] = list(reversed(shuffled["candidates"]))
    shuffled["scopes"] = list(reversed(shuffled["scopes"]))
    assert _freeze(b.base_trace())["decision_digest"] == _freeze(shuffled)["decision_digest"]


# --- 2b. the digest must actually cover every identity class ---------------------------
#
# The digest is the natural cache key, so a regression that quietly drops one of its
# inputs would ship green unless each class is pinned separately.


def test_the_decision_digest_covers_every_identity_class():
    base_digest = _freeze(b.base_trace())["decision_digest"]

    def mutate(fn):
        def apply(trace_value):
            fn(trace_value)
            return trace_value

        return apply

    cases = {
        "component content": mutate(
            lambda t: t["components"][0].__setitem__("content_digest", "0" * 63 + "a")
        ),
        "component matcher": mutate(
            lambda t: t["components"][0].__setitem__("matcher_digest", "0" * 63 + "b")
        ),
        "component display version": mutate(
            lambda t: t["components"][0].__setitem__("version", "9.9.9")
        ),
        "component scope membership": mutate(
            lambda t: t["components"][0].__setitem__("scope_ids", ["scope_child"])
        ),
        "scope field": mutate(lambda t: t["scopes"][0].__setitem__("regime", "sec")),
        "scope form_type": mutate(lambda t: t["scopes"][0].__setitem__("form_type", "10-K")),
        "scope purpose": mutate(lambda t: t["scopes"][0].__setitem__("purpose", "other")),
        "algorithm version value": mutate(lambda t: t["versions"].__setitem__("router", "2.0.0")),
        "algorithm version key added": mutate(lambda t: t["versions"].__setitem__("layout", "1")),
        "algorithm version key removed": mutate(lambda t: t["versions"].pop("structure")),
        "candidate eligibility": mutate(
            lambda t: t["candidates"][1].__setitem__("eligible", not t["candidates"][1]["eligible"])
        ),
        "candidate scope": mutate(lambda t: t["candidates"][0].__setitem__("scope_id", "scope_child")),
        "candidate component membership": mutate(
            lambda t: t["candidates"][0].__setitem__("component_ids", ["c1"])
        ),
    }
    for label, apply in cases.items():
        mutated = apply(copy.deepcopy(b.base_trace()))
        assert _freeze(mutated)["decision_digest"] != base_digest, label

    # And the reverse control: reordering is not an identity class.
    reordered = copy.deepcopy(b.base_trace())
    for key in ("scopes", "components", "candidates"):
        reordered[key] = list(reversed(reordered[key]))
    assert _freeze(reordered)["decision_digest"] == base_digest


def test_a_candidate_appearing_or_disappearing_moves_the_digest():
    base_digest = _freeze(b.base_trace())["decision_digest"]
    with_extra = copy.deepcopy(b.base_trace())
    with_extra["candidates"].append(b.candidate("cand_z", scope_id="scope_parent", component_ids=["c3"]))
    assert _freeze(with_extra)["decision_digest"] != base_digest

    without = copy.deepcopy(b.base_trace())
    without["candidates"] = [row for row in without["candidates"] if row["candidate_id"] != "cand_c"]
    assert _freeze(without)["decision_digest"] != base_digest


def test_the_digest_refuses_a_payload_with_missing_identity_fields():
    frozen = _complete_manifest()
    digest = _manifest_digest(frozen)
    for key in ("schema_version", "scopes", "components", "candidates", "versions"):
        trimmed = copy.deepcopy(frozen)
        trimmed.pop(key)
        with pytest.raises(ValueError):
            _manifest_digest(trimmed)
    assert _manifest_digest(frozen) == digest


def test_equal_digests_are_identity_only_and_never_a_verdict():
    """Same rows, different attestation: same identity, different status.

    This is deliberate and documented -- the digest is identity so that the same decision
    reached under a larger budget keeps its key -- but it means a consumer must check
    ``status``. ``compare`` does, and never turns an unattested freeze into ``same``.
    """
    complete = _freeze(b.base_trace())
    incomplete = _freeze({**b.base_trace(), "inventory_complete": False})
    assert complete["decision_digest"] == incomplete["decision_digest"]
    assert complete["status"] == "complete"
    assert incomplete["status"] == "partial"
    assert _compare(incomplete, b.base_trace())["status"] == "unavailable"
    assert _compare(complete, incomplete)["status"] == "unavailable"


# --- 3. nothing but content identity enters the manifest -------------------------------


def test_manifest_and_comparison_carry_no_runtime_or_secret_fields():
    """Paths, run ids, times, costs, timeouts, key names and raw text are not identity."""
    frozen = _freeze(b.base_trace())
    comparison = _compare(frozen, b.bump_loser_priority(b.base_trace()))
    for payload in (frozen, comparison):
        for name in keys_of(payload):
            assert name not in FORBIDDEN_FIELD_NAMES, name


def test_a_tainted_versions_map_cannot_smuggle_runtime_settings_in():
    """The one caller-supplied map must name adopted algorithms, nothing else.

    The manifest's key set is closed, so the only place a runtime setting or a secret
    handle could enter is the ``versions`` mapping. That door is shut by name.
    """
    for bad_key in ("run_id", "timeout", "api_key_env", "absolute_path", "cost_usd", "now"):
        tainted = b.base_trace()
        tainted["versions"] = {**tainted["versions"], bad_key: "value"}
        with pytest.raises((ValueError, TypeError)) as excinfo:
            import_decision_module().freeze_decision_dependencies(tainted)
        assert "runtime setting" in str(excinfo.value), bad_key


def test_manifest_key_set_is_closed():
    """There is no free-form extension slot for a path, a run id or a document body."""
    frozen = _freeze(b.base_trace())
    structural = keys_of(frozen) - set(frozen["versions"])
    assert structural <= {
        "schema_version", "status", "scopes", "components", "candidates", "versions",
        "decision_digest", "diagnostics",
        "scope_id", "regime", "family", "form_type", "purpose",
        "component_id", "version", "content_digest", "matcher_digest", "scope_ids",
        "candidate_id", "component_ids", "eligible", "code", "detail",
    }
    # The only caller-chosen keys are algorithm names inside ``versions``, and those are
    # already screened against runtime/secret field names.
    assert set(frozen["versions"]) == {"router", "selector", "structure"}


def test_a_tainted_trace_leaks_nothing_into_the_manifest(tmp_path):
    """Even a caller that smuggles identity metadata into ids cannot move it into a key."""
    # Built rather than spelled out, so no host-specific literal enters the suite.
    markers = [
        str(tmp_path / "identity-boundary" / "source.pdf"),
        str(pathlib.PureWindowsPath("Z" + ":" + "\\", "identity-boundary", "source.pdf")),
        "du-identity-boundary-do-not-copy",
    ]
    clean = _freeze(b.base_trace())
    tainted = b.base_trace()
    tainted["scopes"][0] = {**tainted["scopes"][0], "scope_id": markers[0]}
    tainted["candidates"] = [
        {**row, "scope_id": markers[0] if row["scope_id"] == "scope_parent" else row["scope_id"]}
        for row in tainted["candidates"]
    ]
    tainted["components"] = [
        {**row,
         "scope_ids": [markers[0] if sid == "scope_parent" else sid for sid in row["scope_ids"]]}
        for row in tainted["components"]
    ]
    frozen = _freeze(tainted)
    assert frozen != clean
    payload = _canonical(frozen)
    for forbidden in FORBIDDEN_FIELD_NAMES:
        assert f'"{forbidden}"' not in payload, forbidden


def test_full_sha256_is_identity_and_short_versions_are_display_only():
    """A truncated digest is never accepted, so a short version can never stand in for it."""
    trace_value = b.base_trace()
    long_digest = trace_value["components"][0]["content_digest"]
    assert len(long_digest) == 64
    frozen = _freeze(trace_value)
    stored = next(
        row for row in frozen["components"] if row["component_id"] == "c1"
    )
    assert stored["content_digest"] == long_digest
    assert stored["version"] == "1.0.0"
    assert len(stored["version"]) < len(stored["content_digest"])

    truncated = copy.deepcopy(trace_value)
    truncated["components"][0]["content_digest"] = long_digest[:8]
    with pytest.raises((ValueError, TypeError)) as excinfo:
        import_decision_module().freeze_decision_dependencies(truncated)
    assert "64-character" in str(excinfo.value)


def test_a_display_version_is_part_of_the_record_but_not_of_the_digest_field():
    """Changing only the display version still moves the manifest, as it must."""
    trace_value = b.base_trace()
    trace_value["components"][0] = {**trace_value["components"][0], "version": "2.0.0"}
    frozen = _freeze(trace_value)
    stored = next(row for row in frozen["components"] if row["component_id"] == "c1")
    assert stored["content_digest"] == b.base_trace()["components"][0]["content_digest"]
    assert _compare(_freeze(b.base_trace()), trace_value)["status"] == "changed"


# --- 4. budgets really stop the work ---------------------------------------------------


def test_the_frozen_defaults_are_the_published_limits():
    assert DEFAULT_LIMITS == {
        "max_scopes": 64,
        "max_components": 512,
        "max_candidates": 4096,
        "max_input_bytes": 2 * 1024 * 1024,
        "max_work_units": 200_000,
    }


def test_zero_work_budget_freezes_partial_and_never_same():
    frozen = _freeze(b.base_trace(), max_work_units=0)
    assert frozen["status"] == "partial"
    assert frozen["diagnostics"]
    assert "WORK_LIMIT_REACHED" in {item["code"] for item in frozen["diagnostics"]}
    assert _compare(frozen, b.base_trace())["status"] != "same"
    assert _compare(_freeze(b.base_trace()), b.base_trace(), max_work_units=0)["status"] != "same"


def test_a_small_byte_cap_freezes_partial_and_never_same():
    frozen = _freeze(b.base_trace(), max_input_bytes=1)
    assert frozen["status"] == "partial"
    assert "BYTES_LIMIT_REACHED" in {item["code"] for item in frozen["diagnostics"]}
    assert _compare(frozen, b.base_trace())["status"] != "same"
    assert _compare(_freeze(b.base_trace()), b.base_trace(), max_input_bytes=1)["status"] != "same"


def test_missing_inventory_never_reports_same():
    for frozen, current in (
        (_freeze(b.base_trace()), {**b.base_trace(), "inventory_complete": False}),
        (_freeze({**b.base_trace(), "inventory_complete": False}), b.base_trace()),
        (_freeze({**b.base_trace(), "inventory_complete": False}),
         {**b.base_trace(), "inventory_complete": False}),
    ):
        assert _compare(frozen, current)["status"] != "same"


def test_every_row_is_charged_against_the_work_budget():
    """A tight but non-zero budget must still stop, and say so."""
    frozen = _freeze(b.base_trace(), max_work_units=3)
    assert frozen["status"] == "partial"
    codes = {item["code"] for item in frozen["diagnostics"]}
    assert "WORK_LIMIT_REACHED" in codes


def test_the_component_budget_is_never_raised_by_a_caller():
    for key, value in (
        ("max_scopes", 65),
        ("max_components", 513),
        ("max_candidates", 4097),
        ("max_input_bytes", 2 * 1024 * 1024 + 1),
        ("max_work_units", 200_001),
    ):
        with pytest.raises(ValueError) as excinfo:
            import_decision_module().freeze_decision_dependencies(b.base_trace(), limits={key: value})
        assert "LIMIT_ABOVE_FROZEN_DEFAULT" in str(excinfo.value)


def test_callers_may_lower_any_limit():
    for key in DEFAULT_LIMITS:
        frozen = _freeze(b.base_trace(), **{key: 0})
        assert frozen["status"] == "partial", key


@pytest.mark.parametrize(
    "limits",
    [
        {"max_scopes": -1},
        {"max_scopes": 1.5},
        {"max_scopes": True},
        {"max_scopes": "64"},
        {"nope": 1},
    ],
)
def test_a_malformed_limit_is_rejected_not_silently_ignored(limits):
    with pytest.raises(ValueError):
        import_decision_module().freeze_decision_dependencies(b.base_trace(), limits=limits)


def test_limits_must_be_a_mapping():
    for bad in (1, "limits", []):
        with pytest.raises((ValueError, TypeError)):
            import_decision_module().freeze_decision_dependencies(b.base_trace(), limits=bad)


# --- 5. reference integrity -------------------------------------------------------------


def test_a_repeated_reference_inside_one_row_is_rejected():
    trace_value = b.base_trace()
    trace_value["components"][0]["scope_ids"] = ["scope_parent", "scope_parent"]
    with pytest.raises((ValueError, TypeError)) as excinfo:
        import_decision_module().freeze_decision_dependencies(trace_value)
    assert "repeats reference" in str(excinfo.value)


def test_a_repeated_component_reference_on_a_candidate_is_rejected():
    trace_value = b.base_trace()
    trace_value["candidates"][0]["component_ids"] = ["c1", "c2", "c1"]
    with pytest.raises((ValueError, TypeError)):
        import_decision_module().freeze_decision_dependencies(trace_value)


def test_a_scope_reference_that_leaves_the_domain_is_rejected():
    trace_value = b.base_trace()
    trace_value["components"][0]["scope_ids"] = ["scope_other_source"]
    with pytest.raises((ValueError, TypeError)) as excinfo:
        import_decision_module().freeze_decision_dependencies(trace_value)
    assert "scope_other_source" in str(excinfo.value)


def test_compare_rejects_a_dangling_reference_on_the_current_side():
    frozen = _freeze(b.base_trace())
    broken = b.base_trace()
    broken["candidates"][0]["component_ids"] = ["ghost"]
    with pytest.raises((ValueError, TypeError)):
        import_decision_module().compare_decision_dependencies(frozen, broken)


# --- 6. type discrimination between manifest and trace -----------------------------------


def test_compare_accepts_a_manifest_on_both_sides():
    frozen = _freeze(b.base_trace())
    twin = _freeze(b.base_trace())
    assert _compare(frozen, twin)["status"] == "same"


def test_compare_tells_the_two_sides_apart_by_schema_version_alone():
    """A trace and a manifest are never distinguished by shape or content."""
    trace_value = b.base_trace()
    frozen = _freeze(trace_value)
    assert _compare(frozen, trace_value)["status"] == "same"
    assert trace_value["schema_version"] == "du-decision-trace/1"
    assert frozen["schema_version"] == "du-decision-dependencies/1"


def test_compare_refuses_an_arbitrary_mapping_as_frozen():
    for bad in (
        {"schema_version": "du-decision-dependencies/2", "status": "complete",
         "scopes": [], "components": [], "candidates": [], "versions": {}},
        {"schema_version": "du-decision-dependencies/1", "status": "invented",
         "scopes": [], "components": [], "candidates": [], "versions": {}},
        {"schema_version": "du-decision-dependencies/1", "status": "complete",
         "scopes": "x", "components": [], "candidates": [], "versions": {}},
        {"schema_version": "du-decision-dependencies/1", "status": "complete"},
        {"status": "complete"},
        {},
    ):
        result = _compare(bad, b.base_trace())
        assert result["status"] == "unavailable", bad
        assert result["diagnostics"], bad


# --- 7. the package cannot reach the rest of the system ---------------------------------

#: Nothing in this package may import the selector, the registry, the Store or any
#: filesystem/network/clock facility. It is a pure content-identity component. The check
#: covers plain imports, ``from x import y`` (including the *imported name*, so
#: ``from company_wiki.document_understanding import profiles`` is caught even though the
#: module string alone looks harmless) and the dynamic escapes.
FORBIDDEN_IMPORTS = {
    "company_wiki.document_understanding.profiles",
    "company_wiki.document_understanding.structure",
    "company_wiki.document_understanding.selection_bridge",
    "company_wiki.document_understanding.summary_input",
    "company_wiki.document_understanding.orchestration",
    "company_wiki.document_understanding.pipeline",
    "company_wiki.document_understanding.layout_hints",
    "company_wiki.document_understanding.strategy_binding",
    "company_wiki.document_understanding.observation_adapter",
    "company_wiki.source_catalog",
    "company_wiki.automation",
    "company_wiki.document_normalization",
    "tools.document_understanding_benchmark",
    "tools.document_normalization_layout_snapshots",
    "os",
    "sys",
    "io",
    "time",
    "datetime",
    "pathlib",
    "sqlite3",
    "socket",
    "ssl",
    "urllib",
    "http",
    "requests",
    "httpx",
    "subprocess",
    "platform",
    "uuid",
    "random",
    "tempfile",
    "shutil",
    "glob",
    "logging",
    "threading",
    "multiprocessing",
    "importlib",
    "pickle",
}


#: Call names that would reach a module without ever naming it in an import statement.
FORBIDDEN_CALLS = {"__import__", "exec", "eval", "compile", "import_module", "run_module"}


def _imported_modules(path: pathlib.Path) -> set[str]:
    """Every module name reachable from this file, including imported *names*.

    ``from a.b import c`` must contribute both ``a.b`` and ``a.b.c``: the second is what
    catches a forbidden submodule pulled in through an innocent-looking parent.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and module:
                found.add(module)
            for alias in node.names:
                found.add(f"{module}.{alias.name}" if module else alias.name)
        elif isinstance(node, ast.Call):
            name = node.func
            target = name.id if isinstance(name, ast.Name) else getattr(name, "attr", "")
            if target in FORBIDDEN_CALLS:
                found.add(f"<dynamic:{target}>")
    return found


def test_the_package_imports_no_selector_registry_store_or_io():
    sources = sorted(PACKAGE_DIR.glob("*.py"))
    assert sources, "the package must have sources to check"
    checked = 0
    for source in sources:
        for module in _imported_modules(source):
            checked += 1
            if module.startswith("<dynamic:"):
                raise AssertionError(f"{source.name} reaches a module dynamically: {module}")
            for forbidden in FORBIDDEN_IMPORTS:
                assert not (module == forbidden or module.startswith(forbidden + ".")), (
                    f"{source.name} imports {module!r}, which is outside this pure component"
                )
    assert checked > 8, f"the guard only saw {checked} import names; it is not reading the package"


def test_the_import_guard_would_reject_a_forbidden_child_import(tmp_path):
    """A guard that cannot fail is not a guard: prove it on a synthetic offender."""
    offender = tmp_path / "_synthetic_offender.py"
    offender.write_text(
        "from company_wiki.document_understanding import profiles  # forbidden\n",
        encoding="utf-8",
    )
    names = _imported_modules(offender)
    assert "company_wiki.document_understanding.profiles" in names, names
    assert any(
        name == "company_wiki.document_understanding.profiles"
        or name.startswith("company_wiki.document_understanding.profiles.")
        for name in names
    ), names


def test_the_import_guard_would_reject_a_dynamic_import(tmp_path):
    offender = tmp_path / "_synthetic_dynamic.py"
    offender.write_text('__import__("os")\n', encoding="utf-8")
    assert "<dynamic:__import__>" in _imported_modules(offender)


def test_the_public_surface_is_exactly_the_two_frozen_functions():
    module = import_decision_module()
    assert set(module.__all__) == {
        "freeze_decision_dependencies",
        "compare_decision_dependencies",
    }
    for name in module.__all__:
        assert callable(getattr(module, name)), name
    for name in ("router", "selector", "registry", "store", "catalog", "read"):
        assert not hasattr(module, name), name


def test_the_package_does_not_call_into_the_selector_at_runtime():
    """Static imports are one guard; exposing no live handle is the other."""
    module = import_decision_module()
    live = {
        name
        for name, value in vars(module).items()
        if not name.startswith("__")
        and name != "annotations"  # bound by ``from __future__ import annotations``
        and not isinstance(value, types.ModuleType)
    }
    assert live == {"compare_decision_dependencies", "freeze_decision_dependencies"}


# --- 9. the budget must bound the WORK, not just the final walk -------------------------


def _wide_domain(rows: int) -> dict:
    """A wide but cheaply built decision domain, straight off the frozen wire shape."""
    return {
        "schema_version": "du-decision-trace/1",
        "scopes": [{"scope_id": "s", "regime": "r", "family": "f", "form_type": None, "purpose": "p"},
                   {"scope_id": "s2", "regime": "r", "family": "g", "form_type": None, "purpose": "q"}],
        "components": [
            {"component_id": f"c{i}", "version": "1.0.0", "content_digest": "0" * 64,
             "matcher_digest": "1" * 64, "scope_ids": ["s"]}
            for i in range(rows)
        ],
        "candidates": [
            {"candidate_id": f"n{i}", "scope_id": "s", "component_ids": [f"c{i}"], "eligible": True}
            for i in range(rows)
        ],
        "versions": {"router": "1.0.0"},
        "inventory_complete": True,
    }


def test_the_byte_cap_bounds_the_input_not_only_the_output():
    """A caller may not hand over an input far past ``max_input_bytes`` and get it walked.

    The cap is published as a limit on the input encoding, so an input that exceeds it
    must stop the call, not merely truncate what is written out afterwards.
    """
    import time

    wide = _wide_domain(40_000)
    assert len(_canonical(wide).encode("utf-8")) > 2 * 1024 * 1024
    started = time.perf_counter()
    frozen = _freeze(wide)  # the frozen default max_input_bytes is 2 MiB
    elapsed = time.perf_counter() - started
    assert frozen["status"] == "partial"
    codes = {item["code"] for item in frozen["diagnostics"]}
    assert "BYTES_LIMIT_REACHED" in codes, codes
    # A diagnostic trend, not a fragile millisecond assertion: the point is that the call
    # stops early instead of decoding an over-cap input in full.
    assert elapsed < 3.0, f"freezing an oversized input took {elapsed:.3f}s"
    assert len(frozen["components"]) < 40_000, "the walk must not have reached the end"
    assert _compare(frozen, wide)["status"] != "same"


def test_the_work_budget_stops_the_decode_and_not_only_the_walk():
    """``max_work_units`` must bound decoding too, not just the final manifest walk."""
    import time

    wide = _wide_domain(40_000)
    started = time.perf_counter()
    frozen = _freeze(wide, max_work_units=1)
    elapsed = time.perf_counter() - started
    assert frozen["status"] == "partial"
    assert "WORK_LIMIT_REACHED" in {item["code"] for item in frozen["diagnostics"]}
    assert elapsed < 3.0, f"a one-work-unit freeze of 40k rows took {elapsed:.3f}s"
    assert frozen["components"] == []
    assert _compare(frozen, _wide_domain(2))["status"] != "same"


def test_a_budget_stop_is_never_same():
    for limits in (
        {"max_work_units": 1},
        {"max_work_units": 0},
        {"max_input_bytes": 1},
        {"max_input_bytes": 0},
        {"max_scopes": 1},
        {"max_components": 1},
        {"max_candidates": 1},
    ):
        frozen = _freeze(_wide_domain(50), **limits)
        assert frozen["status"] == "partial", limits
        assert frozen["diagnostics"], limits
        assert _compare(frozen, _wide_domain(50))["status"] != "same", limits


def test_compare_charges_the_manifest_diff_against_the_byte_cap():
    """The diff route has the same accounting as the decode route.

    Two wide manifests that are genuinely equal must not come out ``same`` when the
    caller only authorised a handful of bytes for the comparison.
    """
    frozen = _freeze(_wide_domain(200))
    assert frozen["status"] == "complete"
    assert _compare(frozen, frozen)["status"] == "same"
    starved = _compare(frozen, frozen, max_input_bytes=1)
    assert starved["status"] == "unavailable", starved
    assert starved["diagnostics"], starved
    assert _compare(frozen, frozen, max_work_units=1)["status"] == "unavailable"


def _hand_manifest(rows: int) -> dict:
    """A wide, valid manifest built the way a stored record arrives: by hand.

    ``freeze`` caps its own output at the published row limits, so only a hand-built
    record can be wide enough to make the *validation* pass matter.
    """
    manifest = {
        "schema_version": "du-decision-dependencies/1",
        "status": "complete",
        "scopes": [
            {"scope_id": "s", "regime": "r", "family": "f", "form_type": None, "purpose": "p"}
        ],
        "components": [
            {"component_id": f"c{i}", "version": "1.0.0", "content_digest": "0" * 64,
             "matcher_digest": "1" * 64, "scope_ids": ["s"]}
            for i in range(rows)
        ],
        "candidates": [
            {"candidate_id": f"n{i}", "scope_id": "s", "component_ids": [f"c{i}"], "eligible": True}
            for i in range(rows)
        ],
        "versions": {"router": "1.0.0"},
        "diagnostics": [],
    }
    manifest["decision_digest"] = _manifest_digest(manifest)
    return manifest


def test_the_manifest_validation_pass_is_charged_too():
    """Re-deriving a manifest's digest is work; it must not run for free.

    Validation happens before any diff. Left uncharged it was the one place a wide record
    could spend unbounded time while the caller believed the call was bounded.
    """
    import time

    wide = _hand_manifest(60_000)
    started = time.perf_counter()
    result = _compare(wide, wide, max_work_units=1)
    elapsed = time.perf_counter() - started
    assert result["status"] == "unavailable", result
    assert result["diagnostics"], result
    assert elapsed < 3.0, f"a one-work-unit compare of a wide manifest took {elapsed:.3f}s"


def test_the_manifest_reference_check_is_linear():
    """A wide reference list must not make validation quadratic."""
    import time

    scopes = [
        {"scope_id": f"s{j}", "regime": "r", "family": "f", "form_type": None, "purpose": "p"}
        for j in range(20_000)
    ]
    manifest = {
        "schema_version": "du-decision-dependencies/1",
        "status": "complete",
        "scopes": scopes,
        "components": [
            {"component_id": "c0", "version": "1.0.0", "content_digest": "0" * 64,
             "matcher_digest": "1" * 64,
             "scope_ids": [f"s{j}" for j in range(20_000)]}
        ],
        "candidates": [
            {"candidate_id": "n0", "scope_id": "s0", "component_ids": ["c0"], "eligible": True}
        ],
        "versions": {"router": "1.0.0"},
        "diagnostics": [],
    }
    manifest["decision_digest"] = _manifest_digest(manifest)
    started = time.perf_counter()
    result = _compare(manifest, manifest)
    elapsed = time.perf_counter() - started
    assert result["status"] in {"same", "unavailable"}, result
    assert elapsed < 3.0, f"validating 20k references took {elapsed:.3f}s"


def test_a_reference_heavy_trace_still_fits_the_published_byte_budget():
    """The per-row envelope must not be charged once per reference.

    The row's canonical encoding already carries every reference, so charging an extra
    envelope for each one shrank what fits inside the published ``max_input_bytes`` by an
    order of magnitude -- a real capacity regression behind a conservative-looking count.
    """
    rows = 200
    refs_per_row = 60
    scope_ids = [f"s{j}" for j in range(refs_per_row)]
    trace_value = {
        "schema_version": "du-decision-trace/1",
        "scopes": [
            {"scope_id": name, "regime": "r", "family": "f", "form_type": None, "purpose": "p"}
            for name in scope_ids
        ],
        "components": [
            {"component_id": f"c{i}", "version": "1.0.0", "content_digest": "0" * 64,
             "matcher_digest": "1" * 64, "scope_ids": list(scope_ids)}
            for i in range(rows)
        ],
        "candidates": [
            {"candidate_id": f"n{i}", "scope_id": "s0", "component_ids": [f"c{i}"], "eligible": True}
            for i in range(rows)
        ],
        "versions": {"router": "1.0.0"},
        "inventory_complete": True,
    }
    real_bytes = len(_canonical(trace_value).encode("utf-8"))
    # Comfortably inside the published 2 MiB default: only a per-reference envelope
    # charge would push it over.
    assert real_bytes < 2 * 1024 * 1024, real_bytes
    frozen = _freeze(trace_value)
    assert frozen["status"] == "complete", frozen["diagnostics"]
    assert real_bytes > 100_000, real_bytes


def test_decision_digest_refuses_rows_that_are_not_mappings():
    """Garbage rows must not hash the same as no rows at all."""
    frozen = _complete_manifest()
    digest = _manifest_digest(frozen)
    for bad in (["garbage", 42], [None], [7]):
        for key in ("scopes", "components", "candidates"):
            broken = copy.deepcopy(frozen)
            broken[key] = bad
            with pytest.raises(ValueError):
                _manifest_digest(broken)
    assert _manifest_digest(frozen) == digest


def test_a_manifest_scope_row_with_a_wrong_typed_field_is_unavailable():
    """Scope rows are typed like the trace side: declared strings, not free values."""
    frozen = _complete_manifest()
    corruptions = [
        {"regime": 42},
        {"family": ["x"]},
        {"purpose": True},
        {"form_type": {"y": 1}},
        {"form_type": 7},
    ]
    for changes in corruptions:
        tampered = copy.deepcopy(frozen)
        tampered["scopes"][0].update(changes)
        tampered["decision_digest"] = _manifest_digest(tampered)  # isolate the type check
        result = _compare(frozen, tampered)
        assert result["status"] == "unavailable", changes
        assert result["diagnostics"], changes


# --- 10. a stored manifest is a record: unusable means unavailable, never same ----------


def _complete_manifest() -> dict:
    return _freeze(b.base_trace())


def _with(manifest, **changes) -> dict:
    updated = copy.deepcopy(manifest)
    updated.update(changes)
    return updated


def test_an_unknown_field_in_a_manifest_never_reads_as_same():
    """A field this contract does not define may hold the very change being asked about.

    Dropping it silently would let ``compare`` answer ``same`` over information it never
    looked at. DU3/1: unknown items get an explicit diagnostic.
    """
    frozen = _complete_manifest()
    for payload in (
        {**copy.deepcopy(frozen), "junk": {"hidden": "change"}},
        {**copy.deepcopy(frozen), "selection_summary": "extra"},
    ):
        result = _compare(frozen, payload)
        assert result["status"] == "unavailable", payload.keys()
        assert result["diagnostics"]
        assert _compare(payload, frozen)["status"] == "unavailable"


def test_a_manifest_missing_a_contract_field_is_unavailable():
    frozen = _complete_manifest()
    for key in ("decision_digest", "diagnostics", "scopes", "components", "candidates", "versions"):
        trimmed = copy.deepcopy(frozen)
        trimmed.pop(key)
        result = _compare(frozen, trimmed)
        assert result["status"] == "unavailable", key
        assert _compare(trimmed, frozen)["status"] == "unavailable", key


def test_a_manifest_row_with_an_unknown_field_is_unavailable():
    frozen = _complete_manifest()
    tampered = copy.deepcopy(frozen)
    tampered["components"][0]["extra"] = "value"
    assert _compare(frozen, tampered)["status"] == "unavailable"
    assert _compare(tampered, frozen)["status"] == "unavailable"


def test_a_manifest_with_duplicate_ids_is_unavailable_not_silently_collapsed():
    frozen = _complete_manifest()
    tampered = copy.deepcopy(frozen)
    tampered["components"].append(copy.deepcopy(tampered["components"][0]))
    assert _compare(frozen, tampered)["status"] == "unavailable"
    assert _compare(tampered, tampered)["status"] == "unavailable"


def test_a_manifest_with_dangling_references_is_unavailable():
    frozen = _complete_manifest()
    tampered = copy.deepcopy(frozen)
    tampered["components"][0]["scope_ids"] = ["scope_not_here"]
    assert _compare(frozen, tampered)["status"] == "unavailable"

    tampered = copy.deepcopy(frozen)
    tampered["candidates"][0]["component_ids"] = ["component_not_here"]
    assert _compare(frozen, tampered)["status"] == "unavailable"

    tampered = copy.deepcopy(frozen)
    tampered["candidates"][0]["scope_id"] = "scope_not_here"
    assert _compare(frozen, tampered)["status"] == "unavailable"


def test_a_manifest_with_a_repeated_reference_is_unavailable():
    frozen = _complete_manifest()
    tampered = copy.deepcopy(frozen)
    name = tampered["candidates"][0]["component_ids"][0]
    tampered["candidates"][0]["component_ids"] = [name, name]
    assert _compare(frozen, tampered)["status"] == "unavailable"


def test_a_manifest_with_a_malformed_digest_is_unavailable():
    frozen = _complete_manifest()
    for field in ("content_digest", "matcher_digest"):
        for bad in ("0" * 8, "0" * 63, "Z" * 64, 12345, None):
            tampered = copy.deepcopy(frozen)
            tampered["components"][0][field] = bad
            assert _compare(frozen, tampered)["status"] == "unavailable", (field, bad)


def test_a_manifest_with_wrong_typed_rows_is_unavailable_and_does_not_raise():
    frozen = _complete_manifest()
    corruptions = [
        {"components": [{"component_id": 7}]},
        {"scopes": ["s"]},
        {"candidates": [{"candidate_id": "n", "scope_id": 1, "component_ids": [], "eligible": "yes"}]},
        {"versions": ["router"]},
        {"versions": {"router": 1.5}},
        {"status": 5},
        {"diagnostics": {}},
    ]
    for changes in corruptions:
        tampered = _with(frozen, **changes)
        try:
            result = _compare(frozen, tampered)
        except Exception as error:  # noqa: BLE001 - the point is which error escapes
            raise AssertionError(f"{changes} escaped as {type(error).__name__}: {error}") from error
        assert result["status"] == "unavailable", changes
        assert result["diagnostics"], changes


def test_a_manifest_whose_digest_no_longer_matches_its_rows_is_unavailable():
    """A record whose identity digest is stale or edited must not read as unchanged.

    ``freeze`` writes the digest over the identity rows; a stored manifest that has been
    touched since then is exactly the case where ``same`` would be wrong.
    """
    frozen = _complete_manifest()

    stale = copy.deepcopy(frozen)
    stale["decision_digest"] = "9" * 64
    assert _compare(frozen, stale)["status"] == "unavailable"
    assert _compare(stale, frozen)["status"] == "unavailable"

    # Editing rows without recomputing the digest is exactly the tampered/stale case.
    edited = copy.deepcopy(frozen)
    edited["components"][0]["content_digest"] = "0" * 63 + "a"
    assert _compare(frozen, edited)["status"] == "unavailable"

    # ... while the same edit with the digest honestly recomputed is an ordinary `changed`.
    recomputed = copy.deepcopy(edited)
    recomputed["decision_digest"] = _manifest_digest(recomputed)
    assert _compare(frozen, recomputed)["status"] == "changed"


def _manifest_digest(manifest) -> str:
    from company_wiki.document_understanding.decision_dependencies.freeze import decision_digest

    return decision_digest(manifest)


def test_a_manifest_with_no_participating_component_is_unavailable():
    """Components no candidate ever references show no decision link at all."""
    trace_value = b.trace(
        scopes=[b.scope("scope_parent")],
        components=[b.component("c1", content={"policy": "x"}, matcher={"s": ["y"]},
                                scope_ids=["scope_parent"])],
        candidates=[b.candidate("cand_a", scope_id="scope_parent", component_ids=[])],
        versions=b.VERSIONS,
    )
    frozen = _freeze(trace_value)
    assert frozen["status"] == "partial"
    assert "NO_PARTICIPATING_COMPONENT" in {item["code"] for item in frozen["diagnostics"]}
    assert _compare(frozen, trace_value)["status"] == "unavailable"
    assert _compare(frozen, frozen)["status"] == "unavailable"


def test_compare_reports_changes_between_two_manifests_not_only_against_a_trace():
    """The manifest-vs-manifest route is the one a cache actually takes.

    Every earlier ``changed`` case handed a *trace* as ``current``; this walks the same
    mutations through two frozen manifests so neither route can rot unnoticed.
    """
    frozen = _complete_manifest()
    cases = {
        "loser component content": lambda t: t["components"][1].__setitem__(
            "content_digest", "0" * 63 + "a"
        ),
        "loser component matcher": lambda t: t["components"][1].__setitem__(
            "matcher_digest", "0" * 63 + "b"
        ),
        "eligibility flip": lambda t: t["candidates"][1].__setitem__(
            "eligible", not t["candidates"][1]["eligible"]
        ),
        "candidate membership": lambda t: t["candidates"][0].__setitem__("component_ids", ["c1"]),
        "child scope purpose": lambda t: t["scopes"][1].__setitem__("purpose", "changed"),
        "algorithm version": lambda t: t["versions"].__setitem__("selector", "9.9.9"),
    }
    for label, mutate in cases.items():
        changed_trace = copy.deepcopy(b.base_trace())
        mutate(changed_trace)
        current = _freeze(changed_trace)
        result = _compare(frozen, current)
        assert result["status"] == "changed", label
        assert result["diagnostics"] or result["changed_component_ids"], label

    added = copy.deepcopy(b.base_trace())
    added["candidates"].append(b.candidate("cand_z", scope_id="scope_parent", component_ids=["c3"]))
    assert _compare(frozen, _freeze(added))["added_candidate_ids"] == ["cand_z"]

    removed = copy.deepcopy(b.base_trace())
    removed["candidates"] = [row for row in removed["candidates"] if row["candidate_id"] != "cand_c"]
    assert _compare(frozen, _freeze(removed))["removed_candidate_ids"] == ["cand_c"]


# --- 11. 100-source manifest encoding size -----------------------------------------------


def _synthetic_source(index: int) -> dict:
    scopes = [b.scope(f"s{index}-parent")]
    if index % 3 == 0:
        scopes.append(b.scope(f"s{index}-child", purpose="business_review"))
    components = [
        b.component(
            f"s{index}-c{position}",
            version=f"1.{position}.0",
            content={"policy": f"policy-{position}", "priority": position},
            matcher={"signals": [f"signal-{position}", f"经营信号{position}"]},
            scope_ids=[scopes[0]["scope_id"]],
        )
        for position in range(4)
    ]
    candidates = [
        b.candidate(
            f"s{index}-cand{position}",
            scope_id=scopes[0]["scope_id"],
            component_ids=[f"s{index}-c{position % 4}", f"s{index}-c{(position + 1) % 4}"],
            eligible=position % 2 == 0,
        )
        for position in range(6)
    ]
    return b.trace(scopes=scopes, components=components, candidates=candidates, versions=b.VERSIONS)


def test_100_source_manifest_encoding_is_bounded_and_measured(capsys, tmp_path):
    """Serialised size is measured, not assumed -- and it is not allowed to grow with runs."""
    module = import_decision_module()
    sizes = []
    for index in range(100):
        frozen = module.freeze_decision_dependencies(_synthetic_source(index))
        assert frozen["status"] == "complete", index
        sizes.append(len(_canonical(frozen).encode("utf-8")))
    total = sum(sizes)
    report = {
        "report_schema": "du3-dependencies-size-report/1",
        "sources": len(sizes),
        "total_bytes": total,
        "mean_bytes": round(total / len(sizes), 1),
        "max_bytes": max(sizes),
        "min_bytes": min(sizes),
        "shape_per_source": {"scopes": 2, "components": 4, "candidates": 6},
    }
    print("DU3-DEP-SIZE " + json.dumps(report, sort_keys=True))
    emitted = [line for line in capsys.readouterr().out.splitlines() if line.startswith("DU3-DEP-SIZE ")]
    assert emitted, "the size report must be emitted for the node receipt"
    assert json.loads(emitted[0][len("DU3-DEP-SIZE "):]) == report
    out = os.environ.get("DU3_DEP_SIZE_REPORT") or str(tmp_path / "b_size_report.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, sort_keys=True, indent=1)
    # A decision manifest is a compact identity record: ids, versions and two digests per
    # component. Anything approaching the 2 MiB input budget per source would mean the
    # manifest is carrying content it must not carry.
    assert max(sizes) < 8192, report
    assert total < 1024 * 1024, report
    assert report["mean_bytes"] < 4096, report
