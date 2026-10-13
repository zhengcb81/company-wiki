"""du2-family-index/1 覆盖清单不变量：每个文档形态独立状态，不能只列 profile 名。"""
from __future__ import annotations

from _support import (
    INDEX_EVIDENCE_STATUS, INDEX_SCHEMA, INDEX_SPEC_STATUS,
    INTEGRATION_STATUS, load_cases, load_json, load_records, INDEX_PATH,
    PKG_ROOT,
)

COVERAGE_REQUIRED = ["shape", "spec_status", "evidence_status", "integration_status", "case_ids", "gaps"]


def test_index_exists_and_schema():
    assert INDEX_PATH.exists(), "index.json 必须存在"
    index = load_json(INDEX_PATH)
    assert index["schema_version"] == INDEX_SCHEMA
    assert index["records"], "records 相对路径列表非空"
    for rel in index["records"]:
        path = PKG_ROOT / rel
        assert path.exists(), f"index.records 引用不存在的文件 {rel}"
        assert path.suffix == ".json"


def test_coverage_entries_have_independent_status():
    index = load_json(INDEX_PATH)
    cases = load_cases()
    coverage = index["coverage"]
    assert coverage
    shapes = [c["shape"] for c in coverage]
    assert len(shapes) == len(set(shapes)), "coverage.shape 唯一"
    for entry in coverage:
        missing = [f for f in COVERAGE_REQUIRED if f not in entry]
        assert not missing, f"coverage[{entry.get('shape')}] 缺字段 {missing}"
        assert entry["shape"].strip()
        assert entry["spec_status"] in INDEX_SPEC_STATUS
        assert entry["evidence_status"] in INDEX_EVIDENCE_STATUS
        assert entry["integration_status"] in INTEGRATION_STATUS
        assert isinstance(entry["gaps"], list)
        for cid in entry["case_ids"]:
            assert cid in cases, f"coverage[{entry['shape']}] 引用不存在的 case {cid}"
        if not entry["case_ids"]:
            assert entry["gaps"], f"coverage[{entry['shape']}] 无样本时 gaps 必须写明缺什么"
        if entry["evidence_status"] == "real":
            real_kinds = [cases[cid]["kind"] for cid in entry["case_ids"]]
            assert "real_excerpt" in real_kinds, f"coverage[{entry['shape']}] 标 real 必须有真实摘录 case"
        if entry["evidence_status"] == "synthetic_only":
            assert entry["case_ids"], "synthetic_only 也要列出合成 case"


def test_every_record_shape_registered():
    index = load_json(INDEX_PATH)
    records = load_records()
    shapes = {c["shape"] for c in index["coverage"]}
    for rid in records:
        assert rid in shapes, f"规格 {rid} 必须在 index.coverage 独立登记"
    assert len(index["coverage"]) >= len(records), (
        "coverage 要逐形态登记，不能少于规格数量（不能只列 profile 名）"
    )


def test_evidence_status_agrees_with_records():
    index = load_json(INDEX_PATH)
    records = load_records()
    cases = load_cases()
    by_shape = {c["shape"]: c for c in index["coverage"]}
    for rid, rec in records.items():
        entry = by_shape[rid]
        real_cases = [cid for cid in rec["case_ids"] if cases[cid]["kind"] == "real_excerpt"]
        if real_cases:
            assert entry["evidence_status"] == "real", f"{rid} 有真实样本必须标 real"
        else:
            assert entry["evidence_status"] in {"synthetic_only", "missing"}, (
                f"{rid} 无真实样本不得标 real"
            )
        assert entry["spec_status"] == "implemented", f"{rid} 已写完规格应标 implemented"
