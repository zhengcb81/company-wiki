"""Small, independently tested reporting and isolation primitives."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import shutil
import stat
import tempfile


STATES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "NOT_APPLICABLE"}


def format_capability_gap(receipt, *, images_only_checked=False):
    """A proved, unpublished capability gap stays BLOCKED, never PASS.

    Invalid bytes, extraction bugs, arbitrary message text and a published
    artifact with a failed receipt are failures, not capability exclusions.
    """
    known = {"SOURCE_LANGUAGE_UNDETERMINED", "SOURCE_LANGUAGE_PDF_UNAVAILABLE",
             "SOURCE_LANGUAGE_UNSUPPORTED_MIME"}
    documents = receipt.get("documents")
    unpublished = (isinstance(documents, list) and bool(documents)
                   and all(isinstance(row, dict) and row.get("artifact_ref") is None for row in documents))
    if receipt.get("status") in {"failed", "partial"} and unpublished:
        if receipt.get("status") == "failed" and receipt.get("error") in known:
            return receipt["error"]
        if receipt.get("error") is not None:
            return None
        errors = set()
        for row in documents:
            codes = row.get("errors", [])
            if not isinstance(codes, list) or not all(isinstance(code, str) for code in codes):
                return None
            errors.update(codes)
        if (images_only_checked and "PARSER_INCOMPLETE" in errors
                and errors <= {"PARSER_INCOMPLETE", "DEPENDENCY_TERMINAL"}):
            return "PARSER_INCOMPLETE"
    return None


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def safe_child(root, relative):
    if Path(relative).is_absolute() or PureWindowsPath(relative).drive or ".." in Path(relative).parts:
        raise ValueError("path escapes owned root")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()) or target == root.resolve():
        raise ValueError("path escapes owned root")
    return target


@contextmanager
def isolated_directory(parent=None):
    """Remove only the random directory we created, including on assertion failure."""
    if parent is not None:
        Path(parent).mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="cmrf-", dir=parent)).resolve()
    marker = root / ".cross-market-suite-owned"
    marker.write_text("cross-market-suite/1", encoding="utf-8")
    try:
        yield root
    finally:
        # Reject replaced symlinks/reparse points before recursive Windows cleanup.
        assert not root.is_symlink() and not getattr(root.lstat(), "st_file_attributes", 0) & 0x400
        assert marker.read_text(encoding="utf-8") == "cross-market-suite/1"
        for path in root.rglob("*"):
            assert not path.is_symlink() and not getattr(path.lstat(), "st_file_attributes", 0) & 0x400
        def remove_readonly(function, path, _error):
            target = Path(path).resolve()
            assert target.is_relative_to(root) and not Path(path).is_symlink()
            target.chmod(stat.S_IWRITE | stat.S_IREAD)
            function(path)
        for child in root.iterdir():
            if child == marker:
                continue
            if child.is_dir():
                shutil.rmtree(child, onerror=remove_readonly)
            else:
                try:
                    child.unlink()
                except PermissionError:
                    child.chmod(stat.S_IWRITE | stat.S_IREAD)
                    child.unlink()
        marker.unlink()
        root.rmdir()
        assert not root.exists()


def summarize(checks):
    states = {row["status"] for row in checks}
    if not states <= STATES:
        raise ValueError("unknown checkpoint state")
    if "FAIL" in states:
        return "FAIL"
    if not checks or states & {"BLOCKED", "NOT_RUN"}:
        return "PARTIAL"
    return "PASS"


def compare_reports(before, after):
    fields = ("mode", "spec_sha256", "checkpoints_sha256", "suite")
    incompatible = [field for field in fields if before.get(field) != after.get(field)]
    result = {"comparable": not incompatible, "incompatible_fields": incompatible, "changes": [], "observations": []}
    if incompatible:
        return result
    old = {(r["case"], r["id"]): r for r in before["checks"]}
    new = {(r["case"], r["id"]): r for r in after["checks"]}
    if len(old) != len(before["checks"]) or len(new) != len(after["checks"]):
        raise ValueError("duplicate checkpoint key")
    for key in sorted(old.keys() | new.keys()):
        a, b = old.get(key), new.get(key)
        if b is None:
            change = "missing"
        elif a is None:
            change = "added"
        elif a["status"] == b["status"]:
            change = "unchanged"
        elif a["status"] != "PASS" and b["status"] == "PASS":
            change = "improved"
        elif a["status"] == "PASS":
            change = "regressed"
        else:
            change = "changed_unresolved"
        result["changes"].append({"case": key[0], "id": key[1], "change": change,
                                  "before": a["status"] if a else None,
                                  "after": b["status"] if b else None})
    # Timings are observations, never an automatic quality/efficiency improvement.
    for field in ("seconds", "test_tree_final_bytes_before_cleanup", "external_model_calls", "project_llm_cost_usd"):
        if field in before and field in after:
            result["observations"].append({"metric": field, "before": before[field], "after": after[field]})
    for key in sorted(old.keys() & new.keys()):
        for field in ("span_count", "local_model_posts", "repeat_model_posts"):
            if field in old[key] and field in new[key]:
                result["observations"].append({"case": key[0], "checkpoint": key[1], "metric": field,
                                               "before": old[key][field], "after": new[key][field]})
    return result


def domain_checks(data, expected):
    """Frozen facts/semantic boundaries from independent reviews, not engine snapshots."""
    assert data["as_of_date"] == expected["as_of_date"], "as-of changed"
    assert [s["name"] for s in data["segments"]] == expected["segment_names"], "segment perimeter"
    params = {p["parameter_id"]: p for p in data["parameters"]}
    for key, fields in expected["parameters"].items():
        for field, value in fields.items():
            assert params[key][field] == value, f"parameter {key}/{field}"
    sensitivities = {s["parameter_id"]: s for s in data["sensitivity_tests"]}
    for key, fields in expected["sensitivities"].items():
        for field, value in fields.items():
            assert sensitivities[key][field] == value, f"shock {key}/{field}"
    nodes = {n["evidence_id"]: n for d in data["growth_driver_tree"]["drivers"] for n in d["evidence_nodes"]}
    for key, distance in expected.get("evidence_distances", {}).items():
        assert nodes[key]["inference_distance"] == distance, f"evidence {key}"
    targets = {t["target_id"]: t for t in data["management_targets"]}
    for key, fields in expected.get("target_fields", {}).items():
        for field, value in fields.items():
            assert targets[key].get(field) == value, f"target {key}/{field}"


def arithmetic_checks(data, result):
    """Recalculate bridge and requested shocks without calling the forecast engine."""
    for scenario, total in result["consolidated_forecast"].items():
        for year, value in total["annual_revenue"].items():
            parts = sum(row["annual_revenue"][year] for row in total["segment_bridge"])
            adjustment = total["adjustment_total"][year]
            assert math.isclose(value, parts + adjustment, rel_tol=1e-10, abs_tol=1e-7), scenario
    params = {p["parameter_id"]: p["value"] for p in data["parameters"]}
    specs = {s["parameter_id"]: s for s in data["sensitivity_tests"]}
    for row in result["sensitivities"]:
        spec, value = specs[row["parameter_id"]], params[row["parameter_id"]]
        delta = value * spec["shock_value"] if spec["shock_type"] == "percent" else spec["shock_value"]
        for side, sign in (("down", -1), ("up", 1)):
            assert math.isclose(row["requested_values"][side], value + sign * delta, abs_tol=1e-10)
