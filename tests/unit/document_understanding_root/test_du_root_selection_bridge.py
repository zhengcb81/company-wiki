"""ROOT tests for the selection bridge: dependency closure and negation safety."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding.selection_bridge import (  # noqa: E402
    CODE_CONTEXT_RESTORED,
    CODE_NEGATION_PROTECTED,
    dependency_closure,
    package_for_unit,
)


def _packages(*specs):
    return {
        "schema_version": "du-packages/1",
        "packages": [
            {
                "package_id": spec["package_id"],
                "kind": spec.get("kind", "project"),
                "member_unit_ids": list(spec["members"]),
                "anchor_unit_ids": [spec["members"][0]],
                "required_context_unit_ids": list(spec.get("required", ())),
                "completeness": spec.get("completeness", "complete"),
                "section_role": spec.get("section_role", "unknown"),
                "diagnostics": [],
                "truncated": False,
                "priority": 3,
                "section_ids": [],
            }
            for spec in specs
        ],
    }


def test_selection_is_never_reduced() -> None:
    packages = _packages(
        {"package_id": "m1", "members": ["u1", "u2", "u3"], "required": ["u2"]}
    )
    result = dependency_closure(["u1", "u9"], packages, {})
    assert set(["u1", "u9"]) <= set(result["selected_unit_ids"])


def test_required_context_is_restored_for_a_partially_selected_package() -> None:
    packages = _packages(
        {"package_id": "m1", "members": ["row1", "cap1", "hdr1"], "required": ["cap1", "hdr1"]}
    )
    result = dependency_closure(["row1"], packages, {})
    assert set(result["added_unit_ids"]) == {"cap1", "hdr1"}
    assert any(item["code"] == CODE_CONTEXT_RESTORED for item in result["diagnostics"])


def test_context_is_not_added_when_the_package_is_untouched() -> None:
    packages = _packages(
        {"package_id": "m1", "members": ["row1", "cap1"], "required": ["cap1"]}
    )
    result = dependency_closure(["other"], packages, {})
    assert result["added_unit_ids"] == []


def test_negation_is_kept_with_its_package() -> None:
    packages = _packages(
        {
            "package_id": "m1",
            "kind": "qa_exchange",
            "members": ["q1", "a1"],
            "required": ["q1"],
        }
    )
    texts = {"q1": "请问公司是否生产VC？", "a1": "公司现无生产VC的情况。"}
    result = dependency_closure(["q1"], packages, texts)
    assert "a1" in result["selected_unit_ids"]
    assert any(item["code"] == CODE_NEGATION_PROTECTED for item in result["diagnostics"])


def test_negation_detection_does_not_fire_on_plain_text() -> None:
    packages = _packages(
        {"package_id": "m1", "members": ["q1", "a1"], "required": ["q1"]}
    )
    texts = {"q1": "请问公司产能利用率如何？", "a1": "报告期内保持在较高水平。"}
    result = dependency_closure(["q1"], packages, texts)
    assert "a1" not in result["selected_unit_ids"]


def test_added_units_are_bounded_and_reported() -> None:
    packages = _packages(
        {
            "package_id": "m1",
            "members": ["a"] + [f"ctx{i}" for i in range(20)],
            "required": [f"ctx{i}" for i in range(20)],
        }
    )
    result = dependency_closure(["a"], packages, {}, max_added=5)
    assert len(result["added_unit_ids"]) <= 5
    assert any(
        item["code"] == "CONTEXT_BUDGET_EXCEEDED" for item in result["diagnostics"]
    )


def test_selection_order_is_stable_and_deduped() -> None:
    packages = _packages(
        {"package_id": "m1", "members": ["u1", "u2"], "required": ["u2"]}
    )
    result = dependency_closure(["u1", "u1", "u1"], packages, {})
    assert result["selected_unit_ids"] == ["u1", "u2"]


def test_bridge_is_deterministic() -> None:
    packages = _packages(
        {"package_id": "m1", "members": ["u1", "u2"], "required": ["u2"]},
        {"package_id": "m2", "members": ["u3", "u4"], "required": ["u4"]},
    )
    first = json.dumps(dependency_closure(["u1", "u3"], packages, {}), sort_keys=True)
    second = json.dumps(dependency_closure(["u1", "u3"], packages, {}), sort_keys=True)
    assert first == second


def test_package_lookup_finds_the_owner() -> None:
    packages = _packages({"package_id": "m1", "members": ["u1", "u2"], "required": []})
    assert package_for_unit(packages, "u2")["package_id"] == "m1"
    assert package_for_unit(packages, "nope") is None


def test_empty_packages_are_harmless() -> None:
    result = dependency_closure(["u1"], {"packages": []}, {})
    assert result["selected_unit_ids"] == ["u1"]
    assert result["added_unit_ids"] == []
