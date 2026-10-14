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
        # Guard against silently testing the *installed* package instead of this tree.
        assert child["decision_digest"]
        outputs.append(child)
    local = _freeze(trace_value)
    assert outputs[0]["decision_digest"] == outputs[1]["decision_digest"] == local["decision_digest"]
    assert _canonical(outputs[0]) == _canonical(local)


def test_digest_does_not_depend_on_array_ordering_across_processes():
    shuffled = copy.deepcopy(b.base_trace())
    shuffled["components"] = list(reversed(shuffled["components"]))
    shuffled["candidates"] = list(reversed(shuffled["candidates"]))
    shuffled["scopes"] = list(reversed(shuffled["scopes"]))
    assert _freeze(b.base_trace())["decision_digest"] == _freeze(shuffled)["decision_digest"]


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
#: filesystem/network/clock facility. It is a pure content-identity component.
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


def _imported_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                found.add(node.module)
    return found


def test_the_package_imports_no_selector_registry_store_or_io():
    sources = sorted(PACKAGE_DIR.glob("*.py"))
    assert sources, "the package must have sources to check"
    for source in sources:
        for module in _imported_modules(source):
            for forbidden in FORBIDDEN_IMPORTS:
                assert not (module == forbidden or module.startswith(forbidden + ".")), (
                    f"{source.name} imports {module!r}, which is outside this pure component"
                )


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


# --- 8. 100-source manifest encoding size -----------------------------------------------


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
